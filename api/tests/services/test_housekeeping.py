from datetime import timedelta

from sqlmodel import select

from app.db import session_scope
from app.models import (
    Contact,
    EnrichmentCache,
    FactorScoreRow,
    Lead,
    OverpassCache,
    Search,
    Signal,
    new_id,
    utcnow,
)
from app.services.housekeeping import purge_old


def test_purge_removes_old_searches_children_and_expired_caches(db):
    now = utcnow()
    new_lead_id = None
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
            s.add(Signal(lead_id=lead.id, key="hiring", value="true", source="osm"))
            s.add(
                FactorScoreRow(
                    lead_id=lead.id,
                    factor="reachability",
                    points=1.0,
                    max_points=1.0,
                    reasons=[],
                )
            )
            if sr is new:
                new_lead_id = lead.id
        s.add(OverpassCache(key="k1", payload={}, expires_at=now - timedelta(hours=1)))
        s.add(OverpassCache(key="k2", payload={}, expires_at=now + timedelta(hours=1)))
        s.add(EnrichmentCache(domain="dead.com", expires_at=now - timedelta(days=1)))
    with session_scope() as s:
        counts = purge_old(s, now, purge_after_days=30)
    assert counts["searches"] == 1 and counts["leads"] == 1 and counts["contacts"] == 1
    assert counts["signals"] == 1 and counts["factor_scores"] == 1
    assert counts["overpass_cache"] == 1 and counts["enrichment_cache"] == 1
    with session_scope() as s:
        assert [x.location_query for x in s.exec(select(Search)).all()] == ["y"]
        assert [x.key for x in s.exec(select(OverpassCache)).all()] == ["k2"]
        # The surviving search's lead and every one of that lead's children must still be
        # present — a too-greedy delete (e.g. matching on the wrong id list) would still pass
        # the counts assertions above but silently erase the record we're supposed to keep.
        assert [x.id for x in s.exec(select(Lead).where(Lead.id == new_lead_id)).all()] == [
            new_lead_id
        ]
        assert len(s.exec(select(Contact).where(Contact.lead_id == new_lead_id)).all()) == 1
        assert len(s.exec(select(Signal).where(Signal.lead_id == new_lead_id)).all()) == 1
        assert (
            len(s.exec(select(FactorScoreRow).where(FactorScoreRow.lead_id == new_lead_id)).all())
            == 1
        )
