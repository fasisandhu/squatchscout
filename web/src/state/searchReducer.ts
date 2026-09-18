import type { Lead, LeadUpdatedEvent, StatusEvent, Tier, Weights } from "../api/types";
import { WEIGHT_PRESETS, tier, total } from "../lib/rank";

export type Phase = "idle" | "starting" | "streaming" | "refining" | "done" | "error";

export interface SessionState {
  searchId: string | null;
  phase: Phase;
  status: StatusEvent | null;
  leads: Record<string, Lead>;
  order: string[];
  weights: Weights;
  preset: string;
  selected: string[];
  llmPending: number;
  error: string | null;
}

export type SessionAction =
  | { type: "search_starting" }
  | { type: "search_started"; id: string }
  | { type: "status"; status: StatusEvent }
  | { type: "lead"; lead: Lead }
  | { type: "lead_updated"; update: LeadUpdatedEvent }
  | { type: "leads_replaced"; leads: Lead[] }
  | { type: "done"; lead_count: number; llm_pending: number }
  | { type: "llm_pending"; n: number }
  | { type: "error"; message: string }
  | { type: "set_weights"; weights: Weights; preset?: string }
  | { type: "toggle_select"; id: string }
  | { type: "select_all" }
  | { type: "clear_selection" }
  | { type: "reset" };

export const initialState: SessionState = {
  searchId: null, phase: "idle", status: null, leads: {}, order: [], weights: { ...WEIGHT_PRESETS.balanced },
  preset: "balanced", selected: [], llmPending: 0, error: null,
};

export function reducer(state: SessionState, action: SessionAction): SessionState {
  switch (action.type) {
    case "search_starting":
      return { ...initialState, weights: state.weights, preset: state.preset, phase: "starting" };
    case "search_started":
      return { ...state, searchId: action.id, phase: "streaming" };
    case "status":
      return { ...state, status: action.status };
    case "lead":
      return { ...state, leads: { ...state.leads, [action.lead.id]: action.lead },
        order: state.order.includes(action.lead.id) ? state.order : [...state.order, action.lead.id] };
    case "lead_updated": {
      const cur = state.leads[action.update.lead_id];
      if (!cur) return state;
      const { lead_id, ...rest } = action.update;
      return { ...state, leads: { ...state.leads, [lead_id]: { ...cur, ...rest } } };
    }
    case "leads_replaced": {
      const leads: Record<string, Lead> = Object.fromEntries(action.leads.map((l) => [l.id, l]));
      return { ...state, leads, order: action.leads.map((l) => l.id), selected: state.selected.filter((id) => id in leads) };
    }
    case "done":
      if (state.phase === "error") return state;
      return { ...state, llmPending: action.llm_pending, phase: action.llm_pending > 0 ? "refining" : "done" };
    case "llm_pending":
      if (state.phase !== "refining") return state;
      return { ...state, llmPending: action.n, phase: action.n > 0 ? "refining" : "done" };
    case "error":
      return { ...state, phase: "error", error: action.message };
    case "set_weights":
      return { ...state, weights: action.weights, preset: action.preset ?? "custom" };
    case "toggle_select":
      return { ...state, selected: state.selected.includes(action.id) ? state.selected.filter((x) => x !== action.id) : [...state.selected, action.id] };
    case "select_all":
      return { ...state, selected: [...state.order] };
    case "clear_selection":
      return { ...state, selected: [] };
    case "reset":
      return initialState;
  }
}

export type RankedLead = Lead & { computedScore: number; computedTier: Tier };

export function rankedLeads(state: SessionState): RankedLead[] {
  return state.order
    .map((id) => state.leads[id])
    .filter(Boolean)
    .map((l) => { const s = total(l.factor_scores, state.weights); return { ...l, computedScore: s, computedTier: tier(s) }; })
    .sort((a, b) => b.computedScore - a.computedScore || a.display_name.localeCompare(b.display_name));
}

export function summary(state: SessionState) {
  const ranked = rankedLeads(state);
  const found = ranked.length;
  const withVerified = ranked.filter((l) => l.contacts.some((c) => c.kind === "email" && c.verification_status === "verified")).length;
  const tiers: Record<Tier, number> = { A: 0, B: 0, C: 0, D: 0 };
  for (const l of ranked) tiers[l.computedTier]++;
  const refined = ranked.filter((l) => l.llm_status === "done").length;
  return { found, verifiedEmailPct: found ? Math.round((withVerified / found) * 100) : 0, tiers, refined };
}
