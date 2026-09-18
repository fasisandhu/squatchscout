import { X } from "lucide-react";
import { useEffect } from "react";

export function ErrorToast({ message, onDismiss }: { message: string | null; onDismiss: () => void }) {
  useEffect(() => { if (!message) return; const t = setTimeout(onDismiss, 8000); return () => clearTimeout(t); }, [message, onDismiss]);
  if (!message) return null;
  return (
    <div role="alert" className="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-lg border border-tier-c/50 bg-surface px-4 py-2 text-sm shadow-xl">
      <span>{message}</span>
      <button type="button" onClick={onDismiss} aria-label="Dismiss" className="text-muted hover:text-text"><X className="size-4" /></button>
    </div>
  );
}
