import asyncio
import re
from pathlib import Path
from typing import Literal

import dns.exception
import dns.resolver
import phonenumbers

EmailStatus = Literal["verified", "unverified", "invalid"]
PhoneStatus = Literal["valid", "possible", "invalid"]

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})$")
DISPOSABLE_DOMAINS: frozenset[str] = frozenset(
    ln.strip().lower()
    for ln in Path(__file__).with_name("disposable_domains.txt").read_text().splitlines()
    if ln.strip() and not ln.startswith("#")
)

_mx_cache: dict[str, EmailStatus] = {}


def clear_mx_cache() -> None:
    _mx_cache.clear()


def _mx(domain: str, resolver) -> EmailStatus:
    try:
        resolver.resolve(domain, "MX", lifetime=3.0)
        return "verified"
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return "invalid"
    except (dns.resolver.LifetimeTimeout, dns.exception.DNSException):
        return "unverified"


async def verify_email(addr: str, resolver=None) -> EmailStatus:
    m = EMAIL_RE.match(addr.strip())
    if not m:
        return "invalid"
    domain = m.group(1).lower()
    if domain in DISPOSABLE_DOMAINS:
        return "invalid"
    if domain not in _mx_cache:
        res = resolver or dns.resolver.Resolver()
        _mx_cache[domain] = await asyncio.to_thread(_mx, domain, res)
    return _mx_cache[domain]


def verify_phone(e164: str) -> PhoneStatus:
    try:
        num = phonenumbers.parse(e164, None)
    except phonenumbers.NumberParseException:
        return "invalid"
    if phonenumbers.is_valid_number(num):
        return "valid"
    return "possible" if phonenumbers.is_possible_number(num) else "invalid"
