import asyncio
import json
from pathlib import Path

import httpx
import respx
from sqlmodel import select

from app.config import Settings
from app.db import session_scope
from app.llm.client import LLMPool
from app.models import Contact, FactorScoreRow, Lead, Search, Signal, new_id
from app.pipeline import runner
from app.services.events import EventBus
from tests.llm.test_client import FakeGroq

FIX = Path(__file__).parent.parent / "fixtures"
OVERPASS = json.loads((FIX / "overpass_dentists.json").read_text())
# KC Dental here has no addr:street/addr:city, so the LLM gap-fill in test 2 has a gap to fill;
# the original fixture already has an OSM address, which would block the fill. Task 5's tests
# use the original fixture and are not touched.
OVERPASS_NO_ADDR = json.loads((FIX / "overpass_dentists_no_addr.json").read_text())
HOME = (FIX / "site_home.html").read_text(encoding="utf-8")
CONTACT = (FIX / "site_contact.html").read_text(encoding="utf-8")
AUSTIN = [
    {
        "display_name": "Austin, Texas, United States",
        "boundingbox": ["30.09", "30.51", "-97.93", "-97.56"],
        "lat": "30.27",
        "lon": "-97.74",
        "address": {"country_code": "us"},
    }
]


def mock_world():
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(200, json=AUSTIN)
    )
    respx.post("https://overpass-api.de/api/interpreter").mock(
        return_value=httpx.Response(200, json=OVERPASS)
    )
    respx.get("https://www.kcdentalaustin.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://www.kcdentalaustin.com/").mock(return_value=httpx.Response(200, html=HOME))
    respx.get("https://www.kcdentalaustin.com/contact").mock(
        return_value=httpx.Response(200, html=CONTACT)
    )
    respx.get("https://www.kcdentalaustin.com/about-us").mock(return_value=httpx.Response(404))


def new_search():
    with session_scope() as s:
        row = Search(id=new_id(), industry_key="dentist", location_query="Austin, TX", limit=60)
        s.add(row)
        return row.id


async def drain(q):
    events = []
    while (ev := await asyncio.wait_for(q.get(), 10)) is not None:
        events.append(ev)
    return events


@respx.mock
async def test_fast_path_streams_persists_and_scores(db, monkeypatch):
    mock_world()

    async def fake_verify(addr, resolver=None):
        return "verified" if addr.endswith("kcdental.com") else "invalid"

    monkeypatch.setattr(runner, "verify_email", fake_verify)

    sid = new_search()
    bus = EventBus()
    q = bus.subscribe(sid)
    pool = LLMPool(Settings(groq_api_key=None))  # AI disabled
    async with httpx.AsyncClient() as c:
        await runner.run_search(sid, bus=bus, pool=pool, client=c, reference_year=2026)
    events = await drain(q)
    types = [e["type"] for e in events]
    assert types[0] == "status" and types[-1] == "done" and types.count("lead") == 2
    done = events[-1]["data"]
    assert done == {"lead_count": 2, "llm_pending": 0}
    kc = next(e["data"] for e in events if e["type"] == "lead" and e["data"]["name"] == "KC Dental")
    assert kc["enrichment_status"] == "ok" and kc["llm_status"] == "disabled"
    assert kc["tier"] in ("A", "B") and kc["score"] >= 55
    assert any(
        c["kind"] == "email" and c["verification_status"] == "verified" for c in kc["contacts"]
    )
    assert any(
        s["key"] == "founded_year" and s["value"] == "1998" and s["source"] == "regex"
        for s in kc["signals"]
    )
    assert {f["factor"] for f in kc["factor_scores"]} == {
        "reachability",
        "establishment",
        "digital_gap",
        "buybox",
        "succession",
    }
    castle = next(
        e["data"] for e in events if e["type"] == "lead" and e["data"]["name"] == "Castle Dental"
    )
    assert castle["enrichment_status"] == "no_website" and castle["llm_status"] == "not_needed"
    assert next(f for f in castle["factor_scores"] if f["factor"] == "digital_gap")["points"] == 20
    with session_scope() as s:
        row = s.get(Search, sid)
        assert row.status == "done" and row.lead_count == 2 and row.finished_at is not None
        assert len(s.exec(select(Lead).where(Lead.search_id == sid)).all()) == 2
        assert (
            s.exec(select(FactorScoreRow)).all()
            and s.exec(select(Contact)).all()
            and s.exec(select(Signal)).all()
        )


@respx.mock
async def test_llm_queue_refines_lead_and_fills_address(db, monkeypatch):
    mock_world()
    # KC Dental's OSM address is missing in this fixture, so the address gap is open for the LLM
    # to fill (the original overpass_dentists.json fixture has addr:street/addr:city, which would
    # already satisfy lead.street and block the gap-fill).
    respx.post("https://overpass-api.de/api/interpreter").mock(
        return_value=httpx.Response(200, json=OVERPASS_NO_ADDR)
    )

    async def fake_verify(addr, resolver=None):
        return "verified"

    monkeypatch.setattr(runner, "verify_email", fake_verify)
    # Make regex leave a gap so the LLM gate opens: strip the owner sentence from the fixture.
    respx.get("https://www.kcdentalaustin.com/").mock(
        return_value=httpx.Response(
            200,
            html=HOME.replace("Dr. Karen Chen, owner, has served North Austin for 25 years.", ""),
        )
    )
    respx.get("https://www.kcdentalaustin.com/contact").mock(
        return_value=httpx.Response(200, html="<html><body><p>Call us.</p></body></html>")
    )
    llm_json = json.dumps(
        {
            "display_name": "KC Dental",
            "founded_year": 1998,
            "owner_operated": True,
            "owner_name": None,
            "family_owned": True,
            "is_chain": False,
            "hiring": False,
            "services": ["cleanings"],
            "address": {
                "street": "12400 West Parmer Lane",
                "city": "Austin",
                "state": "TX",
                "postcode": "78727",
            },
            "confidence": 0.9,
        }
    )
    fake = FakeGroq({"m1": [llm_json]})
    pool = LLMPool(Settings(groq_api_key="k", groq_models=["m1"]), groq_client=fake)
    sid = new_search()
    bus = EventBus()
    q = bus.subscribe(sid)
    async with httpx.AsyncClient() as c:
        await runner.run_search(sid, bus=bus, pool=pool, client=c, reference_year=2026)
    events = await drain(q)
    upd = [e["data"] for e in events if e["type"] == "lead_updated"]
    assert len(upd) == 1 and upd[0]["llm_status"] == "done"
    assert (
        upd[0]["address"]["street"] == "12400 West Parmer Lane"
        and upd[0]["address_source"] == "llm"
    )
    assert any(s["key"] == "services" and s["source"] == "llm" for s in upd[0]["signals"])
    assert events[-1]["data"]["llm_pending"] == 0
    with session_scope() as s:
        lead = s.exec(select(Lead).where(Lead.name == "KC Dental")).one()
        assert lead.street == "12400 West Parmer Lane" and lead.llm_status == "done"


@respx.mock
async def test_geocode_failure_marks_search_failed(db):
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(200, json=[])
    )
    sid = new_search()
    bus = EventBus()
    q = bus.subscribe(sid)
    async with httpx.AsyncClient() as c:
        await runner.run_search(sid, bus=bus, pool=LLMPool(Settings(groq_api_key=None)), client=c)
    events = await drain(q)
    assert events[-1]["type"] == "error"
    with session_scope() as s:
        assert s.get(Search, sid).status == "failed"
