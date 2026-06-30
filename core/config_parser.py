import os
import json
import re
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator


class ValidationRules(BaseModel):
    minimum_bid_window_days: int = Field(default=7, ge=7)
    gstin_format: str = Field(default=r"^20[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")


class GateRules(BaseModel):
    min_vehicle_year: int = Field(default=2020, ge=2020)
    require_bank_verified: bool = Field(default=True)


class RiskDimension(BaseModel):
    dimension_id: str
    domain_label: str
    weight: float
    scoring_function: str
    input_attributes: List[str]
    invert_score: bool = False
    normalization_range: Dict[str, Any]


class RiskEngine(BaseModel):
    scoring_model: str
    risk_dimensions: List[RiskDimension]
    weight_sum_constraint: float
    band_thresholds: Dict[str, float]
    scoring_formula: str
    disqualification_gates: List[Dict[str, Any]] = Field(default_factory=list)


class TenantProfile(BaseModel):
    tenant_id: str
    tenant_name: str
    tier: str
    feature_flags: Dict[str, bool] = Field(default_factory=dict)
    rate_limits: Dict[str, int] = Field(default_factory=dict)
    notification_channels: List[Any] = Field(default_factory=list)


class IndustryConfig(BaseModel):
    industry: str = Field(default="ccl_procurement")
    state_code: str = Field(default="20")
    val: ValidationRules = Field(default_factory=ValidationRules)
    gate: GateRules = Field(default_factory=GateRules)
    risk_engine: Optional[RiskEngine] = None
    tenant_profile: Optional[TenantProfile] = None

    @field_validator("state_code")
    @classmethod
    def validate_state_code(cls, v: str) -> str:
        if v != "20":
            raise ValueError("State code must be '20' for Jharkhand prefix.")
        return v


def load_config(config_path: str = "industry-config.json") -> IndustryConfig:
    """
    Loads and validates the industry configuration schema.
    If the file does not exist, returns the default configuration.
    """
    if not os.path.exists(config_path):
        default_config = {
            "industry": "ccl_procurement",
            "state_code": "20",
            "val": {
                "minimum_bid_window_days": 7,
                "gstin_format": "^20[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
            },
            "gate": {
                "min_vehicle_year": 2020,
                "require_bank_verified": True
            }
        }
        # Ensure directories exist
        dirname = os.path.dirname(config_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
            
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=2)
        return IndustryConfig(**default_config)

    with open(config_path, "r") as f:
        data = json.load(f)
        
    # ponytail: dynamically map complex json keys to expected IndustryConfig schema fields
    if "val" not in data:
        gstin_pat = r"^20[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
        try:
            gstin_pat = data["entity_mapping"]["attribute_registry"]["gstin"]["constraints"]["pattern"]
        except KeyError:
            pass
        
        min_days = 7
        try:
            for rule in data.get("compliance_rules", {}).get("validation_rules", []):
                if rule.get("rule_id") == "val.minimum_bid_window_7_days":
                    expr = rule.get("rule_expression", "")
                    match = re.search(r"\d+", expr)
                    if match:
                        min_days = int(match.group())
        except Exception:
            pass

        data["val"] = {
            "minimum_bid_window_days": min_days,
            "gstin_format": gstin_pat
        }

    if "gate" not in data:
        min_yr = 2020
        req_bank = True
        try:
            gates = data.get("risk_engine", {}).get("disqualification_gates", [])
            req_bank = any(g.get("gate_id") == "gate.bank_unverified" for g in gates)
        except Exception:
            pass
        
        data["gate"] = {
            "min_vehicle_year": min_yr,
            "require_bank_verified": req_bank
        }
        
    if "state_code" not in data:
        data["state_code"] = "20"
        
    if "industry" not in data:
        data["industry"] = data.get("config_meta", {}).get("industry_domain", "ccl_procurement")

    return IndustryConfig(**data)


class CELRuleEvaluator:
    """
    Simulates Common Expression Language (CEL) / JSONata validation rules 
    for CCL government procurement layout constraint evaluation.
    """
    def __init__(self, config: IndustryConfig):
        self.config = config

    def validate_bid_window(self, window_days: int) -> bool:
        """Evaluates 'val.minimum_bid_window_7_days' CEL equivalent logic."""
        return window_days >= self.config.val.minimum_bid_window_days

    def validate_gstin(self, gstin: str) -> bool:
        """Evaluates 'val.gstin_format' regex CEL equivalent logic."""
        return bool(re.match(self.config.val.gstin_format, gstin))

    def validate_vehicle_year(self, year: int) -> bool:
        """Evaluates 'gate.vehicle_year_non_compliant' CEL equivalent logic."""
        return year >= self.config.gate.min_vehicle_year

    def validate_bank(self, is_verified: bool) -> bool:
        """Evaluates 'gate.bank_unverified' CEL equivalent logic."""
        if self.config.gate.require_bank_verified:
            return is_verified is True
        return True
