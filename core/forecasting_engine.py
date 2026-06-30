import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from core.config_parser import ProcurementException, log_and_raise

logger = logging.getLogger("forecasting_engine")


class ForecastingEngineError(ProcurementException):
    """Exception raised during forecasting engine processing."""
    pass


class BusinessInquestContext(BaseModel):
    """Data structure capturing the mapping of scientist scope to business questions."""
    target_business_question: str
    investigating_scientist: str
    target_sku: str


# Foundational baseline question tracking register
FOUNDATIONAL_BASELINE_QUESTION = (
    "What is our baseline financial exposure if consumption patterns remain completely static, "
    "ignoring seasonality?"
)

BUSINESS_INQUEST_REGISTER: List[BusinessInquestContext] = [
    BusinessInquestContext(
        target_business_question=FOUNDATIONAL_BASELINE_QUESTION,
        investigating_scientist="Lead AI Scientist",
        target_sku="SYSTEM_GLOBAL_BASELINE"
    )
]


class BaselineVelocityModel:
    """Baseline velocity forecasting model using rolling-window averaging."""

    def __init__(self, window_size: int = 3, tenant_id: str = "unknown"):
        self.window_size = window_size
        self.tenant_id = tenant_id
        self.model_version = "v1.0.0-baseline"

    def predict(
        self,
        historical_demand: List[float],
        steps: int = 1,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates forecast predictions and calculates Mean Absolute Error (MAE) against lookbacks.
        """
        active_tenant = tenant_id or self.tenant_id
        scope = "BaselineVelocityModel.predict"

        if not isinstance(historical_demand, list):
            log_and_raise(
                ForecastingEngineError,
                "ERR_FORECAST_INPUT_INVALID",
                active_tenant,
                scope,
                "Historical demand must be a list of numerical values."
            )

        if not historical_demand:
            log_and_raise(
                ForecastingEngineError,
                "ERR_FORECAST_INPUT_EMPTY",
                active_tenant,
                scope,
                "Historical demand list cannot be empty."
            )

        for idx, val in enumerate(historical_demand):
            if not isinstance(val, (int, float)):
                log_and_raise(
                    ForecastingEngineError,
                    "ERR_FORECAST_INPUT_TYPE",
                    active_tenant,
                    scope,
                    f"Non-numerical value at index {idx}: {val}"
                )

        if self.window_size <= 0:
            log_and_raise(
                ForecastingEngineError,
                "ERR_FORECAST_CONFIG_INVALID",
                active_tenant,
                scope,
                f"Window size must be greater than zero, got {self.window_size}"
            )

        n = len(historical_demand)

        # 1. Rolling window average calculation
        recent_window = historical_demand[-self.window_size:] if n >= self.window_size else historical_demand
        baseline_avg = sum(recent_window) / len(recent_window)
        generated_output_matrix = [baseline_avg] * steps

        # 2. Historical lookback error validation (MAE calculation)
        absolute_errors = []
        if n > self.window_size:
            for t in range(self.window_size, n):
                window_data = historical_demand[t - self.window_size:t]
                pred_t = sum(window_data) / self.window_size
                actual_t = historical_demand[t]
                absolute_errors.append(abs(actual_t - pred_t))
            mae = sum(absolute_errors) / len(absolute_errors)
        else:
            mae = 0.0

        return {
            "model_version": self.model_version,
            "generated_output_matrix": generated_output_matrix,
            "evaluation_metrics": {
                "mean_absolute_error": mae,
                "mae": mae,
                "historical_lookback_count": len(absolute_errors)
            }
        }
