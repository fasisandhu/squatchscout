import dns.resolver
import pytest

from app.pipeline import verify as v


class FakeResolver:
    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.calls = 0

    def resolve(self, domain, rtype, lifetime=3.0):
        self.calls += 1
        b = self.behaviour.get(domain)
        if b == "nx":
            raise dns.resolver.NXDOMAIN()
        if b == "timeout":
            raise dns.resolver.LifetimeTimeout()
        if b == "nomx":
            raise dns.resolver.NoAnswer()
        return ["mx.example."]


@pytest.fixture(autouse=True)
def _reset():
    v.clear_mx_cache()


async def test_email_statuses():
    r = FakeResolver(
        {"kcdental.com": "ok", "nx.com": "nx", "slow.com": "timeout", "nomx.com": "nomx"}
    )
    assert await v.verify_email("hello@kcdental.com", r) == "verified"
    assert await v.verify_email("a@nx.com", r) == "invalid"
    assert await v.verify_email("a@nomx.com", r) == "invalid"
    assert await v.verify_email("a@slow.com", r) == "unverified"
    assert await v.verify_email("not-an-email", r) == "invalid"
    assert await v.verify_email("x@mailinator.com", r) == "invalid"


async def test_mx_lookup_cached_per_domain():
    r = FakeResolver({"kcdental.com": "ok"})
    await v.verify_email("a@kcdental.com", r)
    await v.verify_email("b@kcdental.com", r)
    assert r.calls == 1


def test_phone():
    assert v.verify_phone("+15129180888") == "valid"
    assert v.verify_phone("+15550100000") in ("possible", "invalid")
    assert v.verify_phone("+1") == "invalid"
