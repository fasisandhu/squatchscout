import { X } from "lucide-react";
import { useEffect, useRef } from "react";

export function ErrorToast({ message, onDismiss }: { message: string | null; onDismiss: () => void }) {
  const onDismissRef = useRef(onDismiss);
  useEffect(() => { onDismissRef.current = onDismiss; });

  // Keyed on `message` alone (not `onDismiss`, which App.tsx passes as a fresh arrow every
  // render) so an unrelated App re-render — a slider drag, a row toggle, any streaming `lead`
  // event — doesn't restart the 8s timer. A genuinely new message still restarts it, since that
  // changes the dependency.
  useEffect(() => { if (!message) return; const t = setTimeout(() => onDismissRef.current(), 8000); return () => clearTimeout(t); }, [message]);
  if (!message) return null;
  return (
    <div role="alert" className="fixed bottom-4 left-1/2 z-50 flex max-w-[90vw] -translate-x-1/2 flex-wrap items-center gap-3 rounded-lg border border-tier-c/50 bg-surface px-4 py-2 text-sm shadow-xl">
      <span>{message}</span>
      <button type="button" onClick={onDismiss} aria-label="Dismiss" className="text-muted hover:text-text"><X className="size-4" /></button>
    </div>
  );
}
