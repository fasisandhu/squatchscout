import { OSM_ATTRIBUTION } from "../config";

export function AttributionFooter({ version, llmEnabled }: { version: string; llmEnabled: boolean }) {
  return (
    <footer className="mt-auto border-t border-border px-4 py-3 text-center text-xs text-muted">
      Business data {OSM_ATTRIBUTION} (ODbL) and the businesses' own websites, collected with robots.txt respected.
      {!llmEnabled && " AI features are off on this deployment."} {version && <span className="ml-2 opacity-60">v{version}</span>}
    </footer>
  );
}
