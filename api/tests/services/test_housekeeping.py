from datetime import timedelta

from sqlmodel import select

from app.db import session_scope
from app.models import Contact, EnrichmentCache, Lead, OverpassCache, Search, new_id, utcnow
from app.services.housekeeping import purge_old


def test_purge_removes_old_searches_children_and_expired_caches(db):
    now = utcnow()
    with session_scope() as s:
        old = Search(
            id=new_id(),
            industry_key="dentist",
            location_query="x",
            limit=5,
            created_at=now - timedelta(days=40),
        )
        new = Search(
            id=new_id(),
            industry_key="dentist",
            location_query="y",
            limit=5,
            created_at=now - timedelta(days=2),
        )
        s.add(old)
        s.add(new)
        s.flush()
        for sr in (old, new):
            lead = Lead(
                id=new_id(),
                search_id=sr.id,
                osm_type="node",
                osm_id=1,
                name="a",
                display_name="a",
                normalized_name="a",
                lat=0,
                lon=0,
                osm_tags={},
            )
            s.add(lead)
            s.flush()
            s.add(
                Contact(
                    lead_id=lead.id,
                    kind="phone",
                    value="1",
                    normalized_value="1",
                    source="osm",
                )
            )
        s.add(OverpassCache(key="k1", payload={}, expires_at=now - timedelta(hours=1)))
        s.add(OverpassCache(key="k2", payload={}, expires_at=now + timedelta(hours=1)))
        s.add(EnrichmentCache(domain="dead.com", expires_at=now - timedelta(days=1)))
    with session_scope() as s:
        counts = purge_old(s, now, purge_after_days=30)
    assert counts["searches"] == 1 and counts["leads"] == 1 and counts["contacts"] == 1
    assert counts["overpass_cache"] == 1 and counts["enrichment_cache"] == 1
    with session_scope() as s:
        assert [x.location_query for x in s.exec(select(Search)).all()] == ["y"]
        assert [x.key for x in s.exec(select(OverpassCache)).all()] == ["k2"]
