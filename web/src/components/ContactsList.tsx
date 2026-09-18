import { Globe, Mail, Phone } from "lucide-react";
import type { Contact } from "../api/types";

const STATUS: Record<string, string> = { verified: "text-tier-a", valid: "text-tier-a", unverified: "text-tier-c", possible: "text-tier-c", invalid: "text-tier-d line-through", not_checked: "text-muted" };

export function ContactsList({ contacts }: { contacts: Contact[] }) {
  if (!contacts.length) return <p className="text-xs text-muted">No contacts found on OSM or the website.</p>;
  return (
    <ul className="flex flex-col gap-1.5 text-sm">
      {contacts.map((c) => (
        <li key={`${c.kind}:${c.value}`} className="flex items-center gap-2">
          {c.kind === "email" ? <Mail className="size-4 text-muted" /> : c.kind === "phone" ? <Phone className="size-4 text-muted" /> : <Globe className="size-4 text-muted" />}
          {c.kind === "social" ? <a href={c.value} target="_blank" rel="noreferrer" className="truncate text-accent-2 hover:underline">{c.value}</a>
            : <a href={c.kind === "email" ? `mailto:${c.value}` : `tel:${c.value}`} className="truncate hover:underline">{c.value}</a>}
          <span className={`ml-auto text-[11px] ${STATUS[c.verification_status] ?? "text-muted"}`}>{c.verification_status.replace("_", " ")}</span>
          <span className="text-[11px] text-muted">{c.source}</span>
        </li>
      ))}
    </ul>
  );
}
