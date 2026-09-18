import asyncio
from typing import Annotated

import httpx
from fastapi import Depends
from sqlmodel import Session

from app.config import get_settings
from app.db import get_session
from app.llm.client import LLMPool
from app.pipeline.runner import run_search  # re-exported so tests can monkeypatch deps.run_search
from app.services.events import EventBus, bus

_pool: LLMPool | None = None
_http: httpx.AsyncClient | None = None
_tasks: set[asyncio.Task] = set()

# Named alias for the DB-session dependency: `s: SessionDep` in a route reads exactly like
# `s: Session = Depends(get_session)` but the `Depends(...)` call lives here, once, instead of
# in every route's argument defaults (which is what ruff's B008 warns about).
SessionDep = Annotated[Session, Depends(get_session)]


def get_pool() -> LLMPool:
    global _pool
    if _pool is None:
        _pool = LLMPool(get_settings())
    return _pool


def get_http() -> httpx.AsyncClient:
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(headers={"User-Agent": get_settings().user_agent})
    return _http


def get_bus() -> EventBus:
    return bus


def start_search_task(search_id: str) -> None:
    task = asyncio.create_task(
        run_search(search_id, bus=get_bus(), pool=get_pool(), client=get_http())
    )
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def shutdown() -> None:
    global _pool, _http
    tasks = list(_tasks)
    for t in tasks:
        t.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    _tasks.clear()
    if _http is not None:
        await _http.aclose()
    _pool, _http = None, None


def reset_for_tests() -> None:
    global _pool, _http
    _pool, _http = None, None
