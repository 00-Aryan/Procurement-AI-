import { AlertTriangle, ShieldCheck } from "lucide-react";

import { tenantProfile } from "@/lib/dashboard";

export default function AnomaliesPage() {
  return (
    <div className="min-h-screen px-12 py-10">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-950">Risk & Anomalies</h1>
          <p className="mt-2 text-sm text-slate-600">{tenantProfile.tenant_name} anomaly command center</p>
        </div>
        <div className="flex h-10 items-center gap-2 rounded-md border border-indigo-100 bg-white px-4 text-sm font-semibold text-indigo-600 shadow-soft">
          <ShieldCheck className="h-4 w-4" />
          Tenant scoped
        </div>
      </header>

      <section className="mt-8 grid gap-5 md:grid-cols-3">
        {[
          ["Total Risks Detected", "18", "8 resolved this cycle"],
          ["High Risk", "5", "requires review"],
          ["Medium Risk", "8", "monitored by rules"]
        ].map(([label, value, detail]) => (
          <div key={label} className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-500">{label}</span>
              <AlertTriangle className="h-5 w-5 text-indigo-500" />
            </div>
            <div className="mt-4 text-3xl font-bold text-slate-950">{value}</div>
            <div className="mt-2 text-sm text-slate-500">{detail}</div>
          </div>
        ))}
      </section>
    </div>
  );
}
