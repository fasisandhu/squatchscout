import type { Factor, FactorScore, Tier, Weights } from "../api/types";

export const FACTORS: Factor[] = ["reachability", "establishment", "digital_gap", "buybox", "succession"];
export const MAX_POINTS: Record<Factor, number> = { reachability: 25, establishment: 20, digital_gap: 20, buybox: 20, succession: 15 };
export const FACTOR_LABELS: Record<Factor, string> = {
  reachability: "Reachability", establishment: "Establishment", digital_gap: "Digital-maturity gap",
  buybox: "Buy-box fit", succession: "Succession signals" };
export const WEIGHT_PRESETS: Record<string, Weights> = {
  balanced: { reachability: 25, establishment: 20, digital_gap: 20, buybox: 20, succession: 15 },
  succession: { reachability: 25, establishment: 15, digital_gap: 10, buybox: 20, succession: 30 },
  digital_upside: { reachability: 25, establishment: 10, digital_gap: 35, buybox: 20, succession: 10 },
  reachability_first: { reachability: 40, establishment: 15, digital_gap: 15, buybox: 20, succession: 10 },
};

export function normalizeWeights(w: Weights): Weights {
  const sum = FACTORS.reduce((a, f) => a + (w[f] ?? 0), 0) || 1;
  return Object.fromEntries(FACTORS.map((f) => [f, ((w[f] ?? 0) / sum) * 100])) as Weights;
}

/** Same formula as api/app/pipeline/score.py::total — Σ (points/max) × weight share × 100, 1 dp. */
export function total(factorScores: FactorScore[], weights: Weights): number {
  const sum = FACTORS.reduce((a, f) => a + (weights[f] ?? 0), 0) || 1;
  const t = factorScores.reduce((acc, fs) => acc + (fs.points / fs.max_points) * ((weights[fs.factor] ?? 0) / sum) * 100, 0);
  return Math.round(t * 10) / 10;
}

export function tier(t: number): Tier { return t >= 70 ? "A" : t >= 55 ? "B" : t >= 40 ? "C" : "D"; }
