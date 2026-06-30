from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


class ExecutiveReportFormattingError(Exception):
    """Raised when executive report payloads cannot be formatted safely."""


class ExecutiveAIFormatter:
    """Formats core intelligence outputs for an executive LLM or dashboard panel."""

    def generate_executive_brief(
        self,
        anomaly_summary: dict[str, Any],
        optimization_summary: dict[str, Any],
        simulation_deltas: dict[str, Any],
    ) -> str:
        try:
            anomaly_summary = self._ensure_dict(anomaly_summary, "anomaly_summary")
            optimization_summary = self._ensure_dict(optimization_summary, "optimization_summary")
            simulation_deltas = self._ensure_dict(simulation_deltas, "simulation_deltas")

            generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            flagged_count = self._first_value(
                anomaly_summary,
                ("flagged_maverick_spend_count", "maverick_spend_count", "flagged_count"),
                0,
            )
            anomaly_scores = self._numeric_array(
                self._first_value(anomaly_summary, ("anomaly_scores", "raw_scores", "isolation_forest_scores"), []),
            )
            max_anomaly_score = max(anomaly_scores) if anomaly_scores else self._first_value(
                anomaly_summary,
                ("highest_anomaly_score", "max_anomaly_score", "anomaly_score"),
                "n/a",
            )
            recommended_quantity = self._first_value(
                optimization_summary,
                ("recommended_order_quantity", "order_quantity"),
                "n/a",
            )
            execution_days = self._first_value(
                optimization_summary,
                ("execution_date_relative_days", "order_date_relative_days"),
                "n/a",
            )
            capital_delta = self._nested_first_value(
                simulation_deltas,
                (
                    ("deltas", "projected_cost_increase"),
                    ("calculated_financial_delta",),
                    ("projected_cost_increase",),
                ),
            )
            hazard_scale = self._nested_first_value(
                simulation_deltas,
                (
                    ("stockout_hazard_scale",),
                    ("stockout_risk", "level"),
                    ("stockout_risk_level",),
                ),
            )

            lines = [
                "# Executive Procurement Strategy Brief",
                "",
                "```yaml",
                "template: aegisprocure.phase_5.executive_brief",
                "transport: local_llm_or_executive_panel",
                "external_http_clients: false",
                "max_agent_iterations: 5",
                f"generated_at: {generated_at}",
                "```",
                "",
                "## Decision Snapshot",
                "",
                f"- Maverick spend anomalies flagged: **{flagged_count}**",
                f"- Peak Isolation Forest anomaly score: **{max_anomaly_score}**",
                f"- Optimal reorder quantity: **{recommended_quantity}**",
                f"- Reorder execution offset: **{execution_days} days**",
                f"- Stressed capital requirement delta: **{capital_delta}**",
                f"- Stockout hazard scale: **{hazard_scale}**",
                "",
                "## Local LLM Prompt",
                "",
                "You are producing an executive procurement brief from validated system outputs. Use only the structured payload below. Explain operational risk, capital impact, reorder timing, and anomaly-review priorities. Do not infer supplier names, tenant facts, API credentials, or external market data not present in the payload.",
                "",
            ]

            lines.extend(self._score_section("Raw Numerical Scores", anomaly_scores))
            lines.extend(self._section("Anomaly Summary", anomaly_summary))
            lines.extend(self._section("Optimization Summary", optimization_summary))
            lines.extend(self._section("Simulation Deltas", simulation_deltas))
            lines.extend(
                [
                    "## Required Executive Output",
                    "",
                    "1. One-paragraph executive summary",
                    "2. Maverick-spend risk interpretation",
                    "3. Reorder and working-capital recommendation",
                    "4. Stress-scenario stockout hazard assessment",
                    "5. Data gaps and safe follow-up questions",
                    "",
                ]
            )
            return "\n".join(lines).strip() + "\n"
        except ExecutiveReportFormattingError:
            raise
        except Exception as exc:
            raise ExecutiveReportFormattingError(f"Unable to generate executive brief: {exc}") from exc

    def format_prompt_payload(
        self,
        anomaly_metrics: dict[str, Any],
        optimization_outputs: dict[str, Any],
        simulation_deltas: dict[str, Any],
    ) -> str:
        return self.generate_executive_brief(anomaly_metrics, optimization_outputs, simulation_deltas)

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

    def _numeric_array(self, value: Any) -> list[float]:
        if value is None:
            return []
        if isinstance(value, (int, float)):
            return [float(value)]
        if not isinstance(value, list):
            return []
        scores = []
        for item in value:
            try:
                number = float(item)
            except (TypeError, ValueError):
                continue
            scores.append(number)
        return scores

    def _score_section(self, title: str, scores: list[float]) -> list[str]:
        lines = [f"## {title}", ""]
        if not scores:
            return lines + ["- No raw numerical anomaly scores supplied.", ""]
        score_count = len(scores)
        score_sum = sum(scores)
        score_mean = score_sum / score_count if score_count else 0.0
        lines.extend(
            [
                f"- Count: `{score_count}`",
                f"- Minimum: `{round(min(scores), 6)}`",
                f"- Maximum: `{round(max(scores), 6)}`",
                f"- Mean: `{round(score_mean, 6)}`",
                "- Values:",
            ]
        )
        lines.extend(f"  - `{round(score, 6)}`" for score in scores)
        lines.append("")
        return lines

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
