"use client";

import React from "react";

interface AnalyticsSkeletonProps {
  type?: "all" | "risk-chart" | "stockout-counter" | "recommendation-card";
  count?: number;
}

export function RiskChartSkeleton() {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-4">
        <div className="space-y-2">
          <div className="h-5 w-48 rounded bg-slate-800/80 animate-pulse" />
          <div className="h-3.5 w-32 rounded bg-slate-800/40 animate-pulse" />
        </div>
        <div className="h-8 w-24 rounded bg-slate-800/60 animate-pulse" />
      </div>

      {/* Simulated Chart Bars */}
      <div className="mt-8 flex h-48 items-end justify-between gap-3 px-2">
        {[65, 45, 80, 55, 95, 30, 70, 85, 40, 60, 75, 50].map((height, i) => (
          <div key={i} className="flex flex-1 flex-col items-center gap-2">
            <div
              className="w-full rounded-t bg-slate-800/70 animate-pulse"
              style={{ height: `${height}%` }}
            />
            <div className="h-3 w-8 rounded bg-slate-800/30 animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function StockoutCounterSkeleton() {
  return (
    <div className="grid gap-5 md:grid-cols-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
          <div className="flex items-center justify-between">
            <div className="h-4 w-32 rounded bg-slate-800/60 animate-pulse" />
            <div className="h-5 w-5 rounded-full bg-slate-800/40 animate-pulse" />
          </div>
          <div className="mt-4 h-10 w-20 rounded bg-slate-800/80 animate-pulse" />
          <div className="mt-2 h-3.5 w-40 rounded bg-slate-800/40 animate-pulse" />
        </div>
      ))}
    </div>
  );
}

export function RecommendationCardSkeleton({ count = 2 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div className="space-y-3 flex-1">
              <div className="flex items-center gap-3">
                <div className="h-6 w-24 rounded-full bg-slate-800/75 animate-pulse" />
                <div className="h-5 w-40 rounded bg-slate-800/40 animate-pulse" />
              </div>
              <div className="space-y-2">
                <div className="h-4 w-full rounded bg-slate-800/60 animate-pulse" />
                <div className="h-4 w-4/5 rounded bg-slate-800/50 animate-pulse" />
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-3 self-end md:self-start">
              <div className="h-9 w-24 rounded bg-slate-800/70 animate-pulse" />
              <div className="h-9 w-20 rounded bg-slate-800/40 animate-pulse" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function AnalyticsSkeleton({ type = "all", count = 2 }: AnalyticsSkeletonProps) {
  if (type === "risk-chart") {
    return <RiskChartSkeleton />;
  }

  if (type === "stockout-counter") {
    return <StockoutCounterSkeleton />;
  }

  if (type === "recommendation-card") {
    return <RecommendationCardSkeleton count={count} />;
  }

  return (
    <div className="space-y-8">
      <div>
        <div className="mb-4 h-5 w-40 rounded bg-slate-800/80 animate-pulse" />
        <StockoutCounterSkeleton />
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <div className="md:col-span-2">
          <div className="mb-4 h-5 w-44 rounded bg-slate-800/80 animate-pulse" />
          <RiskChartSkeleton />
        </div>
        <div>
          <div className="mb-4 h-5 w-48 rounded bg-slate-800/80 animate-pulse" />
          <RecommendationCardSkeleton count={2} />
        </div>
      </div>
    </div>
  );
}
