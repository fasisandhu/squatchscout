import { ExternalLink, X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { Weights } from "../api/types";
import type { RankedLead } from "../state/searchReducer";
import { ContactsList } from "./ContactsList";
import { FactorBars } from "./FactorBars";
import { OpenerPanel } from "./OpenerPanel";
import { ScoreChip } from "./ScoreChip";
import { SignalsList } from "./SignalsList";

export function LeadDrawer({ lead, weights, llmEnabled, onClose }: { lead: RankedLead | null; weights: Weights; llmEnabled: boolean; onClose: () => void }) {
  const panel = useRef<HTMLDivElement>(null);
  const restore = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => { onCloseRef.current = onClose; });

  // Keyed on the lead's identity only (not the lead object or onClose, both of which are new
  // every render) so an unrelated App re-render — a slider drag, a `lead_updated` SSE event for
  // this same lead, a `status` tick — doesn't tear down and re-arm the trap and bounce focus.
  const leadId = lead?.id ?? null;
  useEffect(() => {
    if (!leadId) return;
    restore.current = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseRef.current();
      if (e.key === "Tab" && panel.current) {  // simple focus trap
        const els = panel.current.querySelectorAll<HTMLElement>('button, a[href], input, [tabindex]:not([tabindex="-1"])');
        if (!els.length) return;
        const first = els[0], last = els[els.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); restore.current?.focus(); };
  }, [leadId]);

  if (!lead) return null;
  const a = lead.address;
  const addr = [a.street && `${a.housenumber ?? ""} ${a.street}`.trim(), a.city, a.state, a.postcode].filter(Boolean).join(", ");
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/50" onClick={onClose}>
      <div ref={panel} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="drawer-title" onClick={(e) => e.stopPropagation()}
        className="flex h-full w-full max-w-lg flex-col gap-5 overflow-y-auto border-l border-border bg-surface p-5 shadow-2xl focus:outline-none">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="drawer-title" className="text-lg font-semibold">{lead.display_name}</h2>
            <p className="text-xs text-muted">{addr || "Address unknown"}{lead.address_source !== "osm" && lead.address_source !== "none" && <span> · address via {lead.address_source}</span>}</p>
            {lead.website && <a href={lead.website} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 text-xs text-accent-2 hover:underline">{lead.domain} <ExternalLink className="size-3" /></a>}
          </div>
          <div className="flex items-center gap-2">
            <ScoreChip score={lead.computedScore} tier={lead.computedTier} />
            <button type="button" onClick={onClose} aria-label="Close" className="rounded-md p-1 text-muted hover:bg-surface-2 hover:text-text"><X className="size-5" /></button>
          </div>
        </div>
        <section aria-labelledby="why-h"><h3 id="why-h" className="mb-2 text-sm font-semibold">Why this score</h3><FactorBars factorScores={lead.factor_scores} weights={weights} /></section>
        <section aria-labelledby="contacts-h"><h3 id="contacts-h" className="mb-2 text-sm font-semibold">Contacts</h3><ContactsList contacts={lead.contacts} /></section>
        <section aria-labelledby="signals-h"><h3 id="signals-h" className="mb-2 text-sm font-semibold">Signals</h3><SignalsList signals={lead.signals} /></section>
        {llmEnabled && <section aria-labelledby="opener-h"><h3 id="opener-h" className="mb-2 text-sm font-semibold">Outreach</h3><OpenerPanel leadId={lead.id} /></section>}
      </div>
    </div>
  );
}
