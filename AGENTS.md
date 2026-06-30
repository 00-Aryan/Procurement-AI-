# AegisProcure Platform Rule Book & Agent Workspace

**CRITICAL RUNTIME INSTRUCTION:** Before writing, editing, or evaluating any code in this repository, you **MUST** read the comprehensive role constraints, data blueprints, and security guardrails located in the configuration folders.

## Universal Workspace Constraints

This is a multi-tenant, schema-driven procurement engine (Project Nika / TenderIQ).

Hardcoding logic for specific industry verticals is an automatic build failure.

Database isolation via Row-Level Security (RLS) is absolute. Never write queries that bypass `app.current_tenant_id`.

## Configuration & Role Mapping

To understand your specific technical boundaries, execution scripts, and drift prevention loops, ingest the following rule files before processing tasks:

- **Execution Guardrails:** Read `.antigravity/skills/ground_rules.md`
- **Hallucination & Risk Triggers:** Read `.antigravity/skills/risk_and_compliance.md`
- **Architectural Specs:** Read `.antigravity/skills/architectural_blueprint.md`
- **Code Optimization Quality (Ponytail):** Read `.antigravity/skills/ponytail.md`
- **Multi-Agent Graph Orchestration:** Read `.antigravity/skills/state_machine_agent_routing.md`

## Specialist Technical Roles

If your current task falls under a specific engineering domain, you must strictly adopt the boundaries mapped in these profile folders:

- **Product & Domain Control:** `.antigravity/skills/role_product_and_domain.md`
- **Data Engineering & Backend:** `.antigravity/skills/role_core_engineering.md`
- **Data Science & MLOps:** `.antigravity/skills/role_data_and_mlops.md`
- **Frontend & UI Interactions:** `.antigravity/skills/role_interface_and_ux.md`