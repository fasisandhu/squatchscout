// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { StreamHandlers } from "../api/sse";
import type { Lead, SearchCreate, SearchRow } from "../api/types";

vi.mock("../api/client", () => ({
  api: {
    createSearch: vi.fn(),
    getSearch: vi.fn(),
    getLeads: vi.fn(),
    streamUrl: vi.fn((id: string) => `http://api.test/searches/${id}/stream`),
  },
  ApiError: class ApiError extends Error {
    status: number;
    code: string;
    constructor(status: number, code: string, message: string) {
      super(message);
      this.status = status;
      this.code = code;
    }
  },
}));

vi.mock("../api/sse", () => ({ openStream: vi.fn(() => vi.fn()) }));

import { api } from "../api/client";
import { openStream } from "../api/sse";
import { useSearchSession } from "./useSearchSession";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => { resolve = res; });
  return { promise, resolve };
}

const flush = async () => {
  for (let i = 0; i < 5; i++) await Promise.resolve();
};

const body: SearchCreate = { industry_key: "landscaping", location: "Austin, TX", limit: 10 };

function searchRow(overrides: Partial<SearchRow> = {}): SearchRow {
  return {
    id: "s1", industry_key: "landscaping", location_query: "Austin, TX", geocoded_name: "Austin, TX",
    weight_preset: "balanced", status: "running", lead_count: 1, llm_pending: 0, error: null,
    created_at: "2026-01-01T00:00:00Z", finished_at: null, ...overrides,
  };
}

const ghostLead: Lead = {
  id: "ghost", name: "Ghost Co", display_name: "Ghost Co",
  address: { street: null, housenumber: null, city: null, state: null, postcode: null, country: null },
  address_source: "none", lat: 0, lon: 0, website: null, domain: null, is_chain_suspected: false,
  enrichment_status: "ok", llm_status: "done", score: 50, tier: "B", contacts: [], signals: [],
  factor_scores: [],
};

beforeEach(() => {
  vi.mocked(api.createSearch).mockReset();
  vi.mocked(api.getSearch).mockReset();
  vi.mocked(api.getLeads).mockReset();
  vi.mocked(api.getLeads).mockResolvedValue([ghostLead]);
  vi.mocked(openStream).mockReset();
  vi.mocked(openStream).mockImplementation(() => vi.fn());
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useSearchSession polling and cancellation", () => {
  it("caps polling at 8 minutes even when the API is unreachable", async () => {
    vi.mocked(api.createSearch).mockResolvedValue({ id: "s1" });
    let handlers!: StreamHandlers;
    vi.mocked(openStream).mockImplementation((_url, h) => { handlers = h; return vi.fn(); });

    const { result, unmount } = renderHook(() => useSearchSession());

    await act(async () => { await result.current.start(body); });
    act(() => { handlers.onDone({ lead_count: 1, llm_pending: 1 }); });
    expect(result.current.state.phase).toBe("refining");

    vi.mocked(api.getSearch).mockRejectedValue(new Error("network down"));

    await act(async () => { await vi.advanceTimersByTimeAsync(8 * 60_000 + 20_000); });

    expect(result.current.state.phase).toBe("done");
    const callsAtCap = vi.mocked(api.getSearch).mock.calls.length;
    expect(callsAtCap).toBeLessThanOrEqual(49);

    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(vi.mocked(api.getSearch).mock.calls.length).toBe(callsAtCap);

    unmount();
  });

  it("ignores a late poll that resolves after reset()", async () => {
    vi.mocked(api.createSearch).mockResolvedValue({ id: "s1" });
    let handlers!: StreamHandlers;
    vi.mocked(openStream).mockImplementation((_url, h) => { handlers = h; return vi.fn(); });

    const { result, unmount } = renderHook(() => useSearchSession());

    await act(async () => { await result.current.start(body); });
    act(() => { handlers.onDone({ lead_count: 1, llm_pending: 1 }); });
    expect(result.current.state.phase).toBe("refining");

    const getSearchDeferred = deferred<SearchRow>();
    vi.mocked(api.getSearch).mockReturnValue(getSearchDeferred.promise);

    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });

    act(() => { result.current.reset(); });
    expect(result.current.state.phase).toBe("idle");

    await act(async () => {
      getSearchDeferred.resolve(searchRow({ llm_pending: 2 }));
      await flush();
    });

    expect(result.current.state.phase).toBe("idle");
    expect(Object.keys(result.current.state.leads)).toHaveLength(0);

    unmount();
  });

  it("ignores a stale start() superseded by a second start()", async () => {
    const first = deferred<{ id: string }>();
    const second = deferred<{ id: string }>();
    vi.mocked(api.createSearch).mockImplementationOnce(() => first.promise).mockImplementationOnce(() => second.promise);

    const { result, unmount } = renderHook(() => useSearchSession());

    act(() => { void result.current.start(body); });
    act(() => { void result.current.start(body); });

    await act(async () => { first.resolve({ id: "old" }); await flush(); });
    await act(async () => { second.resolve({ id: "new" }); await flush(); });

    expect(result.current.state.searchId).toBe("new");
    expect(vi.mocked(openStream).mock.calls).toHaveLength(1);
    expect(vi.mocked(openStream).mock.calls[0][0]).toContain("new");

    unmount();
  });
});
