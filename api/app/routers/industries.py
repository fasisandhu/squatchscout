from fastapi import APIRouter

from app.pipeline.industries import list_industries
from app.pipeline.score import WEIGHT_PRESETS

router = APIRouter(prefix="/api")


@router.get("/industries")
def industries() -> dict:
    return {"industries": list_industries(), "presets": WEIGHT_PRESETS}
