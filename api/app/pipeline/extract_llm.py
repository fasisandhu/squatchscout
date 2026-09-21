import re
from typing import Literal

from pydantic import BaseModel

from app.llm.client import LLMPool, LLMStatus
from app.llm.prompts import extraction_messages
from app.llm.schemas import EXTRACTION_SCHEMA, ExtractionResult
from app.pipeline.crawl import PageBundle
from app.pipeline.extract_regex import RegexSignals

OVERRIDE_CONFIDENCE = 0.85
RELEVANT = re.compile(
    r"since|founded|est\b|est\.|family|owner|our team|about|locations?|address|located", re.I
)
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
GAP_FIELDS = ("founded_year", "owner_operated", "owner_name")


class SignalValue(BaseModel):
    key: str
    value: str
    source: Literal["regex", "llm"]
    confidence: float = 1.0


def needs_llm(regex: RegexSignals, has_street: bool, text_quality: str) -> bool:
    if text_quality == "thin":
        return True
    if any(getattr(regex, f) is None for f in GAP_FIELDS):
        return True
    return not has_street and not regex.street_address


def build_llm_input(bundle: PageBundle, max_chars: int = 2800) -> str:
    first = bundle.pages[0] if bundle.pages else None
    head = f"{first.title}\n{first.meta_description}\n" if first else ""
    sentences: list[str] = []
    for p in bundle.pages:
        sentences.extend(s.strip() for s in SENT_SPLIT.split(p.visible_text) if s.strip())
    relevant = [s for s in sentences if RELEVANT.search(s)]
    rest = [s for s in sentences if s not in relevant]
    out, budget = head, max_chars - len(head)
    for s in relevant + rest:
        if len(s) + 1 > budget:
            continue
        out += s + " "
        budget -= len(s) + 1
    return out.rstrip()[:max_chars]


async def extract_with_llm(
    pool: LLMPool, bundle: PageBundle, osm_name: str, country_code: str, current_year: int
) -> tuple[ExtractionResult | None, LLMStatus]:
    text = build_llm_input(bundle)
    system, user = extraction_messages(text, osm_name)
    data, status = await pool.complete_json(
        schema_name="extraction",
        schema=EXTRACTION_SCHEMA,
        system=system,
        user=user,
        # 800, not 350: one eval page (animal-hospital-signal-mtn) exhausted 350 and came
        # back as a hard 400 json_validate_failed, which burns the model-pool fallback and
        # drops the lead's enrichment entirely. Observed usage is 90-144 tokens.
        max_tokens=800,
    )
    if status != "ok" or data is None:
        return None, status
    try:
        result = ExtractionResult(**data).validated(text, osm_name, country_code, current_year)
    except (TypeError, ValueError):
        return None, "error"
    return result, "ok"


def _s(v) -> str:
    return str(v).lower() if isinstance(v, bool) else str(v)


def merge_signals(regex: RegexSignals, llm: ExtractionResult | None) -> list[SignalValue]:
    out: dict[str, SignalValue] = {}
    for key, val in regex.model_dump().items():
        if val is not None:
            out[key] = SignalValue(key=key, value=_s(val), source="regex", confidence=1.0)
    if llm is None:
        return list(out.values())
    llm_fields = {
        "display_name": llm.display_name,
        "founded_year": llm.founded_year,
        "owner_operated": llm.owner_operated,
        "owner_name": llm.owner_name,
        "family_owned": llm.family_owned,
        "is_chain": llm.is_chain,
        "hiring": llm.hiring,
        "street_address": llm.address.street,
        "city": llm.address.city,
        "state": llm.address.state,
        "postcode": llm.address.postcode,
        "services": ", ".join(llm.services) if llm.services else None,
    }
    for key, val in llm_fields.items():
        if val is None:
            continue
        existing = out.get(key)
        regex_has_value = (
            existing is not None
            and key in RegexSignals.model_fields
            and getattr(regex, key) not in (None, False)
        )
        if not regex_has_value or (
            llm.confidence >= OVERRIDE_CONFIDENCE and _s(val) != existing.value
        ):
            out[key] = SignalValue(key=key, value=_s(val), source="llm", confidence=llm.confidence)
    return list(out.values())
