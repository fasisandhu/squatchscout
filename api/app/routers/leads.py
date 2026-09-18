from fastapi import APIRouter
from sqlmodel import select

from app.deps import SessionDep
from app.models import Contact, FactorScoreRow, Lead, Signal
from app.routers.searches import not_found
from app.schemas import LeadOut, lead_to_out

router = APIRouter(prefix="/api/leads")


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: str, s: SessionDep) -> LeadOut:
    lead = s.get(Lead, lead_id)
    if not lead:
        raise not_found("Lead")
    return lead_to_out(
        lead,
        s.exec(select(Contact).where(Contact.lead_id == lead_id)).all(),
        s.exec(select(Signal).where(Signal.lead_id == lead_id)).all(),
        s.exec(select(FactorScoreRow).where(FactorScoreRow.lead_id == lead_id)).all(),
    )
