from datetime import datetime

from pydantic import BaseModel, Field

from app.models import Contact, FactorScoreRow, Lead, Search, Signal
from app.pipeline.industries import Industry
from app.pipeline.normalize import is_generic_name
from app.pipeline.score import LeadFacts

EMAIL_RANK = {"verified": 3, "unverified": 2, "invalid": 1}
PHONE_RANK = {"valid": 3, "possible": 2, "invalid": 1}


class SearchCreate(BaseModel):
    industry_key: str
    location: str = Field(min_length=2, max_length=120)
    limit: int = Field(default=60, ge=5, le=100)
    weight_preset: str = "balanced"
    nl_query: str | None = None


class IntentRequest(BaseModel):
    text: str = Field(min_length=3, max_length=500)


class AddressOut(BaseModel):
    street: str | None
    housenumber: str | None
    city: str | None
    state: str | None
    postcode: str | None
    country: str | None


class ContactOut(BaseModel):
    kind: str
    value: str
    source: str
    verification_status: str


class SignalOut(BaseModel):
    key: str
    value: str
    source: str
    confidence: float


class FactorScoreOut(BaseModel):
    factor: str
    points: float
    max_points: float
    reasons: list[str]


class LeadOut(BaseModel):
    id: str
    name: str
    display_name: str
    address: AddressOut
    address_source: str
    lat: float
    lon: float
    website: str | None
    domain: str | None
    is_chain_suspected: bool
    enrichment_status: str
    llm_status: str
    score: float | None
    tier: str | None
    contacts: list[ContactOut]
    signals: list[SignalOut]
    factor_scores: list[FactorScoreOut]


class SearchOut(BaseModel):
    id: str
    industry_key: str
    location_query: str
    geocoded_name: str | None
    weight_preset: str
    status: str
    lead_count: int
    llm_pending: int
    error: str | None
    created_at: datetime
    finished_at: datetime | None

    @classmethod
    def from_row(cls, s: Search) -> "SearchOut":
        return cls(**{k: getattr(s, k) for k in cls.model_fields})


def lead_to_out(
    lead: Lead, contacts: list[Contact], signals: list[Signal], factors: list[FactorScoreRow]
) -> LeadOut:
    return LeadOut(
        id=lead.id,
        name=lead.name,
        display_name=lead.display_name,
        address=AddressOut(
            street=lead.street,
            housenumber=lead.housenumber,
            city=lead.city,
            state=lead.state,
            postcode=lead.postcode,
            country=lead.country,
        ),
        address_source=lead.address_source,
        lat=lead.lat,
        lon=lead.lon,
        website=lead.website,
        domain=lead.normalized_domain,
        is_chain_suspected=lead.is_chain_suspected,
        enrichment_status=lead.enrichment_status,
        llm_status=lead.llm_status,
        score=lead.score,
        tier=lead.tier,
        contacts=[
            ContactOut(
                kind=c.kind,
                value=c.value,
                source=c.source,
                verification_status=c.verification_status,
            )
            for c in contacts
        ],
        signals=[
            SignalOut(key=s.key, value=s.value, source=s.source, confidence=s.confidence)
            for s in signals
        ],
        factor_scores=[
            FactorScoreOut(
                factor=f.factor, points=f.points, max_points=f.max_points, reasons=list(f.reasons)
            )
            for f in factors
        ],
    )


def _best(contacts: list[Contact], kind: str, rank: dict[str, int]) -> str:
    statuses = [
        c.verification_status for c in contacts if c.kind == kind and c.verification_status in rank
    ]
    return max(statuses, key=rank.__getitem__) if statuses else "none"


def _int(v: str | None) -> int | None:
    try:
        return int(v) if v is not None else None
    except ValueError:
        return None


def _bool(v: str | None) -> bool | None:
    return None if v is None else v.lower() == "true"


def build_facts(
    lead: Lead, contacts: list[Contact], signals: list[Signal], industry: Industry
) -> LeadFacts:
    sig = {s.key: s.value for s in signals}
    tags = lead.osm_tags or {}
    owner_name_found = bool(sig.get("owner_name"))
    family_owned = _bool(sig.get("family_owned")) or False
    owner_operated = _bool(sig.get("owner_operated"))
    if owner_operated is None and (owner_name_found or family_owned):
        owner_operated = True
    return LeadFacts(
        industry_key=industry.key,
        has_website=bool(lead.website),
        site_reachable=lead.enrichment_status == "ok",
        contact_page_found=_bool(sig.get("contact_page_found")) or False,
        best_email_status=_best(contacts, "email", EMAIL_RANK),
        best_phone_status=_best(contacts, "phone", PHONE_RANK),
        founded_year=_int(sig.get("founded_year")),
        owner_name_found=owner_name_found,
        owner_operated=owner_operated,
        family_owned=family_owned,
        is_chain_suspected=lead.is_chain_suspected or (_bool(sig.get("is_chain")) or False),
        has_physical_address=bool(lead.street and lead.city),
        osm_full_address=all(
            tags.get(k) for k in ("addr:housenumber", "addr:street", "addr:city", "addr:postcode")
        ),
        osm_opening_hours="opening_hours" in tags,
        osm_has_contact=any(
            k in tags for k in ("phone", "contact:phone", "website", "contact:website")
        ),
        site_builder=sig.get("site_builder"),
        has_booking=_bool(sig.get("has_booking")) or False,
        has_chat=_bool(sig.get("has_chat")) or False,
        copyright_year=_int(sig.get("copyright_year")),
        generic_name=is_generic_name(lead.name, industry),
    )
