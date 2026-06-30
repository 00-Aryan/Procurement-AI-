from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.anomaly_engine import ProcurementAnomalyEngine
from core.config_parser import load_config
from core.executive_reporter import ExecutiveAIFormatter
from core.reorder_optimizer import SmartReorderOptimizer
from core.scenario_simulator import ProcurementScenarioSimulator
from main import BidSubmission, evaluate_bid, verify_tenant_isolation


VALID_BID_PAYLOAD = {
    "seller_name": "Compliant Contract Seller Alpha",
    "gstin": "20ABCDE1234F1Z5",
    "bank_account_verified": True,
    "years_of_experience": 8.0,
    "bid_amount": 125000.0,
    "vehicle_year": 2024,
}

BASELINE_REORDER_PARAMS = {
    "current_inventory": 50.0,
    "forecast_demand": 80.0,
    "safety_stock": 20.0,
    "lead_time_days": 7,
    "moq": 25.0,
    "holding_cost": 2.0,
    "ordering_cost": 100.0,
}

STRESS_VECTOR = {
    "scenario_name": "inflation_plus_jharkhand_logistics_delay",
    "inflation_rate": 0.08,
    "holding_cost_multiplier": 1.10,
    "lead_time_delay_days": 5,
    "demand_multiplier": 1.15,
}


def _build_historical_transactions() -> list[dict[str, Any]]:
    records = []
    for index in range(1, 51):
        quantity = 10.0 + (index % 5)
        price = 98.0 + (index % 6)
        records.append(
            {
                "vendor_node_id": "seller.contract.alpha",
                "item_id": "catalog.vehicle_hire.standard",
                "quantity": quantity,
                "price_per_unit": price,
                "total_value": quantity * price,
                "negotiated_rate": 100.0,
                "off_contract": False,
            }
        )
    return records


async def _assert_tenant_guard(expected_tenant_id: str) -> None:
    accepted_tenant_id = await verify_tenant_isolation(x_tenant_id=expected_tenant_id)
    assert accepted_tenant_id == expected_tenant_id, "matching X-Tenant-ID must pass tenant guard"

    compromised_tenant_id = str(uuid.uuid4())
    try:
        await verify_tenant_isolation(x_tenant_id=compromised_tenant_id)
    except HTTPException as exc:
        assert exc.status_code == 403, "compromised tenant UUID must fail with HTTP 403"
        assert "Tenant access forbidden" in str(exc.detail), "tenant guard must return clean handling detail"
    else:
        raise AssertionError("compromised tenant UUID unexpectedly passed tenant guard")


def _assert_score_within_configured_thresholds(score: float, risk_band: str, thresholds: dict[str, float]) -> None:
    assert thresholds, "risk threshold configuration must be present"
    low = float(thresholds.get("low", 0.0))
    critical = float(thresholds.get("critical", 1.0))
    assert low <= score <= 1.0, "composite risk score must stay within normalized scoring bounds"
    assert score < critical or risk_band == "critical", "critical scores must map to the configured critical band"

    sorted_bands = sorted(thresholds.items(), key=lambda item: item[1], reverse=True)
    expected_band = "low"
    for band, threshold in sorted_bands:
        if score >= float(threshold):
            expected_band = band
            break
    assert risk_band == expected_band, "risk band must match configured threshold routing"


async def run_harness() -> str:
    config = load_config(str(PROJECT_ROOT / "industry-config.json"))
    assert config.tenant_profile is not None, "industry-config.json must include tenant_profile"
    assert config.tenant_profile.tenant_name == "Central Coalfields Limited", "must load the CCL tenant profile"
    assert config.risk_engine is not None, "risk engine thresholds must be available"

    tenant_id = config.tenant_profile.tenant_id
    incoming_headers = {"X-Tenant-ID": tenant_id}
    assert incoming_headers["X-Tenant-ID"] == tenant_id, "mock request must carry matching X-Tenant-ID"
    await _assert_tenant_guard(tenant_id)

    valid_bid = BidSubmission(**VALID_BID_PAYLOAD)
    evaluation = await evaluate_bid(valid_bid, tenant_id=tenant_id)
    _assert_score_within_configured_thresholds(
        evaluation.composite_risk_score,
        evaluation.risk_band,
        config.risk_engine.band_thresholds,
    )
    assert evaluation.disqualified is False, "valid transaction must follow normal non-disqualified routing"

    anomaly_engine = ProcurementAnomalyEngine(
        _build_historical_transactions(),
        contract_vendor_nodes={"seller.contract.alpha"},
        negotiated_rates={"catalog.vehicle_hire.standard": 100.0},
        contamination=0.05,
        random_state=7,
    )
    valid_transaction_score = await anomaly_engine.score_transaction(
        {
            "vendor_node_id": "seller.contract.alpha",
            "item_id": "catalog.vehicle_hire.standard",
            "quantity": 12.0,
            "price_per_unit": 101.0,
            "total_value": 1212.0,
            "negotiated_rate": 100.0,
            "off_contract": False,
        }
    )
    anomalous_transaction_score = await anomaly_engine.score_transaction(
        {
            "vendor_node_id": "seller.off_contract.rogue",
            "item_id": "catalog.vehicle_hire.standard",
            "quantity": 15.0,
            "price_per_unit": 450.0,
            "total_value": 6750.0,
            "negotiated_rate": 100.0,
            "off_contract": True,
        }
    )
    assert valid_transaction_score["is_maverick_spend"] is False, "valid contract transaction must not alert"
    assert anomalous_transaction_score["is_maverick_spend"] is True, "off-contract transaction must alert"
    assert "OFF_CONTRACT_VENDOR_NODE" in anomalous_transaction_score["reason_codes"], "off-contract vendor alert missing"
    assert "NEGOTIATED_RATE_DEVIATION" in anomalous_transaction_score["reason_codes"], "rate-deviation alert missing"
    assert "ISOLATION_FOREST_OUTLIER" in anomalous_transaction_score["reason_codes"], "Isolation Forest alert missing"

    optimizer = SmartReorderOptimizer()
    optimization_output = optimizer.calculate_optimal_order(**BASELINE_REORDER_PARAMS)
    assert optimization_output["recommended_order_quantity"] >= BASELINE_REORDER_PARAMS["moq"], "MOQ must be satisfied"
    assert (
        BASELINE_REORDER_PARAMS["current_inventory"] + optimization_output["recommended_order_quantity"]
        >= BASELINE_REORDER_PARAMS["forecast_demand"] + BASELINE_REORDER_PARAMS["safety_stock"]
    ), "demand plus safety stock coverage must be satisfied"

    simulator = ProcurementScenarioSimulator()
    simulation_output = simulator.run_stress_test(BASELINE_REORDER_PARAMS, STRESS_VECTOR)
    assert simulation_output["stressed_order_volume"] >= simulation_output["baseline_order_volume"], "stress should not reduce required order volume"
    assert simulation_output["stockout_hazard_scale"] in {"LOW", "MEDIUM", "HIGH"}, "hazard scale must be normalized"

    telemetry = {
        "tenant_id": tenant_id,
        "tenant_name": config.tenant_profile.tenant_name,
        "gateway": {
            "risk_band": evaluation.risk_band,
            "composite_risk_score": evaluation.composite_risk_score,
            "disqualified": evaluation.disqualified,
        },
        "anomaly": {
            "valid_transaction": valid_transaction_score,
            "anomalous_transaction": anomalous_transaction_score,
        },
        "optimization": optimization_output,
        "simulation": simulation_output,
    }

    anomaly_summary = {
        "flagged_maverick_spend_count": int(anomalous_transaction_score["is_maverick_spend"]),
        "isolation_forest_scores": [
            valid_transaction_score["model_decision_score"],
            anomalous_transaction_score["model_decision_score"],
        ],
        "anomaly_scores": [
            valid_transaction_score["anomaly_score"],
            anomalous_transaction_score["anomaly_score"],
        ],
        "reason_codes": anomalous_transaction_score["reason_codes"],
    }
    report = ExecutiveAIFormatter().generate_executive_brief(
        anomaly_summary,
        optimization_output,
        simulation_output,
    )
    assert report.startswith("# Executive Procurement Strategy Brief"), "executive report header missing"
    assert "Maverick spend anomalies flagged" in report, "executive report must include anomaly telemetry"
    assert "Stockout hazard scale" in report, "executive report must include simulation telemetry"

    status = {
        "harness_status": "PASS",
        "tenant_id": tenant_id,
        "risk_band": evaluation.risk_band,
        "maverick_alert": anomalous_transaction_score["is_maverick_spend"],
        "recommended_order_quantity": optimization_output["recommended_order_quantity"],
        "stockout_hazard_scale": simulation_output["stockout_hazard_scale"],
    }
    print(json.dumps(status, indent=2, sort_keys=True))
    print("\n" + report)
    print("## Raw Telemetry")
    print(json.dumps(telemetry, indent=2, sort_keys=True, default=str))
    return report


def main() -> None:
    asyncio.run(run_harness())


if __name__ == "__main__":
    main()
