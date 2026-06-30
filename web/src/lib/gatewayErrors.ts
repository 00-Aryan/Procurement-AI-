const GATEWAY_ERROR_MARKERS = ["[VALIDATION_ERROR]", "[TENANT_AUTH_ERROR]"] as const;

export type GatewayErrorMarker = (typeof GATEWAY_ERROR_MARKERS)[number];

export type GatewayGovernanceBoundary = {
  marker: GatewayErrorMarker;
  metadata: string;
  status: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function extractGatewayMetadata(payload: unknown): string {
  if (!isRecord(payload)) {
    return typeof payload === "string" ? payload : "";
  }

  const candidate = payload.error ?? payload.detail ?? payload.error_code ?? payload.errors;

  if (typeof candidate === "string") {
    return candidate;
  }

  if (Array.isArray(candidate)) {
    return candidate.filter((item): item is string => typeof item === "string").join("; ");
  }

  return JSON.stringify(payload);
}

function normalizeGatewayMetadata(metadata: string): string {
  const normalized = metadata.replace(/[^\x20-\x7E]+/g, " ").replace(/\s+/g, " ").trim();
  return normalized.slice(0, 520) || "Gateway rejected the request without additional metadata.";
}

export class GatewayGovernanceError extends Error {
  boundary: GatewayGovernanceBoundary;

  constructor(marker: GatewayErrorMarker, metadata: string, status: number) {
    super(`${marker} Gateway governance boundary enforced`);
    this.name = "GatewayGovernanceError";
    this.boundary = {
      marker,
      metadata: normalizeGatewayMetadata(metadata),
      status
    };
  }
}

export async function throwGatewayGovernanceError(response: Response): Promise<never> {
  const bodyText = await response.text();
  const marker = GATEWAY_ERROR_MARKERS.find((entry) => bodyText.includes(entry));

  if (marker) {
    let metadata = bodyText;

    try {
      metadata = extractGatewayMetadata(JSON.parse(bodyText));
    } catch {
      metadata = bodyText;
    }

    throw new GatewayGovernanceError(marker, metadata, response.status);
  }

  throw new Error(`HTTP error ${response.status}`);
}
