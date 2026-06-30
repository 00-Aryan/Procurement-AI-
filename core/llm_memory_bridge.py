import os
import json
import uuid
import logging
import asyncio
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from infra.database import DatabaseLayerError as InfraDatabaseLayerError
from infra.database import TenantContextError, tenant_session, SessionStateRegistry, MLOpsModelRegistry
from core.config_parser import DatabaseLayerException, log_and_raise


# Configure logging
logger = logging.getLogger("llm_memory_bridge")


class CopilotDecisionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executive_summary: str = Field(..., description="High-level analytical summary of the query or recommendation.")
    suggested_action_enum: Literal[
        "flag_anomaly",
        "trigger_reorder",
        "hold_contract",
        "request_approval",
        "no_action",
    ] = Field(..., description="Strict action recommendation enum for downstream automation.")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the suggested action.")


PROVIDER_TOKEN_ENV_BY_PREFIX = {
    "azure/": "AZURE_API_KEY",
    "anthropic/": "ANTHROPIC_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "cohere/": "COHERE_API_KEY",
    "command": "COHERE_API_KEY",
    "gemini/": "GEMINI_API_KEY",
    "google/": "GEMINI_API_KEY",
    "openai/": "OPENAI_API_KEY",
    "gpt-": "OPENAI_API_KEY",
    "o1": "OPENAI_API_KEY",
    "o3": "OPENAI_API_KEY",
    "o4": "OPENAI_API_KEY",
}


def resolve_copilot_model() -> str:
    return os.getenv("COPILOT_LLM_MODEL") or os.getenv("LITELLM_MODEL") or "gpt-4o-mini"


def required_token_env_for_model(model: str) -> str:
    normalized_model = model.lower()
    for prefix, token_env in PROVIDER_TOKEN_ENV_BY_PREFIX.items():
        if normalized_model.startswith(prefix):
            return token_env
    return os.getenv("COPILOT_LLM_TOKEN_ENV", "OPENAI_API_KEY")


def extract_response_content(response: Any) -> str:
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, KeyError, TypeError) as exc:
        log_and_raise(
            DatabaseLayerException,
            "COPILOT_INTEGRATION_ERROR",
            "SYSTEM_LITELLM",
            "extract_response_content",
            f"LiteLLM response did not include choices[0].message.content: {exc}",
            exc,
        )

    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, dict):
        return json.dumps(content)

    log_and_raise(
        DatabaseLayerException,
        "COPILOT_INTEGRATION_ERROR",
        "SYSTEM_LITELLM",
        "extract_response_content",
        "LiteLLM response content was empty or non-JSON serializable.",
    )


class ProcureMindMemoryBridge:
    """
    Manages multi-tenant chatbot session history in PostgreSQL and routes 
    queries via LiteLLM to produce structured Copilot decision outputs.
    """

    async def append_message_turn(
        self,
        session_id: str,
        tenant_id: str,
        user_message: str
    ) -> dict:
        """
        Retrieves historical conversation turns for the given session and tenant,
        appends the new user turn, evaluates it through LiteLLM to construct a 
        CopilotDecisionOutput model, updates the history, and commits the state.
        """
        # Ensure UUID structure validation and secure parameterization
        try:
            parsed_session_uuid = uuid.UUID(str(session_id))
            parsed_tenant_uuid = uuid.UUID(str(tenant_id))
        except ValueError as e:
            log_and_raise(
                DatabaseLayerException,
                "COPILOT_INTEGRATION_ERROR",
                str(tenant_id),
                "append_message_turn_uuid",
                f"Invalid UUID string format: {e}",
                e
            )

        try:
            # Enforce multi-tenant data boundaries via the session context manager.
            async with tenant_session(parsed_tenant_uuid) as session:
                stmt = select(SessionStateRegistry).where(
                    SessionStateRegistry.session_id == parsed_session_uuid,
                    SessionStateRegistry.tenant_id == parsed_tenant_uuid,
                )
                result = await session.execute(stmt)
                registry = result.scalar_one_or_none()

                if not registry:
                    registry = SessionStateRegistry(
                        session_id=parsed_session_uuid,
                        tenant_id=parsed_tenant_uuid,
                        conversation_history=[],
                        cached_telemetry_snapshot={},
                    )
                    session.add(registry)

                history = list(registry.conversation_history or [])
                history.append({"role": "user", "content": str(user_message)})

                model = resolve_copilot_model()
                token_env = required_token_env_for_model(model)
                if not os.getenv(token_env):
                    log_and_raise(
                        DatabaseLayerException,
                        "COPILOT_INTEGRATION_ERROR",
                        str(parsed_tenant_uuid),
                        "append_message_turn_litellm_credentials",
                        f"Required environment token {token_env} is missing for LiteLLM model {model}.",
                    )

                try:
                    import litellm
                except ImportError as e:
                    log_and_raise(
                        DatabaseLayerException,
                        "COPILOT_INTEGRATION_ERROR",
                        str(parsed_tenant_uuid),
                        "append_message_turn_litellm_import",
                        f"LiteLLM dependency is unavailable: {e}",
                        e,
                    )

                # Query latest MLOps runs for system context injection
                mlops_summary_str = "No active MLOps model runs found."
                try:
                    stmt_mlops = select(MLOpsModelRegistry).where(
                        MLOpsModelRegistry.tenant_id == parsed_tenant_uuid
                    ).order_by(MLOpsModelRegistry.execution_timestamp.desc()).limit(5)
                    res_mlops = await session.execute(stmt_mlops)
                    mlops_records = res_mlops.scalars().all()
                    if mlops_records:
                        summary_parts = []
                        for rec in mlops_records:
                            summary_parts.append(
                                f"- Run ID: {rec.run_id} | "
                                f"Model: {rec.model_name} (v: {rec.model_version}) | "
                                f"Question: {rec.associated_business_question} | "
                                f"MAE/RMSE Metrics: {rec.calculated_metrics_score}"
                            )
                        mlops_summary_str = "\n".join(summary_parts)
                except Exception as db_exc:
                    logger.warning(f"Failed to query MLOps registry for copilot bridge context: {db_exc}")

                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are ProcureMind AI. Return only JSON matching the requested schema. "
                            "Use suggested_action_enum only from: flag_anomaly, trigger_reorder, "
                            "hold_contract, request_approval, no_action.\n\n"
                            f"Active MLOps model runs, version histories, and metrics:\n{mlops_summary_str}\n\n"
                            "You must read and evaluate these metrics to answer real-world root-cause questions "
                            "(e.g., explaining exactly why a stockout is projected based on specific supplier lead-time parameters)."
                        ),
                    },
                    *history,
                ]


                response = await asyncio.to_thread(
                    litellm.completion,
                    model=model,
                    messages=messages,
                    response_format=CopilotDecisionOutput,
                    timeout=float(os.getenv("COPILOT_LLM_TIMEOUT_SECONDS", "20")),
                )
                output = CopilotDecisionOutput.model_validate_json(extract_response_content(response))

                history.append({
                    "role": "assistant",
                    "content": json.dumps(output.model_dump()),
                })

                registry.conversation_history = history

                return output.model_dump()
        except DatabaseLayerException:
            raise
        except (
            InfraDatabaseLayerError,
            TenantContextError,
            SQLAlchemyError,
            TimeoutError,
            ConnectionError,
            OSError,
        ) as e:
            log_and_raise(
                DatabaseLayerException,
                "COPILOT_INTEGRATION_ERROR",
                str(parsed_tenant_uuid),
                "append_message_turn_database",
                f"Live PostgreSQL persistence failed: {e}",
                e,
            )
        except Exception as e:
            log_and_raise(
                DatabaseLayerException,
                "COPILOT_INTEGRATION_ERROR",
                str(parsed_tenant_uuid),
                "append_message_turn_litellm",
                f"LiteLLM structured completion or Pydantic validation failed: {e}",
                e,
            )
