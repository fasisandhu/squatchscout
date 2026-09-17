import re

import httpx
from pydantic import BaseModel
from sqlmodel import Session

from app.config import get_settings
from app.models import GeocodeCache

MAX_SPAN_DEG = 2.0  # larger than this → whole state/country; shrink around centroid (spec §5.1)
SHRUNK_SPAN_DEG = 0.5


class GeoBox(BaseModel):
    name: str
    country_code: str
    s: float
    w: float
    n: float
    e: float
    shrunk: bool = False


def normalize_query(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower()).replace(" ,", ",")


def _from_nominatim(item: dict) -> GeoBox:
    s, n, w, e = (float(x) for x in item["boundingbox"])
    box = GeoBox(
        name=item["display_name"],
        country_code=item.get("address", {}).get("country_code", "").upper(),
        s=s,
        w=w,
        n=n,
        e=e,
    )
    if (n - s) > MAX_SPAN_DEG or (e - w) > MAX_SPAN_DEG:
        lat, lon = float(item["lat"]), float(item["lon"])
        h = SHRUNK_SPAN_DEG / 2
        box = box.model_copy(
            update={"s": lat - h, "n": lat + h, "w": lon - h, "e": lon + h, "shrunk": True}
        )
    return box


async def geocode(query: str, client: httpx.AsyncClient, session: Session) -> GeoBox | None:
    settings = get_settings()
    key = normalize_query(query)
    cached = session.get(GeocodeCache, key)
    if cached:
        return GeoBox(**cached.result) if cached.result else None
    r = await client.get(
        f"{settings.nominatim_endpoint}/search",
        params={"q": query.strip(), "format": "json", "limit": 1, "addressdetails": 1},
        headers={"User-Agent": settings.user_agent},
        timeout=10,
    )
    r.raise_for_status()
    items = r.json()
    box = _from_nominatim(items[0]) if items else None
    session.add(GeocodeCache(query_norm=key, result=box.model_dump() if box else {}))
    session.flush()
    return box
