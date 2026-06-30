"use client";

import React, { useState, useRef } from "react";
import {
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileText,
  X,
  TrendingUp,
  Boxes,
  UsersRound,
  Signal,
  Globe,
  Database
} from "lucide-react";
import { BACKEND_URL } from "@/lib/api";
import { GatewayGovernanceError, throwGatewayGovernanceError } from "@/lib/gatewayErrors";
import type { GatewayGovernanceBoundary } from "@/lib/gatewayErrors";

const DEFAULT_TENANT_ID = "f7a2b4c9-3d1e-4f8a-b5c2-9e0d1a2b3c4d";

export type UploadStatus = "idle" | "selected" | "uploading" | "processing" | "success" | "error";

export interface VectorState {
  file: File | null;
  status: UploadStatus;
  progress: number;
  errorMsg?: string;
}

interface MultiFileDropzoneProps {
  onUploadError?: (boundary: GatewayGovernanceBoundary) => void;
  onUploadSuccess?: (stagedVectors: string[], stagedRows: number) => void;
  onClearError?: () => void;
}

interface VectorConfig {
  key: "purchase_history" | "inventory_health" | "supplier_profiles" | "demand_signals" | "economic_indicators";
  label: string;
  description: string;
  icon: React.ComponentType<any>;
}

const BUSINESS_VECTORS: VectorConfig[] = [
  {
    key: "purchase_history",
    label: "Purchase History",
    description: "Historical transactions & purchase orders",
    icon: FileText
  },
  {
    key: "inventory_health",
    label: "Inventory Health",
    description: "Current stock levels & health metrics",
    icon: Boxes
  },
  {
    key: "supplier_profiles",
    label: "Supplier Profiles",
    description: "Supplier performance & validation status",
    icon: UsersRound
  },
  {
    key: "demand_signals",
    label: "Demand Signals",
    description: "Market demand forecasts & consumption speed",
    icon: Signal
  },
  {
    key: "economic_indicators",
    label: "Economic Indicators",
    description: "Macroeconomic indices & external signals",
    icon: Globe
  }
];

export function MultiFileDropzone({
  onUploadError,
  onUploadSuccess,
  onClearError
}: MultiFileDropzoneProps) {
  const [states, setStates] = useState<Record<string, VectorState>>({
    purchase_history: { file: null, status: "idle", progress: 0 },
    inventory_health: { file: null, status: "idle", progress: 0 },
    supplier_profiles: { file: null, status: "idle", progress: 0 },
    demand_signals: { file: null, status: "idle", progress: 0 },
    economic_indicators: { file: null, status: "idle", progress: 0 }
  });

  const [dragOverVector, setDragOverVector] = useState<string | null>(null);
  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const handleFileChange = (vectorKey: string, file: File | null) => {
    if (onClearError) onClearError();
    setStates((prev) => ({
      ...prev,
      [vectorKey]: file
        ? { file, status: "selected", progress: 0 }
        : { file: null, status: "idle", progress: 0 }
    }));
  };

  const handleDragOver = (e: React.DragEvent, vectorKey: string) => {
    e.preventDefault();
    setDragOverVector(vectorKey);
  };

  const handleDragLeave = () => {
    setDragOverVector(null);
  };

  const handleDrop = (e: React.DragEvent, vectorKey: string) => {
    e.preventDefault();
    setDragOverVector(null);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFileChange(vectorKey, files[0]);
    }
  };

  const handleRemoveFile = (e: React.MouseEvent, vectorKey: string) => {
    e.stopPropagation();
    handleFileChange(vectorKey, null);
    if (fileInputRefs.current[vectorKey]) {
      fileInputRefs.current[vectorKey]!.value = "";
    }
  };

  const triggerUpload = async () => {
    if (onClearError) onClearError();

    const selectedVectors = Object.entries(states).filter(
      ([_, state]) => state.file !== null
    );

    if (selectedVectors.length === 0) {
      alert("Please select at least one file vector to upload.");
      return;
    }

    // Set status to uploading for selected files
    setStates((prev) => {
      const next = { ...prev };
      selectedVectors.forEach(([key]) => {
        next[key] = { ...next[key], status: "uploading", progress: 10 };
      });
      return next;
    });

    // Simulate progress upload state before processing
    const progressIntervals: NodeJS.Timeout[] = [];
    selectedVectors.forEach(([key]) => {
      let currentProgress = 10;
      const interval = setInterval(() => {
        currentProgress += Math.floor(Math.random() * 20) + 10;
        if (currentProgress >= 90) {
          currentProgress = 90;
          clearInterval(interval);
          setStates((prev) => ({
            ...prev,
            [key]: { ...prev[key], status: "processing", progress: 90 }
          }));
        } else {
          setStates((prev) => ({
            ...prev,
            [key]: { ...prev[key], progress: currentProgress }
          }));
        }
      }, 150);
      progressIntervals.push(interval);
    });

    // Construct FormData
    const formData = new FormData();
    selectedVectors.forEach(([key, state]) => {
      if (state.file) {
        formData.append(key, state.file);
      }
    });

    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/procurement/ingest-history`, {
        method: "POST",
        headers: {
          "X-Tenant-ID": DEFAULT_TENANT_ID
        },
        body: formData
      });

      // Clear the simulation intervals
      progressIntervals.forEach(clearInterval);

      if (!res.ok) {
        // Transition state to error first
        setStates((prev) => {
          const next = { ...prev };
          selectedVectors.forEach(([key]) => {
            next[key] = {
              ...next[key],
              status: "error",
              errorMsg: `Failed: HTTP ${res.status}`
            };
          });
          return next;
        });

        await throwGatewayGovernanceError(res);
      }

      const responseData = await res.json();

      // Set all selected vectors to success
      setStates((prev) => {
        const next = { ...prev };
        selectedVectors.forEach(([key]) => {
          next[key] = { ...next[key], status: "success", progress: 100 };
        });
        return next;
      });

      if (onUploadSuccess) {
        onUploadSuccess(responseData.staged_vectors || [], responseData.staged_rows || 0);
      }
    } catch (err) {
      // Clear simulation intervals
      progressIntervals.forEach(clearInterval);

      if (err instanceof GatewayGovernanceError) {
        setStates((prev) => {
          const next = { ...prev };
          selectedVectors.forEach(([key]) => {
            next[key] = {
              ...next[key],
              status: "error",
              errorMsg: err.boundary.marker
            };
          });
          return next;
        });

        if (onUploadError) {
          onUploadError(err.boundary);
        }
      } else {
        const message = err instanceof Error ? err.message : String(err);
        setStates((prev) => {
          const next = { ...prev };
          selectedVectors.forEach(([key]) => {
            next[key] = {
              ...next[key],
              status: "error",
              errorMsg: message
            };
          });
          return next;
        });
      }
    }
  };

  const hasStagedFiles = Object.values(states).some((state) => state.file !== null);
  const isUploading = Object.values(states).some(
    (state) => state.status === "uploading" || state.status === "processing"
  );

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-5 md:grid-cols-5">
        {BUSINESS_VECTORS.map((vector) => {
          const state = states[vector.key];
          const Icon = vector.icon;
          const isDragOver = dragOverVector === vector.key;

          let statusClass = "border-slate-200 hover:border-indigo-400 bg-white hover:bg-slate-50/50";
          if (isDragOver) {
            statusClass = "border-indigo-500 bg-indigo-50/30 scale-[1.02]";
          } else if (state.status === "selected") {
            statusClass = "border-indigo-400 bg-indigo-50/10 hover:bg-indigo-50/20";
          } else if (state.status === "uploading") {
            statusClass = "border-indigo-400 bg-white cursor-wait";
          } else if (state.status === "processing") {
            statusClass = "border-amber-400 bg-amber-50/10 cursor-wait";
          } else if (state.status === "success") {
            statusClass = "border-emerald-500 bg-emerald-50/20";
          } else if (state.status === "error") {
            statusClass = "border-rose-500 bg-rose-50/20";
          }

          return (
            <div
              key={vector.key}
              onDragOver={(e) => handleDragOver(e, vector.key)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, vector.key)}
              onClick={() => {
                if (state.status === "idle" || state.status === "selected" || state.status === "success" || state.status === "error") {
                  fileInputRefs.current[vector.key]?.click();
                }
              }}
              className={`group relative flex h-64 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-4 text-center transition-all duration-200 ${statusClass}`}
            >
              <input
                ref={(el) => {
                  fileInputRefs.current[vector.key] = el;
                }}
                type="file"
                className="hidden"
                disabled={isUploading}
                onChange={(e) => {
                  const files = e.target.files;
                  if (files && files.length > 0) {
                    handleFileChange(vector.key, files[0]);
                  }
                }}
              />

              {/* Status Indicator Icon */}
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 text-slate-600 transition-colors duration-200 group-hover:bg-indigo-100 group-hover:text-indigo-600">
                {state.status === "success" ? (
                  <CheckCircle2 className="h-8 w-8 text-emerald-600 animate-in fade-in zoom-in-50" />
                ) : state.status === "error" ? (
                  <AlertCircle className="h-8 w-8 text-rose-600 animate-in fade-in zoom-in-50" />
                ) : state.status === "processing" ? (
                  <Loader2 className="h-8 w-8 text-amber-600 animate-spin" />
                ) : (
                  <Icon className="h-7 w-7 text-slate-600 group-hover:text-indigo-600" />
                )}
              </div>

              <h3 className="text-sm font-bold text-slate-950">{vector.label}</h3>
              <p className="mt-1.5 text-xs leading-4 text-slate-500 px-2 line-clamp-2">
                {state.file ? state.file.name : vector.description}
              </p>

              {/* Status text or actions */}
              <div className="mt-4 w-full">
                {state.status === "idle" && (
                  <span className="text-[11px] font-semibold text-indigo-600 bg-indigo-50 px-2 py-1 rounded">
                    Ready to drop
                  </span>
                )}

                {state.status === "selected" && (
                  <div className="flex items-center justify-center gap-2">
                    <span className="text-[11px] font-semibold text-indigo-700 bg-indigo-100 px-2.5 py-1 rounded">
                      Staged
                    </span>
                    <button
                      onClick={(e) => handleRemoveFile(e, vector.key)}
                      className="rounded p-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-600 transition"
                      aria-label="Remove file"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                )}

                {state.status === "uploading" && (
                  <div className="px-2">
                    <div className="flex items-center justify-between text-[11px] font-semibold text-indigo-600">
                      <span>Uploading</span>
                      <span>{state.progress}%</span>
                    </div>
                    <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full bg-indigo-600 transition-all duration-150"
                        style={{ width: `${state.progress}%` }}
                      />
                    </div>
                  </div>
                )}

                {state.status === "processing" && (
                  <div className="px-2">
                    <div className="flex items-center justify-center gap-1.5 text-[11px] font-semibold text-amber-600">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      <span>Processing signals...</span>
                    </div>
                    <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full w-2/3 bg-amber-500 animate-pulse" />
                    </div>
                  </div>
                )}

                {state.status === "success" && (
                  <span className="inline-flex items-center text-[11px] font-semibold text-emerald-700 bg-emerald-100/80 px-2.5 py-1 rounded">
                    Ingested
                  </span>
                )}

                {state.status === "error" && (
                  <div className="px-2 text-center">
                    <span className="inline-block max-w-full truncate text-[10px] font-semibold text-rose-700 bg-rose-100 px-2 py-0.5 rounded">
                      {state.errorMsg || "Failed"}
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex justify-end border-t border-slate-200/60 pt-5">
        <button
          onClick={triggerUpload}
          disabled={!hasStagedFiles || isUploading}
          className="flex items-center gap-2 rounded-md bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-soft transition hover:bg-indigo-700 disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
        >
          {isUploading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Ingesting Signals...</span>
            </>
          ) : (
            <>
              <UploadCloud className="h-4 w-4" />
              <span>Ingest Selected Signals</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
