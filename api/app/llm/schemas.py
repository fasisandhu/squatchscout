import re
from typing import Literal

from pydantic import BaseModel, Field

PRESETS = ["balanced", "succession", "digital_upside", "reachability_first"]


def _nullable(t: str, **extra) -> dict:
    return {"type": [t, "null"], **extra}


INTENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["industry_key", "location", "limit", "weight_preset", "rationale"],
    "properties": {
        "industry_key": _nullable("string"),
        "location": _nullable("string"),
        "limit": _nullable("integer"),
        "weight_preset": {"type": "string", "enum": PRESETS},
        "rationale": {"type": "string"},
    },
}

ADDRESS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["street", "city", "state", "postcode"],
    "properties": {k: _nullable("string") for k in ("street", "city", "state", "postcode")},
}

EXTRACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "display_name",
        "founded_year",
        "owner_operated",
        "owner_name",
        "family_owned",
        "is_chain",
        "hiring",
        "services",
        "address",
        "confidence",
    ],
    "properties": {
        "display_name": _nullable("string"),
        "founded_year": _nullable("integer"),
        "owner_operated": _nullable("boolean"),
        "owner_name": _nullable("string"),
        "family_owned": _nullable("boolean"),
        "is_chain": _nullable("boolean"),
        "hiring": _nullable("boolean"),
        "services": {"type": "array", "items": {"type": "string"}},
        "address": ADDRESS_SCHEMA,
        "confidence": {"type": "number"},
    },
}

OPENER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["opener"],
    "properties": {"opener": {"type": "string"}},
}


class IntentResult(BaseModel):
    industry_key: str | None
    location: str | None
    limit: int | None
    weight_preset: Literal["balanced", "succession", "digital_upside", "reachability_first"] = (
        "balanced"
    )
    rationale: str = ""


class LLMAddress(BaseModel):
    street: str | None = None
    city: str | None = None
    state: str | None = None
    postcode: str | None = None


class ExtractionResult(BaseModel):
    display_name: str | None = None
    founded_year: int | None = None
    owner_operated: bool | None = None
    owner_name: str | None = None
    family_owned: bool | None = None
    is_chain: bool | None = None
    hiring: bool | None = None
    services: list[str] = Field(default_factory=list)
    address: LLMAddress = Field(default_factory=LLMAddress)
    confidence: float = 0.0

    def validated(
        self, source_text: str, osm_name: str, country_code: str, current_year: int
    ) -> "ExtractionResult":
        """Field-by-field validation (spec §7.2). Bad fields are dropped; the rest survive."""
        r = self.model_copy(deep=True)
        low = source_text.lower()
        if r.founded_year is not None and not (1850 <= r.founded_year <= current_year):
            r.founded_year = None
        if r.owner_name and r.owner_name.lower() not in low:
            r.owner_name = None  # grounding check -- hallucinated names are discarded
        if r.display_name:
            a = set(re.findall(r"\w+", r.display_name.lower()))
            b = set(re.findall(r"\w+", osm_name.lower()))
            if not b or len(a & b) / len(b) < 0.6:
                r.display_name = None
        if r.address.postcode:
            ok = (
                re.fullmatch(r"\d{5}(-\d{4})?", r.address.postcode)
                if country_code == "US"
                else re.fullmatch(r"[A-Za-z]\d[A-Za-z] ?\d[A-Za-z]\d", r.address.postcode)
                if country_code == "CA"
                else re.fullmatch(r"[A-Za-z0-9 -]{3,10}", r.address.postcode)
            )
            if not ok:
                r.address.postcode = None
        r.services = [s.strip()[:40] for s in r.services if s and s.strip()][:8]
        r.confidence = min(max(float(r.confidence), 0.0), 1.0)
        return r
