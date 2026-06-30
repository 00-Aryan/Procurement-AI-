from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

import numpy as np
from pydantic import BaseModel, Field, ValidationError, model_validator

try:
    from sklearn.ensemble import IsolationForest
except ImportError:
    IsolationForest = None


class ProcurementAnomalyEngineError(Exception):
    """Raised when anomaly model construction or scoring cannot be completed."""


class TransactionFeatures(BaseModel):
    price_per_unit: float = Field(..., ge=0.0)
    total_value: float = Field(..., ge=0.0)
    vendor_node_id: str = Field(..., min_length=1)
    target_value: float = 0.0
    item_key: str | None = None
    negotiated_rate: float | None = Field(default=None, ge=0.0)
    explicit_off_contract: bool = False

    @model_validator(mode="after")
    def validate_finite_values(self) -> "TransactionFeatures":
        for field_name in ("price_per_unit", "total_value", "target_value"):
            if not np.isfinite(getattr(self, field_name)):
                raise ValueError(f"{field_name} must be finite")
        if self.negotiated_rate is not None and not np.isfinite(self.negotiated_rate):
            raise ValueError("negotiated_rate must be finite")
        return self


class ProcurementAnomalyEngine:
    """
    Tenant-local anomaly scoring for procurement transactions.

    Historical records are supplied by the caller after tenant isolation has
    already been enforced by the database/session layer.
    """

    DEFAULT_FIELD_ALIASES = {
        "price_per_unit": ("price_per_unit", "unit_price", "rate", "quoted_rate"),
        "quantity": ("quantity", "qty", "units"),
        "total_value": ("total_value", "amount", "bid_amount", "order_value", "contract_value"),
        "vendor_node_id": (
            "vendor_node_id",
            "vendor_id",
            "seller_node_id",
            "supplier_node_id",
            "source_node_id",
            "seller_id",
            "supplier_id",
        ),
        "item_key": ("item_id", "sku", "category_id", "catalog_item_id", "item_code"),
        "negotiated_rate": ("negotiated_rate", "contract_rate", "corporate_rate"),
        "target_value": ("is_maverick_spend", "maverick_spend", "is_anomaly", "off_contract"),
        "off_contract": ("off_contract", "is_off_contract"),
        "contract_status": ("contract_status", "vendor_contract_status"),
    }

    def __init__(
        self,
        historical_records: Iterable[dict[str, Any]],
        contract_vendor_nodes: Iterable[str] | None = None,
        negotiated_rates: dict[str, float] | None = None,
        field_aliases: dict[str, Iterable[str]] | None = None,
        negotiated_rate_tolerance: float = 0.25,
        contamination: str | float = "auto",
        random_state: int = 42,
    ) -> None:
        if IsolationForest is None:
            raise ProcurementAnomalyEngineError(
                "scikit-learn is required for ProcurementAnomalyEngine; install scikit-learn to use IsolationForest."
            )
        if not 0.0 <= negotiated_rate_tolerance <= 1.0:
            raise ProcurementAnomalyEngineError("negotiated_rate_tolerance must be between 0.0 and 1.0.")

        self.field_aliases = self._merge_aliases(field_aliases)
        self.negotiated_rate_tolerance = negotiated_rate_tolerance
        self.negotiated_rates = {str(k): float(v) for k, v in (negotiated_rates or {}).items()}
        self.contract_vendor_nodes = {str(v) for v in contract_vendor_nodes or ()}
        self.global_vendor_encoding = 0.0
        self.vendor_target_encoding: dict[str, float] = {}
        self.model = IsolationForest(contamination=contamination, random_state=random_state)

        records = [self._extract_features(record) for record in historical_records]
        if not records:
            raise ProcurementAnomalyEngineError("At least one historical transaction record is required.")

        inferred_contract_nodes = {
            record.vendor_node_id for record in records if not record.explicit_off_contract
        }
        if not self.contract_vendor_nodes:
            self.contract_vendor_nodes = inferred_contract_nodes

        self._fit_vendor_target_encoding(records)
        matrix = self._feature_matrix(records)
        self.model.fit(matrix)

    def _merge_aliases(self, field_aliases: dict[str, Iterable[str]] | None) -> dict[str, tuple[str, ...]]:
        aliases = {key: tuple(value) for key, value in self.DEFAULT_FIELD_ALIASES.items()}
        if field_aliases:
            for key, value in field_aliases.items():
                aliases[key] = tuple(value)
        return aliases

    def _flatten_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        flattened = dict(data)
        for nested_key in ("industry_attributes", "dynamic_manifest"):
            nested_value = data.get(nested_key)
            if isinstance(nested_value, dict):
                flattened.update({k: v for k, v in nested_value.items() if k not in flattened})
        return flattened

    def _first_present(self, data: dict[str, Any], key: str) -> Any:
        for alias in self.field_aliases.get(key, (key,)):
            if alias in data and data[alias] is not None:
                return data[alias]
        return None

    def _extract_features(self, data: dict[str, Any]) -> TransactionFeatures:
        try:
            flattened_data = self._flatten_payload(data)
            total_value = self._first_present(flattened_data, "total_value")
            quantity = self._first_present(flattened_data, "quantity")
            price_per_unit = self._first_present(flattened_data, "price_per_unit")
            if price_per_unit is None and total_value is not None and quantity is not None:
                quantity_value = float(quantity)
                if quantity_value <= 0.0:
                    raise ProcurementAnomalyEngineError("quantity must be positive when deriving price_per_unit.")
                price_per_unit = float(total_value) / quantity_value

            vendor_node_id = self._first_present(flattened_data, "vendor_node_id")
            if vendor_node_id is None:
                raise ProcurementAnomalyEngineError("vendor_node_id is required.")

            item_key = self._first_present(flattened_data, "item_key")
            negotiated_rate = self._first_present(flattened_data, "negotiated_rate")
            contract_status = self._first_present(flattened_data, "contract_status")
            explicit_off_contract = bool(self._first_present(flattened_data, "off_contract") or False)
            if contract_status is not None:
                explicit_off_contract = explicit_off_contract or str(contract_status).lower() in {
                    "off_contract",
                    "non_contract",
                    "uncontracted",
                }
            target_value = self._first_present(flattened_data, "target_value")
            if target_value is None:
                target_value = total_value or 0.0

            return TransactionFeatures(
                price_per_unit=price_per_unit,
                total_value=total_value,
                vendor_node_id=str(vendor_node_id),
                target_value=float(target_value),
                item_key=str(item_key) if item_key is not None else None,
                negotiated_rate=float(negotiated_rate) if negotiated_rate is not None else None,
                explicit_off_contract=explicit_off_contract,
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise ProcurementAnomalyEngineError(f"Invalid transaction feature payload: {exc}") from exc

    def _fit_vendor_target_encoding(self, records: list[TransactionFeatures]) -> None:
        grouped_targets: dict[str, list[float]] = defaultdict(list)
        all_targets = []
        for record in records:
            grouped_targets[record.vendor_node_id].append(record.target_value)
            all_targets.append(record.target_value)

        self.global_vendor_encoding = float(np.mean(all_targets)) if all_targets else 0.0
        self.vendor_target_encoding = {
            vendor_node_id: float(np.mean(targets))
            for vendor_node_id, targets in grouped_targets.items()
        }

    def _vendor_encoding(self, vendor_node_id: str) -> float:
        return self.vendor_target_encoding.get(vendor_node_id, self.global_vendor_encoding)

    def _feature_matrix(self, records: list[TransactionFeatures]) -> np.ndarray:
        rows = [
            [record.price_per_unit, record.total_value, self._vendor_encoding(record.vendor_node_id)]
            for record in records
        ]
        matrix = np.asarray(rows, dtype=float)
        if matrix.ndim != 2 or matrix.shape[1] != 3 or not np.isfinite(matrix).all():
            raise ProcurementAnomalyEngineError("Feature matrix must be finite with shape (n_records, 3).")
        return matrix

    def _lookup_negotiated_rate(self, record: TransactionFeatures) -> float | None:
        if record.negotiated_rate is not None:
            return record.negotiated_rate
        candidate_keys = [record.vendor_node_id]
        if record.item_key:
            candidate_keys.extend(
                [
                    record.item_key,
                    f"{record.vendor_node_id}:{record.item_key}",
                    f"{record.item_key}:{record.vendor_node_id}",
                ]
            )
        for key in candidate_keys:
            if key in self.negotiated_rates:
                return self.negotiated_rates[key]
        return None

    def _rate_deviation(self, record: TransactionFeatures) -> float:
        negotiated_rate = self._lookup_negotiated_rate(record)
        if negotiated_rate is None or negotiated_rate <= 0.0:
            return 0.0
        return abs(record.price_per_unit - negotiated_rate) / negotiated_rate

    async def score_transaction(self, transaction_data: dict[str, Any]) -> dict[str, Any]:
        record = self._extract_features(transaction_data)
        matrix = self._feature_matrix([record])
        decision_score = float(self.model.decision_function(matrix)[0])
        anomaly_score = max(0.0, -decision_score)
        rate_deviation = self._rate_deviation(record)
        off_contract_vendor = record.explicit_off_contract or record.vendor_node_id not in self.contract_vendor_nodes
        rate_breach = rate_deviation > self.negotiated_rate_tolerance
        model_outlier = decision_score < 0.0

        reason_codes = []
        if off_contract_vendor:
            reason_codes.append("OFF_CONTRACT_VENDOR_NODE")
        if rate_breach:
            reason_codes.append("NEGOTIATED_RATE_DEVIATION")
        if model_outlier:
            reason_codes.append("ISOLATION_FOREST_OUTLIER")

        return {
            "anomaly_score": round(anomaly_score, 6),
            "model_decision_score": round(decision_score, 6),
            "is_maverick_spend": off_contract_vendor or rate_breach or model_outlier,
            "rate_deviation": round(rate_deviation, 6),
            "off_contract_vendor": off_contract_vendor,
            "reason_codes": reason_codes,
        }
