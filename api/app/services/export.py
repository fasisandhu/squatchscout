import csv
import io

from app.pipeline.score import FACTORS, FactorScore, tier, total
from app.schemas import LeadOut

ATTRIBUTION = "data © OpenStreetMap contributors (ODbL) + business websites"

HUBSPOT_COLUMNS = [
    "Company name",
    "Company Domain Name",
    "Phone Number",
    "Street Address",
    "City",
    "State/Region",
    "Postal Code",
    "Country/Region",
    "Industry",
    "Website URL",
    "Description",
    "SquatchScout Score",
    "Tier",
    "Verified Email",
    "Founded Year",
    "Owner Operated",
    "Chain Suspected",
    "Data Sources",
]

CSV_COLUMNS = [
    "id",
    "display_name",
    "name",
    "score",
    "tier",
    "street",
    "city",
    "state",
    "postcode",
    "country",
    "address_source",
    "website",
    "domain",
    "emails",
    "phones",
    "socials",
    "is_chain_suspected",
    "enrichment_status",
    "llm_status",
    "founded_year",
    "owner_operated",
    "owner_name",
    "family_owned",
    "site_builder",
    "has_booking",
    "has_chat",
    "reasons",
]


def _weights_str(w: dict[str, float]) -> str:
    return "/".join(str(int(w.get(f, 0))) for f in FACTORS)


def _rescore(
    lead: LeadOut, weights: dict[str, float], recompute: bool
) -> tuple[float | None, str | None]:
    if not recompute or not lead.factor_scores:
        return lead.score, lead.tier
    fs = [FactorScore(**f.model_dump()) for f in lead.factor_scores]
    t = total(fs, weights)
    return t, tier(t)


def _sig(lead: LeadOut, key: str) -> str:
    return next((s.value for s in lead.signals if s.key == key), "")


def _contacts(lead: LeadOut, kind: str, statuses: set[str] | None = None) -> list[str]:
    return [
        c.value
        for c in lead.contacts
        if c.kind == kind and (statuses is None or c.verification_status in statuses)
    ]


def _reasons(lead: LeadOut) -> str:
    return "; ".join(r for f in lead.factor_scores for r in f.reasons)


def to_csv(leads: list[LeadOut], weights: dict[str, float], recompute: bool = False) -> str:
    buf = io.StringIO()
    buf.write(
        f"# SquatchScout export · weights R/E/D/B/S={_weights_str(weights)} · {ATTRIBUTION}\n"
    )
    w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    w.writeheader()
    for lead in leads:
        score, tr = _rescore(lead, weights, recompute)
        a = lead.address
        w.writerow(
            {
                "id": lead.id,
                "display_name": lead.display_name,
                "name": lead.name,
                "score": score,
                "tier": tr,
                "street": a.street or "",
                "city": a.city or "",
                "state": a.state or "",
                "postcode": a.postcode or "",
                "country": a.country or "",
                "address_source": lead.address_source,
                "website": lead.website or "",
                "domain": lead.domain or "",
                "emails": " ".join(_contacts(lead, "email")),
                "phones": " ".join(_contacts(lead, "phone")),
                "socials": " ".join(_contacts(lead, "social")),
                "is_chain_suspected": lead.is_chain_suspected,
                "enrichment_status": lead.enrichment_status,
                "llm_status": lead.llm_status,
                "founded_year": _sig(lead, "founded_year"),
                "owner_operated": _sig(lead, "owner_operated"),
                "owner_name": _sig(lead, "owner_name"),
                "family_owned": _sig(lead, "family_owned"),
                "site_builder": _sig(lead, "site_builder"),
                "has_booking": _sig(lead, "has_booking"),
                "has_chat": _sig(lead, "has_chat"),
                "reasons": _reasons(lead),
            }
        )
    return buf.getvalue()


def to_hubspot_csv(
    leads: list[LeadOut],
    weights: dict[str, float],
    industry_label: str = "",
    recompute: bool = False,
) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=HUBSPOT_COLUMNS, lineterminator="\n")
    w.writeheader()
    sources = f"SquatchScout · weights R/E/D/B/S={_weights_str(weights)} · {ATTRIBUTION}"
    for lead in leads:
        score, tr = _rescore(lead, weights, recompute)
        a = lead.address
        phones = _contacts(lead, "phone")
        verified = _contacts(lead, "email", {"verified"})
        w.writerow(
            {
                "Company name": lead.display_name,
                "Company Domain Name": lead.domain or "",
                "Phone Number": phones[0] if phones else "",
                "Street Address": a.street or "",
                "City": a.city or "",
                "State/Region": a.state or "",
                "Postal Code": a.postcode or "",
                "Country/Region": a.country or "",
                "Industry": industry_label,
                "Website URL": lead.website or "",
                "Description": _reasons(lead),
                "SquatchScout Score": score,
                "Tier": tr,
                "Verified Email": verified[0] if verified else "",
                "Founded Year": _sig(lead, "founded_year"),
                "Owner Operated": _sig(lead, "owner_operated"),
                "Chain Suspected": lead.is_chain_suspected,
                "Data Sources": sources,
            }
        )
    return buf.getvalue()
