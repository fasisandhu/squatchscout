from typing import Literal

from pydantic import BaseModel

FACTORS = ["reachability", "establishment", "digital_gap", "buybox", "succession"]
MAX_POINTS = {
    "reachability": 25.0,
    "establishment": 20.0,
    "digital_gap": 20.0,
    "buybox": 20.0,
    "succession": 15.0,
}
WEIGHT_PRESETS: dict[str, dict[str, float]] = {
    "balanced": {
        "reachability": 25,
        "establishment": 20,
        "digital_gap": 20,
        "buybox": 20,
        "succession": 15,
    },
    "succession": {
        "reachability": 25,
        "establishment": 15,
        "digital_gap": 10,
        "buybox": 20,
        "succession": 30,
    },
    "digital_upside": {
        "reachability": 25,
        "establishment": 10,
        "digital_gap": 35,
        "buybox": 20,
        "succession": 10,
    },
    "reachability_first": {
        "reachability": 40,
        "establishment": 15,
        "digital_gap": 15,
        "buybox": 20,
        "succession": 10,
    },
}
DIY_BUILDERS = {"wix", "squarespace", "weebly", "godaddy", "duda", "wordpress"}


class LeadFacts(BaseModel):
    industry_key: str
    has_website: bool
    site_reachable: bool
    contact_page_found: bool
    best_email_status: Literal["verified", "unverified", "invalid", "none"]
    best_phone_status: Literal["valid", "possible", "invalid", "none"]
    founded_year: int | None
    owner_name_found: bool
    owner_operated: bool | None
    family_owned: bool
    is_chain_suspected: bool
    has_physical_address: bool
    osm_full_address: bool
    osm_opening_hours: bool
    osm_has_contact: bool
    site_builder: str | None
    has_booking: bool
    has_chat: bool
    copyright_year: int | None
    generic_name: bool


class FactorScore(BaseModel):
    factor: str
    points: float
    max_points: float
    reasons: list[str]


def _reachability(f: LeadFacts) -> FactorScore:
    pts, why = 0.0, []
    if f.best_email_status == "verified":
        pts += 12
        why.append("verified email (MX ok) +12")
    elif f.best_email_status == "unverified":
        pts += 6
        why.append("email found, MX unverified +6")
    if f.best_phone_status == "valid":
        pts += 8
        why.append("valid phone +8")
    if f.contact_page_found:
        pts += 3
        why.append("contact page found +3")
    if f.site_reachable:
        pts += 2
        why.append("website reachable +2")
    return FactorScore(
        factor="reachability",
        points=pts,
        max_points=25,
        reasons=why or ["no reachable contact found"],
    )


def _establishment(f: LeadFacts, ref: int) -> FactorScore:
    pts, why = 0.0, []
    if f.founded_year:
        age = ref - f.founded_year
        add = 8 if age >= 10 else 5 if age >= 5 else 2
        pts += add
        why.append(f"founded {f.founded_year} ({age} yrs) +{add}")
    if f.osm_full_address:
        pts += 3
        why.append("full address in OSM +3")
    if f.osm_opening_hours:
        pts += 2
        why.append("opening hours in OSM +2")
    if f.osm_has_contact:
        pts += 2
        why.append("phone/website in OSM +2")
    if f.site_reachable:
        pts += 5
        why.append("live website +5")
    return FactorScore(
        factor="establishment",
        points=pts,
        max_points=20,
        reasons=why or ["little evidence of establishment"],
    )


def _digital_gap(f: LeadFacts, ref: int) -> FactorScore:
    if not f.has_website:
        return FactorScore(
            factor="digital_gap",
            points=20,
            max_points=20,
            reasons=["no website at all — maximum digital upside +20"],
        )
    pts, why = 0.0, []
    if f.site_builder in DIY_BUILDERS:
        pts += 7
        why.append(f"DIY site builder ({f.site_builder}) +7")
    if not f.has_booking:
        pts += 5
        why.append("no online booking +5")
    if not f.has_chat:
        pts += 3
        why.append("no chat widget +3")
    if f.copyright_year and ref - f.copyright_year >= 2:
        pts += 5
        why.append(f"copyright year {f.copyright_year} is stale +5")
    return FactorScore(
        factor="digital_gap",
        points=min(pts, 20),
        max_points=20,
        reasons=why or ["modern digital presence — low AI upside"],
    )


def _buybox(f: LeadFacts) -> FactorScore:
    pts, why = 0.0, []
    if not f.is_chain_suspected:
        pts += 12
        why.append("independent (not a chain) +12")
    else:
        why.append("chain/franchise suspected +0")
    if f.has_physical_address:
        pts += 4
        why.append("physical address known +4")
    if not f.generic_name:
        pts += 4
        why.append("real business name +4")
    else:
        why.append("generic listing name (e.g. 'Dentist') +0")
    return FactorScore(factor="buybox", points=pts, max_points=20, reasons=why)


def _succession(f: LeadFacts, ref: int) -> FactorScore:
    pts, why = 0.0, []
    if f.founded_year:
        age = ref - f.founded_year
        if age >= 20:
            pts += 8
            why.append(f"{age} years old +8")
        elif age >= 15:
            pts += 5
            why.append(f"{age} years old +5")
    if f.owner_name_found:
        pts += 4
        why.append("owner named on site +4")
    if f.family_owned or f.owner_operated:
        pts += 3
        why.append("family-owned / owner-operated +3")
    return FactorScore(
        factor="succession", points=pts, max_points=15, reasons=why or ["no succession signals"]
    )


def score(facts: LeadFacts, reference_year: int) -> list[FactorScore]:
    return [
        _reachability(facts),
        _establishment(facts, reference_year),
        _digital_gap(facts, reference_year),
        _buybox(facts),
        _succession(facts, reference_year),
    ]


def total(factor_scores: list[FactorScore], weights: dict[str, float]) -> float:
    wsum = sum(weights.get(f, 0) for f in FACTORS) or 1.0
    t = sum(
        (fs.points / fs.max_points) * (weights.get(fs.factor, 0) / wsum) * 100
        for fs in factor_scores
    )
    return round(t, 1)


def tier(t: float) -> Literal["A", "B", "C", "D"]:
    return "A" if t >= 70 else "B" if t >= 55 else "C" if t >= 40 else "D"
