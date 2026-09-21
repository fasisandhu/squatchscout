import { RotateCcw } from "lucide-react";
import type { Factor, Weights } from "../api/types";
import { FACTORS, FACTOR_LABELS, WEIGHT_PRESETS } from "../lib/rank";

const PRESET_LABELS: Record<string, string> = { balanced: "Balanced", succession: "Succession", digital_upside: "Digital upside", reachability_first: "Reachability" };

export function WeightsPanel({ weights, preset, onChange, onPreset }: { weights: Weights; preset: string; onChange: (w: Weights) => void; onPreset: (n: string) => void }) {
  const sum = FACTORS.reduce((a, f) => a + weights[f], 0) || 1;
  return (
    <section className="card p-4 flex flex-col gap-3" aria-labelledby="weights-h">
      <div className="flex items-center justify-between">
        <h2 id="weights-h" className="text-sm font-semibold">Ranking weights</h2>
        <button type="button" onClick={() => onPreset("balanced")} className="btn-quiet" aria-label="Reset weights"><RotateCcw className="size-3" aria-hidden /> Reset</button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {Object.keys(WEIGHT_PRESETS).map((name) => (
          <button key={name} type="button" onClick={() => onPreset(name)} aria-pressed={preset === name} className="chip">{PRESET_LABELS[name]}</button>
        ))}
      </div>
      {FACTORS.map((f: Factor) => (
        <label key={f} className="flex flex-col gap-1 text-xs">
          <span className="flex justify-between"><span>{FACTOR_LABELS[f]}</span><span className="tabular-nums text-muted">{Math.round((weights[f] / sum) * 100)}%</span></span>
          <input type="range" min={0} max={50} step={1} value={weights[f]} aria-label={`${FACTOR_LABELS[f]} weight`}
            onChange={(e) => onChange({ ...weights, [f]: Number(e.target.value) })} className="accent-[var(--color-accent)]" />
        </label>
      ))}
      <p className="text-[11px] text-muted">Re-ranks instantly in your browser — no requests sent. Exports carry these weights.</p>
    </section>
  );
}
