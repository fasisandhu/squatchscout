import { Download } from "lucide-react";
import { api } from "../api/client";
import type { Weights } from "../api/types";

export function ExportMenu({ searchId, selected, total, weights, disabled }: { searchId: string | null; selected: string[]; total: number; weights: Weights; disabled: boolean }) {
  const scope = selected.length ? `${selected.length} selected` : `all ${total}`;
  function download(format: "csv" | "hubspot") {
    if (!searchId) return;
    const a = document.createElement("a");
    a.href = api.exportUrl(searchId, format, selected, weights);
    a.download = "";
    document.body.appendChild(a); a.click(); a.remove();
  }
  return (
    <section className="card p-4 flex flex-col gap-2" aria-labelledby="export-h">
      <h2 id="export-h" className="text-sm font-semibold">Export {total > 0 && <span className="text-muted">({scope})</span>}</h2>
      <div className="grid grid-cols-2 gap-2">
        <button type="button" disabled={disabled || !total} onClick={() => download("csv")} className="btn-secondary"><Download className="size-4" aria-hidden /> CSV</button>
        <button type="button" disabled={disabled || !total} onClick={() => download("hubspot")} className="btn-secondary"><Download className="size-4" aria-hidden /> HubSpot CSV</button>
      </div>
      <p className="text-[11px] text-muted">HubSpot file uses its company-import column names. Both carry your current weights and OSM attribution.</p>
    </section>
  );
}
