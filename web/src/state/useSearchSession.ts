import { useCallback, useEffect, useReducer, useRef } from "react";
import { api, ApiError } from "../api/client";
import { openStream } from "../api/sse";
import type { SearchCreate, Weights } from "../api/types";
import { WEIGHT_PRESETS } from "../lib/rank";
import { initialState, reducer } from "./searchReducer";

const POLL_MS = 10_000;
const POLL_MAX_MS = 8 * 60_000;

export function useSearchSession() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const dispose = useRef<() => void>(() => {});
  const runId = useRef(0);

  useEffect(() => () => dispose.current(), []);

  // Spec §10 "Late LLM updates": after `done` with llm_pending > 0, poll the search row every 10 s and
  // refresh leads when the pending count drops. Stop at 0 or after 8 minutes — the deadline is checked
  // before every request so an unreachable API can't keep this running forever, and in-flight requests
  // that resolve after this effect is torn down (reset, a new search, unmount) are dropped via `cancelled`.
  useEffect(() => {
    if (state.phase !== "refining" || !state.searchId) return;
    const id = state.searchId;
    const startedAt = Date.now();
    let lastPending = state.llmPending;
    let cancelled = false;
    const timer = setInterval(async () => {
      if (Date.now() - startedAt > POLL_MAX_MS) {
        clearInterval(timer);
        dispatch({ type: "llm_pending", n: 0 });
        return;
      }
      try {
        const row = await api.getSearch(id);
        if (cancelled) return;
        if (row.llm_pending !== lastPending) {
          lastPending = row.llm_pending;
          const leads = await api.getLeads(id);
          if (cancelled) return;
          dispatch({ type: "leads_replaced", leads });
        }
        if (row.llm_pending === 0) clearInterval(timer);
        dispatch({ type: "llm_pending", n: row.llm_pending });
      } catch { /* transient; try again next tick */ }
    }, POLL_MS);
    return () => { cancelled = true; clearInterval(timer); };
  }, [state.phase, state.searchId]);

  const start = useCallback(async (body: SearchCreate) => {
    const myRun = ++runId.current;
    dispose.current();
    dispatch({ type: "search_starting" });
    try {
      const { id } = await api.createSearch(body);
      if (myRun !== runId.current) return; // superseded by a later start()/reset()
      dispatch({ type: "search_started", id });
      const stop = openStream(api.streamUrl(id), {
        onStatus: (status) => { if (myRun === runId.current) dispatch({ type: "status", status }); },
        onLead: (lead) => { if (myRun === runId.current) dispatch({ type: "lead", lead }); },
        onLeadUpdated: (update) => { if (myRun === runId.current) dispatch({ type: "lead_updated", update }); },
        onDone: (d) => { if (myRun === runId.current) dispatch({ type: "done", lead_count: d.lead_count, llm_pending: d.llm_pending }); },
        onError: (e) => { if (myRun === runId.current) dispatch({ type: "error", message: e.message }); },
      });
      if (myRun !== runId.current) { stop(); return; }
      dispose.current = stop;
    } catch (e) {
      if (myRun !== runId.current) return;
      dispatch({ type: "error", message: e instanceof ApiError ? e.message : "Could not start the search." });
    }
  }, []);

  const setWeights = useCallback((weights: Weights) => dispatch({ type: "set_weights", weights }), []);
  const applyPreset = useCallback((name: string) => {
    const w = WEIGHT_PRESETS[name];
    if (w) dispatch({ type: "set_weights", weights: { ...w }, preset: name });
  }, []);
  const toggleSelect = useCallback((id: string) => dispatch({ type: "toggle_select", id }), []);
  const selectAll = useCallback(() => dispatch({ type: "select_all" }), []);
  const clearSelection = useCallback(() => dispatch({ type: "clear_selection" }), []);
  const reset = useCallback(() => { runId.current++; dispose.current(); dispatch({ type: "reset" }); }, []);

  return { state, start, setWeights, applyPreset, toggleSelect, selectAll, clearSelection, reset };
}
