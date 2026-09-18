import type { Tier } from "../api/types";

const ORDER: Tier[] = ["A", "B", "C", "D"];
const BAR: Record<Tier, string> = { A: "bg-tier-a", B: "bg-tier-b", C: "bg-tier-c", D: "bg-tier-d" };

export function SummaryTiles({ found, verifiedEmailPct, tiers, refined, llmEnabled }: { found: number; verifiedEmailPct: number; tiers: Record<Tier, number>; refined: number; llmEnabled: boolean }) {
  const total = Math.max(found, 1);
  return (
    <section className="card p-4 grid grid-cols-2 gap-3" aria-label="Search summary">
      <div><div className="text-2xl font-semibold tabular-nums">{found}</div><div className="text-xs text-muted">leads found</div></div>
      <div><div className="text-2xl font-semibold tabular-nums">{verifiedEmailPct}%</div><div className="text-xs text-muted">with verified email</div></div>
      <div className="col-span-2">
        <div className="mb-1 flex justify-between text-xs text-muted"><span>Tier mix</span><span className="tabular-nums">{ORDER.map((t) => `${t}${tiers[t]}`).join(" · ")}</span></div>
        <div className="flex h-2 overflow-hidden rounded-full bg-surface-2" role="img" aria-label={`Tiers: ${ORDER.map((t) => `${tiers[t]} ${t}`).join(", ")}`}>
          {ORDER.map((t) => <div key={t} className={BAR[t]} style={{ width: `${(tiers[t] / total) * 100}%` }} />)}
        </div>
      </div>
      {llmEnabled && <div className="col-span-2 text-xs text-muted"><span className="text-accent">{refined}</span> refined with AI</div>}
    </section>
  );
}
