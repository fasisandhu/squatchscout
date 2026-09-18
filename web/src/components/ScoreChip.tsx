import type { Tier } from "../api/types";

const TIER_CLASS: Record<Tier, string> = {
  A: "bg-tier-a/15 text-tier-a border-tier-a/40", B: "bg-tier-b/15 text-tier-b border-tier-b/40",
  C: "bg-tier-c/15 text-tier-c border-tier-c/40", D: "bg-tier-d/15 text-tier-d border-tier-d/40" };

export function ScoreChip({ score, tier, size = "md" }: { score: number; tier: Tier; size?: "sm" | "md" }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border font-semibold tabular-nums ${TIER_CLASS[tier]} ${size === "sm" ? "px-1.5 py-0.5 text-xs" : "px-2 py-1 text-sm"}`}
      aria-label={`Score ${score}, tier ${tier}`}>
      <span>{tier}</span><span className="opacity-80">{score.toFixed(0)}</span>
    </span>
  );
}
