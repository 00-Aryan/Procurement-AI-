from __future__ import annotations

from typing import Any

import numpy as np
from pydantic import BaseModel, Field, ValidationError, model_validator

from core.reorder_optimizer import ReorderOptimizationError, SmartReorderOptimizer


class ScenarioSimulationError(Exception):
    """Raised when scenario stress-test inputs cannot be evaluated."""


class ReorderBaselineParams(BaseModel):
    current_inventory: float = Field(..., ge=0.0)
    forecast_demand: float = Field(..., ge=0.0)
    safety_stock: float = Field(..., ge=0.0)
    lead_time_days: int = Field(..., ge=0)
    moq: float = Field(..., ge=0.0)
    holding_cost: float = Field(..., ge=0.0)
    ordering_cost: float = Field(..., ge=0.0)

    @model_validator(mode="after")
    def validate_finite_values(self) -> "ReorderBaselineParams":
        for field_name in (
            "current_inventory",
            "forecast_demand",
            "safety_stock",
            "moq",
            "holding_cost",
            "ordering_cost",
        ):
            if not np.isfinite(getattr(self, field_name)):
                raise ValueError(f"{field_name} must be finite")
        return self


class StressFactors(BaseModel):
    demand_multiplier: float = Field(default=1.0, ge=0.0)
    demand_delta: float = 0.0
    lead_time_multiplier: float = Field(default=1.0, ge=0.0)
    lead_time_delay_days: int = Field(default=0, ge=0)
    inflation_rate: float = Field(default=0.0, ge=-0.99)
    holding_cost_multiplier: float = Field(default=1.0, ge=0.0)
    ordering_cost_multiplier: float = Field(default=1.0, ge=0.0)
    inventory_loss_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    inventory_delta: float = 0.0
    safety_stock_multiplier: float = Field(default=1.0, ge=0.0)
    safety_stock_delta: float = 0.0
    moq_multiplier: float = Field(default=1.0, ge=0.0)
    moq_delta: float = 0.0

    @model_validator(mode="after")
    def validate_finite_values(self) -> "StressFactors":
        for field_name, value in self.model_dump().items():
            if not np.isfinite(float(value)):
                raise ValueError(f"{field_name} must be finite")
        return self


class ProcurementScenarioSimulator:
    """Runs deterministic reorder stress tests from baseline inventory parameters."""

    BASELINE_ALIASES = {
        "current_inventory": ("current_inventory", "inventory_on_hand", "on_hand_inventory"),
        "forecast_demand": ("forecast_demand", "demand", "projected_demand"),
        "safety_stock": ("safety_stock", "buffer_stock"),
        "lead_time_days": ("lead_time_days", "lead_time", "supplier_lead_time_days"),
        "moq": ("moq", "minimum_order_quantity"),
        "holding_cost": ("holding_cost", "unit_holding_cost"),
        "ordering_cost": ("ordering_cost", "fixed_ordering_cost"),
    }

    def run_stress_test(self, baseline_params: dict[str, Any], perturbation_matrix: dict[str, Any]) -> dict[str, Any]:
        baseline = self._parse_baseline(baseline_params)
        scenarios = self._scenario_items(perturbation_matrix)
        scenario_results = []

        for scenario_name, scenario_matrix in scenarios:
            stress = self._parse_stress_factors(scenario_matrix)
            stressed = self._apply_perturbations(baseline, stress)
            optimizer = SmartReorderOptimizer()

            try:
                baseline_output = optimizer.calculate_optimal_order(**baseline.model_dump())
                stressed_output = optimizer.calculate_optimal_order(**stressed.model_dump())
            except ReorderOptimizationError as exc:
                raise ScenarioSimulationError(f"Reorder optimization failed during scenario simulation: {exc}") from exc

            baseline_tco = float(baseline_output.get("projected_total_cost_of_ownership", 0.0))
            stressed_tco = float(stressed_output.get("projected_total_cost_of_ownership", 0.0))
            baseline_order = float(baseline_output.get("recommended_order_quantity", 0.0))
            stressed_order = float(stressed_output.get("recommended_order_quantity", 0.0))
            cost_delta = stressed_tco - baseline_tco
            stockout = self._stockout_risk(stressed, stress, stressed_order)

            scenario_results.append(
                {
                    "scenario_name": scenario_name,
                    "baseline_parameters": baseline.model_dump(),
                    "stressed_parameters": stressed.model_dump(),
                    "baseline_optimization": baseline_output,
                    "stressed_optimization": stressed_output,
                    "baseline_order_volume": round(baseline_order, 6),
                    "stressed_order_volume": round(stressed_order, 6),
                    "calculated_financial_delta": round(cost_delta, 6),
                    "stockout_hazard_scale": stockout["level"],
                    "deltas": {
                        "recommended_order_quantity_delta": round(stressed_order - baseline_order, 6),
                        "projected_cost_increase": round(cost_delta, 6),
                        "projected_cost_increase_percent": round((cost_delta / baseline_tco) * 100.0, 6) if baseline_tco else 0.0,
                        "lead_time_delta_days": stressed.lead_time_days - baseline.lead_time_days,
                    },
                    "stockout_risk": stockout,
                }
            )

        if len(scenario_results) == 1:
            return scenario_results[0]
        return {
            "baseline_parameters": baseline.model_dump(),
            "scenario_results": scenario_results,
            "highest_stockout_hazard_scale": self._highest_hazard_scale(scenario_results),
        }

    def _scenario_items(self, perturbation_matrix: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        if perturbation_matrix is None:
            return [("default", {})]
        if not isinstance(perturbation_matrix, dict):
            raise ScenarioSimulationError("perturbation_matrix must be a dictionary.")

        matrix = perturbation_matrix.get("scenarios")
        if matrix is None:
            return [(str(perturbation_matrix.get("scenario_name", "default")), perturbation_matrix)]
        if isinstance(matrix, dict):
            return [(str(name), self._ensure_scenario_dict(value, str(name))) for name, value in matrix.items()]
        if isinstance(matrix, list):
            scenarios = []
            for index, value in enumerate(matrix, start=1):
                scenario = self._ensure_scenario_dict(value, f"scenario_{index}")
                scenarios.append((str(scenario.get("scenario_name", f"scenario_{index}")), scenario))
            return scenarios
        raise ScenarioSimulationError("perturbation_matrix['scenarios'] must be a dictionary or list.")

    def _ensure_scenario_dict(self, value: Any, scenario_name: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ScenarioSimulationError(f"Scenario '{scenario_name}' must be a dictionary.")
        return value

    def _parse_baseline(self, baseline_params: dict[str, Any]) -> ReorderBaselineParams:
        if not isinstance(baseline_params, dict):
            raise ScenarioSimulationError("baseline_params must be a dictionary.")
        normalized = {}
        for canonical_key, aliases in self.BASELINE_ALIASES.items():
            for alias in aliases:
                if alias in baseline_params and baseline_params[alias] is not None:
                    normalized[canonical_key] = baseline_params[alias]
                    break
        try:
            return ReorderBaselineParams(**normalized)
        except ValidationError as exc:
            raise ScenarioSimulationError(f"Invalid or missing baseline reorder parameters: {exc}") from exc

    def _parse_stress_factors(self, perturbation_matrix: dict[str, Any]) -> StressFactors:
        if perturbation_matrix is None:
            perturbation_matrix = {}
        if not isinstance(perturbation_matrix, dict):
            raise ScenarioSimulationError("perturbation_matrix must be a dictionary.")
        try:
            return StressFactors(**perturbation_matrix)
        except ValidationError as exc:
            raise ScenarioSimulationError(f"Invalid stress perturbation matrix: {exc}") from exc

    def _apply_perturbations(
        self,
        baseline: ReorderBaselineParams,
        stress: StressFactors,
    ) -> ReorderBaselineParams:
        inflation_factor = 1.0 + stress.inflation_rate
        return ReorderBaselineParams(
            current_inventory=max(
                0.0,
                baseline.current_inventory * (1.0 - stress.inventory_loss_rate) + stress.inventory_delta,
            ),
            forecast_demand=max(0.0, baseline.forecast_demand * stress.demand_multiplier + stress.demand_delta),
            safety_stock=max(0.0, baseline.safety_stock * stress.safety_stock_multiplier + stress.safety_stock_delta),
            lead_time_days=max(
                0,
                int(round(baseline.lead_time_days * stress.lead_time_multiplier + stress.lead_time_delay_days)),
            ),
            moq=max(0.0, baseline.moq * stress.moq_multiplier + stress.moq_delta),
            holding_cost=max(0.0, baseline.holding_cost * inflation_factor * stress.holding_cost_multiplier),
            ordering_cost=max(0.0, baseline.ordering_cost * inflation_factor * stress.ordering_cost_multiplier),
        )

    def _stockout_risk(
        self,
        stressed: ReorderBaselineParams,
        stress: StressFactors,
        recommended_order_quantity: float,
    ) -> dict[str, float | str | list[str]]:
        demand_cover_required = stressed.forecast_demand + stressed.safety_stock
        pre_receipt_gap = max(0.0, demand_cover_required - stressed.current_inventory)
        post_receipt_gap = max(0.0, demand_cover_required - stressed.current_inventory - recommended_order_quantity)
        coverage_ratio = stressed.current_inventory / demand_cover_required if demand_cover_required else 1.0

        if post_receipt_gap > 0.0 or coverage_ratio < 0.8:
            level = "HIGH"
        elif coverage_ratio < 1.0 or (stress.lead_time_delay_days > 0 and coverage_ratio < 1.25):
            level = "MEDIUM"
        else:
            level = "LOW"

        drivers = []
        if stress.demand_multiplier > 1.0 or stress.demand_delta > 0.0:
            drivers.append("demand_stress")
        if stress.lead_time_delay_days > 0 or stress.lead_time_multiplier > 1.0:
            drivers.append("lead_time_stress")
        if stress.inventory_loss_rate > 0.0 or stress.inventory_delta < 0.0:
            drivers.append("inventory_shock")
        if stress.inflation_rate > 0.0:
            drivers.append("cost_inflation")

        return {
            "level": level,
            "pre_receipt_coverage_ratio": round(coverage_ratio, 6),
            "pre_receipt_inventory_gap": round(pre_receipt_gap, 6),
            "post_receipt_inventory_gap": round(post_receipt_gap, 6),
            "drivers": drivers,
        }

    def _highest_hazard_scale(self, scenario_results: list[dict[str, Any]]) -> str:
        rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        highest = "LOW"
        for result in scenario_results:
            scale = str(result.get("stockout_hazard_scale", "LOW"))
            if rank.get(scale, 0) > rank[highest]:
                highest = scale
        return highest
