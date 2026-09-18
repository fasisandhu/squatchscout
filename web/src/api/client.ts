import { API_BASE } from "../config";
import type { HealthResponse, IndustriesResponse, IntentResult, Lead, SearchCreate, SearchRow, Weights } from "./types";
import { FACTORS } from "../lib/rank";

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) } });
  } catch {
    throw new ApiError(0, "network", "Cannot reach the API. It may be waking up — retry in a moment.");
  }
  if (!res.ok) {
    let code = "http_error", message = res.statusText;
    try { const body = await res.json(); code = body?.error?.code ?? code; message = body?.error?.message ?? message; } catch { /* keep defaults */ }
    throw new ApiError(res.status, code, message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>("/healthz"),
  industries: () => request<IndustriesResponse>("/api/industries"),
  createSearch: (body: SearchCreate) => request<{ id: string }>("/api/searches", { method: "POST", body: JSON.stringify(body) }),
  getSearch: (id: string) => request<SearchRow>(`/api/searches/${id}`),
  getLeads: (id: string) => request<Lead[]>(`/api/searches/${id}/leads`),
  intent: (text: string) => request<IntentResult>("/api/intent", { method: "POST", body: JSON.stringify({ text }) }),
  opener: (leadId: string) => request<{ opener: string }>(`/api/leads/${leadId}/opener`, { method: "POST" }),
  streamUrl: (id: string) => `${API_BASE}/api/searches/${id}/stream`,
  exportUrl: (id: string, format: "csv" | "hubspot", ids: string[], weights: Weights) => {
    const q = new URLSearchParams({ format, weights: FACTORS.map((f) => String(Math.round(weights[f]))).join(",") });
    if (ids.length) q.set("ids", ids.join(","));
    return `${API_BASE}/api/searches/${id}/export?${q.toString()}`;
  },
};
