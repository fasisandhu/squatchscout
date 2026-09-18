import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sse_starlette.sse import EventSourceResponse

from app import deps
from app.db import get_session
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
async def create_search(
    body: SearchCreate,
    s: Session = Depends(get_session),  # noqa: B008
) -> dict:
    if body.industry_key not in INDUSTRIES:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "unknown_industry",
                "message": f"Unknown industry '{body.industry_key}'",
            },
        )
    preset = body.weight_preset if body.weight_preset in WEIGHT_PRESETS else "balanced"
    row = Search(
        id=new_id(),
        industry_key=body.industry_key,
        location_query=body.location.strip(),
        limit=body.limit,
        weight_preset=preset,
        nl_query=body.nl_query,
    )
    s.add(row)
    s.commit()
    deps.start_search_task(row.id)
    return {"id": row.id}


@router.get("/{search_id}", response_model=SearchOut)
def get_search(search_id: str, s: Session = Depends(get_session)) -> SearchOut:  # noqa: B008
    row = s.get(Search, search_id)
    if not row:
        raise not_found("Search")
    return SearchOut.from_row(row)


def leads_for(s: Session, search_id: str) -> list[LeadOut]:
    leads = s.exec(
        select(Lead).where(Lead.search_id == search_id).order_by(Lead.score.desc().nulls_last())
    ).all()
    ids = [x.id for x in leads]
    contacts = s.exec(select(Contact).where(Contact.lead_id.in_(ids))).all() if ids else []
    signals = s.exec(select(Signal).where(Signal.lead_id.in_(ids))).all() if ids else []
    factors = (
        s.exec(select(FactorScoreRow).where(FactorScoreRow.lead_id.in_(ids))).all() if ids else []
    )
    by = lambda rows: {i: [r for r in rows if r.lead_id == i] for i in ids}  # noqa: E731
    c, g, f = by(contacts), by(signals), by(factors)
    return [lead_to_out(x, c[x.id], g[x.id], f[x.id]) for x in leads]


@router.get("/{search_id}/leads", response_model=list[LeadOut])
def get_leads(search_id: str, s: Session = Depends(get_session)) -> list[LeadOut]:  # noqa: B008
    if not s.get(Search, search_id):
        raise not_found("Search")
    return leads_for(s, search_id)


@router.get("/{search_id}/stream")
async def stream(search_id: str, s: Session = Depends(get_session)):  # noqa: B008
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
