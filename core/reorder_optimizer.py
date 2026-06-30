from __future__ import annotations

import numpy as np
from pydantic import BaseModel, Field, model_validator

try:
    from scipy.optimize import linprog
except ImportError:
    linprog = None


class ReorderOptimizationError(Exception):
    """Raised when reorder optimization inputs or solver output are invalid."""


class ReorderInputs(BaseModel):
    current_inventory: float = Field(..., ge=0.0)
    forecast_demand: float = Field(..., ge=0.0)
    safety_stock: float = Field(..., ge=0.0)
    lead_time_days: int = Field(..., ge=0)
    moq: float = Field(..., ge=0.0)
    holding_cost: float = Field(..., ge=0.0)
    ordering_cost: float = Field(..., ge=0.0)

    @model_validator(mode="after")
    def validate_finite_values(self) -> "ReorderInputs":
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


class SmartReorderOptimizer:
    """Computes the lowest-cost feasible reorder quantity for one inventory item."""

    def calculate_optimal_order(
        self,
        current_inventory: float,
        forecast_demand: float,
        safety_stock: float,
        lead_time_days: int,
        moq: float,
        holding_cost: float,
        ordering_cost: float,
    ) -> dict[str, float | int]:
        try:
            inputs = ReorderInputs(
                current_inventory=current_inventory,
                forecast_demand=forecast_demand,
                safety_stock=safety_stock,
                lead_time_days=lead_time_days,
                moq=moq,
                holding_cost=holding_cost,
                ordering_cost=ordering_cost,
            )
        except ValueError as exc:
            raise ReorderOptimizationError(f"Invalid reorder optimization inputs: {exc}") from exc

        required_coverage = max(
            0.0,
            inputs.forecast_demand + inputs.safety_stock - inputs.current_inventory,
        )
        exact_lower_bound = max(inputs.moq, required_coverage, 0.0)
        order_quantity = self._solve_order_quantity(inputs, exact_lower_bound)
        projected_inventory_after_demand = max(
            0.0,
            inputs.current_inventory + order_quantity - inputs.forecast_demand,
        )
        projected_holding_costs = projected_inventory_after_demand * inputs.holding_cost
        projected_tco = projected_holding_costs + (inputs.ordering_cost if order_quantity > 0.0 else 0.0)

        return {
            "recommended_order_quantity": round(order_quantity, 6),
            "execution_date_relative_days": 0 if order_quantity > 0.0 else inputs.lead_time_days,
            "projected_holding_costs": round(projected_holding_costs, 6),
            "projected_total_cost_of_ownership": round(projected_tco, 6),
        }

    def _solve_order_quantity(self, inputs: ReorderInputs, exact_lower_bound: float) -> float:
        if linprog is None:
            return exact_lower_bound

        c = np.asarray([inputs.holding_cost if inputs.holding_cost > 0.0 else 1.0], dtype=float)
        a_ub = np.asarray([[-1.0], [-1.0]], dtype=float)
        b_ub = np.asarray([-inputs.moq, -max(0.0, inputs.forecast_demand + inputs.safety_stock - inputs.current_inventory)], dtype=float)
        if c.shape != (1,) or a_ub.shape != (2, 1) or b_ub.shape != (2,):
            raise ReorderOptimizationError("Linear programming matrices have invalid dimensions.")

        result = linprog(c=c, A_ub=a_ub, b_ub=b_ub, bounds=[(0.0, None)], method="highs")
        if not result.success or result.x is None or len(result.x) != 1:
            raise ReorderOptimizationError(f"Reorder optimization failed: {result.message}")

        quantity = float(result.x[0])
        if not np.isfinite(quantity):
            raise ReorderOptimizationError("Reorder optimization produced a non-finite quantity.")
        return max(quantity, exact_lower_bound)
