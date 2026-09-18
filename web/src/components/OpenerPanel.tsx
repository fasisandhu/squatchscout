import { Copy, Loader2, Sparkles } from "lucide-react";
import { useState } from "react";
import { api, ApiError } from "../api/client";

export function OpenerPanel({ leadId }: { leadId: string }) {
  const [text, setText] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function draft() {
    setBusy(true); setErr(null);
    try { setText((await api.opener(leadId)).opener); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not draft an opener."); }
    finally { setBusy(false); }
  }

  return (
    <div className="flex flex-col gap-2">
      {text ? (
        <>
          <pre className="whitespace-pre-wrap rounded-lg border border-border bg-surface-2 p-3 text-sm">{text}</pre>
          <div className="flex gap-2">
            <button type="button" onClick={() => navigator.clipboard?.writeText(text).catch(() => setErr("Couldn't copy — select the text above instead."))} className="inline-flex items-center gap-1 text-xs text-muted hover:text-text"><Copy className="size-3" /> copy</button>
            <button type="button" onClick={draft} disabled={busy} className="text-xs text-muted hover:text-text">redraft</button>
          </div>
        </>
      ) : (
        <button type="button" onClick={draft} disabled={busy} className="inline-flex items-center gap-2 rounded-lg border border-accent/40 px-3 py-2 text-sm text-accent hover:bg-accent/10 disabled:opacity-50">
          {busy ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />} Draft call opener
        </button>
      )}
      {err && <p className="text-xs text-tier-c" role="alert">{err}</p>}
      <p className="text-[11px] text-muted">Grounded only in the signals above — nothing invented.</p>
    </div>
  );
}
