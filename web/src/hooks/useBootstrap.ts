import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { Industry, Weights } from "../api/types";

export function useBootstrap() {
  const [industries, setIndustries] = useState<Industry[]>([]);
  const [presets, setPresets] = useState<Record<string, Weights>>({});
  const [llmEnabled, setLlmEnabled] = useState(false);
  const [version, setVersion] = useState("");
  const [apiDown, setApiDown] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [h, i] = await Promise.all([api.health(), api.industries()]);
        if (cancelled) return;
        setLlmEnabled(h.llm_enabled); setVersion(h.version); setIndustries(i.industries); setPresets(i.presets); setApiDown(false);
      } catch { if (!cancelled) setApiDown(true); }
    })();
    return () => { cancelled = true; };
  }, [tick]);

  return { industries, presets, llmEnabled, version, apiDown, retry: useCallback(() => setTick((t) => t + 1), []) };
}
