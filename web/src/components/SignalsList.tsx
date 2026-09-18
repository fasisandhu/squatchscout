import type { Signal } from "../api/types";

const PILL: Record<Signal["source"], string> = { osm: "border-border text-muted", regex: "border-accent-2/40 text-accent-2", llm: "border-accent/40 text-accent" };
const HIDE = new Set(["contact_page_found"]);

export function SignalsList({ signals }: { signals: Signal[] }) {
  const rows = signals.filter((s) => !HIDE.has(s.key)).sort((a, b) => a.key.localeCompare(b.key));
  if (!rows.length) return <p className="text-xs text-muted">No website signals (no site, blocked, or unreachable).</p>;
  return (
    <dl className="grid grid-cols-[auto_1fr_auto] gap-x-3 gap-y-1 text-xs">
      {rows.map((s) => (
        <div key={s.key} className="contents">
          <dt className="text-muted">{s.key.replaceAll("_", " ")}</dt>
          <dd className="truncate">{s.value}</dd>
          <dd><span className={`rounded border px-1 py-px text-[10px] ${PILL[s.source]}`} title={s.source === "llm" ? `AI extraction, confidence ${s.confidence.toFixed(2)}` : s.source}>{s.source}</span></dd>
        </div>
      ))}
    </dl>
  );
}
