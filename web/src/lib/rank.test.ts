import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { FACTORS, MAX_POINTS, WEIGHT_PRESETS, normalizeWeights, tier, total } from "./rank";
import type { Factor, FactorScore, Tier } from "../api/types";

interface Gold {
  reference_year: number;
  cases: { name: string; expected_points: Record<Factor, number>; expected_total_balanced: number; expected_tier: Tier }[];
}

const here = dirname(fileURLToPath(import.meta.url));
const gold = JSON.parse(
  readFileSync(resolve(here, "../../../api/tests/fixtures/golden_scores.json"), "utf8"),
) as Gold;

describe("rank.ts mirrors score.py", () => {
  for (const c of gold.cases) {
    it(`golden: ${c.name}`, () => {
      const fs: FactorScore[] = FACTORS.map((f) => ({
        factor: f, points: (c.expected_points as Record<Factor, number>)[f], max_points: MAX_POINTS[f], reasons: [] }));
      const t = total(fs, WEIGHT_PRESETS.balanced);
      expect(t).toBeCloseTo(c.expected_total_balanced, 1);
      expect(tier(t)).toBe(c.expected_tier);
    });
  }
  it("tier boundaries", () => {
    expect([tier(70), tier(69.9), tier(55), tier(54.9), tier(40), tier(39.9)]).toEqual(["A", "B", "B", "C", "C", "D"]);
  });
  it("weights normalise and a single factor can dominate", () => {
    const fs: FactorScore[] = FACTORS.map((f) => ({ factor: f, points: f === "reachability" ? 25 : 0, max_points: MAX_POINTS[f], reasons: [] }));
    expect(total(fs, normalizeWeights({ reachability: 7, establishment: 0, digital_gap: 0, buybox: 0, succession: 0 }))).toBe(100);
    expect(Object.values(WEIGHT_PRESETS.succession).reduce((a, b) => a + b, 0)).toBe(100);
  });
});
