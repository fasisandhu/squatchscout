import { useState } from "react";
import { AttributionFooter } from "./components/AttributionFooter";
import { EmptyState } from "./components/EmptyState";
import { ResultsTable } from "./components/ResultsTable";
import { SearchBar } from "./components/SearchBar";
import { StatusStrip } from "./components/StatusStrip";
import { APP_NAME } from "./config";
import { useBootstrap } from "./hooks/useBootstrap";
import { rankedLeads } from "./state/searchReducer";
import { useSearchSession } from "./state/useSearchSession";

export default function App() {
  const boot = useBootstrap();
  const session = useSearchSession();
  const [exampleText, setExampleText] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);
  void openId; // Task 24 wires the drawer
  const { state } = session;
  const ranked = rankedLeads(state);
  const busy = state.phase === "starting" || state.phase === "streaming";

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-baseline gap-2">
          <span className="bg-gradient-to-r from-accent to-accent-2 bg-clip-text text-lg font-bold text-transparent">{APP_NAME}</span>
          <span className="text-xs text-muted">ranked · verified · explained</span>
        </div>
        {boot.apiDown && (
          <button onClick={boot.retry} className="rounded-md border border-tier-c/50 px-2 py-1 text-xs text-tier-c">API unreachable — retry</button>
        )}
      </header>
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-4 px-4 py-6">
        <SearchBar key={exampleText ?? "bar"} industries={boot.industries} llmEnabled={boot.llmEnabled} busy={busy}
          initialText={exampleText ?? undefined}
          onSubmit={(body, preset) => { if (preset) session.applyPreset(preset); void session.start(body); }} />
        <StatusStrip phase={state.phase} status={state.status} found={ranked.length} llmPending={state.llmPending} error={state.error} />
        {state.phase === "idle" ? (
          <EmptyState llmEnabled={boot.llmEnabled} onExample={(t) => setExampleText(t)} />
        ) : (
          <ResultsTable leads={ranked} selected={state.selected} onToggle={session.toggleSelect} onSelectAll={session.selectAll}
            onClear={session.clearSelection} onOpen={setOpenId} phase={state.phase} />
        )}
      </main>
      <AttributionFooter version={boot.version} llmEnabled={boot.llmEnabled} />
    </div>
  );
}
