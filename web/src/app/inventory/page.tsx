"use client";

import { useState, useTransition } from "react";
import { Boxes, Play, RefreshCw, AlertTriangle } from "lucide-react";
import { executeScenarioSimulation } from "../actions";

export default function InventoryPage() {
  const [demandMultiplier, setDemandMultiplier] = useState(1.15);
  const [leadTimeDelay, setLeadTimeDelay] = useState(5);
  const [inflationRate, setInflationRate] = useState(0.08);

  const [isPending, startTransition] = useTransition();
  const [simulationResult, setSimulationResult] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSimulate = () => {
    setErrorMessage(null);
    startTransition(async () => {
      try {
        const matrix = {
          scenario_name: "custom_interactive_stress_test",
          demand_multiplier: demandMultiplier,
          lead_time_delay_days: leadTimeDelay,
          inflation_rate: inflationRate
        };
        const result = await executeScenarioSimulation(matrix);
        setSimulationResult(result);
      } catch (err: any) {
        setErrorMessage(err.message || "Failed to run simulation");
      }
    });
  };

  return (
    <div className="min-h-screen px-12 py-10 bg-slate-50">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-950">Inventory Intelligence & Simulation</h1>
          <p className="mt-2 text-sm text-slate-600">Deterministic inventory stress testing and reorder optimization</p>
        </div>
        <div className="flex h-10 items-center gap-2 rounded-md border border-indigo-100 bg-white px-4 text-sm font-semibold text-indigo-600 shadow-soft">
          <Boxes className="h-4 w-4" />
          Simulation sandbox
        </div>
      </header>

      <div className="mt-8 grid gap-8 lg:grid-cols-3">
        {/* Sliders Control Panel */}
        <section className="lg:col-span-1 rounded-lg border border-slate-200 bg-white p-6 shadow-soft space-y-6">
          <h2 className="text-lg font-bold text-slate-900 border-b pb-3">Stress Vector Factors</h2>
          
          <div className="space-y-2">
            <div className="flex justify-between text-sm font-medium text-slate-700">
              <label htmlFor="demand-slider">Demand Multiplier</label>
              <span className="text-indigo-600 font-bold">{demandMultiplier.toFixed(2)}x</span>
            </div>
            <input
              id="demand-slider"
              type="range"
              min="0.5"
              max="2.0"
              step="0.05"
              value={demandMultiplier}
              onChange={(e) => setDemandMultiplier(parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-sm font-medium text-slate-700">
              <label htmlFor="lead-time-slider">Lead Time Delay (Days)</label>
              <span className="text-indigo-600 font-bold">+{leadTimeDelay} days</span>
            </div>
            <input
              id="lead-time-slider"
              type="range"
              min="0"
              max="30"
              step="1"
              value={leadTimeDelay}
              onChange={(e) => setLeadTimeDelay(parseInt(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-sm font-medium text-slate-700">
              <label htmlFor="inflation-slider">Inflation Rate</label>
              <span className="text-indigo-600 font-bold">{(inflationRate * 100).toFixed(0)}%</span>
            </div>
            <input
              id="inflation-slider"
              type="range"
              min="-0.2"
              max="0.5"
              step="0.01"
              value={inflationRate}
              onChange={(e) => setInflationRate(parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
          </div>

          <button
            onClick={handleSimulate}
            disabled={isPending}
            className="w-full mt-4 flex items-center justify-center gap-2 rounded-md bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow hover:bg-indigo-700 transition disabled:opacity-50"
          >
            {isPending ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Simulating...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Run Stress Simulation
              </>
            )}
          </button>
        </section>

        {/* Results Panel */}
        <section className="lg:col-span-2 rounded-lg border border-slate-200 bg-white p-6 shadow-soft flex flex-col min-h-[350px]">
          <h2 className="text-lg font-bold text-slate-900 border-b pb-3">Simulation Results</h2>

          {errorMessage && (
            <div className="mt-4 rounded-md bg-red-50 p-4 text-sm text-red-600 flex items-center gap-2 border border-red-100">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {!simulationResult && !isPending && (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-400 py-12">
              <Boxes className="h-12 w-12 stroke-[1.5] mb-3 text-slate-300" />
              <p className="text-sm">Configure the stress vector variables and click run above to evaluate reorder impacts.</p>
            </div>
          )}

          {isPending && (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-400 py-12">
              <RefreshCw className="h-8 w-8 animate-spin mb-3 text-indigo-500" />
              <p className="text-sm">Running deterministic linear-bound reorder simulations...</p>
            </div>
          )}

          {simulationResult && !isPending && (
            <div className="mt-6 flex-1 space-y-6">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-md border border-slate-100 bg-slate-50 p-4">
                  <div className="text-xs font-semibold uppercase text-slate-400">Baseline Qty</div>
                  <div className="mt-2 text-2xl font-bold text-slate-900">{simulationResult.baseline_order_volume}</div>
                </div>
                <div className="rounded-md border border-slate-100 bg-slate-50 p-4">
                  <div className="text-xs font-semibold uppercase text-slate-400">Stressed Qty</div>
                  <div className="mt-2 text-2xl font-bold text-indigo-600">{simulationResult.stressed_order_volume}</div>
                </div>
                <div className="rounded-md border border-slate-100 bg-slate-50 p-4">
                  <div className="text-xs font-semibold uppercase text-slate-400">Hazard Scale</div>
                  <div className={`mt-2 text-lg font-bold ${
                    simulationResult.stockout_hazard_scale === "HIGH" ? "text-rose-600" :
                    simulationResult.stockout_hazard_scale === "MEDIUM" ? "text-amber-500" : "text-emerald-600"
                  }`}>{simulationResult.stockout_hazard_scale}</div>
                </div>
              </div>

              <div className="rounded-md border border-indigo-50 bg-indigo-50/50 p-5">
                <h3 className="text-sm font-bold text-indigo-900">Projected Financial Impact</h3>
                <div className="mt-2 text-3xl font-extrabold text-indigo-950">
                  +₹ {simulationResult.calculated_financial_delta.toFixed(2)} Lakhs
                </div>
                <p className="mt-2 text-xs text-indigo-700/80">
                  Calculated delta representing holding and ordering costs surcharge under the {demandMultiplier}x demand shock.
                </p>
              </div>

              <div className="border border-slate-100 rounded-md p-4 space-y-2">
                <h3 className="text-xs font-semibold uppercase text-slate-400">Active Stockout Drivers</h3>
                <div className="flex flex-wrap gap-2 mt-2">
                  {simulationResult.stockout_risk?.drivers.map((driver: string) => (
                    <span key={driver} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 border border-slate-200">
                      {driver.replace("_", " ")}
                    </span>
                  ))}
                  {simulationResult.stockout_risk?.drivers.length === 0 && (
                    <span className="text-xs text-slate-500">None detected</span>
                  )}
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
