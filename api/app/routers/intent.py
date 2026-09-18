from fastapi import APIRouter, HTTPException

from app import deps
from app.llm.prompts import intent_messages
from app.llm.schemas import INTENT_SCHEMA, PRESETS, IntentResult
from app.pipeline.industries import INDUSTRIES, list_industries
from app.schemas import IntentRequest

router = APIRouter(prefix="/api")


def llm_unavailable(status: str) -> HTTPException:
    code = "llm_disabled" if status == "disabled" else "llm_unavailable"
    return HTTPException(
        status_code=503, detail={"code": code, "message": f"AI features unavailable ({status})"}
    )


@router.post("/intent", response_model=IntentResult)
async def intent(body: IntentRequest) -> IntentResult:
    pool = deps.get_pool()
    system, user = intent_messages(body.text, list_industries(), PRESETS)
    data, status = await pool.complete_json(
        schema_name="intent", schema=INTENT_SCHEMA, system=system, user=user, max_tokens=200
    )
    if status != "ok" or data is None:
        raise llm_unavailable(status)
    result = IntentResult(**data)
    if result.industry_key not in INDUSTRIES:
        result.industry_key = None
    if result.limit is not None:
        result.limit = max(5, min(100, result.limit))
    return result
