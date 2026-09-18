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

  useEffect(() => () => dispose.current(), []);

  // Spec §10 "Late LLM updates": after `done` with llm_pending > 0, poll the search row every 10 s and
  // refresh leads when the pending count drops. Stop at 0 or after 8 minutes.
  useEffect(() => {
    if (state.phase !== "refining" || !state.searchId) return;
    const id = state.searchId;
    const startedAt = Date.now();
    let lastPending = state.llmPending;
    const timer = setInterval(async () => {
      try {
        const row = await api.getSearch(id);
        if (row.llm_pending !== lastPending) {
          lastPending = row.llm_pending;
          dispatch({ type: "leads_replaced", leads: await api.getLeads(id) });
          dispatch({ type: "llm_pending", n: row.llm_pending });
        }
        if (row.llm_pending === 0 || Date.now() - startedAt > POLL_MAX_MS) { dispatch({ type: "llm_pending", n: 0 }); clearInterval(timer); }
      } catch { /* transient; try again next tick */ }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [state.phase, state.searchId]);

  const start = useCallback(async (body: SearchCreate) => {
    dispose.current();
    dispatch({ type: "search_starting" });
    try {
      const { id } = await api.createSearch(body);
      dispatch({ type: "search_started", id });
      dispose.current = openStream(api.streamUrl(id), {
        onStatus: (status) => dispatch({ type: "status", status }),
        onLead: (lead) => dispatch({ type: "lead", lead }),
        onLeadUpdated: (update) => dispatch({ type: "lead_updated", update }),
        onDone: (d) => dispatch({ type: "done", lead_count: d.lead_count, llm_pending: d.llm_pending }),
        onError: (e) => dispatch({ type: "error", message: e.message }),
      });
    } catch (e) {
      dispatch({ type: "error", message: e instanceof ApiError ? e.message : "Could not start the search." });
    }
  }, []);

  const setWeights = useCallback((weights: Weights) => dispatch({ type: "set_weights", weights }), []);
  const applyPreset = useCallback((name: string) => {
    const w = WEIGHT_PRESETS[name];
    if (w) dispatch({ type: "set_weights", weights: w, preset: name });
  }, []);
  const toggleSelect = useCallback((id: string) => dispatch({ type: "toggle_select", id }), []);
  const selectAll = useCallback(() => dispatch({ type: "select_all" }), []);
  const clearSelection = useCallback(() => dispatch({ type: "clear_selection" }), []);
  const reset = useCallback(() => { dispose.current(); dispatch({ type: "reset" }); }, []);

  return { state, start, setWeights, applyPreset, toggleSelect, selectAll, clearSelection, reset };
}
