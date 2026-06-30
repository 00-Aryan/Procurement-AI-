import { ShieldAlert } from "lucide-react";

import type { GatewayGovernanceBoundary } from "@/lib/gatewayErrors";

type GovernanceBoundaryAlertProps = {
  boundary: GatewayGovernanceBoundary;
  surface: string;
};

export function GovernanceBoundaryAlert({ boundary, surface }: GovernanceBoundaryAlertProps) {
  return (
    <section
      role="alert"
      className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-5 text-amber-950 shadow-soft"
    >
      <div className="flex gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-white text-amber-700">
          <ShieldAlert className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <h2 className="text-base font-bold">Governance boundary enforced</h2>
          <p className="mt-1 text-sm leading-6 text-amber-900">
            {surface} is showing safe fallback telemetry because the backend rejected this hydration request at a
            tenant or validation boundary. Primary navigation remains available while the upstream payload is corrected.
          </p>
          <div className="mt-3 rounded-md border border-amber-200 bg-white px-3 py-2 text-xs font-semibold text-amber-800">
            <span>{boundary.marker}</span>
            <span className="mx-2 text-amber-400">|</span>
            <span>HTTP {boundary.status}</span>
            <p className="mt-1 break-words font-mono font-normal text-amber-900">{boundary.metadata}</p>
          </div>
        </div>
      </div>
    </section>
  );
}
