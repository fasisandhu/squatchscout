import type { DoneEvent, ErrorEvent, Lead, LeadUpdatedEvent, StatusEvent } from "./types";

export interface StreamHandlers {
  onStatus: (e: StatusEvent) => void;
  onLead: (l: Lead) => void;
  onLeadUpdated: (u: LeadUpdatedEvent) => void;
  onDone: (d: DoneEvent) => void;
  onError: (e: ErrorEvent) => void;
}

/** Opens the SSE stream. Returns a disposer. Named events match the API's `event:` field exactly. */
export function openStream(url: string, h: StreamHandlers): () => void {
  const es = new EventSource(url);
  const parse = <T>(ev: MessageEvent) => JSON.parse(ev.data as string) as T;
  es.addEventListener("status", (ev) => h.onStatus(parse<StatusEvent>(ev as MessageEvent)));
  es.addEventListener("lead", (ev) => h.onLead(parse<Lead>(ev as MessageEvent)));
  es.addEventListener("lead_updated", (ev) => h.onLeadUpdated(parse<LeadUpdatedEvent>(ev as MessageEvent)));
  es.addEventListener("done", (ev) => { h.onDone(parse<DoneEvent>(ev as MessageEvent)); es.close(); });
  es.addEventListener("error", (ev) => {
    // A named `error` event from the server carries JSON; a transport failure does not.
    const data = (ev as MessageEvent).data as string | undefined;
    if (data) { h.onError(parse<ErrorEvent>(ev as MessageEvent)); es.close(); return; }
    if (es.readyState === EventSource.CLOSED) h.onError({ message: "Connection to the API was lost." });
  });
  return () => es.close();
}
