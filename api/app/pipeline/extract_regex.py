import re
from typing import Literal

import phonenumbers
from pydantic import BaseModel

from app.pipeline.crawl import PageBundle
from app.pipeline.normalize import normalize_phone

YEAR = r"((?:18|19|20)\d{2})"
FOUNDED = re.compile(
    rf"(?:est\.?|established|since|founded|serving[^.]{{0,40}}?since)\s*(?:in\s+)?{YEAR}", re.I
)
FAMILY = re.compile(r"family[- ]owned|owner[- ]operated|locally owned", re.I)
OWNER_A = re.compile(r"\b(?:Dr\.?\s+)?([A-Z][a-z]+ [A-Z][a-z]+),?\s+(?:owner|founder)\b")
OWNER_B = re.compile(r"\bowner[,:]?\s+(?:Dr\.?\s+)?([A-Z][a-z]+ [A-Z][a-z]+)\b")
HIRING = re.compile(r"we'?re hiring|careers|join our team|now hiring", re.I)
BOOKING = re.compile(
    r"book (?:an|your) appointment|schedule online|zocdoc|calendly|acuity"
    r"|localmed|housecall pro|jobber",
    re.I,
)
CHAT = re.compile(r"intercom|drift\.com|tawk\.to|livechat|podium|birdeye", re.I)
COPYRIGHT = re.compile(rf"(?:©|copyright)\s*{YEAR}", re.I)
GENERATOR = re.compile(r'name="generator"\s+content="([^"]+)"', re.I)
BUILDERS = {
    "wordpress": "wordpress",
    "wix": "wix",
    "squarespace": "squarespace",
    "weebly": "weebly",
    "godaddy": "godaddy",
    "duda": "duda",
}
BUILDER_HINTS = {
    "wixstatic": "wix",
    "squarespace.com": "squarespace",
    "godaddysites": "godaddy",
    "wp-content": "wordpress",
}
STREET = re.compile(
    r"\b(\d{1,6}\s+[A-Za-z0-9.' ]{2,40}?\s+"
    r"(?:St|Street|Ave|Avenue|Blvd|Rd|Road|Dr|Drive|Ln|Lane|Way|Pkwy|Hwy|Ct|Pl))\b"
)
POSTCODE_US = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_JUNK = ("example.com", "sentry.io", "wixpress.com", ".png", ".jpg", ".svg", ".gif", ".webp")
SOCIAL = re.compile(
    r"https?://(?:www\.)?(?:facebook|instagram|yelp|x|twitter)\.com/[^\s\"'<>]+"
    r"|https?://(?:www\.)?linkedin\.com/company/[^\s\"'<>]+",
    re.I,
)


class RegexSignals(BaseModel):
    founded_year: int | None = None
    family_owned: bool = False
    owner_name: str | None = None
    owner_operated: bool | None = None
    hiring: bool = False
    site_builder: str | None = None
    has_booking: bool = False
    has_chat: bool = False
    copyright_year: int | None = None
    contact_page_found: bool = False
    street_address: str | None = None
    postcode: str | None = None


class RawContact(BaseModel):
    kind: Literal["email", "phone", "social"]
    value: str


def _all_text(bundle: PageBundle) -> str:
    return "\n".join(f"{p.title}\n{p.meta_description}\n{p.visible_text}" for p in bundle.pages)


def _all_head(bundle: PageBundle) -> str:
    return "\n".join(p.raw_head for p in bundle.pages)


def _builder(head: str, text: str) -> str | None:
    m = GENERATOR.search(head)
    if m:
        for k, v in BUILDERS.items():
            if k in m.group(1).lower():
                return v
    blob = (head + text).lower()
    return next((v for k, v in BUILDER_HINTS.items() if k in blob), None)


def extract_signals(bundle: PageBundle, current_year: int) -> RegexSignals:
    text, head = _all_text(bundle), _all_head(bundle)
    s = RegexSignals()
    years = [int(y) for y in FOUNDED.findall(text) if 1850 <= int(y) <= current_year]
    s.founded_year = min(years) if years else None
    s.family_owned = bool(FAMILY.search(text))
    m = OWNER_A.search(text) or OWNER_B.search(text)
    s.owner_name = m.group(1) if m else None
    s.owner_operated = True if (s.family_owned or s.owner_name) else None
    s.hiring = bool(HIRING.search(text))
    s.site_builder = _builder(head, text)
    s.has_booking = bool(BOOKING.search(text))
    s.has_chat = bool(CHAT.search(head + text))
    cys = [int(y) for y in COPYRIGHT.findall(text) if 1990 <= int(y) <= current_year]
    s.copyright_year = max(cys) if cys else None
    s.contact_page_found = any(
        p.url.rstrip("/").lower().endswith(("/contact", "/contact-us", "/about", "/about-us"))
        for p in bundle.pages
    )
    for line in text.splitlines():
        sm = STREET.search(line)
        if sm:
            s.street_address = sm.group(1).strip()
            pm = POSTCODE_US.search(line[sm.end() : sm.end() + 60])
            s.postcode = pm.group(1) if pm else None
            break
    return s


def extract_contacts(bundle: PageBundle, region: str) -> list[RawContact]:
    text = _all_text(bundle)
    raw_html_links = " ".join(" ".join(p.links) for p in bundle.pages)
    out: list[RawContact] = []
    seen: set[str] = set()
    for e in EMAIL.findall(text + " " + raw_html_links.replace("mailto:", " ")):
        low = e.lower()
        if any(j in low for j in EMAIL_JUNK) or low in seen:
            continue
        seen.add(low)
        out.append(RawContact(kind="email", value=low))
    for m in phonenumbers.PhoneNumberMatcher(text, region or "US"):
        e164 = normalize_phone(m.raw_string, region)
        if e164 and e164 not in seen:
            seen.add(e164)
            out.append(RawContact(kind="phone", value=e164))
    for u in SOCIAL.findall(text + " " + raw_html_links):
        if u not in seen:
            seen.add(u)
            out.append(RawContact(kind="social", value=u))
    return out
