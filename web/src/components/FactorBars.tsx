import type { FactorScore, Weights } from "../api/types";
import { FACTOR_LABELS, FACTORS } from "../lib/rank";

export function FactorBars({ factorScores, weights }: { factorScores: FactorScore[]; weights: Weights }) {
  const sum = FACTORS.reduce((a, f) => a + (weights[f] ?? 0), 0) || 1;
  return (
    <ul className="flex flex-col gap-3">
      {factorScores.map((fs) => (
        <li key={fs.factor}>
          <div className="flex justify-between text-xs">
            <span className="font-medium">{FACTOR_LABELS[fs.factor]}</span>
            <span className="tabular-nums text-muted">{fs.points}/{fs.max_points} · weight {Math.round(((weights[fs.factor] ?? 0) / sum) * 100)}%</span>
          </div>
          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2" role="progressbar" aria-valuenow={fs.points} aria-valuemax={fs.max_points} aria-label={FACTOR_LABELS[fs.factor]}>
            <div className="h-full bg-gradient-to-r from-accent to-accent-2" style={{ width: `${(fs.points / fs.max_points) * 100}%` }} />
          </div>
          <ul className="mt-1 list-disc pl-4 text-xs text-muted">{fs.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
        </li>
      ))}
    </ul>
  );
}
