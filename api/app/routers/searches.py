import asyncio
import json
from collections import defaultdict

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from sse_starlette.sse import EventSourceResponse

from app import deps
from app.config import get_settings
from app.db import session_scope
from app.deps import SessionDep
from app.models import Contact, FactorScoreRow, Lead, Search, Signal, new_id
from app.pipeline.industries import INDUSTRIES
from app.pipeline.score import WEIGHT_PRESETS
from app.schemas import LeadOut, SearchCreate, SearchOut, lead_to_out

router = APIRouter(prefix="/api/searches")


def not_found(what: str) -> HTTPException:
    return HTTPException(
        status_code=404, detail={"code": "not_found", "message": f"{what} not found"}
    )


@router.post("", status_code=202)
async def create_search(body: SearchCreate, s: SessionDep) -> dict:
    if body.industry_key not in INDUSTRIES:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "unknown_industry",
                "message": f"Unknown industry '{body.industry_key}'",
            },
        )
    preset = body.weight_preset if body.weight_preset in WEIGHT_PRESETS else "balanced"
    limit = min(body.limit, get_settings().max_leads_per_search)
    row = Search(
        id=new_id(),
        industry_key=body.industry_key,
        location_query=body.location.strip(),
        limit=limit,
        weight_preset=preset,
        nl_query=body.nl_query,
    )
    s.add(row)
    s.commit()
    deps.start_search_task(row.id)
    return {"id": row.id}


@router.get("/{search_id}", response_model=SearchOut)
def get_search(search_id: str, s: SessionDep) -> SearchOut:
    row = s.get(Search, search_id)
    if not row:
        raise not_found("Search")
    return SearchOut.from_row(row)


def leads_for(s: Session, search_id: str) -> list[LeadOut]:
    leads = s.exec(
        select(Lead).where(Lead.search_id == search_id).order_by(Lead.score.desc().nulls_last())
    ).all()
    ids = [x.id for x in leads]
    contacts_by: dict[str, list[Contact]] = defaultdict(list)
    signals_by: dict[str, list[Signal]] = defaultdict(list)
    factors_by: dict[str, list[FactorScoreRow]] = defaultdict(list)
    if ids:
        for c in s.exec(select(Contact).where(Contact.lead_id.in_(ids))).all():
            contacts_by[c.lead_id].append(c)
        for sig in s.exec(select(Signal).where(Signal.lead_id.in_(ids))).all():
            signals_by[sig.lead_id].append(sig)
        for fac in s.exec(select(FactorScoreRow).where(FactorScoreRow.lead_id.in_(ids))).all():
            factors_by[fac.lead_id].append(fac)
    return [lead_to_out(x, contacts_by[x.id], signals_by[x.id], factors_by[x.id]) for x in leads]


@router.get("/{search_id}/leads", response_model=list[LeadOut])
def get_leads(search_id: str, s: SessionDep) -> list[LeadOut]:
    if not s.get(Search, search_id):
        raise not_found("Search")
    return leads_for(s, search_id)


@router.get("/{search_id}/stream")
async def stream(search_id: str):
    with session_scope() as s:
        if not s.get(Search, search_id):
            raise not_found("Search")
    q = deps.get_bus().subscribe(search_id)

    async def gen():
        while True:
            try:
                ev = await asyncio.wait_for(q.get(), timeout=15)
            except TimeoutError:
                yield {"comment": "keep-alive"}
                continue
            if ev is None:
                return
            yield {"event": ev["type"], "data": json.dumps(ev["data"])}

    return EventSourceResponse(gen(), ping=15)
