import { Loader2, Search, Sparkles } from "lucide-react";
import { useState } from "react";
import type React from "react";
import { api, ApiError } from "../api/client";
import type { Industry, SearchCreate } from "../api/types";

interface Props {
  industries: Industry[];
  llmEnabled: boolean;
  busy: boolean;
  onSubmit: (body: SearchCreate, preset?: string) => void;
  initialText?: string;
}

export function SearchBar({ industries, llmEnabled, busy, onSubmit, initialText }: Props) {
  const [nl, setNl] = useState(initialText ?? "");
  const [industry, setIndustry] = useState("");
  const [location, setLocation] = useState("");
  const [limit, setLimit] = useState(60);
  const [preset, setPreset] = useState<string | undefined>();
  const [rationale, setRationale] = useState<string | null>(null);
  const [parsing, setParsing] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const canRun = industry !== "" && location.trim().length >= 2 && !busy;

  async function parseIntent() {
    if (!nl.trim()) return;
    setParsing(true); setErr(null); setRationale(null);
    try {
      const r = await api.intent(nl.trim());
      if (r.industry_key) setIndustry(r.industry_key);
      if (r.location) setLocation(r.location);
      if (r.limit) setLimit(r.limit);
      setPreset(r.weight_preset);
      setRationale(r.rationale || null);
      if (!r.industry_key) setErr("I couldn't map that to one of the supported industries — pick one below.");
    } catch (e) {
      setErr(e instanceof ApiError && e.code.startsWith("llm") ? "AI parsing is unavailable right now — fill the form instead." : "Could not parse that request.");
    } finally { setParsing(false); }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!canRun) return;
    onSubmit({ industry_key: industry, location: location.trim(), limit, weight_preset: preset, nl_query: nl.trim() || null }, preset);
  }

  return (
    <form onSubmit={submit} className="card p-4 flex flex-col gap-3" aria-label="Search for businesses">
      {llmEnabled && (
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Sparkles className="absolute left-3 top-2.5 size-4 text-accent" aria-hidden />
            <input className="input pl-9" value={nl} onChange={(e) => setNl(e.target.value)} placeholder='Describe it: "dentists in Austin, ideally owners near retirement"'
              aria-label="Describe your search in plain language" onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); void parseIntent(); } }} />
          </div>
          <button type="button" onClick={parseIntent} disabled={parsing || !nl.trim()} className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm hover:bg-border disabled:opacity-50">
            {parsing ? <Loader2 className="size-4 animate-spin" aria-label="Parsing" /> : "Fill form"}
          </button>
        </div>
      )}
      {rationale && <p className="text-xs text-muted"><span className="text-accent">AI:</span> {rationale}</p>}
      <div className="grid gap-2 sm:grid-cols-[1fr_1fr_110px_auto]">
        <select className="input" value={industry} onChange={(e) => setIndustry(e.target.value)} aria-label="Industry" required>
          <option value="">Industry…</option>
          {industries.map((i) => <option key={i.key} value={i.key}>{i.label}</option>)}
        </select>
        <input className="input" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="City, state or country" aria-label="Location" required minLength={2} />
        <input className="input" type="number" min={5} max={100} value={limit} onChange={(e) => setLimit(Number(e.target.value))} aria-label="Maximum results" />
        <button type="submit" disabled={!canRun} className="btn-primary flex items-center justify-center gap-2">
          {busy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Search className="size-4" aria-hidden />} Scout
        </button>
      </div>
      {err && <p className="text-sm text-tier-c" role="alert">{err}</p>}
    </form>
  );
}
