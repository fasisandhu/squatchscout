import { Loader2 } from "lucide-react";
import type { StatusEvent } from "../api/types";
import type { Phase } from "../state/searchReducer";

interface Props { phase: Phase; status: StatusEvent | null; found: number; llmPending: number; error: string | null; }

export function StatusStrip({ phase, status, found, llmPending, error }: Props) {
  if (phase === "idle") return null;
  const text =
    phase === "error" ? error ?? "Something went wrong." :
    phase === "starting" ? "Starting…" :
    phase === "streaming" ? `${status?.message ?? "Working…"} ${found ? `· ${found} found` : ""}` :
    phase === "refining" ? `Refining ${llmPending} lead${llmPending === 1 ? "" : "s"} with AI… · ${found} found` :
    `Done · ${found} lead${found === 1 ? "" : "s"}`;
  const live = phase === "starting" || phase === "streaming" || phase === "refining";
  return (
    <div role="status" aria-live="polite" className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${phase === "error" ? "border-tier-c/50 text-tier-c" : "border-border text-muted"}`}>
      {live && <Loader2 className="size-4 animate-spin text-accent" aria-hidden />}
      <span>{text}</span>
    </div>
  );
}
