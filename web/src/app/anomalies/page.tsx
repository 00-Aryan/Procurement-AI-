import { AlertTriangle, ShieldCheck } from "lucide-react";

import { GovernanceBoundaryAlert } from "@/components/GovernanceBoundaryAlert";
import { tenantProfile } from "@/lib/dashboard";
import { GatewayGovernanceError, throwGatewayGovernanceError } from "@/lib/gatewayErrors";
import type { GatewayGovernanceBoundary } from "@/lib/gatewayErrors";

export const dynamic = "force-dynamic";

const DEFAULT_TENANT_ID = "f7a2b4c9-3d1e-4f8a-b5c2-9e0d1a2b3c4d";

type AnomaliesData = {
  total_risks: number;
  high_risk: number;
  medium_risk: number;
  resolved_this_cycle: number;
};

type AnomaliesFetchResult = {
  data: AnomaliesData;
  governanceBoundary: GatewayGovernanceBoundary | null;
};

const FALLBACK_ANOMALIES_DATA: AnomaliesData = {
  total_risks: 18,
  high_risk: 5,
  medium_risk: 8,
  resolved_this_cycle: 8
};

async function fetchAnomaliesData(): Promise<AnomaliesFetchResult> {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/v1/procurement/anomalies", {
      headers: {
        "X-Tenant-ID": DEFAULT_TENANT_ID,
      },
      next: { revalidate: 0 }
    });
    if (!res.ok) {
      await throwGatewayGovernanceError(res);
    }
    return { data: await res.json() as AnomaliesData, governanceBoundary: null };
  } catch (error) {
    if (error instanceof GatewayGovernanceError) {
      return { data: FALLBACK_ANOMALIES_DATA, governanceBoundary: error.boundary };
    }

    return { data: FALLBACK_ANOMALIES_DATA, governanceBoundary: null };
  }
}

export default async function AnomaliesPage() {
  const { data, governanceBoundary } = await fetchAnomaliesData();

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

      {governanceBoundary ? (
        <GovernanceBoundaryAlert boundary={governanceBoundary} surface="Risk and anomalies" />
      ) : null}

      <section className="mt-8 grid gap-5 md:grid-cols-3">
        {[
          ["Total Risks Detected", String(data.total_risks), `${data.resolved_this_cycle} resolved this cycle`],
          ["High Risk", String(data.high_risk), "requires review"],
          ["Medium Risk", String(data.medium_risk), "monitored by rules"]
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
