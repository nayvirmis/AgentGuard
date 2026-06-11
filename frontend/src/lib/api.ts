import type { EvalCase, EvalRun, Metrics, Run, RunDetail, ToolDefinition } from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? payload?.error?.message ?? "Request failed");
  }
  return response.json() as Promise<T>;
}

export const api = {
  listRuns: (search = "") =>
    request<Run[]>(`/runs${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  getRun: (id: string) => request<RunDetail>(`/runs/${id}`),
  createRun: (query: string, provider: "fake" | "openai" = "fake") =>
    request<{ run_id: string; status: string; events_url: string }>("/runs", {
      method: "POST",
      body: JSON.stringify({ query, provider }),
    }),
  decideApproval: (runId: string, approvalId: string, decision: "approve" | "reject") =>
    request(`/runs/${runId}/approvals/${approvalId}`, {
      method: "POST",
      body: JSON.stringify({ decision }),
    }),
  cancelRun: (runId: string) =>
    request<Run>(`/runs/${runId}/cancel`, { method: "POST" }),
  listTools: () => request<ToolDefinition[]>("/tools"),
  listPolicies: () =>
    request<
      Array<{
        id: string;
        name: string;
        description: string;
        severity: string;
        enabled: boolean;
      }>
    >("/policies"),
  metrics: () => request<Metrics>("/metrics"),
  listEvalCases: () => request<EvalCase[]>("/eval-cases"),
  startEval: () =>
    request<{ eval_run_id: string; status: string }>("/eval-runs", { method: "POST" }),
  getEvalRun: (id: string) => request<EvalRun>(`/eval-runs/${id}`),
};
