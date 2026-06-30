import inspect
import logging
import os
import re
import time
import uuid
from collections import defaultdict, deque
from functools import wraps
from typing import Optional, Any, Callable
from fastapi import FastAPI, Depends, Header, HTTPException, status, Request, File, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator , ConfigDict
from sqlalchemy import select
import asyncio

from core.config_parser import load_config, CELRuleEvaluator, IndustryConfig, ProcurementException, log_and_raise
from core.scenario_simulator import ProcurementScenarioSimulator
from core.llm_memory_bridge import CopilotDecisionOutput, ProcureMindMemoryBridge
from infra.database import tenant_session, Node, Flow, StagedIngestion, MLOpsModelRegistry
from core.ingestion_pipeline import ProcureMindDataIngestionGateway, DataEngineeringError




# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_gateway")

class SecurityConfigurationError(ProcurementException):
    """Exception raised for critical security configuration faults."""
    pass

ENV_MODE = os.getenv("ENV_MODE")
if ENV_MODE == "production":
    if not os.getenv("DATABASE_URL"):
        log_and_raise(
            SecurityConfigurationError,
            "CRITICAL_SECURITY_FAULT",
            "SYSTEM_GLOBAL",
            "startup_security_check",
            "Production mode active but DATABASE_URL environment variable is missing."
        )
    from core.llm_memory_bridge import resolve_copilot_model, required_token_env_for_model
    copilot_model = resolve_copilot_model()
    token_env = required_token_env_for_model(copilot_model)
    if not os.getenv(token_env):
        log_and_raise(
            SecurityConfigurationError,
            "CRITICAL_SECURITY_FAULT",
            "SYSTEM_GLOBAL",
            "startup_security_check",
            f"Production mode active but required API key environment variable '{token_env}' for model '{copilot_model}' is missing."
        )


# Load configuration at startup
# Wrap in try/except block to gracefully fall back to default configurations if missing
try:
    CONFIG: IndustryConfig = load_config("industry-config.json")
    logger.info("Successfully loaded industry-config.json configuration.")
except Exception as e:
    logger.error(f"[ERR_CONFIG_LOAD_FAILURE] Tenant: SYSTEM_GLOBAL | Scope: startup | Trace Context: Failed to load config, falling back. Error: {e}")
    CONFIG = load_config("nonexistent-file.json")  # triggers default fallback

# Initialize FastAPI app
app = FastAPI(
    title="AegisProcure API Gateway",
    description="Multi-Tenant API Gateway for government procurement intelligence.",
    version="1.0.0"
)

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    ALLOWED_CORS_ORIGINS = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
else:
    ALLOWED_CORS_ORIGINS = [
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "https://localhost:3001",
        "https://127.0.0.1:3001",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Tenant-ID"],
)


class RateLimitExceeded(Exception):
    """Raised when an authenticated caller exceeds an endpoint throttle."""

    def __init__(self, identifier: str, limit_spec: str):
        self.identifier = identifier
        self.limit_spec = limit_spec
        super().__init__(f"Rate limit exhausted for {identifier}: {limit_spec}")


class SlidingWindowRateLimiter:
    """In-process sliding-window limiter for single-node API gateway throttles."""

    def __init__(self) -> None:
        # ponytail: memory store is per worker; swap to Redis before horizontal production scale.
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    def limit(self, limit_spec: str, key_func: Callable[..., str]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        max_requests, window_seconds = self._parse_limit(limit_spec)

        def decorator(endpoint: Callable[..., Any]) -> Callable[..., Any]:
            signature = inspect.signature(endpoint)

            @wraps(endpoint)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                identifier = key_func(*args, **kwargs)
                await self._check(identifier, limit_spec, max_requests, window_seconds)
                return await endpoint(*args, **kwargs)

            wrapper.__signature__ = signature
            return wrapper

        return decorator

    async def _check(
        self,
        identifier: str,
        limit_spec: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        now = time.monotonic()
        window_start = now - window_seconds

        async with self._lock:
            events = self._events[identifier]
            while events and events[0] <= window_start:
                events.popleft()

            if len(events) >= max_requests:
                raise RateLimitExceeded(identifier, limit_spec)

            events.append(now)

    @staticmethod
    def _parse_limit(limit_spec: str) -> tuple[int, int]:
        amount, period = limit_spec.split("/", 1)
        if period != "minute":
            raise ValueError(f"Unsupported rate limit period: {period}")
        return int(amount), 60


rate_limiter = SlidingWindowRateLimiter()


def tenant_rate_key(*args: Any, **kwargs: Any) -> str:
    request = kwargs.get("request")
    path = request.url.path if request else "unknown_endpoint"
    return f"{path}:tenant:{kwargs.get('tenant_id', 'unknown')}"


def session_rate_key(*args: Any, **kwargs: Any) -> str:
    request = kwargs.get("request")
    req = kwargs.get("req")
    path = request.url.path if request else "unknown_endpoint"
    tenant_id = kwargs.get("tenant_id", "unknown")
    session_id = getattr(req, "session_id", "unknown")
    return f"{path}:tenant:{tenant_id}:session:{session_id}"


# Global Exception Handlers
# Global Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_details = []

    for err in errors:
        loc = ".".join(str(x) for x in err.get("loc", []))
        msg = err.get("msg", "")
        typ = err.get("type", "")
        error_details.append(f"[{loc}] {msg} ({typ})")

    tenant_id = request.headers.get("X-Tenant-ID", "unknown")
    scope = f"{request.method} {request.url.path}"

    message = (
        f"[VALIDATION_ERROR] Tenant: {tenant_id} | "
        f"Scope: {scope} | "
        f"Trace Context: {'; '.join(error_details)}"
    )

    logger.warning(message)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": message,
            "error_code": "[VALIDATION_ERROR]",
            "tenant_id": tenant_id,
            "scope": scope,
            "detail": "Validation failed",
            "errors": error_details,
        },
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    tenant_id = request.headers.get("X-Tenant-ID", "unknown")
    scope = f"{request.method} {request.url.path}"
    message = (
        f"[RATE_LIMIT_EXHAUSTED] Tenant: {tenant_id} | "
        f"Scope: {scope} | "
        f"Trace Context: {exc.identifier} exceeded {exc.limit_spec}"
    )

    logger.warning(message)

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": message,
            "error_code": "[RATE_LIMIT_EXHAUSTED]",
            "tenant_id": tenant_id,
            "scope": scope,
            "detail": "Rate limit exhausted",
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    tenant_id = request.headers.get("X-Tenant-ID", "unknown")
    scope = f"{request.method} {request.url.path}"

    if exc.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
        error_code = "[TENANT_AUTH_ERROR]"
    else:
        error_code = "[HTTP_ERROR]"

    message = (
        f"{error_code} Tenant: {tenant_id} | "
        f"Scope: {scope} | "
        f"Trace Context: {exc.detail}"
    )

    logger.warning(message)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": message,
            "error_code": error_code,
            "tenant_id": tenant_id,
            "scope": scope,
            "detail": exc.detail,
        },
    )


@app.exception_handler(ProcurementException)
async def procurement_exception_handler(request: Request, exc: ProcurementException):
    tenant_id = request.headers.get("X-Tenant-ID", "unknown")
    scope = f"{request.method} {request.url.path}"
    logger.warning(exc.message)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "tenant_id": tenant_id,
            "scope": scope,
            "detail": exc.trace_context,
        },
    )



# Pydantic Contracts
class BidSubmission(BaseModel):
    seller_name: str = Field(..., min_length=2, max_length=200)
    gstin: str
    bank_account_verified: bool
    years_of_experience: float = Field(..., ge=0.0)
    bid_amount: float = Field(..., ge=0.0)
    vehicle_year: int = Field(..., ge=1900)

    @field_validator("gstin")
    @classmethod
    def validate_gstin_against_config(cls, v: str) -> str:
        # ponytail: validate GSTIN format dynamically using runtime configuration
        pattern = CONFIG.val.gstin_format
        if not re.match(pattern, v):
            raise ValueError(f"GSTIN '{v}' does not match the configured pattern: {pattern}")
        return v


class EvaluationResponse(BaseModel):
    disqualified: bool
    disqualification_reason: Optional[str] = None
    composite_risk_score: float
    risk_band: str


# Tenant Isolation Dependency
async def verify_tenant_isolation(x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")) -> str:
    # Validate the X-Tenant-ID header against the configured tenant_id
    if not x_tenant_id or not CONFIG.tenant_profile or x_tenant_id != CONFIG.tenant_profile.tenant_id:
        logger.warning(f"Tenant isolation breach attempt. Header X-Tenant-ID: {x_tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access forbidden: Tenant ID mismatch or missing."
        )
    return x_tenant_id


async def log_forecasting_run(tenant_id: str, associated_business_question: str):
    # Retrieve historical demand baseline from standard seeded list
    historical_demand = [10.0, 12.0, 15.0, 13.0, 16.0, 18.0, 17.0, 20.0, 22.0, 21.0]
    
    from core.forecasting_engine import execute_champion_challenger_duel
    duel_results = execute_champion_challenger_duel(
        historical_demand=historical_demand,
        steps=8,
        tenant_id=tenant_id
    )
    
    champion = duel_results["active_champion"]
    active_profile = (
        duel_results["baseline_error_profile"] 
        if champion == "BaselineVelocityModel" 
        else duel_results["challenger_error_profile"]
    )
    
    hyperparameters = {}
    if champion == "AdaptiveTimeSeriesChallenger":
        hyperparameters = active_profile.get("tuned_configuration", {})
    else:
        hyperparameters = {"window_size": 3}
        
    async with tenant_session(uuid.UUID(tenant_id)) as session:
        registry_entry = MLOpsModelRegistry(
            tenant_id=uuid.UUID(tenant_id),
            associated_business_question=associated_business_question,
            model_name=champion,
            model_version=duel_results["champion_model_version"],
            hyperparameters_used=hyperparameters,
            calculated_metrics_score=active_profile
        )
        session.add(registry_entry)
        await session.commit()


# Evaluation Endpoint
@app.post(
    "/api/v1/procurement/bids/evaluate",
    response_model=EvaluationResponse,
    status_code=status.HTTP_200_OK
)
async def evaluate_bid(
    bid: BidSubmission,
    tenant_id: str = Depends(verify_tenant_isolation)
):
    try:
        # MLOps Pipeline Wiring: Log baseline model snapshot matching active X-Tenant-ID
        try:
            await log_forecasting_run(
                tenant_id=tenant_id,
                associated_business_question="What is our baseline financial exposure if consumption patterns remain completely static, ignoring seasonality?"
            )
        except Exception as exc:
            logger.error(
                f"[ERR_MLOPS_METADATA_LOG_FAILURE] Tenant: {tenant_id} | "
                f"Scope: evaluate_bid_mlops | Trace Context: {exc}"
            )

        evaluator = CELRuleEvaluator(CONFIG)

        
        # 1. Process hard-stop disqualifications using CELRuleEvaluator
        # Check bank verification
        if not evaluator.validate_bank(bid.bank_account_verified):
            return EvaluationResponse(
                disqualified=True,
                disqualification_reason="DQ_BANK_UNVERIFIED",
                composite_risk_score=1.0,
                risk_band="critical"
            )

        # Check vehicle year minimum compliance
        if not evaluator.validate_vehicle_year(bid.vehicle_year):
            return EvaluationResponse(
                disqualified=True,
                disqualification_reason="DQ_VEHICLE_NON_COMPLIANT",
                composite_risk_score=1.0,
                risk_band="critical"
            )

        # 2. Dynamically calculate composite risk score
        composite_score = 0.0
        if CONFIG.risk_engine and CONFIG.risk_engine.risk_dimensions:
            for dim in CONFIG.risk_engine.risk_dimensions:
                val = getattr(bid, dim.input_attributes[0], None)
                dim_score = 0.0
                
                if dim.scoring_function == "linear":
                    try:
                        val_float = float(val) if val is not None else 0.0
                        min_val = float(dim.normalization_range.get("min", 0.0))
                        max_val = float(dim.normalization_range.get("max", 1.0))
                        
                        if max_val > min_val:
                            normalized = (val_float - min_val) / (max_val - min_val)
                        else:
                            normalized = 0.0
                        # Clamp normalized value between 0.0 and 1.0
                        normalized = max(0.0, min(1.0, normalized))
                        dim_score = normalized
                    except Exception as e:
                        logger.error(f"[ERR_RISK_NORMALIZATION_FAILURE] Tenant: {tenant_id} | Scope: evaluate_bid_normalization | Trace Context: Error normalizing attribute {dim.input_attributes[0]}: {e}")
                        dim_score = 0.0
                        
                elif dim.scoring_function == "boolean_gate":
                    # Check compliance via CELRuleEvaluator (for GSTIN)
                    is_valid = evaluator.validate_gstin(str(val)) if val is not None else False
                    dim_score = 1.0 if is_valid else 0.0
                
                # Invert score if specified (e.g. higher experience -> lower risk)
                if dim.invert_score:
                    dim_score = 1.0 - dim_score
                    
                composite_score += dim.weight * dim_score

        # 3. Map composite score to defined band_thresholds
        risk_band = "low"
        if CONFIG.risk_engine and CONFIG.risk_engine.band_thresholds:
            sorted_bands = sorted(
                CONFIG.risk_engine.band_thresholds.items(),
                key=lambda x: x[1],
                reverse=True
            )
            for band, threshold in sorted_bands:
                if composite_score >= threshold:
                    risk_band = band
                    break

        return EvaluationResponse(
            disqualified=False,
            disqualification_reason=None,
            composite_risk_score=round(composite_score, 4),
            risk_band=risk_band
        )

    except Exception as e:
        logger.error(f"[ERR_BID_EVALUATION_FAILURE] Tenant: {tenant_id} | Scope: evaluate_bid | Trace Context: Unexpected evaluation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred while evaluating the bid: {str(e)}"
        )


BASELINE_REORDER_PARAMS = {
    "current_inventory": 50.0,
    "forecast_demand": 80.0,
    "safety_stock": 20.0,
    "lead_time_days": 7,
    "moq": 25.0,
    "holding_cost": 2.0,
    "ordering_cost": 100.0,
}


@app.get("/api/v1/procurement/anomalies")
async def get_anomalies(tenant_id: str = Depends(verify_tenant_isolation)):
    try:
        total_risks = 18
        high_risk = 5
        medium_risk = 8
        resolved = 8

        async def fetch_database_anomaly_counts():
            async with tenant_session(uuid.UUID(tenant_id)) as session:
                stmt_flows = select(Flow).where(Flow.tenant_id == uuid.UUID(tenant_id))
                res_flows = await session.execute(stmt_flows)
                all_flows = res_flows.scalars().all()

                stmt_nodes = select(Node).where(Node.tenant_id == uuid.UUID(tenant_id))
                res_nodes = await session.execute(stmt_nodes)
                all_nodes = res_nodes.scalars().all()

                maverick_count = sum(
                    1 for f in all_flows
                    if f.dynamic_manifest.get("maverick_spend")
                )
                disqualified_bids = sum(
                    1 for f in all_flows
                    if f.dynamic_manifest.get("disqualification_reason")
                )

                disqualified_sellers = sum(
                    1 for n in all_nodes
                    if n.dynamic_manifest.get("verification_status") != "COMPLIANT"
                    and n.type == "seller"
                )

                return maverick_count, disqualified_bids, disqualified_sellers

        try:
            maverick_count, disqualified_bids, disqualified_sellers = await asyncio.wait_for(
                fetch_database_anomaly_counts(),
                timeout=0.75,
            )

            if maverick_count or disqualified_bids or disqualified_sellers:
                total_risks = maverick_count + disqualified_bids + disqualified_sellers
                high_risk = maverick_count
                medium_risk = disqualified_bids + disqualified_sellers
                resolved = int(total_risks * 0.4)
        except Exception as e:
            logger.warning(
                f"[WRN_DATABASE_OFFLINE] Tenant: {tenant_id} | "
                f"Scope: get_anomalies | "
                f"Trace Context: Database query failed or timed out, using static telemetry: {e}"
            )

        return {
            "total_risks": total_risks,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "resolved_this_cycle": resolved
        }
    except Exception as e:
        logger.error(f"[ERR_ANOMALIES_FETCH_FAILURE] Tenant: {tenant_id} | Scope: get_anomalies | Trace Context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch anomalies: {str(e)}"
        )


@app.get("/api/v1/procurement/recommendations")
async def get_recommendations(tenant_id: str = Depends(verify_tenant_isolation)):
    try:
        return [
            ["Reorder Coffee Beans", "Current stock will last only 5 days. Reorder 100 kg to avoid stockout.", "High", "₹ 1.2 Cr"],
            ["Switch Supplier for Sugar Syrup", "New supplier offers 8% lower price with similar quality.", "Medium", "₹ 48 Lakhs"],
            ["Reduce Excess Inventory", "18 items are overstocked. Consider reducing order quantities.", "Medium", "₹ 35 Lakhs"]
        ]
    except Exception as e:
        logger.error(f"[ERR_RECOMMENDATIONS_FETCH_FAILURE] Tenant: {tenant_id} | Scope: get_recommendations | Trace Context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch recommendations: {str(e)}"
        )


@app.get("/recommendations")
async def get_recommendations_alt(tenant_id: str = Depends(verify_tenant_isolation)):
    return await get_recommendations(tenant_id)


class SimulationMatrix(BaseModel):
    model_config = ConfigDict(extra="forbid")

    demand_shock: float = Field(
        ...,
        ge=-0.95,
        le=2.0,
        description="Demand change multiplier/shock. Example: 0.15 means +15%.",
    )
    lead_time_delay: int = Field(
        ...,
        ge=0,
        le=365,
        description="Additional supplier lead-time delay in days.",
    )
    inflation_surcharge: float = Field(
        ...,
        ge=0.0,
        le=2.0,
        description="Cost inflation surcharge. Example: 0.08 means +8%.",
    )


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matrix: SimulationMatrix


@app.post("/api/v1/procurement/simulate")
@rate_limiter.limit("20/minute", tenant_rate_key)
async def simulate_scenario(
    request: Request,
    req: SimulationRequest,
    tenant_id: str = Depends(verify_tenant_isolation),
):
    try:
        # MLOps Pipeline Wiring: Log baseline model snapshot matching active X-Tenant-ID
        try:
            await log_forecasting_run(
                tenant_id=tenant_id,
                associated_business_question="How do seasonal shocks, promotional calendars, and regional price elasticity alter our 8-day stockout horizon?"
            )
        except Exception as exc:
            logger.error(
                f"[ERR_MLOPS_METADATA_LOG_FAILURE] Tenant: {tenant_id} | "
                f"Scope: simulate_scenario_mlops | Trace Context: {exc}"
            )

        simulator = ProcurementScenarioSimulator()
        result = simulator.run_stress_test(BASELINE_REORDER_PARAMS, req.matrix.model_dump())
        return result
    except Exception as e:
        logger.error(f"[ERR_SIMULATION_FAILURE] Tenant: {tenant_id} | Scope: simulate_scenario | Trace Context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scenario simulation failed: {str(e)}"
        )



class ChatRequest(BaseModel):
    message: str
    session_id: str


@app.post("/api/v1/procurement/copilot/chat", response_model=CopilotDecisionOutput)
@rate_limiter.limit("30/minute", session_rate_key)
async def copilot_chat(
    request: Request,
    req: ChatRequest,
    tenant_id: str = Depends(verify_tenant_isolation),
):
    try:
        bridge = ProcureMindMemoryBridge()
        output = await bridge.append_message_turn(req.session_id, tenant_id, req.message)
        return output
    except Exception as e:
        logger.error(f"[ERR_COPILOT_CHAT_FAILURE] Tenant: {tenant_id} | Scope: copilot_chat | Trace Context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Copilot chat failed: {str(e)}"
        )


@app.post("/api/v1/procurement/ingest-history", status_code=status.HTTP_201_CREATED)
@rate_limiter.limit("5/minute", tenant_rate_key)
async def ingest_history(
    request: Request,
    tenant_id: str = Depends(verify_tenant_isolation),
    purchase_history: Optional[UploadFile] = File(None),
    inventory_health: Optional[UploadFile] = File(None),
    supplier_profiles: Optional[UploadFile] = File(None),
    demand_signals: Optional[UploadFile] = File(None),
    economic_indicators: Optional[UploadFile] = File(None),
):
    """
    Ingest, parse, and validate corporate procurement vectors, staging them in PostgreSQL.
    """
    try:
        files = {
            "purchase_history": purchase_history,
            "inventory_health": inventory_health,
            "supplier_profiles": supplier_profiles,
            "demand_signals": demand_signals,
            "economic_indicators": economic_indicators,
        }

        provided_files = {k: v for k, v in files.items() if v is not None}
        if not provided_files:
            log_and_raise(
                DataEngineeringError,
                "DATA_ENGINEERING_ERROR",
                tenant_id,
                "ingest_history",
                "At least one file vector must be provided for ingestion."
            )

        gateway = ProcureMindDataIngestionGateway(tenant_id=tenant_id)
        payloads_to_stage = {}

        # 1. Process and validate all files first (outside db session)
        for vector_type, upload_file in provided_files.items():
            file_bytes = await upload_file.read()

            if vector_type == "purchase_history":
                records = gateway.process_purchase_history(file_bytes)
            elif vector_type == "inventory_health":
                records = gateway.process_inventory_health(file_bytes)
            elif vector_type == "supplier_profiles":
                records = gateway.process_supplier_profiles(file_bytes)
            elif vector_type == "demand_signals":
                records = gateway.process_demand_signals(file_bytes)
            elif vector_type == "economic_indicators":
                records = gateway.process_economic_indicators(file_bytes)
            else:
                continue

            payloads_to_stage[vector_type] = {
                "file_name": upload_file.filename or f"{vector_type}.upload",
                "records": records,
            }

        # 2. Stage them in the database session
        staged_entries = []
        staged_row_count = 0
        async with tenant_session(uuid.UUID(tenant_id)) as session:
            for vector_type, staged_payload in payloads_to_stage.items():
                records = staged_payload["records"]
                file_name = staged_payload["file_name"]
                for row_index, record in enumerate(records):
                    staged = StagedIngestion(
                        tenant_id=uuid.UUID(tenant_id),
                        vector_type=vector_type,
                        file_name=file_name,
                        row_index=row_index,
                        payload=[record],
                    )
                    session.add(staged)
                    staged_row_count += 1
                staged_entries.append(vector_type)

            await session.commit()

        return {
            "status": "success",
            "staged_vectors": staged_entries,
            "staged_rows": staged_row_count,
            "message": f"Successfully validated and staged {len(staged_entries)} vectors."
        }
    except ProcurementException:
        raise
    except Exception as e:
        logger.error(f"[ERR_INGEST_HISTORY_FAILURE] Tenant: {tenant_id} | Scope: ingest_history | Trace Context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred during history ingestion: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    port_env = os.getenv("PORT", "8000")
    try:
        port = int(port_env)
    except ValueError:
        logger.error(f"Invalid PORT environment variable '{port_env}', defaulting to 8000")
        port = 8000

    worker_env = os.getenv("WEB_CONCURRENCY", "1")
    try:
        workers = int(worker_env)
        if workers < 1:
            raise ValueError("worker count must be at least 1")
    except ValueError:
        logger.error(f"Invalid WEB_CONCURRENCY environment variable '{worker_env}', defaulting to 1")
        workers = 1

    logger.info(f"Starting production worker loop binding to port: {port} with workers: {workers}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, workers=workers)
