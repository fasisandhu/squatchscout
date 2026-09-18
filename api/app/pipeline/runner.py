import asyncio
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta

import httpx
from pydantic import BaseModel
from sqlmodel import Session, delete, select, update

from app.config import get_settings
from app.db import session_scope
from app.llm.client import LLMPool
from app.llm.schemas import ExtractionResult
from app.models import (
    Contact,
    EnrichmentCache,
    FactorScoreRow,
    Lead,
    Search,
    Signal,
    new_id,
    utcnow,
)
from app.pipeline.crawl import PageBundle, PageText, crawl_site, quality
from app.pipeline.dedupe import Candidate, dedupe_and_flag
from app.pipeline.discover import OverpassUnavailable, fetch_places
from app.pipeline.extract_llm import (
    SignalValue,
    build_llm_input,
    extract_with_llm,
    merge_signals,
    needs_llm,
)
from app.pipeline.extract_regex import RawContact, RegexSignals, extract_contacts, extract_signals
from app.pipeline.geocode import geocode
from app.pipeline.industries import INDUSTRIES, Industry
from app.pipeline.normalize import normalize_phone
from app.pipeline.score import WEIGHT_PRESETS, score, tier, total
from app.pipeline.verify import verify_email, verify_phone
from app.schemas import build_facts, lead_to_out
from app.services.events import EventBus

log = logging.getLogger(__name__)
FAST_DONE_GRACE_S = 90
LLM_PER_SEARCH_CAP = 40
CRAWL_CONCURRENCY = 8


class Enriched(BaseModel):
    status: str  # ok | no_website | blocked_by_robots | unreachable
    regex: RegexSignals | None = None
    contacts: list[RawContact] = []
    bundle: PageBundle | None = None
    llm: ExtractionResult | None = None


class LLMJob(BaseModel):
    lead_id: str
    osm_name: str
    bundle: PageBundle
    regex: RegexSignals


def _lead_from_candidate(search: Search, c: Candidate) -> Lead:
    t = c.place.tags
    street = t.get("addr:street")
    return Lead(
        id=new_id(),
        search_id=search.id,
        osm_type=c.place.osm_type,
        osm_id=c.place.osm_id,
        name=c.place.name,
        display_name=c.display,
        normalized_name=c.norm_name,
        lat=c.place.lat,
        lon=c.place.lon,
        street=street,
        housenumber=t.get("addr:housenumber"),
        city=t.get("addr:city"),
        state=t.get("addr:state"),
        postcode=t.get("addr:postcode"),
        country=t.get("addr:country") or search.country_code,
        address_source="osm" if street else "none",
        website=t.get("website") or t.get("contact:website"),
        normalized_domain=c.domain,
        osm_tags=t,
        is_chain_suspected=c.is_chain_suspected,
        enrichment_status="pending" if c.domain else "no_website",
    )


def _osm_contacts(c: Candidate) -> list[RawContact]:
    out = []
    if c.phone_e164:
        out.append(RawContact(kind="phone", value=c.phone_e164))
    email = c.place.tags.get("email") or c.place.tags.get("contact:email")
    if email:
        out.append(RawContact(kind="email", value=email.lower()))
    return out


def _synthetic_bundle(domain: str, text: str) -> PageBundle:
    return PageBundle(
        domain=domain,
        fetched_at=utcnow(),
        pages=[PageText(url=f"https://{domain}/", visible_text=text, text_quality=quality(text))],
    )


async def _enrich(c: Candidate, client: httpx.AsyncClient, year: int, region: str) -> Enriched:
    if not c.domain or not (c.place.tags.get("website") or c.place.tags.get("contact:website")):
        return Enriched(status="no_website")
    settings = get_settings()
    with session_scope() as s:
        cached = s.get(EnrichmentCache, c.domain)
        if cached and cached.expires_at > utcnow():
            if cached.robots_blocked:
                return Enriched(status="blocked_by_robots")
            llm = None
            if cached.llm_signals:
                try:
                    llm = ExtractionResult(**cached.llm_signals)
                except (TypeError, ValueError):
                    llm = None
            return Enriched(
                status="ok",
                regex=RegexSignals(**cached.regex_signals),
                contacts=[RawContact(**x) for x in cached.contacts],
                bundle=_synthetic_bundle(c.domain, cached.text_excerpt),
                llm=llm,
            )
    url = c.place.tags.get("website") or c.place.tags.get("contact:website")
    res = await crawl_site(url, client)
    ttl = timedelta(days=settings.enrich_cache_ttl_days)
    if res.status == "blocked_by_robots":
        with session_scope() as s:
            s.merge(
                EnrichmentCache(domain=c.domain, robots_blocked=True, expires_at=utcnow() + ttl)
            )
        return Enriched(status="blocked_by_robots")
    if res.status != "ok" or res.bundle is None:
        return Enriched(status="unreachable")
    regex = extract_signals(res.bundle, year)
    contacts = extract_contacts(res.bundle, region)
    with session_scope() as s:
        existing = s.get(EnrichmentCache, c.domain)
        s.merge(
            EnrichmentCache(
                domain=c.domain,
                text_excerpt=build_llm_input(res.bundle),
                regex_signals=regex.model_dump(),
                llm_signals=existing.llm_signals if existing else {},
                contacts=[x.model_dump() for x in contacts],
                robots_blocked=False,
                expires_at=utcnow() + ttl,
            )
        )
    return Enriched(status="ok", regex=regex, contacts=contacts, bundle=res.bundle)


async def _verified_contacts(
    lead_id: str, raw: list[tuple[RawContact, str]], region: str
) -> list[Contact]:
    seen: set[tuple[str, str]] = set()
    out: list[Contact] = []
    for rc, source in raw:
        norm = normalize_phone(rc.value, region) if rc.kind == "phone" else rc.value.lower()
        if not norm or (rc.kind, norm) in seen:
            continue
        seen.add((rc.kind, norm))
        status = "not_checked"
        if rc.kind == "email":
            status = await verify_email(norm)
        elif rc.kind == "phone":
            status = verify_phone(norm)
        out.append(
            Contact(
                lead_id=lead_id,
                kind=rc.kind,
                value=rc.value,
                normalized_value=norm,
                source=source,
                verification_status=status,
            )
        )
    return out


def _apply_signals_and_score(
    s: Session,
    lead: Lead,
    contacts: list[Contact],
    values: list[SignalValue],
    industry: Industry,
    weights: dict[str, float],
    year: int,
) -> None:
    s.execute(delete(Signal).where(Signal.lead_id == lead.id))
    s.execute(delete(FactorScoreRow).where(FactorScoreRow.lead_id == lead.id))
    rows = [
        Signal(lead_id=lead.id, key=v.key, value=v.value, source=v.source, confidence=v.confidence)
        for v in values
    ]
    sig = {v.key: v for v in values}
    if not lead.street and sig.get("street_address"):
        lead.street, lead.address_source = sig["street_address"].value, sig["street_address"].source
        if sig.get("postcode") and not lead.postcode:
            lead.postcode = sig["postcode"].value
        if sig.get("city") and not lead.city:
            lead.city = sig["city"].value
        if sig.get("state") and not lead.state:
            lead.state = sig["state"].value
    if sig.get("display_name") and sig["display_name"].source == "llm":
        lead.display_name = sig["display_name"].value
    facts = build_facts(lead, contacts, rows, industry)
    fs = score(facts, year)
    lead.score = total(fs, weights)
    lead.tier = tier(lead.score)
    lead.updated_at = utcnow()
    s.add(lead)
    for r in rows:
        s.add(r)
    for f in fs:
        s.add(
            FactorScoreRow(
                lead_id=lead.id,
                factor=f.factor,
                points=f.points,
                max_points=f.max_points,
                reasons=f.reasons,
            )
        )


def _load_out(s: Session, lead_id: str):
    lead = s.get(Lead, lead_id)
    contacts = s.exec(select(Contact).where(Contact.lead_id == lead_id)).all()
    signals = s.exec(select(Signal).where(Signal.lead_id == lead_id)).all()
    factors = s.exec(select(FactorScoreRow).where(FactorScoreRow.lead_id == lead_id)).all()
    return lead, contacts, signals, factors


async def _process_candidate(
    search: Search,
    c: Candidate,
    industry: Industry,
    weights: dict[str, float],
    year: int,
    client: httpx.AsyncClient,
    pool: LLMPool,
    bus: EventBus,
    sem: asyncio.Semaphore,
    domain_locks: dict[str, asyncio.Lock],
) -> LLMJob | None:
    lead = _lead_from_candidate(search, c)
    try:
        try:
            async with sem, domain_locks[c.domain or lead.id]:
                enriched = await _enrich(c, client, year, search.country_code or "US")
        except Exception:  # noqa: BLE001 — one bad site must not sink the search
            log.exception("enrich.failed", extra={"domain": c.domain})
            enriched = Enriched(status="unreachable")
        lead.enrichment_status = enriched.status
        raw = [(x, "osm") for x in _osm_contacts(c)] + [(x, "website") for x in enriched.contacts]
        contacts = await _verified_contacts(lead.id, raw, search.country_code or "US")
        regex = enriched.regex or RegexSignals()
        values = merge_signals(regex, None) if enriched.status == "ok" else []
        job = None
        if enriched.status == "ok" and enriched.bundle is not None:
            if enriched.llm is not None:
                # Already extracted (and validated) for this domain on a prior search — reuse it
                # and skip the LLM queue entirely (spec §7.3's per-domain budget guard).
                values = merge_signals(regex, enriched.llm)
                lead.llm_status = "done"
            elif not pool.enabled:
                lead.llm_status = "disabled"
            elif needs_llm(regex, bool(lead.street), enriched.bundle.pages[0].text_quality):
                lead.llm_status = "queued"
                job = LLMJob(
                    lead_id=lead.id, osm_name=lead.name, bundle=enriched.bundle, regex=regex
                )
        with session_scope() as s:
            s.add(lead)
            # Flush the parent row before adding its children: SQLAlchemy's unit of work has no
            # relationship() linking Lead/Contact, so without this it may emit the Contact INSERTs
            # before the Lead INSERT — harmless when a DB has FK enforcement off, a genuine
            # ForeignKeyViolation when it doesn't (SQLite now matches Postgres here; see db.py).
            s.flush()
            for ct in contacts:
                s.add(ct)
            s.flush()
            _apply_signals_and_score(s, lead, contacts, values, industry, weights, year)
            s.flush()
            out = lead_to_out(*_load_out(s, lead.id))
        bus.publish(search.id, "lead", out.model_dump())
        return job
    except Exception:  # noqa: BLE001 — one lead's failure must not sink the whole search
        log.exception("lead.failed", extra={"osm_id": c.place.osm_id})
        return None


async def _run_llm_job(
    search: Search,
    job: LLMJob,
    industry: Industry,
    weights: dict[str, float],
    year: int,
    pool: LLMPool,
    bus: EventBus,
) -> None:
    result, status = await extract_with_llm(
        pool, job.bundle, job.osm_name, search.country_code or "US", year
    )
    with session_scope() as s:
        lead, contacts, _, _ = _load_out(s, job.lead_id)
        lead.llm_status = "done" if status == "ok" else status
        values = merge_signals(job.regex, result)
        _apply_signals_and_score(s, lead, contacts, values, industry, weights, year)
        if result is not None and lead.normalized_domain:
            cache = s.get(EnrichmentCache, lead.normalized_domain)
            if cache:
                cache.llm_signals = result.model_dump()
                s.add(cache)
        row = s.get(Search, search.id)
        row.llm_pending = max(0, row.llm_pending - 1)
        s.add(row)
        s.flush()
        lead, contacts, signals, factors = _load_out(s, job.lead_id)
        out = lead_to_out(lead, contacts, signals, factors).model_dump()
    bus.publish(
        search.id,
        "lead_updated",
        {
            "lead_id": out["id"],
            "display_name": out["display_name"],
            "address": out["address"],
            "address_source": out["address_source"],
            "signals": out["signals"],
            "factor_scores": out["factor_scores"],
            "score": out["score"],
            "tier": out["tier"],
            "llm_status": out["llm_status"],
        },
    )


def _fail(search_id: str, bus: EventBus, message: str) -> None:
    with session_scope() as s:
        row = s.get(Search, search_id)
        row.status, row.error, row.finished_at = "failed", message, utcnow()
        s.add(row)
    bus.publish(search_id, "error", {"message": message})
    bus.close(search_id)


async def run_search(
    search_id: str,
    *,
    bus: EventBus,
    pool: LLMPool,
    client: httpx.AsyncClient | None = None,
    reference_year: int | None = None,
) -> None:
    year = reference_year or datetime.now(UTC).year
    own_client = client is None
    client = client or httpx.AsyncClient()
    drain_task: asyncio.Task | None = None
    try:
        with session_scope() as s:
            search = s.get(Search, search_id)
            industry = INDUSTRIES.get(search.industry_key)
        if industry is None:
            return _fail(search_id, bus, f"Unknown industry '{search.industry_key}'")
        weights = WEIGHT_PRESETS.get(search.weight_preset, WEIGHT_PRESETS["balanced"])
        bus.publish(
            search_id,
            "status",
            {"stage": "geocode", "message": f"Locating {search.location_query}…", "count": 0},
        )
        with session_scope() as s:
            box = await geocode(search.location_query, client, s)
            if box is None:
                return _fail(
                    search_id, bus, f"Could not find a place called '{search.location_query}'."
                )
            search = s.get(Search, search_id)
            search.geocoded_name, search.country_code = box.name, box.country_code
            search.bbox_s, search.bbox_w, search.bbox_n, search.bbox_e = box.s, box.w, box.n, box.e
            s.add(search)
        if box.shrunk:
            bus.publish(
                search_id,
                "status",
                {"stage": "geocode", "message": "Large area — searching the centre.", "count": 0},
            )
        bus.publish(
            search_id,
            "status",
            {
                "stage": "discover",
                "message": f"Finding {industry.label.lower()} in {box.name.split(',')[0]}…",
                "count": 0,
            },
        )
        try:
            with session_scope() as s:
                places = await fetch_places(industry, box, search.limit, client, s)
        except OverpassUnavailable:
            return _fail(
                search_id,
                bus,
                "OpenStreetMap's Overpass API is unavailable right now. Please retry in a minute.",
            )
        candidates = dedupe_and_flag(places, box.country_code or "US")[: search.limit]
        bus.publish(
            search_id,
            "status",
            {
                "stage": "enrich",
                "message": f"Checking {len(candidates)} businesses…",
                "count": len(candidates),
            },
        )
        sem = asyncio.Semaphore(CRAWL_CONCURRENCY)
        locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        with session_scope() as s:
            search = s.get(Search, search_id)
        raw_results = await asyncio.gather(
            *[
                _process_candidate(
                    search, c, industry, weights, year, client, pool, bus, sem, locks
                )
                for c in candidates
            ],
            return_exceptions=True,
        )
        jobs: list[LLMJob] = []
        for r in raw_results:
            if isinstance(r, LLMJob):
                jobs.append(r)
            elif isinstance(r, BaseException):
                log.error("candidate.failed", exc_info=r)
        queue = jobs[:LLM_PER_SEARCH_CAP]
        over_cap = jobs[LLM_PER_SEARCH_CAP:]
        with session_scope() as s:
            row = s.get(Search, search_id)
            row.lead_count, row.llm_pending = len(candidates), len(queue)
            s.add(row)
            if over_cap:
                s.execute(
                    update(Lead)
                    .where(Lead.id.in_([j.lead_id for j in over_cap]))
                    .values(llm_status="skipped_budget")
                )
        if queue:
            bus.publish(
                search_id,
                "status",
                {
                    "stage": "refine",
                    "message": f"Refining {len(queue)} leads with AI…",
                    "count": len(queue),
                },
            )

        async def drain() -> None:
            for job in queue:
                try:
                    await _run_llm_job(search, job, industry, weights, year, pool, bus)
                except Exception:  # noqa: BLE001
                    log.exception("llm_job.failed", extra={"lead_id": job.lead_id})
                    with session_scope() as s:
                        row = s.get(Search, search_id)
                        row.llm_pending = max(0, row.llm_pending - 1)
                        s.add(row)
                        lead = s.get(Lead, job.lead_id)
                        if lead:
                            lead.llm_status = "skipped_budget"
                            s.add(lead)

        drain_task = asyncio.create_task(drain())
        try:
            await asyncio.wait_for(asyncio.shield(drain_task), timeout=FAST_DONE_GRACE_S)
        except TimeoutError:
            pass
        with session_scope() as s:
            row = s.get(Search, search_id)
            row.status, row.finished_at = "done", utcnow()
            s.add(row)
            pending = row.llm_pending
        bus.publish(search_id, "done", {"lead_count": len(candidates), "llm_pending": pending})
        bus.close(search_id)
        if not drain_task.done():
            await drain_task  # keep refining after the stream closed; updates persist for polling
    except asyncio.CancelledError:
        if drain_task is not None:
            drain_task.cancel()
        raise
    except Exception as e:  # noqa: BLE001
        log.exception("search.failed", extra={"search_id": search_id})
        _fail(search_id, bus, f"Search failed: {type(e).__name__}")
    finally:
        if own_client:
            await client.aclose()
