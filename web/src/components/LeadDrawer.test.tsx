// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { RankedLead } from "../state/searchReducer";
import { LeadDrawer } from "./LeadDrawer";

function lead(overrides: Partial<RankedLead> = {}): RankedLead {
  return {
    id: "1", name: "acme", display_name: "Acme Plumbing Co",
    address: { street: "1 Main St", housenumber: null, city: "Springfield", state: "IL", postcode: "62701", country: "US" },
    address_source: "osm", lat: 0, lon: 0, website: "https://acme.example", domain: "acme.example", is_chain_suspected: false,
    enrichment_status: "ok", llm_status: "done", score: 91, tier: "A",
    contacts: [{ kind: "email", value: "info@acme.example", source: "site", verification_status: "verified" }],
    signals: [],
    factor_scores: [
      { factor: "reachability", points: 20, max_points: 25, reasons: ["verified email found on site"] },
    ],
    computedScore: 91, computedTier: "A",
    ...overrides,
  };
}

const weights = { reachability: 25, establishment: 20, digital_gap: 20, buybox: 20, succession: 15 };

describe("LeadDrawer", () => {
  it("renders nothing when lead is null", () => {
    render(<LeadDrawer lead={null} weights={weights} llmEnabled={false} onClose={vi.fn()} />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("shows an accessible dialog with the factor reasons, and Escape closes it", () => {
    const onClose = vi.fn();
    render(<LeadDrawer lead={lead()} weights={weights} llmEnabled={false} onClose={onClose} />);

    const dialog = screen.getByRole("dialog");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(screen.getByText("verified email found on site")).toBeTruthy();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
