from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.db import session_scope
from app.models import Lead, OverpassCache, Search, new_id, utcnow


def test_search_and_lead_roundtrip(db):
    with session_scope() as s:
        search = Search(id=new_id(), industry_key="dentist", location_query="Austin, TX", limit=60)
        s.add(search)
        s.flush()
        lead = Lead(
            id=new_id(),
            search_id=search.id,
            osm_type="node",
            osm_id=1,
            name="KC Dental",
            display_name="KC Dental",
            normalized_name="kc dental",
            lat=30.4,
            lon=-97.7,
            osm_tags={"amenity": "dentist"},
        )
        s.add(lead)
    with session_scope() as s:
        got = s.exec(select(Lead).where(Lead.search_id == search.id)).one()
        assert got.osm_tags == {"amenity": "dentist"}
        assert got.score is None and got.tier is None
        assert got.address_source == "none"


def test_utcnow_is_naive_utc():
    assert utcnow().tzinfo is None
    assert abs((utcnow() - datetime.now(UTC).replace(tzinfo=None)).total_seconds()) < 5


def test_datetime_columns_round_trip_naive(db):
    with session_scope() as s:
        s.add(OverpassCache(key="k", payload={}, expires_at=utcnow() + timedelta(hours=1)))
    with session_scope() as s:
        row = s.get(OverpassCache, "k")
        assert row.expires_at.tzinfo is None
        assert (row.expires_at > utcnow()) is True
