from sqlmodel import select

from app.db import session_scope
from app.models import Lead, Search, new_id


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
