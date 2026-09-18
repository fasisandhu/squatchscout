// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RankedLead } from "../state/searchReducer";
import { ResultsTable } from "./ResultsTable";

afterEach(cleanup);

function lead(overrides: Partial<RankedLead> = {}): RankedLead {
  return {
    id: "1", name: "acme", display_name: "Acme Plumbing Co",
    address: { street: "1 Main St", housenumber: null, city: "Springfield", state: "IL", postcode: "62701", country: "US" },
    address_source: "osm", lat: 0, lon: 0, website: "https://acme.example", domain: "acme.example", is_chain_suspected: false,
    enrichment_status: "ok", llm_status: "done", score: 91, tier: "A",
    contacts: [{ kind: "email", value: "info@acme.example", source: "site", verification_status: "verified" }],
    signals: [], factor_scores: [], computedScore: 91, computedTier: "A",
    ...overrides,
  };
}

function noop() {}

describe("ResultsTable keyboard vs pointer selection", () => {
  it("pressing Space on a row checkbox toggles selection and does not open the drawer", () => {
    const onOpen = vi.fn();
    const onToggle = vi.fn();
    const leads = [lead(), lead({ id: "2", display_name: "Downtown Roofing" })];

    render(<ResultsTable leads={leads} selected={[]} onToggle={onToggle} onSelectAll={noop} onClear={noop} onOpen={onOpen} phase="done" />);

    const checkboxes = screen.getAllByRole("checkbox");
    const rowCheckbox = checkboxes[1]; // 0 = "Select all" header checkbox

    fireEvent.keyDown(rowCheckbox, { key: " " });
    expect(onOpen).not.toHaveBeenCalled();

    fireEvent.click(rowCheckbox); // the browser's native space->click activation
    expect(onToggle).toHaveBeenCalledWith("1");
    expect(onOpen).not.toHaveBeenCalled();
  });

  it("pressing Enter on a row opens the drawer", () => {
    const onOpen = vi.fn();
    const leads = [lead(), lead({ id: "2", display_name: "Downtown Roofing" })];

    render(<ResultsTable leads={leads} selected={[]} onToggle={noop} onSelectAll={noop} onClear={noop} onOpen={onOpen} phase="done" />);

    const row = screen.getByText("Acme Plumbing Co").closest("tr");
    expect(row).not.toBeNull();
    fireEvent.keyDown(row as HTMLElement, { key: "Enter" });

    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen).toHaveBeenCalledWith("1");
  });
});

describe("ResultsTable badges", () => {
  it("a robots-blocked lead's badge reads \"blocked by robots\"", () => {
    const leads = [lead({ enrichment_status: "blocked_by_robots" })];

    render(<ResultsTable leads={leads} selected={[]} onToggle={noop} onSelectAll={noop} onClear={noop} onOpen={noop} phase="done" />);

    expect(screen.getByText("blocked by robots")).toBeTruthy();
  });
});
