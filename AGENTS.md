# AegisProcure Platform Rule Book & Agent Workspace

**CRITICAL RUNTIME INSTRUCTION:** Before writing, editing, or evaluating any code in this repository, you **MUST** read the comprehensive role constraints, data blueprints, and security guardrails located in the configuration folders.

## Universal Workspace Constraints

1. This is a multi-tenant, schema-driven procurement engine (Project Nika / TenderIQ).

2. Hardcoding logic for specific industry verticals is an automatic build failure.

3. Database isolation via Row-Level Security (RLS) is absolute. Never write queries that bypass `app.current_tenant_id`.

## Configuration & Role Mapping

To understand your specific technical boundaries, execution scripts, and drift prevention loops, ingest the following rule files before processing tasks:

- **Execution Guardrails:** Read `.antigravity/skills/ground_rules.md`
- **Hallucination & Risk Triggers:** Read `.antigravity/skills/risk_and_compliance.md`
- **Architectural Specs:** Read `.antigravity/skills/architectural_blueprint.md`
- **Code Optimization Quality (Ponytail):** Read `.antigravity/skills/ponytail.md`
- **Multi-Agent Graph Orchestration:** Read `.antigravity/skills/state_machine_agent_routing.md`
- - **Active Task Backlog & Technical Debt Ledger:** Read `.antigravity/backlog_and_debt.md`
- **Error Isolation & Logging Quality:** Read `.antigravity/skills/error_handling_and_logging.md`

> MANDATORY BOUNDARY RULE: Before starting a terminal change, match your assignment target against the 'Active Milestone' checklist inside `.antigravity/backlog_and_debt.md`. If a task is marked as COMPLETED, do not re-engineer it. If your code introduces a structural shortcut, you must append an tracking log to the 'Active Technical Debt Log' section.

## Specialist Technical Roles
If your current task falls under a specific engineering domain, you must strictly adopt the boundaries mapped in these profile folders:
- **Product & Domain Control:** `.antigravity/skills/role_product_and_domain.md`
- **Data Engineering & Backend:** `.antigravity/skills/role_core_engineering.md`
- **Data Science & MLOps:** `.antigravity/skills/role_data_and_mlops.md`
- **Frontend & UI Interactions:** `.antigravity/skills/role_interface_and_ux.md`

### 🧠 Mandatory Agent Memory Synchronization Invariant
- **Rule:** Before concluding ANY execution turn, terminal code mutation, or package installation, you MUST update and patch the centralized memory index at `.antigravity/agent_memory_harness.json`.
- **Execution Invariant:** 1. Increment the historical state check values.
  2. Log the exact timestamp, active milestone phase, and any new code files created or modified.
  3. Append any technical debt, structural shortcuts, or newly imported packages introduced during the turn.
- **Boundary:** Saving code changes without immediately synchronizing this JSON state ledger is an absolute pipeline failure. If a task is blocked or hits a compiler error, log the failure state into the harness file before terminating the terminal session.