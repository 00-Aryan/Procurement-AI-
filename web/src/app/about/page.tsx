import { Banknote, Boxes, Building2, ChevronDown, Cpu, FileCheck2, Gauge, Landmark, LockKeyhole, Scale, ShieldCheck, Zap } from "lucide-react";

import { tenantProfile } from "@/lib/dashboard";

export default function AboutPage() {
  return (
    <div className="min-h-screen px-12 py-12 bg-slate-50 text-slate-800">
      {/* Header Segment */}
      <header className="max-w-6xl pb-8 border-b border-slate-200">
        <div className="inline-flex h-10 items-center gap-2 rounded-md border border-indigo-100 bg-white px-4 text-sm font-semibold text-indigo-600 shadow-soft">
          <Building2 className="h-4 w-4" />
          Enterprise Assurance Core
        </div>
        <h1 className="mt-6 max-w-5xl text-4xl font-extrabold tracking-tight text-slate-950 sm:text-5xl">
          ProcureMind AI — Operational Governance & Value Assurance Platform
        </h1>
        <p className="mt-4 max-w-4xl text-lg leading-8 text-slate-600">
          A unified, metadata-driven command layer built to enforce capital efficiency, isolate maverick spend,
          and secure strict tenant isolation across regulated high-velocity procurement environments.
        </p>
      </header>

      {/* Stats Quick Grid */}
      <section className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Active Enterprise", value: tenantProfile.tenant_name, icon: Building2 },
          { label: "Governance Posture", value: tenantProfile.tier, icon: ShieldCheck },
          { label: "Isolation Protocol", value: "Row-Level Security Active", icon: LockKeyhole },
          { label: "Assurance Focus", value: "Capital Leakage Prevention", icon: Scale }
        ].map((metric) => {
          const Icon = metric.icon;
          return (
            <div key={metric.label} className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft transition hover:border-slate-300">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{metric.label}</span>
                  <div className="mt-3 text-lg font-bold text-slate-900">{metric.value}</div>
                </div>
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
                  <Icon className="h-5 w-5" />
                </div>
              </div>
            </div>
          );
        })}
      </section>

      {/* Deep Whitepaper Strategic Sections */}
      <section className="mt-16 space-y-16 max-w-6xl">
        
        {/* Section 1: CEO focus */}
        <article className="rounded-xl border border-slate-200 bg-white p-8 shadow-soft relative overflow-hidden">
          <div className="absolute top-0 left-0 w-2 h-full bg-indigo-600" />
          <span className="text-xs font-bold uppercase tracking-widest text-indigo-600">Operational Continuity & Capital Efficiency</span>
          <h2 className="mt-4 text-2xl font-extrabold text-slate-950 sm:text-3xl leading-tight">
            How do you eliminate supply chain amnesia before it freezes millions in unoptimized operational capital?
          </h2>
          <p className="mt-4 text-base leading-7 text-slate-600">
            For chief executives, supply chain disruptions and static forecasting present immediate capital risks. ProcureMind AI eliminates operational blind spots through continuous inventory stress simulation. By evaluating demand multipliers and logistically delayed lead times, the platform dynamically calculates stockout hazard scales and optimizes reorder paths. Rather than reactive planning, you secure absolute operating continuity while maintaining lean capital reserves.
          </p>
          <div className="mt-8 grid gap-6 sm:grid-cols-3 border-t border-slate-100 pt-6">
            <div>
              <h4 className="text-sm font-bold text-slate-950">Capital Containment</h4>
              <p className="mt-1 text-sm text-slate-600">Minimizes overbuying and avoids excessive holding costs through linear-bound optimization models.</p>
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-950">Continuity Assurance</h4>
              <p className="mt-1 text-sm text-slate-600">Predictive stress testing identifies stock depletion threats before they propagate into downstream delays.</p>
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-950">Asset Agility</h4>
              <p className="mt-1 text-sm text-slate-600">Ensures inventory allocation reacts dynamically to shifting vendor lead times and market shocks.</p>
            </div>
          </div>
        </article>

        {/* Section 2: CFO focus */}
        <article className="rounded-xl border border-slate-200 bg-white p-8 shadow-soft relative overflow-hidden">
          <div className="absolute top-0 left-0 w-2 h-full bg-rose-500" />
          <span className="text-xs font-bold uppercase tracking-widest text-rose-500">Value Protection & Maverick Spend Control</span>
          <h2 className="mt-4 text-2xl font-extrabold text-slate-950 sm:text-3xl leading-tight">
            Are invisible contract leakages quietly draining your bottom-line profitability weeks before your audits even begin?
          </h2>
          <p className="mt-4 text-base leading-7 text-slate-600">
            CFOs struggle with maverick spending—purchases routed off-contract or at prices deviating from negotiated vendor agreements. ProcureMind AI employs an unsupervised Isolation Forest anomaly engine to score transaction streams in real time. The model detects outliers based on rate deviations and off-contract vendor nodes, immediately flagging them for review before capital departs the enterprise.
          </p>
          <div className="mt-8 grid gap-6 sm:grid-cols-3 border-t border-slate-100 pt-6">
            <div>
              <h4 className="text-sm font-bold text-slate-950">Outlier Detection</h4>
              <p className="mt-1 text-sm text-slate-600">Isolation Forest algorithms isolate non-standard behaviors without requiring manual rules.</p>
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-950">Leakage Defense</h4>
              <p className="mt-1 text-sm text-slate-600">Instantly flags deviation in negotiated contract rates at ingestion boundaries.</p>
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-950">Audit Trails</h4>
              <p className="mt-1 text-sm text-slate-600">Chronological telemetry snapshots map every flagged exception for comprehensive governance reviews.</p>
            </div>
          </div>
        </article>

        {/* Section 3: CTO focus */}
        <article className="rounded-xl border border-slate-200 bg-white p-8 shadow-soft relative overflow-hidden">
          <div className="absolute top-0 left-0 w-2 h-full bg-emerald-500" />
          <span className="text-xs font-bold uppercase tracking-widest text-emerald-500">Data Architecture & Metadata Isolation</span>
          <h2 className="mt-4 text-2xl font-extrabold text-slate-950 sm:text-3xl leading-tight">
            Can an enterprise core adapt to shifting cross-industry compliance frameworks instantly without rewriting a single line of backend code?
          </h2>
          <p className="mt-4 text-base leading-7 text-slate-600">
            For the technical leadership, ProcureMind AI provides a metadata-driven schema model. Rather than hardcoding vertical boundaries or compliance limits, the core engine parses rules, constraints, and thresholds dynamically from configuration profiles. Strict tenant isolation is enforced at the database layer using async SQLAlchemy context sessions mapping directly to Row-Level Security (RLS) policies, preventing cross-tenant data leaks.
          </p>
          <div className="mt-8 grid gap-6 sm:grid-cols-3 border-t border-slate-100 pt-6">
            <div>
              <h4 className="text-sm font-bold text-slate-950">Metadata Independence</h4>
              <p className="mt-1 text-sm text-slate-600">Validation, scoring models, and gates load dynamically from isolated JSON profiles.</p>
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-950">Absolute RLS Isolation</h4>
              <p className="mt-1 text-sm text-slate-600">Guarantees data integrity by isolating connection scopes to active tenant IDs at session boundaries.</p>
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-950">Low-Latency Processing</h4>
              <p className="mt-1 text-sm text-slate-600">Executes optimized Python routines locally to deliver instant anomaly scores and optimization deltas.</p>
            </div>
          </div>
        </article>

      </section>

      {/* Governance Controls Bar */}
      <section className="mt-16 rounded-xl border border-indigo-100 bg-white p-6 shadow-soft max-w-6xl">
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-4">
          {[
            { label: "Rate Limits", value: `${tenantProfile.rate_limits.api_requests_per_minute} API requests/min`, icon: Gauge },
            { label: "Flow Capacity", value: `${tenantProfile.rate_limits.max_concurrent_flows} concurrent flows`, icon: Zap },
            { label: "Tender Capacity", value: `${tenantProfile.rate_limits.max_active_tenders} active tenders`, icon: Boxes },
            { label: "Compliance Profile", value: "GFR 2017 & GeM Aligned", icon: FileCheck2 }
          ].map((control) => {
            const Icon = control.icon;
            return (
              <div key={control.label} className="flex items-center gap-4 rounded-md border border-slate-100 bg-slate-50 p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white text-indigo-600 shadow-soft">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-semibold uppercase text-slate-400">{control.label}</div>
                  <div className="mt-1 truncate text-sm font-bold text-slate-950">{control.value}</div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Expanded FAQ Segment */}
      <section className="mt-16 rounded-xl border border-slate-200 bg-white shadow-soft max-w-6xl overflow-hidden">
        <div className="border-b border-slate-200 p-8 bg-slate-50/50">
          <div className="text-xs font-bold uppercase tracking-wider text-indigo-600">Security & Integration Protocol</div>
          <h2 className="mt-2 text-2xl font-bold text-slate-950">Service Governance & Isolation FAQ</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">
            Answers for enterprise risk officers evaluating compliance alignments, tenant isolation architecture, and database-level security guardrails.
          </p>
        </div>

        <div className="divide-y divide-slate-200">
          {[
            {
              question: "How does ProcureMind AI ensure strict data isolation in shared database environments?",
              answer: "The backend isolates data at the database boundary. Every transaction, node, and session query binds the active `X-Tenant-ID` as a mandatory parameter context. Database sessions wrap queries inside async connection contexts where Row-Level Security (RLS) prevents database sessions from accessing or modifying data from other tenant records, ensuring zero tenant cross-contamination."
            },
            {
              question: "What is a 'Service Governance Level'?",
              answer: "A Service Governance Level is a schema-defined metadata structure that configures limits and validation standards based on the tenant tier. In government tiers, operations are verified against General Financial Rules (GFR 2017) and Government e-Marketplace (GeM) requirements. This enforces compliance controls, such as minimum window policies and seller compliance checks, for major corporate entities like Central Coalfields Limited."
            },
            {
              question: "How does ProcureMind AI protect negotiated contract rates?",
              answer: "The platform's rule engine evaluates every bid and invoice against rate boundaries defined in the schema. When rate deviation anomalies are detected, they are immediately flagged by the unsupervised anomaly scoring engine, helping to isolate and block Maverick Spend."
            },
            {
              question: "Why does the platform use a metadata-driven approach rather than hardcoded rules?",
              answer: "A metadata-driven approach ensures the platform remains vertical-agnostic and resilient to changing compliance laws. By loading validation rules, disqualification gates, and risk band thresholds dynamically from active configuration schemas, changes can be rolled out across the platform instantly without modifying backend source code."
            }
          ].map((item) => (
            <details key={item.question} className="group p-6">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-6 text-left focus:outline-none">
                <span className="text-base font-bold text-slate-950 hover:text-indigo-600 transition">{item.question}</span>
                <ChevronDown className="h-5 w-5 shrink-0 text-indigo-600 transition group-open:rotate-180" />
              </summary>
              <p className="mt-4 text-sm leading-7 text-slate-600 whitespace-pre-line">{item.answer}</p>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}
