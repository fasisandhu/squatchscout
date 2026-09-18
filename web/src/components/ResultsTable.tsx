import { flexRender, type SortingState } from "@tanstack/react-table";
import { getCoreRowModel, getSortedRowModel, useLegacyTable as useReactTable, type LegacyColumnDef as ColumnDef } from "@tanstack/react-table/legacy";
import { ArrowDown, ArrowUp, Building2, MailCheck, ShieldAlert, Sparkles, Store } from "lucide-react";
import { useMemo, useState } from "react";
import type React from "react";
import type { RankedLead, Phase } from "../state/searchReducer";
import { ScoreChip } from "./ScoreChip";

interface Props { leads: RankedLead[]; selected: string[]; onToggle: (id: string) => void; onSelectAll: () => void;
  onClear: () => void; onOpen: (id: string) => void; phase: Phase; }

function Badge({ children, title, tone = "muted" }: { children: React.ReactNode; title: string; tone?: "muted" | "good" | "warn" }) {
  const cls = tone === "good" ? "text-tier-a border-tier-a/40" : tone === "warn" ? "text-tier-c border-tier-c/40" : "text-muted border-border";
  return <span title={title} className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[11px] ${cls}`}>{children}</span>;
}

export function ResultsTable({ leads, selected, onToggle, onSelectAll, onClear, onOpen, phase }: Props) {
  const [sorting, setSorting] = useState<SortingState>([{ id: "computedScore", desc: true }]);
  const allSelected = leads.length > 0 && selected.length === leads.length;
  const someSelected = selected.length > 0 && !allSelected;

  const columns = useMemo<ColumnDef<RankedLead>[]>(() => [
    { id: "select", enableSorting: false, size: 36,
      header: () => <input type="checkbox" aria-label="Select all" checked={allSelected}
        ref={(el) => { if (el) el.indeterminate = someSelected; }}
        onChange={() => (allSelected ? onClear() : onSelectAll())} />,
      cell: ({ row }) => <input type="checkbox" aria-label={`Select ${row.original.display_name}`} checked={selected.includes(row.original.id)}
        onChange={() => onToggle(row.original.id)} onClick={(e) => e.stopPropagation()} /> },
    { id: "computedScore", accessorKey: "computedScore", header: "Score", size: 90,
      cell: ({ row }) => <ScoreChip score={row.original.computedScore} tier={row.original.computedTier} size="sm" /> },
    { id: "name", accessorKey: "display_name", header: "Business",
      cell: ({ row }) => {
        const l = row.original;
        const verified = l.contacts.some((c) => c.kind === "email" && c.verification_status === "verified");
        return (
          <div className="flex flex-col gap-1">
            <span className="font-medium">{l.display_name}</span>
            <div className="flex flex-wrap gap-1">
              {verified && <Badge tone="good" title="Email verified via MX lookup"><MailCheck className="size-3" /> verified email</Badge>}
              {l.is_chain_suspected ? <Badge tone="warn" title="Name repeats or has a brand tag"><Building2 className="size-3" /> chain?</Badge>
                : <Badge title="Single independent listing"><Store className="size-3" /> independent</Badge>}
              {l.enrichment_status === "no_website" && <Badge title="No website found — high digital upside">no website</Badge>}
              {(l.enrichment_status === "unreachable" || l.enrichment_status === "blocked_by_robots") &&
                <Badge tone="warn" title={l.enrichment_status === "blocked_by_robots" ? "Site's robots.txt disallows crawling" : "Website did not respond"}><ShieldAlert className="size-3" /> {l.enrichment_status.replace("_", " ")}</Badge>}
              {l.llm_status === "done" && <Badge title="Refined with AI extraction"><Sparkles className="size-3 text-accent" /> refined</Badge>}
            </div>
          </div>
        );
      } },
    { id: "city", accessorFn: (l) => l.address.city ?? "", header: "City", size: 140, cell: ({ getValue }) => <span className="text-muted">{getValue<string>() || "—"}</span> },
    { id: "phone", enableSorting: false, header: "Phone", size: 150,
      cell: ({ row }) => { const p = row.original.contacts.find((c) => c.kind === "phone"); return <span className="tabular-nums text-muted">{p?.value ?? "—"}</span>; } },
  ], [selected, allSelected, someSelected, onToggle, onSelectAll, onClear]);

  const table = useReactTable({ data: leads, columns, state: { sorting }, onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel() });

  if (leads.length === 0 && (phase === "done" || phase === "error")) {
    return <div className="card px-6 py-10 text-center text-sm text-muted">No businesses found here. Try a larger city, a nearby one, or a different industry.</div>;
  }

  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-xs uppercase tracking-wide text-muted">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} className="border-b border-border">
              {hg.headers.map((h) => (
                <th key={h.id} style={{ width: h.getSize() }} className="px-3 py-2 font-medium">
                  {h.column.getCanSort() ? (
                    <button type="button" onClick={h.column.getToggleSortingHandler()} className="inline-flex items-center gap-1 hover:text-text">
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      {h.column.getIsSorted() === "asc" ? <ArrowUp className="size-3" /> : h.column.getIsSorted() === "desc" ? <ArrowDown className="size-3" /> : null}
                    </button>
                  ) : flexRender(h.column.columnDef.header, h.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} tabIndex={0} onClick={() => onOpen(row.original.id)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen(row.original.id); } }}
              className="cursor-pointer border-b border-border/60 hover:bg-surface-2 focus:bg-surface-2 focus:outline-none">
              {row.getVisibleCells().map((cell) => <td key={cell.id} className="px-3 py-2 align-top">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      {phase === "streaming" && <div className="px-3 py-2 text-xs text-muted">More results arriving…</div>}
    </div>
  );
}
