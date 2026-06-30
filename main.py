import logging
import re
from typing import Optional
from fastapi import FastAPI, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from core.config_parser import load_config, CELRuleEvaluator, IndustryConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_gateway")

# Load configuration at startup
# Wrap in try/except block to gracefully fall back to default configurations if missing
try:
    CONFIG: IndustryConfig = load_config("industry-config.json")
    logger.info("Successfully loaded industry-config.json configuration.")
except Exception as e:
    logger.error(f"Failed to load industry-config.json: {e}. Falling back to default IndustryConfig.")
    CONFIG = load_config("nonexistent-file.json")  # triggers default fallback

# Initialize FastAPI app
app = FastAPI(
    title="AegisProcure API Gateway",
    description="Multi-Tenant API Gateway for government procurement intelligence.",
    version="1.0.0"
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
                        logger.error(f"Error normalizing attribute {dim.input_attributes[0]}: {e}")
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
        logger.exception("Unexpected error occurred during bid evaluation.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred while evaluating the bid: {str(e)}"
        )
