import { describe, expect, it } from "vitest";
import { initialState, rankedLeads, reducer, summary } from "./searchReducer";
import type { Lead } from "../api/types";
import { WEIGHT_PRESETS } from "../lib/rank";

const lead = (id: string, points: Record<string, number>, extra: Partial<Lead> = {}): Lead => ({
  id, name: id, display_name: id, address: { street: null, housenumber: null, city: null, state: null, postcode: null, country: null },
  address_source: "none", lat: 0, lon: 0, website: null, domain: null, is_chain_suspected: false, enrichment_status: "ok",
  llm_status: "not_needed", score: null, tier: null, contacts: [], signals: [],
  factor_scores: (["reachability", "establishment", "digital_gap", "buybox", "succession"] as const).map((f) => ({
    factor: f, points: points[f] ?? 0, max_points: { reachability: 25, establishment: 20, digital_gap: 20, buybox: 20, succession: 15 }[f], reasons: [] })),
  ...extra,
});

describe("searchReducer", () => {
  it("streams leads, ranks client-side and re-ranks on weight change", () => {
    let s = reducer(initialState, { type: "search_started", id: "s1" });
    s = reducer(s, { type: "lead", lead: lead("A", { reachability: 25 }) });
    s = reducer(s, { type: "lead", lead: lead("B", { succession: 15 }) });
    expect(s.phase).toBe("streaming");
    expect(rankedLeads(s).map((l) => l.id)).toEqual(["A", "B"]);           // balanced: 25 > 15
    s = reducer(s, { type: "set_weights", weights: WEIGHT_PRESETS.succession });
    expect(rankedLeads(s).map((l) => l.id)).toEqual(["B", "A"]);           // succession 30 > reachability 25
    expect(rankedLeads(s)[0].computedTier).toBe("D");
  });

  it("applies lead_updated in place and tracks refine phase", () => {
    let s = reducer(initialState, { type: "search_started", id: "s1" });
    s = reducer(s, { type: "lead", lead: lead("A", {}, { llm_status: "queued" }) });
    s = reducer(s, { type: "done", lead_count: 1, llm_pending: 1 });
    expect(s.phase).toBe("refining");
    s = reducer(s, { type: "lead_updated", update: { lead_id: "A", display_name: "A Co", address: lead("A", {}).address, address_source: "llm",
      signals: [{ key: "founded_year", value: "1990", source: "llm", confidence: 0.9 }], factor_scores: lead("A", { establishment: 20 }).factor_scores,
      score: 20, tier: "D", llm_status: "done" } });
    expect(s.leads.A.display_name).toBe("A Co");
    expect(s.leads.A.signals[0].value).toBe("1990");
    s = reducer(s, { type: "llm_pending", n: 0 });
    expect(s.phase).toBe("done");
    expect(summary(s).refined).toBe(1);
  });

  it("selection, summary and error", () => {
    let s = reducer(initialState, { type: "search_started", id: "s1" });
    s = reducer(s, { type: "lead", lead: lead("A", {}, { contacts: [{ kind: "email", value: "a@x.com", source: "website", verification_status: "verified" }] }) });
    s = reducer(s, { type: "lead", lead: lead("B", {}) });
    s = reducer(s, { type: "toggle_select", id: "A" });
    expect(s.selected).toEqual(["A"]);
    s = reducer(s, { type: "select_all" });
    expect(s.selected.sort()).toEqual(["A", "B"]);
    expect(summary(s).found).toBe(2);
    expect(summary(s).verifiedEmailPct).toBe(50);
    s = reducer(s, { type: "error", message: "boom" });
    expect(s.phase).toBe("error");
    expect(reducer(s, { type: "reset" })).toEqual(initialState);
  });
});
