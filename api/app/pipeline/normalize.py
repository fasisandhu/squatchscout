import re
from urllib.parse import urlparse

import phonenumbers

from app.pipeline.industries import Industry

LEGAL_SUFFIXES = {
    "llc",
    "l.l.c.",
    "inc",
    "inc.",
    "pllc",
    "pc",
    "p.c.",
    "dds",
    "pa",
    "ltd",
    "co",
    "corp",
    "llp",
}
_LOCATION_TAIL = re.compile(r"\s+[-–|:]\s+.*$")  # " - Dentist in Austin"
_KEEP_UPPER = {
    "llc": "LLC",
    "pllc": "PLLC",
    "dds": "DDS",
    "pc": "PC",
    "inc": "Inc",
    "hvac": "HVAC",
    "cpa": "CPA",
}


def normalize_domain(url: str | None) -> str | None:
    if not url:
        return None
    u = url.strip()
    if "://" not in u:
        u = "http://" + u
    host = (urlparse(u).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host if "." in host and " " not in host else None


def normalize_phone(raw: str | None, region: str) -> str | None:
    if not raw:
        return None
    try:
        num = phonenumbers.parse(raw, region or "US")
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_possible_number(num):
        return None
    return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)


def normalize_name(name: str) -> str:
    # Drop periods first (not just leading/trailing) so dotted acronyms like "L.L.C."
    # collapse to one token ("llc") instead of splitting into "l", "l", "c" on the dots.
    s = re.sub(r"\.", "", name.lower())
    s = re.sub(r"[^\w\s]", " ", s)
    suffixes = {x.replace(".", "") for x in LEGAL_SUFFIXES}
    tokens = [t for t in s.split() if t not in suffixes]
    return " ".join(tokens)


def display_name(name: str) -> str:
    s = re.sub(r"\s+", " ", name.strip())
    s = _LOCATION_TAIL.sub("", s) if len(s.split()) > 3 else s
    if s.isupper():
        s = s.title()
    words = []
    for w in s.split(" "):
        key = w.strip(".,").lower()
        words.append(_KEEP_UPPER.get(key, w))
    return " ".join(words)


def is_generic_name(name: str, industry: Industry) -> bool:
    n = normalize_name(name)
    return n in {normalize_name(x) for x in industry.synonyms} or n == normalize_name(
        industry.label
    )
