from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


class ExecutiveReportFormattingError(Exception):
    """Raised when executive report payloads cannot be formatted safely."""


class ExecutiveAIFormatter:
    """Formats core intelligence outputs for an executive LLM or dashboard panel."""

    def format_prompt_payload(
        self,
        anomaly_metrics: dict[str, Any],
        optimization_outputs: dict[str, Any],
        simulation_deltas: dict[str, Any],
    ) -> str:
        try:
            anomaly_metrics = self._ensure_dict(anomaly_metrics, "anomaly_metrics")
            optimization_outputs = self._ensure_dict(optimization_outputs, "optimization_outputs")
            simulation_deltas = self._ensure_dict(simulation_deltas, "simulation_deltas")

            generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            lines = [
                "# Executive Procurement Intelligence Payload",
                "",
                f"- Generated at: `{generated_at}`",
                "- Intended consumer: localized OpenCode/MCP language service or executive panel",
                "- External network clients: `not instantiated`",
                "",
                "## Executive Briefing Instructions",
                "",
                "Produce a concise executive report using only the raw system outputs below. Call out risk, cost movement, ordering action, and recommended review focus. Do not invent supplier, tenant, or market facts that are not present in the payload.",
                "",
                "## Key Signals",
                "",
                f"- Flagged maverick spend anomalies: `{self._first_value(anomaly_metrics, ('flagged_maverick_spend_count', 'maverick_spend_count', 'flagged_count'), 0)}`",
                f"- Highest anomaly score: `{self._first_value(anomaly_metrics, ('highest_anomaly_score', 'max_anomaly_score', 'anomaly_score'), 'n/a')}`",
                f"- Recommended order quantity: `{self._first_value(optimization_outputs, ('recommended_order_quantity', 'order_quantity'), 'n/a')}`",
                f"- Execution date relative days: `{self._first_value(optimization_outputs, ('execution_date_relative_days', 'order_date_relative_days'), 'n/a')}`",
                f"- Projected holding costs: `{self._first_value(optimization_outputs, ('projected_holding_costs', 'holding_costs'), 'n/a')}`",
                f"- Scenario projected cost increase: `{self._nested_first_value(simulation_deltas, (('deltas', 'projected_cost_increase'), ('projected_cost_increase',)))}`",
                f"- Scenario stockout risk: `{self._nested_first_value(simulation_deltas, (('stockout_risk', 'level'), ('stockout_risk_level',)))}`",
                "",
            ]

            lines.extend(self._section("Anomaly Metrics", anomaly_metrics))
            lines.extend(self._section("Optimization Outputs", optimization_outputs))
            lines.extend(self._section("Scenario Simulation Deltas", simulation_deltas))
            lines.extend(
                [
                    "## Required Output Shape",
                    "",
                    "1. Executive summary",
                    "2. Procurement risk interpretation",
                    "3. Inventory and cost impact",
                    "4. Immediate actions",
                    "5. Data caveats from the raw payload",
                    "",
                ]
            )
            return "\n".join(lines).strip() + "\n"
        except ExecutiveReportFormattingError:
            raise
        except Exception as exc:
            raise ExecutiveReportFormattingError(f"Unable to format executive report payload: {exc}") from exc

    def _ensure_dict(self, payload: dict[str, Any], name: str) -> dict[str, Any]:
        if payload is None:
            return {}
        if not isinstance(payload, dict):
            raise ExecutiveReportFormattingError(f"{name} must be a dictionary.")
        return payload

    def _first_value(self, payload: dict[str, Any], keys: tuple[str, ...], default: Any) -> Any:
        for key in keys:
            if key in payload and payload[key] is not None:
                return payload[key]
        return default

    def _nested_first_value(self, payload: dict[str, Any], paths: tuple[tuple[str, ...], ...]) -> Any:
        for path in paths:
            current: Any = payload
            for key in path:
                if not isinstance(current, dict) or key not in current:
                    current = None
                    break
                current = current[key]
            if current is not None:
                return current
        return "n/a"

    def _section(self, title: str, payload: dict[str, Any]) -> list[str]:
        lines = [f"## {title}", ""]
        if not payload:
            return lines + ["- No data supplied.", ""]
        for key in sorted(payload):
            value = payload[key]
            if isinstance(value, dict):
                lines.append(f"- `{key}`:")
                lines.extend(f"  - `{child_key}`: {self._format_value(child_value)}" for child_key, child_value in sorted(value.items()))
            elif isinstance(value, list):
                lines.append(f"- `{key}`:")
                lines.extend(f"  - {self._format_value(item)}" for item in value)
            else:
                lines.append(f"- `{key}`: {self._format_value(value)}")
        lines.append("")
        lines.append(f"```json\n{json.dumps(payload, indent=2, sort_keys=True, default=str)}\n```")
        lines.append("")
        return lines

    def _format_value(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)) or value is None:
            return f"`{value}`"
        return f"`{json.dumps(value, sort_keys=True, default=str)}`"
