"use client";

import React, { useState } from "react";
import { ShieldCheck, Database, CheckCircle, AlertTriangle } from "lucide-react";

import { MultiFileDropzone } from "@/components/MultiFileDropzone";
import { AnalyticsSkeleton } from "@/components/AnalyticsSkeleton";
import { GovernanceBoundaryAlert } from "@/components/GovernanceBoundaryAlert";
import { tenantProfile } from "@/lib/dashboard";
import type { GatewayGovernanceBoundary } from "@/lib/gatewayErrors";

export default function IngestionPage() {
  const [governanceBoundary, setGovernanceBoundary] = useState<GatewayGovernanceBoundary | null>(null);
  const [successInfo, setSuccessInfo] = useState<{
    vectors: string[];
    rows: number;
    timestamp: string;
  } | null>(null);

  const handleUploadSuccess = (stagedVectors: string[], stagedRows: number) => {
    setSuccessInfo({
      vectors: stagedVectors,
      rows: stagedRows,
      timestamp: new Date().toLocaleTimeString()
    });
    setGovernanceBoundary(null);
  };

  const handleClearError = () => {
    setGovernanceBoundary(null);
    setSuccessInfo(null);
  };

  return (
    <div className="min-h-screen px-12 py-10 overflow-y-auto">
      {/* Scrollable Layout Frame wrapped with space-y-8 */}
      <div className="mx-auto max-w-7xl space-y-8">
        
        {/* Page Header */}
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-200/60 pb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Data Gateway</h1>
            <p className="mt-2 text-sm text-slate-600">
              Ingest, parse, and validate multi-tenant business vectors to hydrate downstream analytics.
            </p>
          </div>
          <div className="flex h-10 items-center gap-2 self-start rounded-md border border-indigo-100 bg-white px-4 text-sm font-semibold text-indigo-600 shadow-soft sm:self-center">
            <ShieldCheck className="h-4 w-4" />
            <span>Tenant: {tenantProfile.tenant_name}</span>
          </div>
        </header>

        {/* Hydra-injected Governance Boundary Alert Banner */}
        {governanceBoundary && (
          <div className="animate-in fade-in slide-in-from-top-4 duration-300">
            <GovernanceBoundaryAlert
              boundary={governanceBoundary}
              surface="Data Ingestion Gateway"
            />
          </div>
        )}

        {/* Success Alert Banner */}
        {successInfo && (
          <div className="flex items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-5 text-emerald-950 shadow-soft animate-in fade-in slide-in-from-top-4 duration-300">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-white text-emerald-700">
              <CheckCircle className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-base font-bold">Data Ingestion Complete</h2>
              <p className="mt-1 text-sm text-emerald-900 leading-5">
                Staging completed successfully at <span className="font-semibold">{successInfo.timestamp}</span>. 
                Ingested <span className="font-semibold">{successInfo.vectors.length}</span> vectors 
                (<span className="font-mono text-xs">{successInfo.vectors.join(", ")}</span>) staging a total of{" "}
                <span className="font-semibold">{successInfo.rows}</span> records in PostgreSQL.
              </p>
            </div>
          </div>
        )}

        {/* Multi-File Dropzone Section */}
        <section className="space-y-4">
          <div className="border-l-4 border-indigo-600 pl-4">
            <h2 className="text-lg font-bold text-slate-950 flex items-center gap-2">
              <Database className="h-5 w-5 text-indigo-600" />
              <span>Multi-File Vector Staging Area</span>
            </h2>
            <p className="text-sm text-slate-500">
              Stage files for Purchase History, Inventory, Suppliers, Demand, and Economics.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-soft">
            <MultiFileDropzone
              onUploadError={setGovernanceBoundary}
              onUploadSuccess={handleUploadSuccess}
              onClearError={handleClearError}
            />
          </div>
        </section>

        {/* Analytics Skeletons Preview Section */}
        <section className="space-y-4">
          <div className="border-l-4 border-indigo-600 pl-4">
            <h2 className="text-lg font-bold text-slate-950 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-indigo-600" />
              <span>Operational Forecasts & Analytics Preview</span>
            </h2>
            <p className="text-sm text-slate-500">
              Downstream intelligence models will refresh dynamically once staged vectors are committed.
            </p>
          </div>
          
          {/* Shimmering skeletons replicate the target charts layout-stable */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-6">
            <AnalyticsSkeleton type="all" />
          </div>
        </section>

      </div>
    </div>
  );
}
