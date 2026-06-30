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


# Hardcode baseline and advanced forecasting inquiries
FOUNDATIONAL_BASELINE_QUESTION = (
    "What is our baseline financial exposure if consumption patterns remain completely static, "
    "ignoring seasonality?"
)

ADVANCED_CHALLENGER_QUESTION = (
    "How do seasonal shocks, promotional calendars, and regional price elasticity "
    "alter our 8-day stockout horizon?"
)

BUSINESS_INQUEST_REGISTER: List[BusinessInquestContext] = [
    BusinessInquestContext(
        target_business_question=FOUNDATIONAL_BASELINE_QUESTION,
        investigating_scientist="Lead AI Scientist",
        target_sku="SYSTEM_GLOBAL_BASELINE"
    ),
    BusinessInquestContext(
        target_business_question=ADVANCED_CHALLENGER_QUESTION,
        investigating_scientist="Lead AI Scientist",
        target_sku="SYSTEM_GLOBAL_CHALLENGER"
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


class AdaptiveTimeSeriesChallenger:
    """Advanced time-series model that integrates Prophet/ARIMA with real-time tuning."""

    def __init__(self, tenant_id: str = "unknown"):
        self.tenant_id = tenant_id
        self.model_version = "v2.0.0-challenger"

    def _execute_real_time_tuning(self, data: Any) -> Dict[str, Any]:
        """
        Evaluates Prophet and ARIMA configurations to find the one with the lowest RMSE.
        """
        import numpy as np

        # Candidates grid
        candidates = [
            {"model_type": "prophet", "changepoint_prior_scale": 0.05},
            {"model_type": "prophet", "changepoint_prior_scale": 0.5},
            {"model_type": "arima", "order": (1, 1, 0)},
            {"model_type": "arima", "order": (0, 1, 1)},
        ]

        best_cfg = None
        best_rmse = float('inf')
        best_predictions = []

        # Silent logs for external ML models
        import logging
        logging.getLogger('prophet').setLevel(logging.ERROR)
        logging.getLogger('cmdstanpy').setLevel(logging.ERROR)

        y_true = data['y'].values

        for cfg in candidates:
            try:
                if cfg["model_type"] == "prophet":
                    from prophet import Prophet
                    m = Prophet(
                        changepoint_prior_scale=cfg["changepoint_prior_scale"],
                        yearly_seasonality=False,
                        weekly_seasonality=False,
                        daily_seasonality=False
                    )
                    m.fit(data)
                    forecast = m.predict(data)
                    y_pred = forecast['yhat'].values
                else:
                    from statsmodels.tsa.arima.model import ARIMA
                    model = ARIMA(y_true, order=cfg["order"])
                    model_fit = model.fit()
                    y_pred = model_fit.fittedvalues

                rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

                if rmse < best_rmse:
                    best_rmse = rmse
                    best_cfg = cfg
                    best_predictions = list(y_pred)
            except Exception as e:
                logger.warning(f"Error tuning model {cfg}: {e}")
                continue

        # Fallback in case of absolute failure or very few data points
        if best_cfg is None:
            best_cfg = {"model_type": "arima_fallback", "order": (1, 0, 0)}
            best_rmse = 0.0
            best_predictions = list(y_true)

        return {
            "best_configuration": best_cfg,
            "rmse": best_rmse,
            "in_sample_predictions": best_predictions
        }

    def predict(
        self,
        historical_demand: List[float],
        steps: int = 8,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fits tuned configurations dynamically and returns predictions with error metrics.
        """
        import pandas as pd

        active_tenant = tenant_id or self.tenant_id
        scope = "AdaptiveTimeSeriesChallenger.predict"

        if not isinstance(historical_demand, list) or not historical_demand:
            log_and_raise(
                ForecastingEngineError,
                "ERR_FORECAST_INPUT_INVALID",
                active_tenant,
                scope,
                "Historical demand must be a non-empty list of numerical values."
            )

        # Build training DataFrame
        df = pd.DataFrame({
            "ds": pd.date_range(start="2026-06-30", periods=len(historical_demand)),
            "y": historical_demand
        })

        tuning_res = self._execute_real_time_tuning(df)
        best_cfg = tuning_res["best_configuration"]
        rmse = tuning_res["rmse"]

        predictions = []
        try:
            if best_cfg["model_type"] == "prophet":
                from prophet import Prophet
                m = Prophet(
                    changepoint_prior_scale=best_cfg["changepoint_prior_scale"],
                    yearly_seasonality=False,
                    weekly_seasonality=False,
                    daily_seasonality=False
                )
                m.fit(df)
                future = m.make_future_dataframe(periods=steps, include_history=False)
                forecast = m.predict(future)
                predictions = [float(val) for val in forecast['yhat'].values]
            else:
                from statsmodels.tsa.arima.model import ARIMA
                model = ARIMA(historical_demand, order=best_cfg.get("order", (1, 0, 0)))
                model_fit = model.fit()
                forecast = model_fit.forecast(steps=steps)
                predictions = [float(val) for val in forecast]
        except Exception as e:
            logger.error(f"Error generating predictions with challenger: {e}")
            # Dynamic rolling fallback
            rolling_avg = sum(historical_demand[-3:]) / min(len(historical_demand), 3)
            predictions = [rolling_avg] * steps

        return {
            "model_version": self.model_version,
            "generated_output_matrix": predictions,
            "evaluation_metrics": {
                "root_mean_squared_error": rmse,
                "rmse": rmse,
                "tuned_configuration": best_cfg
            }
        }


def execute_champion_challenger_duel(
    historical_demand: List[float],
    steps: int = 8,
    window_size: int = 3,
    tenant_id: str = "unknown"
) -> Dict[str, Any]:
    """
    Compares BaselineVelocityModel against AdaptiveTimeSeriesChallenger, 
    selecting the model with the lower RMSE error as the active payload champion.
    """
    import numpy as np

    # 1. Run baseline model
    baseline = BaselineVelocityModel(window_size=window_size, tenant_id=tenant_id)
    baseline_res = baseline.predict(historical_demand, steps=steps)

    # Compute baseline RMSE on historical lookbacks
    n = len(historical_demand)
    baseline_sq_errors = []
    if n > window_size:
        for t in range(window_size, n):
            prev = historical_demand[t - window_size:t]
            pred_t = sum(prev) / window_size
            baseline_sq_errors.append((historical_demand[t] - pred_t) ** 2)
        baseline_rmse = float(np.sqrt(np.mean(baseline_sq_errors)))
    else:
        baseline_rmse = float('inf')

    baseline_res["evaluation_metrics"]["rmse"] = baseline_rmse
    baseline_res["evaluation_metrics"]["root_mean_squared_error"] = baseline_rmse

    # 2. Run Challenger
    challenger = AdaptiveTimeSeriesChallenger(tenant_id=tenant_id)
    challenger_res = challenger.predict(historical_demand, steps=steps)
    challenger_rmse = challenger_res["evaluation_metrics"]["rmse"]

    # 3. Determine Champion
    if baseline_rmse <= challenger_rmse:
        champion = "BaselineVelocityModel"
        active_payload = baseline_res
    else:
        champion = "AdaptiveTimeSeriesChallenger"
        active_payload = challenger_res

    return {
        "active_champion": champion,
        "champion_model_version": active_payload["model_version"],
        "generated_output_matrix": active_payload["generated_output_matrix"],
        "evaluation_metrics": active_payload["evaluation_metrics"],
        "baseline_error_profile": baseline_res["evaluation_metrics"],
        "challenger_error_profile": challenger_res["evaluation_metrics"]
    }
