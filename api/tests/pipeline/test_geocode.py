import httpx
import pytest
import respx

from app.db import session_scope
from app.pipeline.geocode import geocode

AUSTIN = [
    {
        "display_name": "Austin, Travis County, Texas, United States",
        "boundingbox": ["30.0985133", "30.5166255", "-97.9367663", "-97.5605288"],
        "lat": "30.2711286",
        "lon": "-97.7436995",
        "address": {"country_code": "us"},
    }
]
TEXAS = [
    {
        "display_name": "Texas, United States",
        "boundingbox": ["25.83", "36.50", "-106.64", "-93.50"],
        "lat": "31.0",
        "lon": "-100.0",
        "address": {"country_code": "us"},
    }
]


@respx.mock
async def test_geocode_city_returns_box_and_caches(db):
    route = respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(200, json=AUSTIN)
    )
    async with httpx.AsyncClient() as client:
        with session_scope() as s:
            box = await geocode("  Austin,  TX ", client, s)
        assert box and box.country_code == "US" and not box.shrunk
        assert (box.s, box.n) == pytest.approx((30.0985133, 30.5166255))
        with session_scope() as s:
            again = await geocode("austin, tx", client, s)  # different case/spacing → cache hit
    assert route.call_count == 1 and again.name == box.name


@respx.mock
async def test_geocode_shrinks_huge_areas(db):
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(200, json=TEXAS)
    )
    async with httpx.AsyncClient() as client:
        with session_scope() as s:
            box = await geocode("Texas", client, s)
    assert box.shrunk
    assert box.n - box.s == pytest.approx(0.5) and box.e - box.w == pytest.approx(0.5)
    assert (box.s + box.n) / 2 == pytest.approx(31.0)


@respx.mock
async def test_geocode_unknown_returns_none(db):
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(200, json=[])
    )
    async with httpx.AsyncClient() as client:
        with session_scope() as s:
            assert await geocode("Nowhereville Zzz", client, s) is None
