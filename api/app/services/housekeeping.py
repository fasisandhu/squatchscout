import asyncio
import logging
from datetime import datetime, timedelta

from sqlmodel import Session, col, delete, select

from app.config import get_settings
from app.db import session_scope
from app.models import (
    Contact,
    EnrichmentCache,
    FactorScoreRow,
    Lead,
    OverpassCache,
    Search,
    Signal,
    utcnow,
)

log = logging.getLogger(__name__)
DAY_S = 24 * 3600


def purge_old(session: Session, now: datetime, purge_after_days: int) -> dict[str, int]:
    cutoff = now - timedelta(days=purge_after_days)
    old_ids = [r for r in session.exec(select(Search.id).where(Search.created_at < cutoff)).all()]
    counts = {
        "searches": 0,
        "leads": 0,
        "contacts": 0,
        "signals": 0,
        "factor_scores": 0,
        "overpass_cache": 0,
        "enrichment_cache": 0,
    }
    if old_ids:
        lead_ids = list(session.exec(select(Lead.id).where(col(Lead.search_id).in_(old_ids))).all())
        if lead_ids:
            for table, key in (
                (Contact, "contacts"),
                (Signal, "signals"),
                (FactorScoreRow, "factor_scores"),
            ):
                counts[key] = session.execute(
                    delete(table).where(col(table.lead_id).in_(lead_ids))
                ).rowcount
            counts["leads"] = session.execute(
                delete(Lead).where(col(Lead.id).in_(lead_ids))
            ).rowcount
        counts["searches"] = session.execute(
            delete(Search).where(col(Search.id).in_(old_ids))
        ).rowcount
    counts["overpass_cache"] = session.execute(
        delete(OverpassCache).where(OverpassCache.expires_at < now)
    ).rowcount
    counts["enrichment_cache"] = session.execute(
        delete(EnrichmentCache).where(EnrichmentCache.expires_at < now)
    ).rowcount
    return counts


async def run_daily(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            with session_scope() as s:
                counts = purge_old(s, utcnow(), get_settings().purge_after_days)
            log.info("housekeeping.purged", extra={"counts": counts})
        except Exception:
            log.exception("housekeeping.failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=DAY_S)
        except TimeoutError:
            continue
