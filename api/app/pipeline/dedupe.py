from collections import Counter

from pydantic import BaseModel
from rapidfuzz import fuzz

from app.pipeline.discover import RawPlace
from app.pipeline.normalize import display_name, normalize_domain, normalize_name, normalize_phone

FUZZY_THRESHOLD = 90
CHAIN_REPEATS = 3


class Candidate(BaseModel):
    place: RawPlace
    domain: str | None
    phone_e164: str | None
    norm_name: str
    display: str
    is_chain_suspected: bool = False


def _phone_tag(tags: dict) -> str | None:
    return tags.get("phone") or tags.get("contact:phone")


def _site_tag(tags: dict) -> str | None:
    return tags.get("website") or tags.get("contact:website")


def _merge(keep: Candidate, other: Candidate) -> Candidate:
    """Keep the record with more tags; fill its gaps from the other."""
    a, b = (keep, other) if len(keep.place.tags) >= len(other.place.tags) else (other, keep)
    tags = {**b.place.tags, **a.place.tags}
    place = a.place.model_copy(update={"tags": tags})
    return Candidate(
        place=place,
        domain=a.domain or b.domain,
        phone_e164=a.phone_e164 or b.phone_e164,
        norm_name=a.norm_name,
        display=a.display,
    )


def dedupe_and_flag(places: list[RawPlace], region: str) -> list[Candidate]:
    cands = [
        Candidate(
            place=p,
            domain=normalize_domain(_site_tag(p.tags)),
            phone_e164=normalize_phone(_phone_tag(p.tags), region),
            norm_name=normalize_name(p.name),
            display=display_name(p.name),
        )
        for p in places
    ]
    # chain detection is computed on the *pre-dedupe* set so 3 identical branches count as a chain
    name_counts = Counter(c.norm_name for c in cands)
    kept: list[Candidate] = []
    for c in cands:
        dup_idx = None
        for i, k in enumerate(kept):
            same_city = k.place.tags.get("addr:city") == c.place.tags.get("addr:city")
            if (
                (c.domain and c.domain == k.domain)
                or (c.phone_e164 and c.phone_e164 == k.phone_e164)
                or (same_city and fuzz.token_set_ratio(c.norm_name, k.norm_name) >= FUZZY_THRESHOLD)
            ):
                dup_idx = i
                break
        if dup_idx is None:
            kept.append(c)
        else:
            kept[dup_idx] = _merge(kept[dup_idx], c)
    for c in kept:
        tags = c.place.tags
        c.is_chain_suspected = (
            name_counts[c.norm_name] >= CHAIN_REPEATS or "brand" in tags or "brand:wikidata" in tags
        )
    return kept
