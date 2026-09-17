import json
from pathlib import Path

import httpx
import pytest
import respx

from app.db import session_scope
from app.pipeline.discover import OverpassUnavailable, fetch_places
from app.pipeline.geocode import GeoBox
from app.pipeline.industries import INDUSTRIES

FIX = json.loads(
    Path(__file__).parent.parent.joinpath("fixtures/overpass_dentists.json").read_text()
)
BOX = GeoBox(name="Austin", country_code="US", s=30.1, w=-97.9, n=30.5, e=-97.5)
PRIMARY = "https://overpass-api.de/api/interpreter"
MIRROR = "https://overpass.kumi.systems/api/interpreter"


@respx.mock
async def test_parses_nodes_and_way_centers_and_drops_unnamed(db):
    respx.post(PRIMARY).mock(return_value=httpx.Response(200, json=FIX))
    async with httpx.AsyncClient() as c:
        with session_scope() as s:
            places = await fetch_places(INDUSTRIES["dentist"], BOX, 60, c, s)
    assert [p.name for p in places] == ["KC Dental", "Castle Dental"]
    way = places[1]
    assert (way.osm_type, way.osm_id, way.lat, way.lon) == ("way", 202, 30.30, -97.75)


@respx.mock
async def test_falls_back_to_mirror_and_caches(db):
    primary = respx.post(PRIMARY).mock(return_value=httpx.Response(504))
    mirror = respx.post(MIRROR).mock(return_value=httpx.Response(200, json=FIX))
    async with httpx.AsyncClient() as c:
        with session_scope() as s:
            first = await fetch_places(INDUSTRIES["dentist"], BOX, 60, c, s)
        with session_scope() as s:
            second = await fetch_places(INDUSTRIES["dentist"], BOX, 60, c, s)
    assert len(first) == len(second) == 2
    assert primary.call_count == 2  # one try + one retry before falling to the mirror
    assert mirror.call_count == 1  # second call served from cache


@respx.mock
async def test_all_endpoints_failing_raises(db):
    respx.post(PRIMARY).mock(return_value=httpx.Response(429))
    respx.post(MIRROR).mock(side_effect=httpx.ConnectError("down"))
    async with httpx.AsyncClient() as c:
        with session_scope() as s:
            with pytest.raises(OverpassUnavailable):
                await fetch_places(INDUSTRIES["dentist"], BOX, 60, c, s)
