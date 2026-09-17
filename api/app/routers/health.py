from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.db import session_scope

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict:
    s = get_settings()
    try:
        with session_scope() as db:
            db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:  # noqa: BLE001 — health must never raise
        db_status = "error"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
        "llm_enabled": s.llm_enabled,
        "version": s.app_version,
    }
