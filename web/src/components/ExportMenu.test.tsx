// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import type { Weights } from "../api/types";
import { ExportMenu } from "./ExportMenu";

const weights: Weights = { reachability: 25, establishment: 20, digital_gap: 20, buybox: 20, succession: 15 };

describe("ExportMenu", () => {
  it("clicking HubSpot CSV creates an anchor whose href matches api.exportUrl(...) with format, ids and R/E/D/B/S weights", () => {
    const created: HTMLAnchorElement[] = [];
    const realCreateElement = document.createElement.bind(document);
    const spy = vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = realCreateElement(tag);
      // jsdom doesn't implement anchor navigation; stub click() so a real href doesn't log a "Not implemented" warning.
      if (tag === "a") { (el as HTMLAnchorElement).click = vi.fn(); created.push(el as HTMLAnchorElement); }
      return el;
    });

    render(<ExportMenu searchId="search-1" selected={["lead-1", "lead-2"]} total={5} weights={weights} disabled={false} />);

    fireEvent.click(screen.getByRole("button", { name: /HubSpot CSV/ }));

    const expected = api.exportUrl("search-1", "hubspot", ["lead-1", "lead-2"], weights);
    expect(created).toHaveLength(1);
    // getAttribute, not the `.href` property, since jsdom resolves the latter to an absolute URL
    expect(created[0].getAttribute("href")).toBe(expected);
    expect(expected).toContain("format=hubspot");
    expect(expected).toMatch(/ids=lead-1(%2C|,)lead-2/);
    expect(expected).toMatch(/weights=25(%2C|,)20(%2C|,)20(%2C|,)20(%2C|,)15/);

    spy.mockRestore();
  });

  it("disables both export buttons when total is 0", () => {
    render(<ExportMenu searchId="search-1" selected={[]} total={0} weights={weights} disabled={false} />);

    expect((screen.getByRole("button", { name: /^CSV$/ }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: /HubSpot CSV/ }) as HTMLButtonElement).disabled).toBe(true);
  });
});
