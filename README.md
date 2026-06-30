# ProcureMind AI

ProcureMind AI is a multi-tenant, schema-driven procurement intelligence platform for Project Nika / TenderIQ. The system combines tenant-isolated API evaluation, configuration-driven procurement semantics, anomaly detection, reorder optimization, stress simulation, and executive report assembly into one validation-ready MVP.

The core invariant is strict separation between platform logic and industry vocabulary. Business semantics are read from `industry-config.json`; application code must not hardcode behavior for a specific industry vertical. Tenant data isolation is enforced through the API guard and database session layer, with Row-Level Security context carried by `app.current_tenant_id`.

## System Objectives

| Objective | Implementation Surface | Validation Gate |
| --- | --- | --- |
| Multi-tenant request isolation | `main.py`, `infra/database.py`, `tenant_session()` | Reject mismatched `X-Tenant-ID`; set `app.current_tenant_id` before tenant-scoped database work |
| Schema-driven procurement semantics | `industry-config.json`, `core/config_parser.py` | Dynamic labels, risk dimensions, validation rules, tenant profile, and flow metadata |
| Risk and anomaly intelligence | `core/anomaly_engine.py` | Isolation Forest scoring over tenant-local transaction vectors and contract deviation checks |
| Reorder optimization | `core/reorder_optimizer.py` | Minimum order quantity and demand plus safety stock constraints |
| Scenario simulation | `core/scenario_simulator.py` | Counterfactual perturbation of demand, lead time, inventory, and cost parameters |
| Executive reporting | `core/executive_reporter.py` | Dense Markdown prompt package for local LLM or executive panel consumption |
| Frontend dashboard shell | `web/` | Next.js 14 App Router, TypeScript, Tailwind CSS, config-derived dashboard labels |
| End-to-end MVP verification | `scripts/run_integration_harness.py` | `uv run` integration harness with asserts across parser, tenant guard, gateway, anomaly engine, optimizer, simulator, and reporter |

## Architectural Invariants

### 1. Cross-Industry Schema Control

The platform is designed as a procurement engine whose runtime vocabulary comes from `industry-config.json`.

- `entity_mapping.node_types` defines abstract platform actors such as buyer and seller nodes.
- `entity_mapping.flow_types` defines transactional flow vocabulary and concurrency limits.
- `entity_mapping.attribute_registry` defines typed domain attributes, constraints, searchability, and PII status.
- `risk_engine.risk_dimensions` defines weighted, normalized risk features and thresholds.
- `tenant_profile` defines the active tenant identifier, name, tier, feature flags, and limits.

No backend or frontend module should branch on a named industry. UI labels and business terms should be derived from config whenever the information is available there.

### 2. Multi-Tenancy and RLS Boundary

The backend follows a shared database model with Row-Level Security. Every transactional data access path must establish a tenant context before database work:

```sql
SET LOCAL app.current_tenant_id = :tenant_id
```

The API layer validates `X-Tenant-ID` against `CONFIG.tenant_profile.tenant_id`. A mismatched or missing tenant identifier must fail cleanly before domain evaluation or database work proceeds.

### 3. Data Flow Topology

The target data topology follows a Medallion model:

| Layer | Responsibility | Mutation Rule |
| --- | --- | --- |
| Bronze | Raw ingestion records and source-aligned payloads | Append source payloads; avoid business mutation |
| Silver | Validated, normalized, schema-conformant records | Runtime schema validation before controller entry |
| Gold | Analytics, graph objects, scoring views, and reportable aggregates | Read-optimized analytical structures |

Private tenant configuration and transaction data must not propagate into shared public market features.

### 4. Intelligence Layer

The current MVP implements deterministic and statistical decision modules:

- `ProcurementAnomalyEngine` fits tenant-local historical records with `sklearn.ensemble.IsolationForest`.
- Vendor nodes are encoded through target encoding over historical transaction values.
- Maverick spend is flagged when a transaction is off-contract, materially deviates from negotiated rates, or is classified as an Isolation Forest outlier.
- `SmartReorderOptimizer` solves the minimum feasible order quantity satisfying:
  - `Order Quantity >= MOQ`
  - `Current Inventory + Order Quantity >= Forecast Demand + Safety Stock`
- `ProcurementScenarioSimulator` applies perturbation matrices such as demand multipliers, lead-time delays, inflation, inventory shocks, and safety-stock shifts.
- `ExecutiveAIFormatter` assembles local Markdown reports without live HTTP clients or external API secrets.

## Repository Layout

| Path | Role |
| --- | --- |
| `core/` | Pydantic config parsing, CEL-style validation, anomaly scoring, reorder optimization, scenario simulation, and executive report formatting |
| `infra/` | SQLAlchemy async engine, tenant session context, RLS setup, and database model definitions |
| `scripts/` | Synthetic data generation and executable validation harnesses |
| `web/` | Next.js 14 App Router frontend for the ProcureMind AI operational dashboard |
| `.antigravity/` | Agent rulebook, role constraints, architectural blueprint, backlog, and technical-debt ledger |
| `industry-config.json` | Active tenant and procurement-domain configuration |
| `industry-config.schema.json` | Cross-industry metaschema for portable procurement deployments |

## Backend Quick Start

Use `uv` execution gates for backend validation and harness execution.

```bash
uv sync
```

```bash
uv run python -m compileall .
```

```bash
uv run python scripts/run_integration_harness.py
```

```bash
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Expected harness behavior:

- Loads the Central Coalfields Limited tenant profile from `industry-config.json`.
- Verifies a matching `X-Tenant-ID`.
- Verifies a compromised UUID receives clean `HTTP 403` handling.
- Evaluates a valid bid payload through `main.py`.
- Scores valid and anomalous transactions through the Isolation Forest anomaly engine.
- Optimizes reorder quantity under MOQ and demand coverage constraints.
- Runs inflation and logistics-delay scenario simulation.
- Emits an executive Markdown report payload.

## Frontend Quick Start

The frontend is isolated under `web/`.

```bash
cd web
npm install
npm run lint
npx tsc --noEmit
npm run build
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Core frontend routes:

| Route | Purpose |
| --- | --- |
| `/` | ProcureMind AI dashboard shell and Explore Insights grid |
| `/about` | Technical and capstone context view |
| `/anomalies` | Risk and anomaly command surface |
| `/recommendations` | Recommendation list surface |

## API Gateway Contract

`main.py` exposes the active procurement bid evaluation flow:

- `POST /api/v1/procurement/bids/evaluate`
- Required tenant header: `X-Tenant-ID`
- Request model: `BidSubmission`
- Response model: `EvaluationResponse`

Risk scoring is driven by `CONFIG.risk_engine.risk_dimensions`. Risk bands are selected from configured thresholds, sorted by descending threshold value.

## 🏋️‍♂️ Production Reliability & Stress-Test Validation

The Phase 6 network hardening validation exercised the FastAPI gateway under production-shaped load and explicit malformed-payload chaos conditions.

| Validation Layer | Verified Result |
| --- | --- |
| Load volume | 1,000 requests |
| Peak concurrency | 100 concurrency |
| Sustained throughput | 100.52 req/s |
| Timeout stability | 0 ReadTimeouts |

Chaos validation confirmed that the runtime boundary stays closed under malformed simulator traffic. Strict Pydantic `SimulationMatrix` schemas reject unknown fields and out-of-range perturbation values before controller execution, while the custom gateway error shield converts failures into structured tracking blocks instead of raw traces.

All 50 malformed vectors were intercepted cleanly with explicit governance markers:

- `[VALIDATION_ERROR]` for malformed or schema-invalid payloads, including invalid wrapped `{"matrix": SimulationMatrix}` requests.
- `[TENANT_AUTH_ERROR]` for tenant header mismatches or missing tenant context before domain evaluation.

These outcomes validate that stress traffic, validation failures, and tenant-auth failures remain observable without bypassing the RLS-aligned tenant boundary or crashing frontend Server Component hydration paths.

## Security and Runtime Guardrails

- Never bypass `app.current_tenant_id`.
- Never construct open-ended tenant queries without verified session context.
- Do not hardcode behavior for a named industry vertical.
- Validate all boundary payloads through runtime schema models before controller execution.
- Avoid raw database stack traces in frontend responses.
- Do not instantiate live LLM HTTP clients in report-formatting modules.
- Keep generated frontend layouts schema-driven where config values exist.

## MVP Verification Matrix

| Verification | Command |
| --- | --- |
| Python syntax compilation | `uv run python -m compileall .` |
| End-to-end harness | `uv run python scripts/run_integration_harness.py` |
| Next lint | `cd web && npm run lint` |
| Next type check | `cd web && npx tsc --noEmit` |
| Next production build | `cd web && npm run build` |

## Known Debt

The authoritative backlog and debt ledger is `.antigravity/backlog_and_debt.md`.

Current active technical debt includes:

- `main.py`: FastAPI uses an in-memory configuration singleton. Target mitigation is request-scoped dependency injection.
- `core/anomaly_engine.py`: Isolation Forest training is static on initial load. Target mitigation is a rolling asynchronous fitting worker.

Resolved optimization debt includes:

- `infra/database.py`: removed heavy unused graph relationships and GIN index setup.
- `scripts/generate_synthetic_data.py`: removed heavy pandas/numpy dependency from synthetic generation loops.


## 🚀 Production Deployment & Multi-Container Boot

This section describes how to configure, compile, and run the entire multi-container application locally using Docker Compose in a production configuration.

### 1. Environmental Setup
Duplicate the production template configuration to create a working `.env.production` file:
```bash
cp .env.production.example .env.production
```
Make sure to fill in any required credentials in `.env.production`, such as model provider API keys (`OPENAI_API_KEY`, `GEMINI_API_KEY`) if needed.

### 2. Multi-Container Orchestration & Compilation
Compile and spin up the production container network in detached mode using the production compose configuration:
```bash
docker compose -f docker-compose.prod.yml up --build -d
```
This builds both multi-stage containers (`pm-backend` and `pm-frontend`) and launches PostgreSQL (`pm-db`), binding them to a shared network bridge with appropriate database health checks.

### 3. Local Target URL Verification
Once the container boot sequence completes, verify the service endpoints locally:
- **Operational Frontend Dashboard**: http://localhost:3001
- **Headless Backend API Engine**: http://127.0.0.1:8000

