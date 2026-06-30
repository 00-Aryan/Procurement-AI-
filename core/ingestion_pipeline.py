import csv
import json
import io
import logging
from typing import List, Dict, Any, Optional

from core.config_parser import ProcurementException, log_and_raise

logger = logging.getLogger("ingestion_pipeline")


class DataEngineeringError(ProcurementException):
    """Exception raised during data engineering and ingestion."""
    pass


class ProcureMindDataIngestionGateway:
    """Centralized engine class for processing corporate procurement datasets."""

    def __init__(self, tenant_id: str = "unknown"):
        self.tenant_id = tenant_id

    def _parse_and_validate(
        self,
        file_bytes: bytes,
        required_columns: List[str],
        scope: str
    ) -> List[Dict[str, Any]]:
        if not file_bytes:
            log_and_raise(
                DataEngineeringError,
                "DATA_ENGINEERING_ERROR",
                self.tenant_id,
                scope,
                "Empty file stream provided."
            )

        try:
            content_str = file_bytes.decode("utf-8")
        except Exception as e:
            log_and_raise(
                DataEngineeringError,
                "DATA_ENGINEERING_ERROR",
                self.tenant_id,
                scope,
                f"Corrupted file stream: failed to decode UTF-8. Error: {e}",
                original_exc=e
            )

        stripped = content_str.strip()
        if not stripped:
            log_and_raise(
                DataEngineeringError,
                "DATA_ENGINEERING_ERROR",
                self.tenant_id,
                scope,
                "Empty file content after stripping whitespace."
            )

        # 1. Try parsing as JSON first
        records: List[Dict[str, Any]] = []
        is_json = False
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                parsed = json.loads(stripped)
                is_json = True
                if isinstance(parsed, list):
                    records = parsed
                elif isinstance(parsed, dict):
                    records = [parsed]
                else:
                    log_and_raise(
                        DataEngineeringError,
                        "DATA_ENGINEERING_ERROR",
                        self.tenant_id,
                        scope,
                        "Malformed JSON: expected a list of objects or a single object."
                    )
            except json.JSONDecodeError as e:
                log_and_raise(
                    DataEngineeringError,
                    "DATA_ENGINEERING_ERROR",
                    self.tenant_id,
                    scope,
                    f"Malformed JSON file stream. Error: {e}",
                    original_exc=e
                )

        # 2. Try parsing as CSV if not JSON
        if not is_json:
            try:
                f = io.StringIO(content_str)
                reader = csv.DictReader(f)
                records = list(reader)
                if reader.fieldnames is None:
                    log_and_raise(
                        DataEngineeringError,
                        "DATA_ENGINEERING_ERROR",
                        self.tenant_id,
                        scope,
                        "Malformed CSV: missing headers/empty file."
                    )
            except DataEngineeringError:
                raise
            except Exception as e:
                log_and_raise(
                    DataEngineeringError,
                    "DATA_ENGINEERING_ERROR",
                    self.tenant_id,
                    scope,
                    f"Malformed CSV file stream. Error: {e}",
                    original_exc=e
                )

        if not records:
            log_and_raise(
                DataEngineeringError,
                "DATA_ENGINEERING_ERROR",
                self.tenant_id,
                scope,
                "No records found in the uploaded file."
            )

        # Extract headers from the first record
        first_record = records[0]
        if not isinstance(first_record, dict):
            log_and_raise(
                DataEngineeringError,
                "DATA_ENGINEERING_ERROR",
                self.tenant_id,
                scope,
                "Malformed records: records must be key-value dictionaries."
            )

        headers = list(first_record.keys())
        missing_headers = [col for col in required_columns if col not in headers]
        if missing_headers:
            log_and_raise(
                DataEngineeringError,
                "DATA_ENGINEERING_ERROR",
                self.tenant_id,
                scope,
                f"Missing required columns: {', '.join(missing_headers)}"
            )

        return records

    def process_purchase_history(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        required = ["Purchase Order ID", "Quantity"]
        return self._parse_and_validate(file_bytes, required, "process_purchase_history")

    def process_inventory_health(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        required = ["Item Name", "Current Stock"]
        return self._parse_and_validate(file_bytes, required, "process_inventory_health")

    def process_supplier_profiles(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        required = ["Supplier ID", "Supplier Name"]
        return self._parse_and_validate(file_bytes, required, "process_supplier_profiles")

    def process_demand_signals(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        required = ["Demand Forecast"]
        return self._parse_and_validate(file_bytes, required, "process_demand_signals")

    def process_economic_indicators(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        required = ["Competitor Pricing", "Seasonality"]
        return self._parse_and_validate(file_bytes, required, "process_economic_indicators")
