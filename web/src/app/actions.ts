"use server";

const DEFAULT_TENANT_ID = "f7a2b4c9-3d1e-4f8a-b5c2-9e0d1a2b3c4d";
const BACKEND_URL = "http://127.0.0.1:8000";

export async function executeScenarioSimulation(matrix: Record<string, any>) {
  const res = await fetch(`${BACKEND_URL}/api/v1/procurement/simulate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Tenant-ID": DEFAULT_TENANT_ID,
    },
    body: JSON.stringify({ matrix }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Simulation failed: ${res.status} - ${errorText}`);
  }
  return await res.json();
}

export async function submitCopilotMessage(message: string, sessionId: string) {
  const res = await fetch(`${BACKEND_URL}/api/v1/procurement/copilot/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Tenant-ID": DEFAULT_TENANT_ID,
    },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Copilot chat failed: ${res.status} - ${errorText}`);
  }
  return await res.json();
}
