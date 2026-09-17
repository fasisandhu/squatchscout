import asyncio
import hashlib
from datetime import UTC, timedelta

import httpx
from pydantic import BaseModel
from sqlmodel import Session

from app.config import get_settings
from app.models import OverpassCache, utcnow
from app.pipeline.geocode import GeoBox
from app.pipeline.industries import Industry

RETRYABLE = {429, 502, 503, 504}


class OverpassUnavailable(Exception):
    """Every configured Overpass endpoint failed."""


class RawPlace(BaseModel):
    osm_type: str
    osm_id: int
    name: str
    lat: float
    lon: float
    tags: dict[str, str]


def build_overpass_query(
    industry: Industry, s: float, w: float, n: float, e: float, limit: int
) -> str:
    bbox = f"({s},{w},{n},{e})"
    parts = []
    for key, value in industry.selectors:
        parts.append(f'node["{key}"="{value}"]{bbox};')
        parts.append(f'way["{key}"="{value}"]{bbox};')
    body = "\n  ".join(parts)
    return f"[out:json][timeout:25];\n(\n  {body}\n);\nout center tags {limit};"


def cache_key(industry_key: str, box: GeoBox, limit: int) -> str:
    raw = f"{industry_key}|{box.s:.3f}|{box.w:.3f}|{box.n:.3f}|{box.e:.3f}|{limit}"
    return hashlib.sha256(raw.encode()).hexdigest()


def parse_elements(payload: dict) -> list[RawPlace]:
    out: list[RawPlace] = []
    for el in payload.get("elements", []):
        tags = el.get("tags") or {}
        name = tags.get("name")
        if not name:
            continue
        if el["type"] == "node":
            lat, lon = el["lat"], el["lon"]
        else:
            c = el.get("center") or {}
            if "lat" not in c:
                continue
            lat, lon = c["lat"], c["lon"]
        out.append(
            RawPlace(osm_type=el["type"], osm_id=el["id"], name=name, lat=lat, lon=lon, tags=tags)
        )
    return out


async def _post_with_retry(client: httpx.AsyncClient, url: str, query: str) -> dict | None:
    for attempt in range(2):
        try:
            r = await client.post(
                url,
                data={"data": query},
                headers={"User-Agent": get_settings().user_agent},
                timeout=40,
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code not in RETRYABLE:
                return None
        except (httpx.TransportError, ValueError):
            pass
        if attempt == 0:
            await asyncio.sleep(1.5)
    return None


async def fetch_places(
    industry: Industry, box: GeoBox, limit: int, client: httpx.AsyncClient, session: Session
) -> list[RawPlace]:
    settings = get_settings()
    key = cache_key(industry.key, box, limit)
    cached = session.get(OverpassCache, key)
    if cached:
        # SQLite's DateTime column drops tzinfo on read-back (the stored wall-clock
        # value is still UTC, per utcnow()), so re-attach UTC before comparing.
        expires_at = cached.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at > utcnow():
            return parse_elements(cached.payload)
    query = build_overpass_query(industry, box.s, box.w, box.n, box.e, limit)
    for url in settings.overpass_endpoints:
        payload = await _post_with_retry(client, url, query)
        if payload is not None:
            session.merge(
                OverpassCache(
                    key=key,
                    payload=payload,
                    expires_at=utcnow() + timedelta(hours=settings.overpass_cache_ttl_hours),
                )
            )
            session.flush()
            return parse_elements(payload)
    raise OverpassUnavailable("All Overpass endpoints failed")
