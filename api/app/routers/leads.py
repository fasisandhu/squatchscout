from fastapi import APIRouter
from sqlmodel import select

from app import deps
from app.deps import SessionDep
from app.llm.prompts import opener_messages
from app.llm.schemas import OPENER_SCHEMA
from app.models import Contact, FactorScoreRow, Lead, Search, Signal
from app.pipeline.industries import INDUSTRIES
from app.routers.intent import llm_unavailable
from app.routers.searches import not_found
from app.schemas import LeadOut, lead_to_out

router = APIRouter(prefix="/api/leads")


def strip_control_chars(text: str) -> str:
    """Drop C0 control characters and DEL, keeping tab and newline."""
    return "".join(c for c in text if c in "\n\t" or (ord(c) >= 32 and ord(c) != 127))


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: str, s: SessionDep) -> LeadOut:
    lead = s.get(Lead, lead_id)
    if not lead:
        raise not_found("Lead")
    return lead_to_out(
        lead,
        s.exec(select(Contact).where(Contact.lead_id == lead_id)).all(),
        s.exec(select(Signal).where(Signal.lead_id == lead_id)).all(),
        s.exec(select(FactorScoreRow).where(FactorScoreRow.lead_id == lead_id)).all(),
    )


@router.post("/{lead_id}/opener")
async def opener(lead_id: str, s: SessionDep) -> dict:
    lead = s.get(Lead, lead_id)
    if not lead:
        raise not_found("Lead")
    signals = {
        x.key: x.value for x in s.exec(select(Signal).where(Signal.lead_id == lead_id)).all()
    }
    search = s.get(Search, lead.search_id)
    industry = INDUSTRIES.get(search.industry_key) if search else None
    summary = {
        "business": lead.display_name,
        "city": lead.city,
        "industry": industry.label if industry else None,
        "facts": {
            k: signals[k]
            for k in (
                "founded_year",
                "owner_name",
                "family_owned",
                "services",
                "hiring",
                "site_builder",
                "has_booking",
            )
            if k in signals
        },
    }
    system, user = opener_messages(summary)
    # 600, not 160. A three-line opener costs 74-90 completion tokens, but Groq's strict-JSON
    # decoder force-closes the string as the generation nears its budget, so a starved call
    # comes back as a *successful* two-line draft cut mid-sentence: finish_reason is "stop",
    # not "length". Measured across five leads, 160 truncated every one and 600 truncated none.
    data, status = await deps.get_pool().complete_json(
        schema_name="opener", schema=OPENER_SCHEMA, system=system, user=user, max_tokens=600
    )
    if status != "ok" or not data or not data.get("opener"):
        raise llm_unavailable(status)
    raw = data["opener"]
    cleaned = strip_control_chars(raw)
    # A stray C0 control character is the one in-band marker that the decoder was cut off
    # mid-string. Better a clean error than half a sentence the caller might read aloud.
    if cleaned != raw or not cleaned.strip():
        raise llm_unavailable("truncated")
    return {"opener": cleaned.strip()}
