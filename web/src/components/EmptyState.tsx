import { Compass } from "lucide-react";

const EXAMPLES = ["Plumbers in Austin, TX with owners near retirement", "Independent pharmacies in Columbus, Ohio with outdated websites"];

export function EmptyState({ onExample, llmEnabled }: { onExample: (text: string) => void; llmEnabled: boolean }) {
  return (
    <div className="card flex flex-col items-center gap-3 px-6 py-14 text-center">
      <Compass className="size-8 text-accent" aria-hidden />
      <h2 className="text-lg font-semibold">Find the businesses worth calling first</h2>
      <p className="max-w-md text-sm text-muted">
        Pick an industry and a place. SquatchScout finds independent businesses on OpenStreetMap, checks their websites,
        verifies contacts, and ranks each one with a score you can read the reasons for.
      </p>
      {llmEnabled && (
        <div className="flex flex-wrap justify-center gap-2 pt-2">
          {EXAMPLES.map((t) => (
            <button key={t} type="button" onClick={() => onExample(t)} className="chip">“{t}”</button>
          ))}
        </div>
      )}
    </div>
  );
}
