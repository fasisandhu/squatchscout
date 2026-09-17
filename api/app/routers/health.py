from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict:
    s = get_settings()
    return {"status": "ok", "db": "unknown", "llm_enabled": s.llm_enabled, "version": s.app_version}
