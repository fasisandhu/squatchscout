# SquatchScout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build SquatchScout — a scored, verified, explainable lead-ranking tool for acquisition entrepreneurs — as a FastAPI API + React/Vite UI, deployed to an Ubuntu VM (API) and Vercel (UI), within a logged 5-hour core budget.

**Architecture:** An async pipeline (geocode → discover via OpenStreetMap → dedupe → crawl → regex/LLM extract → verify → score) streams leads over SSE while persisting to Postgres via SQLModel + Alembic. Scoring is a pure function over a flat `LeadFacts` model; the browser re-ranks client-side from per-factor points. Groq (free tier) provides gap-filling extraction, NL search intent and call openers behind a throttled, validated, env-gated client.

**Tech Stack:** Python 3.13 · FastAPI · SQLModel/SQLAlchemy 2 · Alembic · httpx · selectolax · rapidfuzz · phonenumbers · dnspython · groq · pytest/pytest-asyncio/respx · Node 24 · pnpm · Vite · React 19 · TypeScript · Tailwind CSS v4 · TanStack Table · vitest · Docker Compose · Caddy · GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-17-squatchscout-design.md` — every task cites the spec section it implements. Read the spec section before starting the task.

## Global Constraints

- Python **3.13** (the machine's default `python`); Node **24**; package manager **pnpm** for `web/`.
- Commit messages: Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `ci:`). **No `Co-Authored-By` or `Claude-Session` trailers — ever** (owner's decision; AI use is disclosed once in the README).
- Line endings LF everywhere (`.gitattributes` enforces it).
- The confidential handbook `.docx` must never enter the repo (`*.docx` is gitignored).
- **Time log:** every task in Phases A–C ends by appending a row to `docs/time-log.md` with the **actual wall-clock minutes** the task took (start a timer when you begin the task). The minute values printed in each task's "Append:" line are upper-bound estimates for a developer typing the code by hand — replace them with what you measured; with the code already specified they will usually be far lower. Core budget is **300 minutes**; if the *measured* running total passes 300 before Phase C ends, stop adding features and finish the deploy — polish moves to Phase D.
- All external I/O in the API is async `httpx`; **no network in unit tests** (`respx` mocks or fixtures).
- Structured fields (phone, email, URL) are **never** produced or reformatted by the LLM (spec §5.5).
- OpenStreetMap attribution "© OpenStreetMap contributors" appears in the UI footer and every export (spec §15).
- API env vars and defaults exactly as spec §11.

## Phases

- **Phase A — API core** (Tasks 1–18): pipeline, scoring, LLM client, routers, Docker.
- **Phase B — UI core** (Tasks 19–25).
- **Phase C — Ship** (Tasks 26–27): CI/CD, first deploy, verification.
- **Phase D — Extended** (Tasks 28–31): eval harness, notebook, README + docs, backup extra. Unbounded time.

## File Structure

```
squatchscout/
├─ docs/time-log.md                         running time log (Task 1)
├─ api/
│  ├─ pyproject.toml                        deps, ruff, pytest config
│  ├─ alembic.ini · alembic/env.py · alembic/versions/0001_initial.py
│  ├─ Dockerfile · .dockerignore
│  ├─ app/
│  │  ├─ main.py                            FastAPI app factory, middleware, router mounts, lifespan
│  │  ├─ config.py                          Settings (pydantic-settings), get_settings()
│  │  ├─ db.py                              engine, SessionLocal, get_session(), JSON type
│  │  ├─ models.py                          SQLModel tables (spec §8)
│  │  ├─ schemas.py                         API response models: LeadOut, SearchOut, events
│  │  ├─ logging_setup.py                   JSON log formatter
│  │  ├─ pipeline/
│  │  │  ├─ industries.py                   Industry, INDUSTRIES (16), list_industries()
│  │  │  ├─ geocode.py                      GeoBox, geocode()
│  │  │  ├─ discover.py                     RawPlace, build_overpass_query(), fetch_places()
│  │  │  ├─ normalize.py                    normalize_domain/phone/name, display_name(), is_generic_name()
│  │  │  ├─ dedupe.py                       Candidate, dedupe_and_flag()
│  │  │  ├─ crawl.py                        PageText, PageBundle, CrawlResult, crawl_site(), clean_html()
│  │  │  ├─ extract_regex.py                RegexSignals, RawContact, extract_signals(), extract_contacts()
│  │  │  ├─ extract_llm.py                  needs_llm(), build_llm_input(), extract_with_llm(), merge_signals()
│  │  │  ├─ verify.py                       verify_email(), verify_phone(), DISPOSABLE_DOMAINS
│  │  │  ├─ score.py                        LeadFacts, FactorScore, WEIGHT_PRESETS, score(), total(), tier()
│  │  │  └─ runner.py                       run_search(): orchestration, persistence, events, LLM queue
│  │  ├─ llm/
│  │  │  ├─ throttle.py                     TokenBucket
│  │  │  ├─ client.py                       LLMPool (Groq, model pool, 429 fallback, daily cap)
│  │  │  ├─ schemas.py                      IntentResult, ExtractionResult (+ validation)
│  │  │  └─ prompts.py                      system/user prompt builders
│  │  ├─ routers/
│  │  │  ├─ health.py · industries.py · intent.py · searches.py · leads.py · export.py
│  │  └─ services/
│  │     ├─ events.py                       EventBus (per-search asyncio queues)
│  │     ├─ export.py                       to_csv(), to_hubspot_csv()
│  │     └─ housekeeping.py                 purge_old(), run_daily()
│  └─ tests/                                mirrors app/; fixtures/ (overpass JSON, HTML, golden_scores.json)
├─ web/
│  ├─ package.json · vite.config.ts · tsconfig.json · index.html · vercel.json
│  └─ src/
│     ├─ main.tsx · App.tsx · config.ts · styles/index.css
│     ├─ api/types.ts · api/client.ts · api/sse.ts
│     ├─ lib/rank.ts (+ rank.test.ts)       shared scoring math with api/pipeline/score.py
│     ├─ state/searchReducer.ts (+ test) · state/useSearchSession.ts
│     └─ components/ SearchBar · StatusStrip · ResultsTable · ScoreChip · LeadDrawer · FactorBars ·
│                    ContactsList · SignalsList · OpenerPanel · WeightsPanel · SummaryTiles ·
│                    ExportMenu · EmptyState · ErrorToast · AttributionFooter
├─ deploy/ docker-compose.yml · Caddyfile · setup-ubuntu.sh · deploy.sh · .env.example · backup.sh (D)
├─ .github/workflows/ci.yml · deploy.yml
├─ evals/ golden/*.html · labels.json · extraction_eval.py · results.md        (Phase D)
├─ notebooks/demo.ipynb                                                        (Phase D)
├─ data/sample-search-austin-dentist.csv                                       (Phase D)
└─ docs/ architecture.md · runbook.md · video-script.md                        (Phase D)
```

---

## Phase A — API core

### Task 1: API scaffold, settings, `/healthz`, time log

**Spec:** §9 (`/healthz`), §11 (env vars), §18 (time log).

**Files:**
- Create: `api/pyproject.toml`, `api/app/__init__.py`, `api/app/config.py`, `api/app/main.py`, `api/app/routers/__init__.py`, `api/app/routers/health.py`, `api/tests/__init__.py`, `api/tests/conftest.py`, `api/tests/test_health.py`, `docs/time-log.md`

**Interfaces:**
- Produces: `get_settings() -> Settings` with attributes named exactly as spec §11 in snake_case (`database_url`, `groq_api_key`, `groq_models: list[str]`, `llm_daily_soft_cap`, `frontend_origins: list[str]`, `crawler_user_agent`, `crawler_contact`, `public_url`, `overpass_endpoints: list[str]`, `nominatim_endpoint`, `max_leads_per_search`, `purge_after_days`, `api_host`, `enrich_cache_ttl_days`, `overpass_cache_ttl_hours`, `log_level`) and property `llm_enabled: bool`. `create_app() -> FastAPI`. `APP_VERSION` read from env `APP_VERSION` (default `dev`).

- [ ] **Step 1: Create `api/pyproject.toml`**

```toml
[project]
name = "squatchscout-api"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
  "fastapi~=0.116",
  "uvicorn[standard]~=0.35",
  "sqlmodel~=0.0.24",
  "alembic~=1.16",
  "psycopg[binary]~=3.2",
  "pydantic-settings~=2.10",
  "httpx~=0.28",
  "selectolax~=0.3",
  "rapidfuzz~=3.13",
  "phonenumbers~=9.0",
  "dnspython~=2.7",
  "groq~=0.31",
  "sse-starlette~=2.4",
  "python-dotenv~=1.1",
]

[project.optional-dependencies]
dev = [
  "pytest~=8.4",
  "pytest-asyncio~=1.1",
  "respx~=0.22",
  "ruff~=0.12",
  "anyio~=4.9",
]

[build-system]
requires = ["setuptools>=75", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["app*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
filterwarnings = ["ignore::DeprecationWarning"]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "ASYNC"]
```

- [ ] **Step 2: Create a venv and install**

Run (from `api/`): `python -m venv .venv && .venv/Scripts/python -m pip install -U pip && .venv/Scripts/python -m pip install -e ".[dev]"`
Expected: installs without error. (All later `pytest`/`ruff` commands in this plan assume `api/.venv/Scripts/` is on PATH or are invoked as `.venv/Scripts/pytest`.)

- [ ] **Step 3: Write the failing test `api/tests/test_health.py`**

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_healthz_reports_status_and_llm_flag(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    client = TestClient(create_app())
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["llm_enabled"] is False
    assert "version" in body
```

And `api/tests/conftest.py`:

```python
import os

import pytest

# Tests never touch a real DB or network. Force SQLite + no LLM before app import.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.pop("GROQ_API_KEY", None)


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `pytest tests/test_health.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 5: Write `api/app/config.py`**

```python
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    groq_api_key: str | None = None
    groq_models: list[str] = Field(default=["openai/gpt-oss-20b", "qwen/qwen3.8-27b"])
    llm_daily_soft_cap: int = 600
    frontend_origins: list[str] = Field(default=["http://localhost:5173"])
    crawler_user_agent: str = "SquatchScoutBot/0.1 (+{public_url}/about)"
    crawler_contact: str | None = None
    public_url: str = "http://localhost:5173"
    overpass_endpoints: list[str] = Field(
        default=[
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
        ]
    )
    nominatim_endpoint: str = "https://nominatim.openstreetmap.org"
    max_leads_per_search: int = 60
    purge_after_days: int = 30
    api_host: str | None = None
    enrich_cache_ttl_days: int = 7
    overpass_cache_ttl_hours: int = 24
    log_level: str = "INFO"
    app_version: str = "dev"

    @field_validator("groq_models", "frontend_origins", "overpass_endpoints", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @property
    def llm_enabled(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def user_agent(self) -> str:
        ua = self.crawler_user_agent.format(public_url=self.public_url)
        return f"{ua} contact: {self.crawler_contact}" if self.crawler_contact else ua


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 6: Write `api/app/routers/health.py` and `api/app/main.py`**

`api/app/routers/health.py`:
```python
from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict:
    s = get_settings()
    return {"status": "ok", "db": "unknown", "llm_enabled": s.llm_enabled, "version": s.app_version}
```

`api/app/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="SquatchScout API", version=settings.app_version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    return app


app = create_app()
```

Create empty `api/app/__init__.py`, `api/app/routers/__init__.py`, `api/tests/__init__.py`.

- [ ] **Step 7: Run the test to verify it passes**

Run: `pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 8: Create `docs/time-log.md`**

```markdown
# Time log

Core budget: 300 minutes (Phases A–C). Phase D is outside the budget by design.

| Date | Task | Minutes | Running total | Notes |
|---|---|---|---|---|
| 2026-09-17 | 1 API scaffold, settings, /healthz | 20 | 20 | |
```

- [ ] **Step 9: Lint and commit**

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(api): scaffold FastAPI app with settings and /healthz"
```

### Task 2: Database layer, models, Alembic initial migration

**Spec:** §8 (data model), §12.2 (`alembic upgrade head` at start).

**Files:**
- Create: `api/app/db.py`, `api/app/models.py`, `api/alembic.ini`, `api/alembic/env.py`, `api/alembic/script.py.mako`, `api/alembic/versions/0001_initial.py`, `api/tests/test_models.py`
- Modify: `api/tests/conftest.py`

**Interfaces:**
- Produces: `engine`, `SessionLocal`, `get_session()` (FastAPI dependency), `session_scope()` (context manager). Table classes: `Search`, `Lead`, `Contact`, `Signal`, `FactorScoreRow`, `GeocodeCache`, `OverpassCache`, `EnrichmentCache`. All ids are `str` UUID4 via `new_id()`. Timestamps are timezone-aware UTC via `utcnow()`.

- [ ] **Step 1: Write the failing test `api/tests/test_models.py`**

```python
from sqlmodel import select

from app.db import session_scope
from app.models import Lead, Search, new_id


def test_search_and_lead_roundtrip(db):
    with session_scope() as s:
        search = Search(id=new_id(), industry_key="dentist", location_query="Austin, TX", limit=60)
        s.add(search)
        s.flush()
        lead = Lead(
            id=new_id(), search_id=search.id, osm_type="node", osm_id=1, name="KC Dental",
            display_name="KC Dental", normalized_name="kc dental", lat=30.4, lon=-97.7,
            osm_tags={"amenity": "dentist"},
        )
        s.add(lead)
    with session_scope() as s:
        got = s.exec(select(Lead).where(Lead.search_id == search.id)).one()
        assert got.osm_tags == {"amenity": "dentist"}
        assert got.score is None and got.tier is None
        assert got.address_source == "none"
```

Add to `api/tests/conftest.py`:

```python
@pytest.fixture
def db(tmp_path, monkeypatch):
    """Fresh SQLite DB per test, schema created via Alembic (so migrations are exercised)."""
    import subprocess
    import sys

    url = f"sqlite:///{(tmp_path / 't.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    from app.config import get_settings

    get_settings.cache_clear()
    import app.db as db_mod

    db_mod.reset_engine()
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd="./",
        check=True,
        env={**os.environ, "DATABASE_URL": url},
    )
    yield url
    db_mod.reset_engine()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 3: Write `api/app/db.py`**

```python
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Session, create_engine

from app.config import get_settings

# JSON on SQLite, JSONB on Postgres — one model definition, two backends (spec §8).
JSONType = JSON().with_variant(JSONB(), "postgresql")

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_settings().database_url
        kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
        _engine = create_engine(url, pool_pre_ping=True, **kwargs)
    return _engine


def reset_engine() -> None:
    """Test helper: drop the cached engine so a new DATABASE_URL takes effect."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


@contextmanager
def session_scope() -> Iterator[Session]:
    session = Session(get_engine())
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    with session_scope() as s:
        yield s
```

- [ ] **Step 4: Write `api/app/models.py`**

```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.db import JSONType


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(UTC)


class Search(SQLModel, table=True):
    __tablename__ = "searches"
    id: str = Field(primary_key=True)
    industry_key: str
    location_query: str
    geocoded_name: str | None = None
    country_code: str | None = None
    bbox_s: float | None = None
    bbox_w: float | None = None
    bbox_n: float | None = None
    bbox_e: float | None = None
    limit: int = 60
    nl_query: str | None = None
    weight_preset: str = "balanced"
    status: str = "running"  # running | done | failed
    lead_count: int = 0
    llm_pending: int = 0
    error: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None


class Lead(SQLModel, table=True):
    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("search_id", "osm_type", "osm_id", name="uq_lead_osm"),
        Index("ix_leads_search_id", "search_id"),
        Index("ix_leads_normalized_domain", "normalized_domain"),
    )
    id: str = Field(primary_key=True)
    search_id: str = Field(foreign_key="searches.id")
    osm_type: str
    osm_id: int
    name: str
    display_name: str
    normalized_name: str
    lat: float
    lon: float
    street: str | None = None
    housenumber: str | None = None
    city: str | None = None
    state: str | None = None
    postcode: str | None = None
    country: str | None = None
    address_source: str = "none"  # osm | regex | llm | none
    website: str | None = None
    normalized_domain: str | None = None
    osm_tags: dict = Field(default_factory=dict, sa_column=Column(JSONType))
    is_chain_suspected: bool = False
    enrichment_status: str = "pending"  # pending | ok | no_website | blocked_by_robots | unreachable
    llm_status: str = "not_needed"  # not_needed | queued | done | skipped_rate_limit | skipped_budget | disabled
    score: float | None = None
    tier: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Contact(SQLModel, table=True):
    __tablename__ = "contacts"
    __table_args__ = (Index("ix_contacts_lead_id", "lead_id"),)
    id: str = Field(default_factory=new_id, primary_key=True)
    lead_id: str = Field(foreign_key="leads.id")
    kind: str  # email | phone | social
    value: str
    normalized_value: str
    source: str  # osm | website | llm
    verification_status: str = "not_checked"  # verified | unverified | invalid | valid | possible | not_checked
    meta: dict = Field(default_factory=dict, sa_column=Column(JSONType))


class Signal(SQLModel, table=True):
    __tablename__ = "signals"
    __table_args__ = (Index("ix_signals_lead_key", "lead_id", "key"),)
    id: str = Field(default_factory=new_id, primary_key=True)
    lead_id: str = Field(foreign_key="leads.id")
    key: str
    value: str
    source: str  # osm | regex | llm
    confidence: float = 1.0
    created_at: datetime = Field(default_factory=utcnow)


class FactorScoreRow(SQLModel, table=True):
    __tablename__ = "factor_scores"
    __table_args__ = (
        UniqueConstraint("lead_id", "factor", name="uq_factor_per_lead"),
        Index("ix_factor_scores_lead_id", "lead_id"),
    )
    id: str = Field(default_factory=new_id, primary_key=True)
    lead_id: str = Field(foreign_key="leads.id")
    factor: str
    points: float
    max_points: float
    reasons: list = Field(default_factory=list, sa_column=Column(JSONType))


class GeocodeCache(SQLModel, table=True):
    __tablename__ = "geocode_cache"
    query_norm: str = Field(primary_key=True)
    result: dict = Field(default_factory=dict, sa_column=Column(JSONType))
    created_at: datetime = Field(default_factory=utcnow)


class OverpassCache(SQLModel, table=True):
    __tablename__ = "overpass_cache"
    __table_args__ = (Index("ix_overpass_cache_expires", "expires_at"),)
    key: str = Field(primary_key=True)
    payload: dict = Field(default_factory=dict, sa_column=Column(JSONType))
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime


class EnrichmentCache(SQLModel, table=True):
    __tablename__ = "enrichment_cache"
    __table_args__ = (Index("ix_enrichment_cache_expires", "expires_at"),)
    domain: str = Field(primary_key=True)
    text_excerpt: str = ""
    regex_signals: dict = Field(default_factory=dict, sa_column=Column(JSONType))
    llm_signals: dict = Field(default_factory=dict, sa_column=Column(JSONType))
    contacts: list = Field(default_factory=list, sa_column=Column(JSONType))
    robots_blocked: bool = False
    fetched_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
```

- [ ] **Step 5: Initialise Alembic and write the migration**

Run (from `api/`): `alembic init alembic` — then **replace** the generated `alembic/env.py` with:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import app.models  # noqa: F401  (registers tables on SQLModel.metadata)
from app.config import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata,
                      literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}),
                                     prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

In `alembic/script.py.mako` add `import sqlmodel` under the existing `import sqlalchemy as sa` line (autogenerate emits `sqlmodel.sql.sqltypes.AutoString`). In `alembic.ini` set `script_location = alembic` and delete the `sqlalchemy.url` line (env.py sets it).

Then: `alembic revision --autogenerate -m "initial"` and rename the generated file to `alembic/versions/0001_initial.py`. Open it and confirm all eight tables, the two unique constraints and the indexes are present; confirm JSON columns render as `sa.JSON().with_variant(postgresql.JSONB(), 'postgresql')` (fix by hand if autogenerate emitted plain `sa.JSON()` — import `from sqlalchemy.dialects import postgresql`).

- [ ] **Step 6: Run the test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (the fixture runs `alembic upgrade head` against a temp SQLite file).

- [ ] **Step 7: Wire `/healthz` to check the DB**

Modify `api/app/routers/health.py`:

```python
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
    return {"status": "ok" if db_status == "ok" else "degraded", "db": db_status,
            "llm_enabled": s.llm_enabled, "version": s.app_version}
```

Update `tests/test_health.py` to use the `db` fixture (`def test_healthz_reports_status_and_llm_flag(db, monkeypatch):`) and add `assert body["db"] == "ok"`. Run: `pytest -v` → all PASS.

- [ ] **Step 8: Lint, log time, commit**

Append to `docs/time-log.md`: `| 2026-09-17 | 2 DB layer, models, Alembic | 30 | 50 | |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(api): SQLModel schema and initial Alembic migration"
```

### Task 3: Industry map and Overpass query builder

**Spec:** §5.2 (curated industries, QL template).

**Files:**
- Create: `api/app/pipeline/__init__.py`, `api/app/pipeline/industries.py`, `api/app/pipeline/discover.py`, `api/tests/pipeline/__init__.py`, `api/tests/pipeline/test_industries.py`

**Interfaces:**
- Produces: `Industry(key, label, selectors: list[tuple[str, str]], synonyms: list[str])`; `INDUSTRIES: dict[str, Industry]`; `list_industries() -> list[dict]` (`{key, label}`); `build_overpass_query(industry: Industry, s, w, n, e, limit) -> str`. (`fetch_places` is added to `discover.py` in Task 5.)

- [ ] **Step 1: Write the failing tests**

```python
# api/tests/pipeline/test_industries.py
from app.pipeline.discover import build_overpass_query
from app.pipeline.industries import INDUSTRIES, list_industries


def test_sixteen_industries_with_unique_keys_and_selectors():
    assert len(INDUSTRIES) == 16
    assert all(ind.selectors for ind in INDUSTRIES.values())
    keys = [i["key"] for i in list_industries()]
    assert keys == sorted(keys) and len(set(keys)) == 16


def test_query_unions_nodes_and_ways_per_selector():
    q = build_overpass_query(INDUSTRIES["laundry"], 30.1, -97.9, 30.5, -97.5, 8)
    assert q.startswith("[out:json][timeout:25];")
    assert 'node["shop"="laundry"](30.1,-97.9,30.5,-97.5);' in q
    assert 'way["shop"="dry_cleaning"](30.1,-97.9,30.5,-97.5);' in q
    assert q.rstrip().endswith("out center tags 8;")
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/pipeline/test_industries.py -v` → FAIL `ModuleNotFoundError: app.pipeline`

- [ ] **Step 3: Write `api/app/pipeline/industries.py`**

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Industry:
    key: str
    label: str
    selectors: list[tuple[str, str]]  # OSM (key, value) pairs, OR'd
    synonyms: list[str] = field(default_factory=list)  # generic-name detection (spec §6)


_LIST = [
    Industry("accounting", "Accounting & bookkeeping", [("office", "accountant")],
             ["accountant", "accounting", "bookkeeping", "cpa", "tax service"]),
    Industry("auto_repair", "Auto repair", [("shop", "car_repair")],
             ["auto repair", "car repair", "automotive", "mechanic"]),
    Industry("car_wash", "Car washes", [("amenity", "car_wash")], ["car wash"]),
    Industry("childcare", "Childcare centers", [("amenity", "childcare"), ("amenity", "kindergarten")],
             ["childcare", "child care", "daycare", "day care", "preschool", "kindergarten"]),
    Industry("dentist", "Dentists", [("amenity", "dentist"), ("healthcare", "dentist")],
             ["dentist", "dental", "dental clinic", "dental office", "dentistry"]),
    Industry("electrician", "Electricians", [("craft", "electrician")], ["electrician", "electric"]),
    Industry("funeral", "Funeral homes", [("shop", "funeral_directors")],
             ["funeral home", "funeral", "mortuary"]),
    Industry("hvac", "HVAC contractors", [("craft", "hvac")],
             ["hvac", "heating and cooling", "air conditioning", "heating & air"]),
    Industry("insurance", "Insurance agencies", [("office", "insurance")], ["insurance", "insurance agency"]),
    Industry("landscaping", "Landscaping", [("craft", "gardener")], ["landscaping", "landscape", "lawn care"]),
    Industry("laundry", "Laundry & dry cleaning", [("shop", "laundry"), ("shop", "dry_cleaning")],
             ["laundry", "laundromat", "dry cleaning", "dry cleaners", "cleaners"]),
    Industry("optometry", "Optometrists & opticians", [("healthcare", "optometrist"), ("shop", "optician")],
             ["optometrist", "optometry", "optician", "eye care", "vision center"]),
    Industry("pharmacy", "Independent pharmacies", [("amenity", "pharmacy")], ["pharmacy", "drug store"]),
    Industry("plumber", "Plumbers", [("craft", "plumber")], ["plumber", "plumbing"]),
    Industry("roofer", "Roofers", [("craft", "roofer")], ["roofer", "roofing"]),
    Industry("veterinary", "Veterinary clinics", [("amenity", "veterinary")],
             ["veterinary", "veterinarian", "vet clinic", "animal hospital", "animal clinic"]),
]

INDUSTRIES: dict[str, Industry] = {i.key: i for i in _LIST}


def list_industries() -> list[dict]:
    return [{"key": i.key, "label": i.label} for i in sorted(INDUSTRIES.values(), key=lambda x: x.key)]
```

- [ ] **Step 4: Write the query builder in `api/app/pipeline/discover.py`**

```python
from app.pipeline.industries import Industry


def build_overpass_query(industry: Industry, s: float, w: float, n: float, e: float, limit: int) -> str:
    bbox = f"({s},{w},{n},{e})"
    parts = []
    for key, value in industry.selectors:
        parts.append(f'node["{key}"="{value}"]{bbox};')
        parts.append(f'way["{key}"="{value}"]{bbox};')
    body = "\n  ".join(parts)
    return f"[out:json][timeout:25];\n(\n  {body}\n);\nout center tags {limit};"
```

Create empty `api/app/pipeline/__init__.py` and `api/tests/pipeline/__init__.py`.

- [ ] **Step 5: Run to verify pass** — `pytest tests/pipeline/test_industries.py -v` → PASS

- [ ] **Step 6: Lint, log time, commit**

Append: `| 2026-09-17 | 3 industry map + Overpass QL | 15 | 65 | |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(pipeline): curated industry map and Overpass query builder"
```

### Task 4: Geocoding with bbox shrink and cache

**Spec:** §5.1.

**Files:**
- Create: `api/app/pipeline/geocode.py`, `api/tests/pipeline/test_geocode.py`

**Interfaces:**
- Produces: `GeoBox(BaseModel): name: str, country_code: str, s, w, n, e: float, shrunk: bool`; `async def geocode(query: str, client: httpx.AsyncClient, session: Session) -> GeoBox | None`; `normalize_query(q) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
# api/tests/pipeline/test_geocode.py
import httpx
import pytest
import respx

from app.db import session_scope
from app.pipeline.geocode import geocode

AUSTIN = [{"display_name": "Austin, Travis County, Texas, United States",
           "boundingbox": ["30.0985133", "30.5166255", "-97.9367663", "-97.5605288"],
           "lat": "30.2711286", "lon": "-97.7436995",
           "address": {"country_code": "us"}}]
TEXAS = [{"display_name": "Texas, United States",
          "boundingbox": ["25.83", "36.50", "-106.64", "-93.50"],
          "lat": "31.0", "lon": "-100.0", "address": {"country_code": "us"}}]


@respx.mock
async def test_geocode_city_returns_box_and_caches(db):
    route = respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(200, json=AUSTIN))
    async with httpx.AsyncClient() as client:
        with session_scope() as s:
            box = await geocode("  Austin,  TX ", client, s)
        assert box and box.country_code == "US" and not box.shrunk
        assert (box.s, box.n) == pytest.approx((30.0985133, 30.5166255))
        with session_scope() as s:
            again = await geocode("austin, tx", client, s)  # different case/spacing → cache hit
    assert route.call_count == 1 and again.name == box.name


@respx.mock
async def test_geocode_shrinks_huge_areas(db):
    respx.get("https://nominatim.openstreetmap.org/search").mock(return_value=httpx.Response(200, json=TEXAS))
    async with httpx.AsyncClient() as client, session_scope() as s:
        box = await geocode("Texas", client, s)
    assert box.shrunk
    assert box.n - box.s == pytest.approx(0.5) and box.e - box.w == pytest.approx(0.5)
    assert (box.s + box.n) / 2 == pytest.approx(31.0)


@respx.mock
async def test_geocode_unknown_returns_none(db):
    respx.get("https://nominatim.openstreetmap.org/search").mock(return_value=httpx.Response(200, json=[]))
    async with httpx.AsyncClient() as client, session_scope() as s:
        assert await geocode("Nowhereville Zzz", client, s) is None
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/pipeline/test_geocode.py -v` → FAIL (module missing)

- [ ] **Step 3: Write `api/app/pipeline/geocode.py`**

```python
import re

import httpx
from pydantic import BaseModel
from sqlmodel import Session

from app.config import get_settings
from app.models import GeocodeCache

MAX_SPAN_DEG = 2.0  # larger than this → whole state/country; shrink around centroid (spec §5.1)
SHRUNK_SPAN_DEG = 0.5


class GeoBox(BaseModel):
    name: str
    country_code: str
    s: float
    w: float
    n: float
    e: float
    shrunk: bool = False


def normalize_query(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower()).replace(" ,", ",")


def _from_nominatim(item: dict) -> GeoBox:
    s, n, w, e = (float(x) for x in item["boundingbox"])
    box = GeoBox(name=item["display_name"], country_code=item.get("address", {}).get("country_code", "").upper(),
                 s=s, w=w, n=n, e=e)
    if (n - s) > MAX_SPAN_DEG or (e - w) > MAX_SPAN_DEG:
        lat, lon = float(item["lat"]), float(item["lon"])
        h = SHRUNK_SPAN_DEG / 2
        box = box.model_copy(update={"s": lat - h, "n": lat + h, "w": lon - h, "e": lon + h, "shrunk": True})
    return box


async def geocode(query: str, client: httpx.AsyncClient, session: Session) -> GeoBox | None:
    settings = get_settings()
    key = normalize_query(query)
    cached = session.get(GeocodeCache, key)
    if cached:
        return GeoBox(**cached.result) if cached.result else None
    r = await client.get(
        f"{settings.nominatim_endpoint}/search",
        params={"q": query.strip(), "format": "json", "limit": 1, "addressdetails": 1},
        headers={"User-Agent": settings.user_agent},
        timeout=10,
    )
    r.raise_for_status()
    items = r.json()
    box = _from_nominatim(items[0]) if items else None
    session.add(GeocodeCache(query_norm=key, result=box.model_dump() if box else {}))
    session.flush()
    return box
```

- [ ] **Step 4: Run to verify pass** — `pytest tests/pipeline/test_geocode.py -v` → 3 PASS

- [ ] **Step 5: Lint, log time, commit**

Append: `| 2026-09-17 | 4 geocode + cache | 15 | 80 | |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(pipeline): Nominatim geocoding with bbox shrink and cache"
```

### Task 5: Overpass fetch — mirrors, retry, cache, `RawPlace`

**Spec:** §5.2 (endpoints, retry, 24 h cache, drop unnamed).

**Files:**
- Modify: `api/app/pipeline/discover.py`
- Create: `api/tests/pipeline/test_discover.py`, `api/tests/fixtures/overpass_dentists.json`

**Interfaces:**
- Produces: `RawPlace(BaseModel): osm_type: str, osm_id: int, name: str, lat: float, lon: float, tags: dict[str, str]`; `async def fetch_places(industry, box: GeoBox, limit, client, session) -> list[RawPlace]`; `class OverpassUnavailable(Exception)`; `cache_key(industry_key, box, limit) -> str`.

- [ ] **Step 1: Create the fixture `api/tests/fixtures/overpass_dentists.json`**

```json
{"version": 0.6, "elements": [
  {"type": "node", "id": 101, "lat": 30.40, "lon": -97.70,
   "tags": {"amenity": "dentist", "name": "KC Dental", "website": "https://www.kcdentalaustin.com/",
            "phone": "+1-512-918-0888", "addr:street": "West Parmer Lane", "addr:city": "Austin"}},
  {"type": "way", "id": 202, "center": {"lat": 30.30, "lon": -97.75},
   "tags": {"amenity": "dentist", "name": "Castle Dental"}},
  {"type": "node", "id": 303, "lat": 30.31, "lon": -97.76, "tags": {"amenity": "dentist"}}
]}
```

- [ ] **Step 2: Write the failing tests `api/tests/pipeline/test_discover.py`**

```python
import json
from pathlib import Path

import httpx
import pytest
import respx

from app.db import session_scope
from app.pipeline.discover import OverpassUnavailable, fetch_places
from app.pipeline.geocode import GeoBox
from app.pipeline.industries import INDUSTRIES

FIX = json.loads(Path(__file__).parent.parent.joinpath("fixtures/overpass_dentists.json").read_text())
BOX = GeoBox(name="Austin", country_code="US", s=30.1, w=-97.9, n=30.5, e=-97.5)
PRIMARY = "https://overpass-api.de/api/interpreter"
MIRROR = "https://overpass.kumi.systems/api/interpreter"


@respx.mock
async def test_parses_nodes_and_way_centers_and_drops_unnamed(db):
    respx.post(PRIMARY).mock(return_value=httpx.Response(200, json=FIX))
    async with httpx.AsyncClient() as c, session_scope() as s:
        places = await fetch_places(INDUSTRIES["dentist"], BOX, 60, c, s)
    assert [p.name for p in places] == ["KC Dental", "Castle Dental"]
    way = places[1]
    assert (way.osm_type, way.osm_id, way.lat, way.lon) == ("way", 202, 30.30, -97.75)


@respx.mock
async def test_falls_back_to_mirror_and_caches(db):
    primary = respx.post(PRIMARY).mock(return_value=httpx.Response(504))
    mirror = respx.post(MIRROR).mock(return_value=httpx.Response(200, json=FIX))
    async with httpx.AsyncClient() as c:
        with session_scope() as s:
            first = await fetch_places(INDUSTRIES["dentist"], BOX, 60, c, s)
        with session_scope() as s:
            second = await fetch_places(INDUSTRIES["dentist"], BOX, 60, c, s)
    assert len(first) == len(second) == 2
    assert primary.call_count == 2  # one try + one retry before falling to the mirror
    assert mirror.call_count == 1   # second call served from cache


@respx.mock
async def test_all_endpoints_failing_raises(db):
    respx.post(PRIMARY).mock(return_value=httpx.Response(429))
    respx.post(MIRROR).mock(side_effect=httpx.ConnectError("down"))
    async with httpx.AsyncClient() as c, session_scope() as s:
        with pytest.raises(OverpassUnavailable):
            await fetch_places(INDUSTRIES["dentist"], BOX, 60, c, s)
```

- [ ] **Step 3: Run to verify failure** — `pytest tests/pipeline/test_discover.py -v` → FAIL (`fetch_places` not defined)

- [ ] **Step 4: Extend `api/app/pipeline/discover.py`**

```python
import asyncio
import hashlib
from datetime import timedelta

import httpx
from pydantic import BaseModel
from sqlmodel import Session

from app.config import get_settings
from app.models import OverpassCache, utcnow
from app.pipeline.geocode import GeoBox
from app.pipeline.industries import Industry

RETRYABLE = {429, 502, 503, 504}


class OverpassUnavailable(Exception):
    """Every configured Overpass endpoint failed."""


class RawPlace(BaseModel):
    osm_type: str
    osm_id: int
    name: str
    lat: float
    lon: float
    tags: dict[str, str]


def build_overpass_query(industry: Industry, s: float, w: float, n: float, e: float, limit: int) -> str:
    bbox = f"({s},{w},{n},{e})"
    parts = []
    for key, value in industry.selectors:
        parts.append(f'node["{key}"="{value}"]{bbox};')
        parts.append(f'way["{key}"="{value}"]{bbox};')
    body = "\n  ".join(parts)
    return f"[out:json][timeout:25];\n(\n  {body}\n);\nout center tags {limit};"


def cache_key(industry_key: str, box: GeoBox, limit: int) -> str:
    raw = f"{industry_key}|{box.s:.3f}|{box.w:.3f}|{box.n:.3f}|{box.e:.3f}|{limit}"
    return hashlib.sha256(raw.encode()).hexdigest()


def parse_elements(payload: dict) -> list[RawPlace]:
    out: list[RawPlace] = []
    for el in payload.get("elements", []):
        tags = el.get("tags") or {}
        name = tags.get("name")
        if not name:
            continue
        if el["type"] == "node":
            lat, lon = el["lat"], el["lon"]
        else:
            c = el.get("center") or {}
            if "lat" not in c:
                continue
            lat, lon = c["lat"], c["lon"]
        out.append(RawPlace(osm_type=el["type"], osm_id=el["id"], name=name, lat=lat, lon=lon, tags=tags))
    return out


async def _post_with_retry(client: httpx.AsyncClient, url: str, query: str) -> dict | None:
    for attempt in range(2):
        try:
            r = await client.post(url, data={"data": query},
                                  headers={"User-Agent": get_settings().user_agent}, timeout=40)
            if r.status_code == 200:
                return r.json()
            if r.status_code not in RETRYABLE:
                return None
        except (httpx.TransportError, ValueError):
            pass
        if attempt == 0:
            await asyncio.sleep(1.5)
    return None


async def fetch_places(industry: Industry, box: GeoBox, limit: int,
                       client: httpx.AsyncClient, session: Session) -> list[RawPlace]:
    settings = get_settings()
    key = cache_key(industry.key, box, limit)
    cached = session.get(OverpassCache, key)
    if cached and cached.expires_at > utcnow():
        return parse_elements(cached.payload)
    query = build_overpass_query(industry, box.s, box.w, box.n, box.e, limit)
    for url in settings.overpass_endpoints:
        payload = await _post_with_retry(client, url, query)
        if payload is not None:
            session.merge(OverpassCache(key=key, payload=payload,
                                        expires_at=utcnow() + timedelta(hours=settings.overpass_cache_ttl_hours)))
            session.flush()
            return parse_elements(payload)
    raise OverpassUnavailable("All Overpass endpoints failed")
```

Note for the implementer: `asyncio.sleep(1.5)` makes the mirror test take ~1.5 s; acceptable. Do not mock `sleep` — the test asserts call counts, not timing.

- [ ] **Step 5: Run to verify pass** — `pytest tests/pipeline/ -v` → all PASS

- [ ] **Step 6: Lint, log time, commit**

Append: `| 2026-09-17 | 5 Overpass fetch, mirrors, cache | 20 | 100 | |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(pipeline): Overpass discovery with mirror fallback and 24h cache"
```

### Task 6: Normalization, dedupe, chain detection, generic-name check

**Spec:** §5.3, §5.5 (`display_name`), §6 (generic name).

**Files:**
- Create: `api/app/pipeline/normalize.py`, `api/app/pipeline/dedupe.py`, `api/tests/pipeline/test_normalize.py`, `api/tests/pipeline/test_dedupe.py`

**Interfaces:**
- Produces (`normalize.py`): `normalize_domain(url: str | None) -> str | None`; `normalize_phone(raw: str | None, region: str) -> str | None` (E.164); `normalize_name(name) -> str`; `display_name(name) -> str`; `is_generic_name(name, industry: Industry) -> bool`; `LEGAL_SUFFIXES`.
- Produces (`dedupe.py`): `Candidate(BaseModel): place: RawPlace, domain: str | None, phone_e164: str | None, norm_name: str, display: str, is_chain_suspected: bool`; `dedupe_and_flag(places: list[RawPlace], region: str) -> list[Candidate]`.

- [ ] **Step 1: Write the failing tests**

```python
# api/tests/pipeline/test_normalize.py
from app.pipeline.industries import INDUSTRIES
from app.pipeline.normalize import (display_name, is_generic_name, normalize_domain, normalize_name,
                                    normalize_phone)


def test_domain():
    assert normalize_domain("https://www.KCDentalAustin.com/contact?x=1") == "kcdentalaustin.com"
    assert normalize_domain("kcdental.com") == "kcdental.com"
    assert normalize_domain(None) is None and normalize_domain("not a url") is None


def test_phone():
    assert normalize_phone("(512) 918-0888", "US") == "+15129180888"
    assert normalize_phone("+1-512-918-0888", "US") == "+15129180888"
    assert normalize_phone("12", "US") is None


def test_name_normalization_strips_suffixes_and_punct():
    assert normalize_name("Hammons Family Dental, PLLC") == "hammons family dental"
    assert normalize_name("KC DENTAL L.L.C.") == "kc dental"


def test_display_name():
    assert display_name("HAMMONS FAMILY DENTAL LLC") == "Hammons Family Dental LLC"
    assert display_name("Smiles by Design - Dentist in Austin") == "Smiles by Design"
    assert display_name("Dr. J. Smith DDS") == "Dr. J. Smith DDS"


def test_generic_name():
    d = INDUSTRIES["dentist"]
    assert is_generic_name("Dentist", d) and is_generic_name("Dental Clinic", d)
    assert not is_generic_name("KC Dental", d)
```

```python
# api/tests/pipeline/test_dedupe.py
from app.pipeline.dedupe import dedupe_and_flag
from app.pipeline.discover import RawPlace


def P(i, name, **tags):
    return RawPlace(osm_type="node", osm_id=i, name=name, lat=30.0, lon=-97.0, tags={"addr:city": "Austin", **tags})


def test_merges_same_domain_and_same_phone_and_fuzzy_names():
    places = [
        P(1, "KC Dental", website="https://www.kcdental.com"),
        P(2, "K.C. Dental PLLC", website="http://kcdental.com/about"),          # same domain
        P(3, "Austin Dental Works", phone="(512) 555-0100"),
        P(4, "Austin Dental Works Inc", **{"contact:phone": "+1 512 555 0100"}),  # same phone
        P(5, "Lone Star Pediatric Dental"),
        P(6, "Lone Star Pediatric Dental Care"),                                 # fuzzy ≥ 90
    ]
    out = dedupe_and_flag(places, "US")
    assert [c.place.osm_id for c in out] == [1, 3, 5]
    assert out[0].domain == "kcdental.com" and out[1].phone_e164 == "+15125550100"


def test_merged_record_keeps_most_tags_and_fills_gaps():
    places = [P(1, "KC Dental", website="https://kcdental.com"),
              P(2, "KC Dental", website="https://kcdental.com", phone="512-918-0888", opening_hours="Mo-Fr")]
    out = dedupe_and_flag(places, "US")
    assert len(out) == 1 and out[0].place.osm_id == 2 and out[0].phone_e164 == "+15129180888"


def test_chain_detection_by_repetition_and_brand_tag():
    places = [P(i, "Castle Dental") for i in range(3)] + [P(9, "Aspen Dental", brand="Aspen Dental"), P(10, "KC Dental")]
    out = dedupe_and_flag(places, "US")
    flags = {c.place.osm_id: c.is_chain_suspected for c in out}
    assert flags[9] is True and flags[10] is False
    assert any(flags[i] for i in (0, 1, 2))  # the surviving Castle Dental is flagged
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/pipeline/test_normalize.py tests/pipeline/test_dedupe.py -v` → FAIL (modules missing)

- [ ] **Step 3: Write `api/app/pipeline/normalize.py`**

```python
import re
from urllib.parse import urlparse

import phonenumbers

from app.pipeline.industries import Industry

LEGAL_SUFFIXES = {"llc", "l.l.c.", "inc", "inc.", "pllc", "pc", "p.c.", "dds", "pa", "ltd", "co", "corp", "llp"}
_LOCATION_TAIL = re.compile(r"\s+[-–|:]\s+.*$")  # " - Dentist in Austin"
_KEEP_UPPER = {"llc": "LLC", "pllc": "PLLC", "dds": "DDS", "pc": "PC", "inc": "Inc", "hvac": "HVAC", "cpa": "CPA"}


def normalize_domain(url: str | None) -> str | None:
    if not url:
        return None
    u = url.strip()
    if "://" not in u:
        u = "http://" + u
    host = (urlparse(u).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host if "." in host and " " not in host else None


def normalize_phone(raw: str | None, region: str) -> str | None:
    if not raw:
        return None
    try:
        num = phonenumbers.parse(raw, region or "US")
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_possible_number(num):
        return None
    return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)


def normalize_name(name: str) -> str:
    s = re.sub(r"[^\w\s]", " ", name.lower())
    tokens = [t for t in s.split() if t not in {x.strip(".") for x in LEGAL_SUFFIXES}]
    return " ".join(tokens)


def display_name(name: str) -> str:
    s = re.sub(r"\s+", " ", name.strip())
    s = _LOCATION_TAIL.sub("", s) if len(s.split()) > 3 else s
    if s.isupper():
        s = s.title()
    words = []
    for w in s.split(" "):
        key = w.strip(".,").lower()
        words.append(_KEEP_UPPER.get(key, w))
    return " ".join(words)


def is_generic_name(name: str, industry: Industry) -> bool:
    n = normalize_name(name)
    return n in {normalize_name(x) for x in industry.synonyms} or n == normalize_name(industry.label)
```

- [ ] **Step 4: Write `api/app/pipeline/dedupe.py`**

```python
from collections import Counter

from pydantic import BaseModel
from rapidfuzz import fuzz

from app.pipeline.discover import RawPlace
from app.pipeline.normalize import display_name, normalize_domain, normalize_name, normalize_phone

FUZZY_THRESHOLD = 90
CHAIN_REPEATS = 3


class Candidate(BaseModel):
    place: RawPlace
    domain: str | None
    phone_e164: str | None
    norm_name: str
    display: str
    is_chain_suspected: bool = False


def _phone_tag(tags: dict) -> str | None:
    return tags.get("phone") or tags.get("contact:phone")


def _site_tag(tags: dict) -> str | None:
    return tags.get("website") or tags.get("contact:website")


def _merge(keep: Candidate, other: Candidate) -> Candidate:
    """Keep the record with more tags; fill its gaps from the other."""
    a, b = (keep, other) if len(keep.place.tags) >= len(other.place.tags) else (other, keep)
    tags = {**b.place.tags, **a.place.tags}
    place = a.place.model_copy(update={"tags": tags})
    return Candidate(place=place, domain=a.domain or b.domain, phone_e164=a.phone_e164 or b.phone_e164,
                     norm_name=a.norm_name, display=a.display)


def dedupe_and_flag(places: list[RawPlace], region: str) -> list[Candidate]:
    cands = [Candidate(place=p, domain=normalize_domain(_site_tag(p.tags)),
                       phone_e164=normalize_phone(_phone_tag(p.tags), region),
                       norm_name=normalize_name(p.name), display=display_name(p.name)) for p in places]
    # chain detection is computed on the *pre-dedupe* set so 3 identical branches count as a chain
    name_counts = Counter(c.norm_name for c in cands)
    kept: list[Candidate] = []
    for c in cands:
        dup_idx = None
        for i, k in enumerate(kept):
            same_city = k.place.tags.get("addr:city") == c.place.tags.get("addr:city")
            if (c.domain and c.domain == k.domain) or (c.phone_e164 and c.phone_e164 == k.phone_e164) or \
               (same_city and fuzz.token_set_ratio(c.norm_name, k.norm_name) >= FUZZY_THRESHOLD):
                dup_idx = i
                break
        if dup_idx is None:
            kept.append(c)
        else:
            kept[dup_idx] = _merge(kept[dup_idx], c)
    for c in kept:
        tags = c.place.tags
        c.is_chain_suspected = name_counts[c.norm_name] >= CHAIN_REPEATS or "brand" in tags or "brand:wikidata" in tags
    return kept
```

- [ ] **Step 5: Run to verify pass** — `pytest tests/pipeline/ -v` → all PASS. If `test_merges_...` fails on the fuzzy pair, print `fuzz.token_set_ratio("lone star pediatric dental", "lone star pediatric dental care")` — it is 100 (token-set), so a failure means normalization, not the threshold.

- [ ] **Step 6: Lint, log time, commit**

Append: `| 2026-09-17 | 6 normalize, dedupe, chain flag | 25 | 125 | |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(pipeline): normalization, dedupe, chain and generic-name detection"
```

### Task 7: Polite crawler — robots.txt, page fetch, text cleaning, `text_quality`

**Spec:** §5.4, §15.

**Files:**
- Create: `api/app/pipeline/crawl.py`, `api/tests/pipeline/test_crawl.py`, `api/tests/fixtures/site_home.html`, `api/tests/fixtures/site_contact.html`

**Interfaces:**
- Produces: `PageText(BaseModel): url, title: str, meta_description: str, visible_text: str, text_quality: Literal["good","thin","empty"], raw_head: str, links: list[str]`; `PageBundle(BaseModel): domain: str, pages: list[PageText], fetched_at: datetime`; `CrawlResult(BaseModel): status: Literal["ok","blocked_by_robots","unreachable"], bundle: PageBundle | None`; `async def crawl_site(url: str, client: httpx.AsyncClient) -> CrawlResult`; `clean_html(html: str) -> tuple[str, str, str, list[str], str]` (title, meta, visible_text, links, raw_head).
- The per-domain serial lock and global concurrency 8 live in the runner (Task 13) using `asyncio.Semaphore`; `crawl_site` itself is sequential per site.

- [ ] **Step 1: Create fixtures**

`api/tests/fixtures/site_home.html`:
```html
<!doctype html><html><head><title>KC Dental | Austin Family Dentist</title>
<meta name="description" content="Family-owned dental practice serving Austin since 1998.">
<meta name="generator" content="WordPress 6.5"></head>
<body><nav><a href="/">Home</a><a href="/about-us">About</a><a href="/contact">Contact</a></nav>
<div class="cookie-banner">We use cookies. Accept</div>
<main><h1>Welcome to KC Dental</h1>
<p>Family-owned and operated since 1998, Dr. Karen Chen, owner, has served North Austin for 25 years.</p>
<p>Call <a href="tel:5129180888">(512) 918-0888</a> or email <a href="mailto:hello@kcdental.com">hello@kcdental.com</a>.</p>
<p>Book an appointment online today.</p></main>
<footer>© 2021 KC Dental. <a href="https://facebook.com/kcdental">Facebook</a></footer>
<script>var x = 1;</script></body></html>
```

`api/tests/fixtures/site_contact.html`:
```html
<!doctype html><html><head><title>Contact</title></head><body>
<nav><a href="/">Home</a><a href="/about-us">About</a><a href="/contact">Contact</a></nav>
<main><h2>Visit us</h2><p>12400 West Parmer Lane, Austin, TX 78727</p><p>Now hiring: dental hygienist.</p></main>
<footer>© 2021 KC Dental.</footer></body></html>
```

- [ ] **Step 2: Write the failing tests `api/tests/pipeline/test_crawl.py`**

```python
from pathlib import Path

import httpx
import respx

from app.pipeline.crawl import clean_html, crawl_site

FIX = Path(__file__).parent.parent / "fixtures"
HOME = (FIX / "site_home.html").read_text(encoding="utf-8")
CONTACT = (FIX / "site_contact.html").read_text(encoding="utf-8")


def test_clean_html_strips_boilerplate_and_dedupes_lines():
    title, meta, text, links, head = clean_html(HOME)
    assert title == "KC Dental | Austin Family Dentist"
    assert "since 1998" in meta
    assert "We use cookies" not in text and "var x" not in text and "Home About Contact" not in text
    assert "Family-owned and operated since 1998" in text
    assert "/about-us" in links and "/contact" in links
    assert 'name="generator" content="WordPress' in head


@respx.mock
async def test_crawl_fetches_home_and_linked_contact_pages():
    respx.get("https://kcdental.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://kcdental.com/").mock(return_value=httpx.Response(200, html=HOME))
    respx.get("https://kcdental.com/contact").mock(return_value=httpx.Response(200, html=CONTACT))
    respx.get("https://kcdental.com/about-us").mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as c:
        res = await crawl_site("https://kcdental.com", c)
    assert res.status == "ok"
    urls = [p.url for p in res.bundle.pages]
    assert urls[0] == "https://kcdental.com/" and "https://kcdental.com/contact" in urls
    assert len(urls) == 2  # /about-us returned 500 and is excluded
    assert res.bundle.pages[0].text_quality == "good"


@respx.mock
async def test_crawl_respects_robots():
    respx.get("https://blocked.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /\n"))
    async with httpx.AsyncClient() as c:
        res = await crawl_site("https://blocked.com", c)
    assert res.status == "blocked_by_robots" and res.bundle is None


@respx.mock
async def test_crawl_unreachable_and_thin_pages():
    respx.get("https://down.com/robots.txt").mock(side_effect=httpx.ConnectError("x"))
    respx.get("https://down.com/").mock(side_effect=httpx.ConnectError("x"))
    respx.get("https://thin.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://thin.com/").mock(return_value=httpx.Response(200, html="<html><body><div id=root></div></body></html>"))
    async with httpx.AsyncClient() as c:
        assert (await crawl_site("https://down.com", c)).status == "unreachable"
        thin = await crawl_site("https://thin.com", c)
    assert thin.status == "ok" and thin.bundle.pages[0].text_quality == "empty"
```

- [ ] **Step 3: Run to verify failure** — `pytest tests/pipeline/test_crawl.py -v` → FAIL (module missing)

- [ ] **Step 4: Write `api/app/pipeline/crawl.py`**

```python
import re
from datetime import datetime
from typing import Literal
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel
from selectolax.parser import HTMLParser

from app.config import get_settings
from app.models import utcnow
from app.pipeline.normalize import normalize_domain

TIMEOUT = 6.0
MAX_BYTES = 1_000_000
MAX_TEXT = 20_000
MAX_PAGES = 3
SECONDARY_PATHS = ("/contact", "/contact-us", "/about", "/about-us")
STRIP_TAGS = ("script", "style", "nav", "header", "footer", "noscript", "svg", "iframe", "form")
BANNER_HINT = re.compile(r"cookie|consent|gdpr|banner|popup|modal", re.I)


class PageText(BaseModel):
    url: str
    title: str = ""
    meta_description: str = ""
    visible_text: str = ""
    text_quality: Literal["good", "thin", "empty"] = "empty"
    raw_head: str = ""
    links: list[str] = []


class PageBundle(BaseModel):
    domain: str
    pages: list[PageText]
    fetched_at: datetime


class CrawlResult(BaseModel):
    status: Literal["ok", "blocked_by_robots", "unreachable"]
    bundle: PageBundle | None = None


def clean_html(html: str) -> tuple[str, str, str, list[str], str]:
    tree = HTMLParser(html)
    head = tree.head.html if tree.head else ""
    title = (tree.css_first("title").text(strip=True) if tree.css_first("title") else "")
    meta_node = tree.css_first('meta[name="description"]')
    meta = meta_node.attributes.get("content", "") if meta_node else ""
    links = [a.attributes.get("href", "") for a in tree.css("a[href]")]
    for tag in STRIP_TAGS:
        for n in tree.css(tag):
            n.decompose()
    for n in tree.css("[class], [id]"):
        ident = f'{n.attributes.get("class", "")} {n.attributes.get("id", "")}'
        if BANNER_HINT.search(ident):
            n.decompose()
    body = tree.body.text(separator="\n") if tree.body else tree.text(separator="\n")
    seen: set[str] = set()
    lines: list[str] = []
    for raw in body.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if len(line) < 2 or line in seen:
            continue
        seen.add(line)
        lines.append(line)
    text = "\n".join(lines)[:MAX_TEXT]
    return title, meta, text, links, head or ""


def quality(text: str) -> Literal["good", "thin", "empty"]:
    n = len(text)
    return "empty" if n < 80 else "thin" if n < 400 else "good"


async def _get(client: httpx.AsyncClient, url: str) -> httpx.Response | None:
    ua = get_settings().user_agent
    for attempt in range(3):
        try:
            r = await client.get(url, headers={"User-Agent": ua, "Accept": "text/html"},
                                 timeout=TIMEOUT, follow_redirects=True)
            return r
        except httpx.TransportError:
            if attempt == 2:
                return None
    return None


async def _allowed(client: httpx.AsyncClient, base: str) -> bool | None:
    """True/False from robots.txt; None if robots.txt itself was unreachable (treated as allowed)."""
    r = await _get(client, urljoin(base, "/robots.txt"))
    if r is None or r.status_code >= 400:
        return True
    rp = robotparser.RobotFileParser()
    rp.parse(r.text.splitlines())
    return rp.can_fetch(get_settings().user_agent.split("/")[0], base)


def _page(url: str, r: httpx.Response) -> PageText | None:
    ctype = r.headers.get("content-type", "")
    if r.status_code >= 400 or ("html" not in ctype and not r.text.lstrip().lower().startswith("<")):
        return None
    html = r.text[:MAX_BYTES]
    title, meta, text, links, head = clean_html(html)
    return PageText(url=url, title=title, meta_description=meta, visible_text=text,
                    text_quality=quality(text), raw_head=head, links=links)


async def crawl_site(url: str, client: httpx.AsyncClient) -> CrawlResult:
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}/"
    domain = normalize_domain(url) or parsed.netloc
    if not await _allowed(client, base):
        return CrawlResult(status="blocked_by_robots")
    home = await _get(client, base)
    if home is None:
        return CrawlResult(status="unreachable")
    first = _page(base, home)
    if first is None:
        return CrawlResult(status="unreachable")
    pages = [first]
    wanted = [urljoin(base, h) for h in first.links
              if urlparse(urljoin(base, h)).path.rstrip("/").lower() in SECONDARY_PATHS]
    seen = {base}
    for u in wanted:
        if len(pages) >= MAX_PAGES or u in seen:
            continue
        seen.add(u)
        r = await _get(client, u)
        p = _page(u, r) if r is not None else None
        if p:
            pages.append(p)
    return CrawlResult(status="ok", bundle=PageBundle(domain=domain, pages=pages, fetched_at=utcnow()))
```

- [ ] **Step 5: Run to verify pass** — `pytest tests/pipeline/test_crawl.py -v` → 4 PASS. If the first test fails on `"Home About Contact" not in text`, confirm `nav` decomposition ran before `body.text()`; if it fails on the cookie line, the class regex must run *after* tag stripping (as written).

- [ ] **Step 6: Lint, log time, commit**

Append: `| 2026-09-17 | 7 crawler + text cleaning | 30 | 155 | |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(pipeline): robots-aware crawler with boilerplate stripping"
```

### Task 8: Regex signal and contact extraction

**Spec:** §5.5 (regex pass).

**Files:**
- Create: `api/app/pipeline/extract_regex.py`, `api/tests/pipeline/test_extract_regex.py`

**Interfaces:**
- Produces: `RegexSignals(BaseModel)` with fields `founded_year: int | None`, `family_owned: bool`, `owner_name: str | None`, `owner_operated: bool | None`, `hiring: bool`, `site_builder: str | None`, `has_booking: bool`, `has_chat: bool`, `copyright_year: int | None`, `contact_page_found: bool`, `street_address: str | None`, `postcode: str | None`; `RawContact(BaseModel): kind: Literal["email","phone","social"], value: str`; `extract_signals(bundle: PageBundle, current_year: int) -> RegexSignals`; `extract_contacts(bundle: PageBundle, region: str) -> list[RawContact]`. Every `RegexSignals` field name is also a `signals.key` in the DB.

- [ ] **Step 1: Write the failing tests**

```python
# api/tests/pipeline/test_extract_regex.py
from datetime import datetime
from pathlib import Path

from app.pipeline.crawl import PageBundle, PageText, clean_html
from app.pipeline.extract_regex import extract_contacts, extract_signals

FIX = Path(__file__).parent.parent / "fixtures"


def page(url, html):
    title, meta, text, links, head = clean_html(html)
    return PageText(url=url, title=title, meta_description=meta, visible_text=text, links=links, raw_head=head,
                    text_quality="good")


def bundle(*pages):
    return PageBundle(domain="kcdental.com", pages=list(pages), fetched_at=datetime(2026, 1, 1))


def test_signals_from_fixture_site():
    b = bundle(page("https://kcdental.com/", (FIX / "site_home.html").read_text(encoding="utf-8")),
               page("https://kcdental.com/contact", (FIX / "site_contact.html").read_text(encoding="utf-8")))
    s = extract_signals(b, current_year=2026)
    assert s.founded_year == 1998 and s.family_owned and s.owner_operated is True
    assert s.owner_name == "Karen Chen"
    assert s.site_builder == "wordpress" and s.has_booking and not s.has_chat
    assert s.copyright_year == 2021 and s.hiring and s.contact_page_found
    assert s.street_address == "12400 West Parmer Lane" and s.postcode == "78727"


def test_contacts_dedupe_and_filter_assets():
    html = ('<html><body><p>hello@kcdental.com HELLO@kcdental.com logo@2x.png noreply@sentry.io '
            '(512) 918-0888 512.918.0888 <a href="https://www.instagram.com/kcdental">ig</a></p></body></html>')
    out = extract_contacts(bundle(page("https://kcdental.com/", html)), "US")
    kinds = {(c.kind, c.value) for c in out}
    assert ("email", "hello@kcdental.com") in kinds and len([c for c in out if c.kind == "email"]) == 1
    assert ("phone", "+15129180888") in kinds and len([c for c in out if c.kind == "phone"]) == 1
    assert ("social", "https://www.instagram.com/kcdental") in kinds


def test_unknowns_stay_none():
    s = extract_signals(bundle(page("https://x.com/", "<html><body><p>Hi.</p></body></html>")), 2026)
    assert s.founded_year is None and s.owner_operated is None and s.owner_name is None and s.site_builder is None
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/pipeline/test_extract_regex.py -v` → FAIL (module missing)

- [ ] **Step 3: Write `api/app/pipeline/extract_regex.py`**

```python
import re
from typing import Literal

import phonenumbers
from pydantic import BaseModel

from app.pipeline.crawl import PageBundle
from app.pipeline.normalize import normalize_phone

YEAR = r"((?:18|19|20)\d{2})"
FOUNDED = re.compile(rf"(?:est\.?|established|since|founded|serving[^.]{{0,40}}?since)\s*(?:in\s+)?{YEAR}", re.I)
FAMILY = re.compile(r"family[- ]owned|owner[- ]operated|locally owned", re.I)
OWNER_A = re.compile(r"\b(?:Dr\.?\s+)?([A-Z][a-z]+ [A-Z][a-z]+),?\s+(?:owner|founder)\b")
OWNER_B = re.compile(r"\bowner[,:]?\s+(?:Dr\.?\s+)?([A-Z][a-z]+ [A-Z][a-z]+)\b")
HIRING = re.compile(r"we'?re hiring|careers|join our team|now hiring", re.I)
BOOKING = re.compile(r"book (?:an|your) appointment|schedule online|zocdoc|calendly|acuity|localmed|housecall pro|jobber", re.I)
CHAT = re.compile(r"intercom|drift\.com|tawk\.to|livechat|podium|birdeye", re.I)
COPYRIGHT = re.compile(rf"(?:©|copyright)\s*{YEAR}", re.I)
GENERATOR = re.compile(r'name="generator"\s+content="([^"]+)"', re.I)
BUILDERS = {"wordpress": "wordpress", "wix": "wix", "squarespace": "squarespace", "weebly": "weebly",
            "godaddy": "godaddy", "duda": "duda"}
BUILDER_HINTS = {"wixstatic": "wix", "squarespace.com": "squarespace", "godaddysites": "godaddy", "wp-content": "wordpress"}
STREET = re.compile(r"\b(\d{1,6}\s+[A-Za-z0-9.' ]{2,40}?\s+(?:St|Street|Ave|Avenue|Blvd|Rd|Road|Dr|Drive|Ln|Lane|Way|Pkwy|Hwy|Ct|Pl))\b")
POSTCODE_US = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_JUNK = ("example.com", "sentry.io", "wixpress.com", ".png", ".jpg", ".svg", ".gif", ".webp")
SOCIAL = re.compile(r"https?://(?:www\.)?(?:facebook|instagram|yelp|x|twitter)\.com/[^\s\"'<>]+|https?://(?:www\.)?linkedin\.com/company/[^\s\"'<>]+", re.I)


class RegexSignals(BaseModel):
    founded_year: int | None = None
    family_owned: bool = False
    owner_name: str | None = None
    owner_operated: bool | None = None
    hiring: bool = False
    site_builder: str | None = None
    has_booking: bool = False
    has_chat: bool = False
    copyright_year: int | None = None
    contact_page_found: bool = False
    street_address: str | None = None
    postcode: str | None = None


class RawContact(BaseModel):
    kind: Literal["email", "phone", "social"]
    value: str


def _all_text(bundle: PageBundle) -> str:
    return "\n".join(f"{p.title}\n{p.meta_description}\n{p.visible_text}" for p in bundle.pages)


def _all_head(bundle: PageBundle) -> str:
    return "\n".join(p.raw_head for p in bundle.pages)


def _builder(head: str, text: str) -> str | None:
    m = GENERATOR.search(head)
    if m:
        for k, v in BUILDERS.items():
            if k in m.group(1).lower():
                return v
    blob = (head + text).lower()
    return next((v for k, v in BUILDER_HINTS.items() if k in blob), None)


def extract_signals(bundle: PageBundle, current_year: int) -> RegexSignals:
    text, head = _all_text(bundle), _all_head(bundle)
    s = RegexSignals()
    years = [int(y) for y in FOUNDED.findall(text) if 1850 <= int(y) <= current_year]
    s.founded_year = min(years) if years else None
    s.family_owned = bool(FAMILY.search(text))
    m = OWNER_A.search(text) or OWNER_B.search(text)
    s.owner_name = m.group(1) if m else None
    s.owner_operated = True if (s.family_owned or s.owner_name) else None
    s.hiring = bool(HIRING.search(text))
    s.site_builder = _builder(head, text)
    s.has_booking = bool(BOOKING.search(text))
    s.has_chat = bool(CHAT.search(head + text))
    cys = [int(y) for y in COPYRIGHT.findall(text) if 1990 <= int(y) <= current_year]
    s.copyright_year = max(cys) if cys else None
    s.contact_page_found = any(p.url.rstrip("/").lower().endswith(("/contact", "/contact-us", "/about", "/about-us"))
                               for p in bundle.pages)
    for line in text.splitlines():
        sm = STREET.search(line)
        if sm:
            s.street_address = sm.group(1).strip()
            pm = POSTCODE_US.search(line[sm.end():sm.end() + 60])
            s.postcode = pm.group(1) if pm else None
            break
    return s


def extract_contacts(bundle: PageBundle, region: str) -> list[RawContact]:
    text = _all_text(bundle)
    raw_html_links = " ".join(" ".join(p.links) for p in bundle.pages)
    out: list[RawContact] = []
    seen: set[str] = set()
    for e in EMAIL.findall(text + " " + raw_html_links.replace("mailto:", " ")):
        low = e.lower()
        if any(j in low for j in EMAIL_JUNK) or low in seen:
            continue
        seen.add(low)
        out.append(RawContact(kind="email", value=low))
    for m in phonenumbers.PhoneNumberMatcher(text, region or "US"):
        e164 = normalize_phone(m.raw_string, region)
        if e164 and e164 not in seen:
            seen.add(e164)
            out.append(RawContact(kind="phone", value=e164))
    for u in SOCIAL.findall(text + " " + raw_html_links):
        if u not in seen:
            seen.add(u)
            out.append(RawContact(kind="social", value=u))
    return out
```

- [ ] **Step 4: Run to verify pass** — `pytest tests/pipeline/test_extract_regex.py -v` → 3 PASS. Debug tip: if `owner_name` is `None`, the fixture sentence is "Dr. Karen Chen, owner, has served…" → `OWNER_A` needs the optional `Dr.` prefix consumed outside the capture group (as written).

- [ ] **Step 5: Lint, log time, commit**

Append: `| 2026-09-17 | 8 regex extraction | 25 | 180 | |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(pipeline): regex signal and contact extraction"
```

### Task 9: Verification — email MX, disposable list, phone validity

**Spec:** §5.6.

**Files:**
- Create: `api/app/pipeline/verify.py`, `api/app/pipeline/disposable_domains.txt`, `api/tests/pipeline/test_verify.py`

**Interfaces:**
- Produces: `EmailStatus = Literal["verified","unverified","invalid"]`; `PhoneStatus = Literal["valid","possible","invalid"]`; `async def verify_email(addr: str, resolver=None) -> EmailStatus`; `def verify_phone(e164: str) -> PhoneStatus`; `DISPOSABLE_DOMAINS: frozenset[str]`; `clear_mx_cache()`.

- [ ] **Step 1: Create `api/app/pipeline/disposable_domains.txt`** — one domain per line. Seed with at least: `mailinator.com`, `guerrillamail.com`, `10minutemail.com`, `tempmail.com`, `yopmail.com`, `trashmail.com`, `getnada.com`, `sharklasers.com`, `dispostable.com`, `maildrop.cc` (the implementer may paste a longer public list; keep the file under 50 KB).

- [ ] **Step 2: Write the failing tests `api/tests/pipeline/test_verify.py`**

```python
import dns.resolver
import pytest

from app.pipeline import verify as v


class FakeResolver:
    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.calls = 0

    def resolve(self, domain, rtype, lifetime=3.0):
        self.calls += 1
        b = self.behaviour.get(domain)
        if b == "nx":
            raise dns.resolver.NXDOMAIN()
        if b == "timeout":
            raise dns.resolver.LifetimeTimeout()
        if b == "nomx":
            raise dns.resolver.NoAnswer()
        return ["mx.example."]


@pytest.fixture(autouse=True)
def _reset():
    v.clear_mx_cache()


async def test_email_statuses():
    r = FakeResolver({"kcdental.com": "ok", "nx.com": "nx", "slow.com": "timeout", "nomx.com": "nomx"})
    assert await v.verify_email("hello@kcdental.com", r) == "verified"
    assert await v.verify_email("a@nx.com", r) == "invalid"
    assert await v.verify_email("a@nomx.com", r) == "invalid"
    assert await v.verify_email("a@slow.com", r) == "unverified"
    assert await v.verify_email("not-an-email", r) == "invalid"
    assert await v.verify_email("x@mailinator.com", r) == "invalid"


async def test_mx_lookup_cached_per_domain():
    r = FakeResolver({"kcdental.com": "ok"})
    await v.verify_email("a@kcdental.com", r)
    await v.verify_email("b@kcdental.com", r)
    assert r.calls == 1


def test_phone():
    assert v.verify_phone("+15129180888") == "valid"
    assert v.verify_phone("+15550100000") in ("possible", "invalid")
    assert v.verify_phone("+1") == "invalid"
```

- [ ] **Step 3: Run to verify failure** — `pytest tests/pipeline/test_verify.py -v` → FAIL (module missing)

- [ ] **Step 4: Write `api/app/pipeline/verify.py`**

```python
import asyncio
import re
from pathlib import Path
from typing import Literal

import dns.resolver
import phonenumbers

EmailStatus = Literal["verified", "unverified", "invalid"]
PhoneStatus = Literal["valid", "possible", "invalid"]

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})$")
DISPOSABLE_DOMAINS: frozenset[str] = frozenset(
    ln.strip().lower() for ln in Path(__file__).with_name("disposable_domains.txt").read_text().splitlines()
    if ln.strip() and not ln.startswith("#"))

_mx_cache: dict[str, EmailStatus] = {}


def clear_mx_cache() -> None:
    _mx_cache.clear()


def _mx(domain: str, resolver) -> EmailStatus:
    try:
        resolver.resolve(domain, "MX", lifetime=3.0)
        return "verified"
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return "invalid"
    except (dns.resolver.LifetimeTimeout, dns.exception.DNSException):
        return "unverified"


async def verify_email(addr: str, resolver=None) -> EmailStatus:
    m = EMAIL_RE.match(addr.strip())
    if not m:
        return "invalid"
    domain = m.group(1).lower()
    if domain in DISPOSABLE_DOMAINS:
        return "invalid"
    if domain not in _mx_cache:
        res = resolver or dns.resolver.Resolver()
        _mx_cache[domain] = await asyncio.to_thread(_mx, domain, res)
    return _mx_cache[domain]


def verify_phone(e164: str) -> PhoneStatus:
    try:
        num = phonenumbers.parse(e164, None)
    except phonenumbers.NumberParseException:
        return "invalid"
    if phonenumbers.is_valid_number(num):
        return "valid"
    return "possible" if phonenumbers.is_possible_number(num) else "invalid"
```

Add `import dns.exception` at the top (used in the except clause).

- [ ] **Step 5: Run to verify pass** — `pytest tests/pipeline/test_verify.py -v` → 3 PASS

- [ ] **Step 6: Lint, log time, commit**

Append: `| 2026-09-17 | 9 verification | 15 | 195 | |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(pipeline): email MX/disposable and phone verification"
```

### Task 10: Scoring engine — `LeadFacts`, factors, presets, golden fixture

**Spec:** §5.7, §6.

**Files:**
- Create: `api/app/pipeline/score.py`, `api/tests/pipeline/test_score.py`, `api/tests/fixtures/golden_scores.json`

**Interfaces:**
- Produces: `LeadFacts(BaseModel)` (fields exactly as spec §5.7); `FactorScore(BaseModel): factor: str, points: float, max_points: float, reasons: list[str]`; `FACTORS = ["reachability","establishment","digital_gap","buybox","succession"]`; `MAX_POINTS = {"reachability":25,"establishment":20,"digital_gap":20,"buybox":20,"succession":15}`; `WEIGHT_PRESETS: dict[str, dict[str, float]]`; `score(facts, reference_year) -> list[FactorScore]`; `total(factor_scores, weights) -> float` (0–100, 1 dp); `tier(total) -> Literal["A","B","C","D"]`. The golden JSON is **the** contract with `web/src/lib/rank.ts` (Task 19).

- [ ] **Step 1: Write the failing tests `api/tests/pipeline/test_score.py`**

```python
import json
from pathlib import Path

import pytest

from app.pipeline.score import MAX_POINTS, WEIGHT_PRESETS, FactorScore, LeadFacts, score, tier, total

GOLD = json.loads((Path(__file__).parent.parent / "fixtures/golden_scores.json").read_text())


def facts(**over) -> LeadFacts:
    base = dict(industry_key="dentist", has_website=True, site_reachable=True, contact_page_found=True,
                best_email_status="verified", best_phone_status="valid", founded_year=1998,
                owner_name_found=True, owner_operated=True, family_owned=True, is_chain_suspected=False,
                has_physical_address=True, osm_full_address=True, osm_opening_hours=True, osm_has_contact=True,
                site_builder="wix", has_booking=False, has_chat=False, copyright_year=2021, generic_name=False)
    return LeadFacts(**{**base, **over})


def test_ideal_lead_maxes_every_factor_except_digital_gap_partial():
    fs = {f.factor: f for f in score(facts(), reference_year=2026)}
    assert fs["reachability"].points == 25 and fs["establishment"].points == 20
    assert fs["buybox"].points == 20 and fs["succession"].points == 15
    assert fs["digital_gap"].points == 7 + 5 + 3 + 5  # wix, no booking, no chat, stale ©
    assert any("verified email" in r for r in fs["reachability"].reasons)


def test_no_website_is_full_digital_gap_but_hurts_reachability():
    fs = {f.factor: f for f in score(facts(has_website=False, site_reachable=False, contact_page_found=False,
                                            best_email_status="none", site_builder=None, copyright_year=None),
                                      reference_year=2026)}
    assert fs["digital_gap"].points == 20 and fs["reachability"].points == 8


def test_chain_and_generic_name_lose_buybox_points():
    fs = {f.factor: f for f in score(facts(is_chain_suspected=True, generic_name=True), reference_year=2026)}
    assert fs["buybox"].points == 4  # address only


def test_total_tier_and_weights():
    fs = score(facts(), reference_year=2026)
    t = total(fs, WEIGHT_PRESETS["balanced"])
    assert t == pytest.approx(25 + 20 + 20 * 20 / 20 * 1.0 + 20 + 15, abs=0.1) or t > 0  # sanity, exact below
    assert tier(70) == "A" and tier(69.9) == "B" and tier(55) == "B" and tier(40) == "C" and tier(39.9) == "D"
    heavy = total(fs, {"reachability": 100, "establishment": 0, "digital_gap": 0, "buybox": 0, "succession": 0})
    assert heavy == 100.0
    assert sum(WEIGHT_PRESETS["succession"].values()) == 100


@pytest.mark.parametrize("case", GOLD["cases"], ids=[c["name"] for c in GOLD["cases"]])
def test_golden_cases(case):
    fs = score(LeadFacts(**case["facts"]), reference_year=GOLD["reference_year"])
    got = {f.factor: f.points for f in fs}
    assert got == case["expected_points"]
    assert total(fs, WEIGHT_PRESETS["balanced"]) == pytest.approx(case["expected_total_balanced"], abs=0.05)
    assert tier(total(fs, WEIGHT_PRESETS["balanced"])) == case["expected_tier"]
    assert {f.factor: f.max_points for f in fs} == MAX_POINTS
```

- [ ] **Step 2: Create `api/tests/fixtures/golden_scores.json`** (hand-computed from the §6 table; the TS test reads this same file)

```json
{
  "reference_year": 2026,
  "cases": [
    {"name": "ideal_independent_wix",
     "facts": {"industry_key": "dentist", "has_website": true, "site_reachable": true, "contact_page_found": true,
               "best_email_status": "verified", "best_phone_status": "valid", "founded_year": 1998,
               "owner_name_found": true, "owner_operated": true, "family_owned": true, "is_chain_suspected": false,
               "has_physical_address": true, "osm_full_address": true, "osm_opening_hours": true, "osm_has_contact": true,
               "site_builder": "wix", "has_booking": false, "has_chat": false, "copyright_year": 2021, "generic_name": false},
     "expected_points": {"reachability": 25, "establishment": 20, "digital_gap": 20, "buybox": 20, "succession": 15},
     "expected_total_balanced": 100.0, "expected_tier": "A"},
    {"name": "no_website_phone_only",
     "facts": {"industry_key": "plumber", "has_website": false, "site_reachable": false, "contact_page_found": false,
               "best_email_status": "none", "best_phone_status": "valid", "founded_year": null,
               "owner_name_found": false, "owner_operated": null, "family_owned": false, "is_chain_suspected": false,
               "has_physical_address": true, "osm_full_address": false, "osm_opening_hours": false, "osm_has_contact": true,
               "site_builder": null, "has_booking": false, "has_chat": false, "copyright_year": null, "generic_name": false},
     "expected_points": {"reachability": 8, "establishment": 2, "digital_gap": 20, "buybox": 20, "succession": 0},
     "expected_total_balanced": 50.0, "expected_tier": "C"},
    {"name": "chain_modern_site",
     "facts": {"industry_key": "dentist", "has_website": true, "site_reachable": true, "contact_page_found": true,
               "best_email_status": "unverified", "best_phone_status": "valid", "founded_year": 2019,
               "owner_name_found": false, "owner_operated": null, "family_owned": false, "is_chain_suspected": true,
               "has_physical_address": true, "osm_full_address": true, "osm_opening_hours": true, "osm_has_contact": true,
               "site_builder": null, "has_booking": true, "has_chat": true, "copyright_year": 2026, "generic_name": false},
     "expected_points": {"reachability": 19, "establishment": 17, "digital_gap": 0, "buybox": 8, "succession": 0},
     "expected_total_balanced": 44.0, "expected_tier": "C"},
    {"name": "old_family_business_generic_name",
     "facts": {"industry_key": "laundry", "has_website": true, "site_reachable": true, "contact_page_found": false,
               "best_email_status": "invalid", "best_phone_status": "possible", "founded_year": 1985,
               "owner_name_found": true, "owner_operated": true, "family_owned": true, "is_chain_suspected": false,
               "has_physical_address": false, "osm_full_address": false, "osm_opening_hours": false, "osm_has_contact": false,
               "site_builder": "godaddy", "has_booking": false, "has_chat": false, "copyright_year": 2019, "generic_name": true},
     "expected_points": {"reachability": 2, "establishment": 13, "digital_gap": 20, "buybox": 12, "succession": 15},
     "expected_total_balanced": 62.0, "expected_tier": "B"}
  ]
}
```

Hand verification against §6 (balanced weights equal the maxima, so total = sum of points):
- `ideal_independent_wix`: digital gap 7 (wix) + 5 (no booking) + 3 (no chat) + 5 (© 2021 stale in 2026) = 20; all others max → 100, A.
- `no_website_phone_only`: reachability 8 (phone only); establishment 2 (OSM contact tag); digital 20 (no website); buybox 12 + 4 + 4 = 20; succession 0 → 50, C.
- `chain_modern_site`: reachability 6 + 8 + 3 + 2 = 19; establishment: age 7 → 5, OSM 3+2+2 = 7, live 5 → 17; digital 0 (no DIY builder, has booking and chat, © current); buybox: chain 0 + address 4 + real name 4 = 8; succession 0 → 44, C.
- `old_family_business_generic_name`: reachability 2 (reachable only); establishment: age 41 → 8, OSM 0, live 5 → 13; digital 7 + 5 + 3 + 5 = 20; buybox 12 + 0 + 0 = 12; succession 8 + 4 + 3 = 15 → 62, B.

**The implementer must recompute every case by hand against §6 before running, and correct the fixture — not the code — when they disagree.** The fixture is the contract.

- [ ] **Step 3: Run to verify failure** — `pytest tests/pipeline/test_score.py -v` → FAIL (module missing)

- [ ] **Step 4: Write `api/app/pipeline/score.py`**

```python
from typing import Literal

from pydantic import BaseModel

FACTORS = ["reachability", "establishment", "digital_gap", "buybox", "succession"]
MAX_POINTS = {"reachability": 25.0, "establishment": 20.0, "digital_gap": 20.0, "buybox": 20.0, "succession": 15.0}
WEIGHT_PRESETS: dict[str, dict[str, float]] = {
    "balanced": {"reachability": 25, "establishment": 20, "digital_gap": 20, "buybox": 20, "succession": 15},
    "succession": {"reachability": 25, "establishment": 15, "digital_gap": 10, "buybox": 20, "succession": 30},
    "digital_upside": {"reachability": 25, "establishment": 10, "digital_gap": 35, "buybox": 20, "succession": 10},
    "reachability_first": {"reachability": 40, "establishment": 15, "digital_gap": 15, "buybox": 20, "succession": 10},
}
DIY_BUILDERS = {"wix", "squarespace", "weebly", "godaddy", "duda", "wordpress"}


class LeadFacts(BaseModel):
    industry_key: str
    has_website: bool
    site_reachable: bool
    contact_page_found: bool
    best_email_status: Literal["verified", "unverified", "invalid", "none"]
    best_phone_status: Literal["valid", "possible", "invalid", "none"]
    founded_year: int | None
    owner_name_found: bool
    owner_operated: bool | None
    family_owned: bool
    is_chain_suspected: bool
    has_physical_address: bool
    osm_full_address: bool
    osm_opening_hours: bool
    osm_has_contact: bool
    site_builder: str | None
    has_booking: bool
    has_chat: bool
    copyright_year: int | None
    generic_name: bool


class FactorScore(BaseModel):
    factor: str
    points: float
    max_points: float
    reasons: list[str]


def _reachability(f: LeadFacts) -> FactorScore:
    pts, why = 0.0, []
    if f.best_email_status == "verified":
        pts += 12; why.append("verified email (MX ok) +12")
    elif f.best_email_status == "unverified":
        pts += 6; why.append("email found, MX unverified +6")
    if f.best_phone_status == "valid":
        pts += 8; why.append("valid phone +8")
    if f.contact_page_found:
        pts += 3; why.append("contact page found +3")
    if f.site_reachable:
        pts += 2; why.append("website reachable +2")
    return FactorScore(factor="reachability", points=pts, max_points=25, reasons=why or ["no reachable contact found"])


def _establishment(f: LeadFacts, ref: int) -> FactorScore:
    pts, why = 0.0, []
    if f.founded_year:
        age = ref - f.founded_year
        add = 8 if age >= 10 else 5 if age >= 5 else 2
        pts += add; why.append(f"founded {f.founded_year} ({age} yrs) +{add}")
    if f.osm_full_address:
        pts += 3; why.append("full address in OSM +3")
    if f.osm_opening_hours:
        pts += 2; why.append("opening hours in OSM +2")
    if f.osm_has_contact:
        pts += 2; why.append("phone/website in OSM +2")
    if f.site_reachable:
        pts += 5; why.append("live website +5")
    return FactorScore(factor="establishment", points=pts, max_points=20, reasons=why or ["little evidence of establishment"])


def _digital_gap(f: LeadFacts, ref: int) -> FactorScore:
    if not f.has_website:
        return FactorScore(factor="digital_gap", points=20, max_points=20, reasons=["no website at all — maximum digital upside +20"])
    pts, why = 0.0, []
    if f.site_builder in DIY_BUILDERS:
        pts += 7; why.append(f"DIY site builder ({f.site_builder}) +7")
    if not f.has_booking:
        pts += 5; why.append("no online booking +5")
    if not f.has_chat:
        pts += 3; why.append("no chat widget +3")
    if f.copyright_year and ref - f.copyright_year >= 2:
        pts += 5; why.append(f"copyright year {f.copyright_year} is stale +5")
    return FactorScore(factor="digital_gap", points=min(pts, 20), max_points=20, reasons=why or ["modern digital presence — low AI upside"])


def _buybox(f: LeadFacts) -> FactorScore:
    pts, why = 0.0, []
    if not f.is_chain_suspected:
        pts += 12; why.append("independent (not a chain) +12")
    else:
        why.append("chain/franchise suspected +0")
    if f.has_physical_address:
        pts += 4; why.append("physical address known +4")
    if not f.generic_name:
        pts += 4; why.append("real business name +4")
    else:
        why.append("generic listing name (e.g. 'Dentist') +0")
    return FactorScore(factor="buybox", points=pts, max_points=20, reasons=why)


def _succession(f: LeadFacts, ref: int) -> FactorScore:
    pts, why = 0.0, []
    if f.founded_year:
        age = ref - f.founded_year
        if age >= 20:
            pts += 8; why.append(f"{age} years old +8")
        elif age >= 15:
            pts += 5; why.append(f"{age} years old +5")
    if f.owner_name_found:
        pts += 4; why.append("owner named on site +4")
    if f.family_owned or f.owner_operated:
        pts += 3; why.append("family-owned / owner-operated +3")
    return FactorScore(factor="succession", points=pts, max_points=15, reasons=why or ["no succession signals"])


def score(facts: LeadFacts, reference_year: int) -> list[FactorScore]:
    return [_reachability(facts), _establishment(facts, reference_year), _digital_gap(facts, reference_year),
            _buybox(facts), _succession(facts, reference_year)]


def total(factor_scores: list[FactorScore], weights: dict[str, float]) -> float:
    wsum = sum(weights.get(f, 0) for f in FACTORS) or 1.0
    t = sum((fs.points / fs.max_points) * (weights.get(fs.factor, 0) / wsum) * 100 for fs in factor_scores)
    return round(t, 1)


def tier(t: float) -> Literal["A", "B", "C", "D"]:
    return "A" if t >= 70 else "B" if t >= 55 else "C" if t >= 40 else "D"
```

Ruff will flag the `pts += 12; why.append(...)` one-liners (E702). Either split them onto two lines or add `# noqa: E702`; splitting is preferred.

- [ ] **Step 5: Run to verify pass** — `pytest tests/pipeline/test_score.py -v` → all PASS (including 4 golden cases). Remove the sanity `or t > 0` line from `test_total_tier_and_weights` and assert `t == 100.0` once the fixture is confirmed.

- [ ] **Step 6: Lint, log time, commit**

Append: `| 2026-09-17 | 10 scoring engine + golden fixture | 30 | 225 | |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(pipeline): explainable five-factor scoring with golden fixture"
```

### Task 11: Groq client — token bucket, model pool, 429 fallback, daily cap, schemas, prompts

**Spec:** §7.1, §7.3, §7.2 (schemas).

**Files:**
- Create: `api/app/llm/__init__.py`, `api/app/llm/throttle.py`, `api/app/llm/client.py`, `api/app/llm/schemas.py`, `api/app/llm/prompts.py`, `api/tests/llm/__init__.py`, `api/tests/llm/test_throttle.py`, `api/tests/llm/test_client.py`, `api/tests/llm/test_schemas.py`

**Interfaces:**
- Produces: `TokenBucket(rpm, tpm, clock=time.monotonic, sleep=asyncio.sleep)` with `async acquire(tokens: int)`. `LLMPool(settings, groq_client=None, clock=time.monotonic, sleep=asyncio.sleep)` with `enabled: bool` and `async complete_json(*, schema_name, schema, system, user, max_tokens=300) -> tuple[dict | None, LLMStatus]` where `LLMStatus = Literal["ok","disabled","skipped_rate_limit","skipped_budget","error"]`. `IntentResult`, `ExtractionResult` (+ `.validated(source_text, osm_name, country_code, current_year)`), `INTENT_SCHEMA`, `EXTRACTION_SCHEMA`, `OPENER_SCHEMA`. `prompts.intent_messages(text, industries, presets) -> tuple[str, str]`, `prompts.extraction_messages(page_text, osm_name) -> tuple[str, str]`, `prompts.opener_messages(summary: dict) -> tuple[str, str]`.

- [ ] **Step 1: Write the failing throttle test `api/tests/llm/test_throttle.py`**

```python
from app.llm.throttle import TokenBucket


async def test_bucket_waits_when_request_or_token_budget_exhausted():
    now = [0.0]
    slept = []

    async def fake_sleep(s):
        slept.append(s)
        now[0] += s

    b = TokenBucket(rpm=2, tpm=1000, clock=lambda: now[0], sleep=fake_sleep)
    await b.acquire(300)
    await b.acquire(300)
    assert slept == []
    await b.acquire(300)          # third request within 60 s → must wait for the window
    assert slept and now[0] >= 60.0
    await b.acquire(900)          # tokens: 300 used in the new window + 900 > 1000 → wait again
    assert len(slept) >= 2
```

- [ ] **Step 2: Write `api/app/llm/throttle.py`**

```python
import asyncio
import time
from collections import deque

WINDOW = 60.0


class TokenBucket:
    """Sliding 60 s window over requests and estimated tokens (spec §7.3)."""

    def __init__(self, rpm: int, tpm: int, clock=time.monotonic, sleep=asyncio.sleep):
        self.rpm, self.tpm, self.clock, self.sleep = rpm, tpm, clock, sleep
        self._events: deque[tuple[float, int]] = deque()

    def _trim(self) -> None:
        cutoff = self.clock() - WINDOW
        while self._events and self._events[0][0] <= cutoff:
            self._events.popleft()

    def _would_exceed(self, tokens: int) -> bool:
        return len(self._events) >= self.rpm or sum(t for _, t in self._events) + tokens > self.tpm

    async def acquire(self, tokens: int) -> None:
        self._trim()
        while self._events and self._would_exceed(tokens):
            wait = max(0.05, self._events[0][0] + WINDOW - self.clock())
            await self.sleep(wait)
            self._trim()
        self._events.append((self.clock(), tokens))
```

Run: `pytest tests/llm/test_throttle.py -v` → PASS. Create empty `api/app/llm/__init__.py`, `api/tests/llm/__init__.py`.

- [ ] **Step 3: Write `api/app/llm/schemas.py`** (hand-written strict JSON schemas + Pydantic models with validation)

```python
import re
from typing import Literal

from pydantic import BaseModel, Field

PRESETS = ["balanced", "succession", "digital_upside", "reachability_first"]


def _nullable(t: str, **extra) -> dict:
    return {"type": [t, "null"], **extra}


INTENT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["industry_key", "location", "limit", "weight_preset", "rationale"],
    "properties": {
        "industry_key": _nullable("string"),
        "location": _nullable("string"),
        "limit": _nullable("integer"),
        "weight_preset": {"type": "string", "enum": PRESETS},
        "rationale": {"type": "string"},
    },
}

ADDRESS_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["street", "city", "state", "postcode"],
    "properties": {k: _nullable("string") for k in ("street", "city", "state", "postcode")},
}

EXTRACTION_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["display_name", "founded_year", "owner_operated", "owner_name", "family_owned", "is_chain",
                 "hiring", "services", "address", "confidence"],
    "properties": {
        "display_name": _nullable("string"),
        "founded_year": _nullable("integer"),
        "owner_operated": _nullable("boolean"),
        "owner_name": _nullable("string"),
        "family_owned": _nullable("boolean"),
        "is_chain": _nullable("boolean"),
        "hiring": _nullable("boolean"),
        "services": {"type": "array", "items": {"type": "string"}},
        "address": ADDRESS_SCHEMA,
        "confidence": {"type": "number"},
    },
}

OPENER_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["opener"],
                 "properties": {"opener": {"type": "string"}}}


class IntentResult(BaseModel):
    industry_key: str | None
    location: str | None
    limit: int | None
    weight_preset: Literal["balanced", "succession", "digital_upside", "reachability_first"] = "balanced"
    rationale: str = ""


class LLMAddress(BaseModel):
    street: str | None = None
    city: str | None = None
    state: str | None = None
    postcode: str | None = None


class ExtractionResult(BaseModel):
    display_name: str | None = None
    founded_year: int | None = None
    owner_operated: bool | None = None
    owner_name: str | None = None
    family_owned: bool | None = None
    is_chain: bool | None = None
    hiring: bool | None = None
    services: list[str] = Field(default_factory=list)
    address: LLMAddress = Field(default_factory=LLMAddress)
    confidence: float = 0.0

    def validated(self, source_text: str, osm_name: str, country_code: str, current_year: int) -> "ExtractionResult":
        """Field-by-field validation (spec §7.2). Bad fields are dropped; the rest survive."""
        r = self.model_copy(deep=True)
        low = source_text.lower()
        if r.founded_year is not None and not (1850 <= r.founded_year <= current_year):
            r.founded_year = None
        if r.owner_name and r.owner_name.lower() not in low:
            r.owner_name = None  # grounding check — hallucinated names are discarded
        if r.display_name:
            a = set(re.findall(r"\w+", r.display_name.lower()))
            b = set(re.findall(r"\w+", osm_name.lower()))
            if not b or len(a & b) / len(b) < 0.6:
                r.display_name = None
        if r.address.postcode:
            ok = re.fullmatch(r"\d{5}(-\d{4})?", r.address.postcode) if country_code == "US" else \
                re.fullmatch(r"[A-Za-z]\d[A-Za-z] ?\d[A-Za-z]\d", r.address.postcode) if country_code == "CA" else \
                re.fullmatch(r"[A-Za-z0-9 -]{3,10}", r.address.postcode)
            if not ok:
                r.address.postcode = None
        r.services = [s.strip()[:40] for s in r.services if s and s.strip()][:8]
        r.confidence = min(max(float(r.confidence), 0.0), 1.0)
        return r
```

- [ ] **Step 4: Write the failing schema test `api/tests/llm/test_schemas.py`**

```python
from app.llm.schemas import ExtractionResult, LLMAddress


def test_validation_drops_ungrounded_and_out_of_range_fields():
    raw = ExtractionResult(display_name="Totally Different Co", founded_year=1799, owner_name="Jane Doe",
                           services=["a"] * 12, address=LLMAddress(postcode="ABCDE"), confidence=1.7)
    v = raw.validated(source_text="KC Dental — family owned since 1998. Dr. Karen Chen, owner.",
                      osm_name="KC Dental", country_code="US", current_year=2026)
    assert v.display_name is None and v.founded_year is None and v.owner_name is None
    assert len(v.services) == 8 and v.address.postcode is None and v.confidence == 1.0


def test_validation_keeps_grounded_fields():
    raw = ExtractionResult(display_name="KC Dental PLLC", founded_year=1998, owner_name="Karen Chen",
                           address=LLMAddress(postcode="78727"), confidence=0.9)
    v = raw.validated("… Dr. Karen Chen, owner …", "KC Dental", "US", 2026)
    assert (v.display_name, v.founded_year, v.owner_name, v.address.postcode) == ("KC Dental PLLC", 1998, "Karen Chen", "78727")
```

Run: `pytest tests/llm/test_schemas.py -v` → PASS.

- [ ] **Step 5: Write `api/app/llm/prompts.py`**

```python
import json


def intent_messages(text: str, industries: list[dict], presets: list[str]) -> tuple[str, str]:
    system = ("You turn a searcher's natural-language request into a structured search for small businesses. "
              "Choose industry_key ONLY from the provided list (or null if none fits). Extract the location as the "
              "user wrote it. limit is an integer 5-100 or null. Pick weight_preset: 'succession' if they mention "
              "retirement, aging owners or succession; 'digital_upside' if they mention outdated websites, no online "
              "presence or modernization; 'reachability_first' if they stress contactability; else 'balanced'. "
              "rationale: one sentence. Never invent industries.")
    user = json.dumps({"request": text, "industries": industries, "presets": presets})
    return system, user


def extraction_messages(page_text: str, osm_name: str) -> tuple[str, str]:
    system = ("You read messy text scraped from a small business website and return clean structured facts. "
              "Only state what the text supports; use null when unsure. display_name is the business's proper name "
              "(fix casing, drop slogans). founded_year is a 4-digit year only if stated. owner_name must appear "
              "verbatim in the text. address fields only if present. services: up to 8 short phrases. "
              "confidence 0-1 for the whole answer.")
    user = json.dumps({"osm_listing_name": osm_name, "page_text": page_text})
    return system, user


def opener_messages(summary: dict) -> tuple[str, str]:
    system = ("Write a 3-line cold-call opener for an acquisition entrepreneur calling a small business owner. "
              "Ground every sentence in the provided facts; do not invent details, numbers or names. Warm, direct, "
              "no sales jargon. Return JSON {opener: string} with exactly three lines separated by \\n.")
    return system, json.dumps(summary)
```

- [ ] **Step 6: Write the failing client tests `api/tests/llm/test_client.py`**

```python
import json
from types import SimpleNamespace

import groq
import httpx
import pytest

from app.config import Settings
from app.llm.client import LLMPool
from app.llm.schemas import OPENER_SCHEMA


def rate_limit_error(retry_after="0"):
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return groq.RateLimitError("rate limited", response=httpx.Response(429, headers={"retry-after": retry_after}, request=req), body=None)


class FakeGroq:
    """Scripted responses per model: list of callables returning content or raising."""

    def __init__(self, script: dict[str, list]):
        self.script, self.calls = script, []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, *, model, messages, response_format, max_completion_tokens):
        self.calls.append(model)
        step = self.script[model].pop(0)
        if isinstance(step, Exception):
            raise step
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=step))])


def settings(**over):
    return Settings(groq_api_key="k", groq_models=["m1", "m2"], llm_daily_soft_cap=3, **over)


async def fast_sleep(_s):
    return None


async def test_disabled_without_key():
    pool = LLMPool(Settings(groq_api_key=None), groq_client=FakeGroq({}))
    assert not pool.enabled
    assert await pool.complete_json(schema_name="o", schema=OPENER_SCHEMA, system="s", user="u") == (None, "disabled")


async def test_ok_parses_json():
    fake = FakeGroq({"m1": [json.dumps({"opener": "hi"})]})
    pool = LLMPool(settings(), groq_client=fake, sleep=fast_sleep)
    data, status = await pool.complete_json(schema_name="o", schema=OPENER_SCHEMA, system="s", user="u")
    assert status == "ok" and data == {"opener": "hi"} and fake.calls == ["m1"]


async def test_429_retries_once_then_falls_to_next_model_then_skips():
    fake = FakeGroq({"m1": [rate_limit_error(), rate_limit_error()], "m2": [json.dumps({"opener": "from m2"})]})
    pool = LLMPool(settings(), groq_client=fake, sleep=fast_sleep)
    data, status = await pool.complete_json(schema_name="o", schema=OPENER_SCHEMA, system="s", user="u")
    assert status == "ok" and data["opener"] == "from m2" and fake.calls == ["m1", "m1", "m2"]

    fake2 = FakeGroq({"m1": [rate_limit_error(), rate_limit_error()], "m2": [rate_limit_error(), rate_limit_error()]})
    pool2 = LLMPool(settings(), groq_client=fake2, sleep=fast_sleep)
    assert await pool2.complete_json(schema_name="o", schema=OPENER_SCHEMA, system="s", user="u") == (None, "skipped_rate_limit")


async def test_daily_soft_cap_and_bad_json():
    fake = FakeGroq({"m1": ["not json", json.dumps({"opener": "a"}), json.dumps({"opener": "b"}), json.dumps({"opener": "c"})]})
    pool = LLMPool(settings(llm_daily_soft_cap=3), groq_client=fake, sleep=fast_sleep)
    assert (await pool.complete_json(schema_name="o", schema=OPENER_SCHEMA, system="s", user="u"))[1] == "error"
    for _ in range(2):
        assert (await pool.complete_json(schema_name="o", schema=OPENER_SCHEMA, system="s", user="u"))[1] == "ok"
    assert (await pool.complete_json(schema_name="o", schema=OPENER_SCHEMA, system="s", user="u"))[1] == "skipped_budget"
```

- [ ] **Step 7: Run to verify failure** — `pytest tests/llm/test_client.py -v` → FAIL (module missing)

- [ ] **Step 8: Write `api/app/llm/client.py`**

```python
import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from typing import Literal

import groq

from app.config import Settings
from app.llm.throttle import TokenBucket

log = logging.getLogger(__name__)
LLMStatus = Literal["ok", "disabled", "skipped_rate_limit", "skipped_budget", "error"]
RPM, TPM, RETRY_CAP_S = 6, 7000, 20.0


class LLMPool:
    def __init__(self, settings: Settings, groq_client=None, clock=time.monotonic, sleep=asyncio.sleep):
        self.settings, self.clock, self.sleep = settings, clock, sleep
        self.enabled = settings.llm_enabled
        self.models = list(settings.groq_models)
        self._client = groq_client or (groq.AsyncGroq(api_key=settings.groq_api_key) if self.enabled else None)
        self._buckets = {m: TokenBucket(RPM, TPM, clock, sleep) for m in self.models}
        self._day = datetime.now(UTC).date()
        self._used_today = 0

    def _budget_ok(self) -> bool:
        today = datetime.now(UTC).date()
        if today != self._day:
            self._day, self._used_today = today, 0
        return self._used_today < self.settings.llm_daily_soft_cap

    @staticmethod
    def _estimate_tokens(system: str, user: str, max_tokens: int) -> int:
        return (len(system) + len(user)) // 4 + max_tokens

    async def _call(self, model: str, system: str, user: str, schema_name: str, schema: dict, max_tokens: int) -> str:
        resp = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}},
            max_completion_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    async def complete_json(self, *, schema_name: str, schema: dict, system: str, user: str,
                            max_tokens: int = 300) -> tuple[dict | None, LLMStatus]:
        if not self.enabled:
            return None, "disabled"
        if not self._budget_ok():
            return None, "skipped_budget"
        est = self._estimate_tokens(system, user, max_tokens)
        for model in self.models:
            for attempt in range(2):
                await self._buckets[model].acquire(est)
                try:
                    self._used_today += 1
                    content = await self._call(model, system, user, schema_name, schema, max_tokens)
                    return json.loads(content), "ok"
                except groq.RateLimitError as e:
                    if attempt == 0:
                        ra = e.response.headers.get("retry-after") if e.response is not None else None
                        try:
                            wait = min(float(ra), RETRY_CAP_S) if ra else 2.0
                        except ValueError:
                            wait = 2.0
                        await self.sleep(wait)
                        continue
                    log.warning("llm.rate_limited", extra={"model": model})
                    break  # next model
                except (json.JSONDecodeError, groq.APIError, KeyError, IndexError) as e:
                    log.warning("llm.error", extra={"model": model, "err": type(e).__name__})
                    return None, "error"
        return None, "skipped_rate_limit"
```

- [ ] **Step 9: Run to verify pass** — `pytest tests/llm -v` → all PASS. If `groq.RateLimitError(...)` construction fails in the test helper, check the installed `groq` version's signature (`APIStatusError.__init__(self, message, *, response, body)`) and adjust the helper, not the client.

- [ ] **Step 10: Lint, log time, commit**

Append: `| 2026-09-17 | 11 Groq client, throttle, schemas | 30 | — | measured |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(llm): Groq pool with token bucket, 429 fallback, daily cap and strict schemas"
```

### Task 12: LLM extraction stage — gating, relevant-text input, merge policy

**Spec:** §5.5 (LLM pass, merge policy), §7.2.

**Files:**
- Create: `api/app/pipeline/extract_llm.py`, `api/tests/pipeline/test_extract_llm.py`

**Interfaces:**
- Consumes: `RegexSignals` (Task 8), `PageBundle` (Task 7), `LLMPool.complete_json` (Task 11), `ExtractionResult` (Task 11).
- Produces: `needs_llm(regex: RegexSignals, has_street: bool, text_quality: str) -> bool`; `build_llm_input(bundle: PageBundle, max_chars: int = 2800) -> str`; `async def extract_with_llm(pool, bundle, osm_name, country_code, current_year) -> tuple[ExtractionResult | None, LLMStatus]`; `SignalValue(BaseModel): key: str, value: str, source: Literal["regex","llm"], confidence: float`; `merge_signals(regex: RegexSignals, llm: ExtractionResult | None) -> list[SignalValue]`; `OVERRIDE_CONFIDENCE = 0.85`.

- [ ] **Step 1: Write the failing tests `api/tests/pipeline/test_extract_llm.py`**

```python
import json
from datetime import datetime

from app.llm.schemas import ExtractionResult, LLMAddress
from app.pipeline.crawl import PageBundle, PageText
from app.pipeline.extract_llm import build_llm_input, merge_signals, needs_llm
from app.pipeline.extract_regex import RegexSignals


def test_needs_llm_gate():
    full = RegexSignals(founded_year=1998, owner_operated=True, owner_name="K C", street_address="1 Main St")
    assert not needs_llm(full, has_street=True, text_quality="good")
    assert needs_llm(RegexSignals(founded_year=1998, owner_operated=True, owner_name="K C"), has_street=False, text_quality="good")
    assert needs_llm(RegexSignals(), has_street=True, text_quality="good")          # owner/founded unknown
    assert needs_llm(full, has_street=True, text_quality="thin")                     # thin text always


def test_build_input_prioritises_relevant_sentences_and_caps_length():
    filler = "Lorem ipsum dolor sit amet. " * 300
    text = filler + "We are a family owned practice founded in 1998 by Dr. Karen Chen. " + filler + \
           "Our office is located at 12400 West Parmer Lane. " + filler
    b = PageBundle(domain="x.com", fetched_at=datetime(2026, 1, 1), pages=[
        PageText(url="https://x.com/", title="KC Dental", meta_description="Austin dentist", visible_text=text,
                 text_quality="good")])
    out = build_llm_input(b, max_chars=600)
    assert len(out) <= 600
    assert out.startswith("KC Dental\nAustin dentist\n")
    assert "founded in 1998" in out and "located at 12400" in out
    assert out.index("founded in 1998") < out.index("Lorem")


def test_merge_regex_wins_llm_fills_gaps_and_overrides_only_when_confident():
    regex = RegexSignals(founded_year=1998, family_owned=True, owner_operated=True, site_builder="wix")
    llm_low = ExtractionResult(founded_year=2001, owner_name="Karen Chen", is_chain=False,
                               address=LLMAddress(street="12400 West Parmer Lane", postcode="78727"), confidence=0.6)
    merged = {s.key: s for s in merge_signals(regex, llm_low)}
    assert merged["founded_year"].value == "1998" and merged["founded_year"].source == "regex"
    assert merged["owner_name"].value == "Karen Chen" and merged["owner_name"].source == "llm"
    assert merged["street_address"].value == "12400 West Parmer Lane" and merged["postcode"].value == "78727"
    assert merged["is_chain"].value == "false"
    llm_high = llm_low.model_copy(update={"confidence": 0.9})
    merged2 = {s.key: s for s in merge_signals(regex, llm_high)}
    assert merged2["founded_year"].value == "2001" and merged2["founded_year"].source == "llm"
    assert merged2["founded_year"].confidence == 0.9


def test_merge_without_llm_serialises_regex_only():
    out = merge_signals(RegexSignals(has_booking=True, copyright_year=2021), None)
    keys = {s.key for s in out}
    assert {"has_booking", "copyright_year", "family_owned", "hiring", "has_chat", "contact_page_found"} <= keys
    assert all(s.source == "regex" for s in out)
    assert "founded_year" not in keys  # None values are not emitted
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/pipeline/test_extract_llm.py -v` → FAIL (module missing)

- [ ] **Step 3: Write `api/app/pipeline/extract_llm.py`**

```python
import re
from typing import Literal

from pydantic import BaseModel

from app.llm.client import LLMPool, LLMStatus
from app.llm.prompts import extraction_messages
from app.llm.schemas import EXTRACTION_SCHEMA, ExtractionResult
from app.pipeline.crawl import PageBundle
from app.pipeline.extract_regex import RegexSignals

OVERRIDE_CONFIDENCE = 0.85
RELEVANT = re.compile(r"since|founded|est\b|est\.|family|owner|our team|about|locations?|address|located", re.I)
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
GAP_FIELDS = ("founded_year", "owner_operated", "owner_name")


class SignalValue(BaseModel):
    key: str
    value: str
    source: Literal["regex", "llm"]
    confidence: float = 1.0


def needs_llm(regex: RegexSignals, has_street: bool, text_quality: str) -> bool:
    if text_quality == "thin":
        return True
    if any(getattr(regex, f) is None for f in GAP_FIELDS):
        return True
    return not has_street and not regex.street_address


def build_llm_input(bundle: PageBundle, max_chars: int = 2800) -> str:
    first = bundle.pages[0] if bundle.pages else None
    head = f"{first.title}\n{first.meta_description}\n" if first else ""
    sentences: list[str] = []
    for p in bundle.pages:
        sentences.extend(s.strip() for s in SENT_SPLIT.split(p.visible_text) if s.strip())
    relevant = [s for s in sentences if RELEVANT.search(s)]
    rest = [s for s in sentences if s not in relevant]
    out, budget = head, max_chars - len(head)
    for s in relevant + rest:
        if len(s) + 1 > budget:
            continue
        out += s + " "
        budget -= len(s) + 1
    return out.rstrip()[:max_chars]


async def extract_with_llm(pool: LLMPool, bundle: PageBundle, osm_name: str, country_code: str,
                           current_year: int) -> tuple[ExtractionResult | None, LLMStatus]:
    text = build_llm_input(bundle)
    system, user = extraction_messages(text, osm_name)
    data, status = await pool.complete_json(schema_name="extraction", schema=EXTRACTION_SCHEMA,
                                            system=system, user=user, max_tokens=350)
    if status != "ok" or data is None:
        return None, status
    try:
        result = ExtractionResult(**data).validated(text, osm_name, country_code, current_year)
    except (TypeError, ValueError):
        return None, "error"
    return result, "ok"


def _s(v) -> str:
    return str(v).lower() if isinstance(v, bool) else str(v)


def merge_signals(regex: RegexSignals, llm: ExtractionResult | None) -> list[SignalValue]:
    out: dict[str, SignalValue] = {}
    for key, val in regex.model_dump().items():
        if val is not None:
            out[key] = SignalValue(key=key, value=_s(val), source="regex", confidence=1.0)
    if llm is None:
        return list(out.values())
    llm_fields = {
        "display_name": llm.display_name, "founded_year": llm.founded_year, "owner_operated": llm.owner_operated,
        "owner_name": llm.owner_name, "family_owned": llm.family_owned, "is_chain": llm.is_chain,
        "hiring": llm.hiring, "street_address": llm.address.street, "city": llm.address.city,
        "state": llm.address.state, "postcode": llm.address.postcode,
        "services": ", ".join(llm.services) if llm.services else None,
    }
    for key, val in llm_fields.items():
        if val is None:
            continue
        existing = out.get(key)
        regex_has_value = existing is not None and key in RegexSignals.model_fields and \
            getattr(regex, key) not in (None, False)
        if not regex_has_value or (llm.confidence >= OVERRIDE_CONFIDENCE and _s(val) != existing.value):
            out[key] = SignalValue(key=key, value=_s(val), source="llm", confidence=llm.confidence)
    return list(out.values())
```

Note on the `regex_has_value` rule: regex booleans default to `False` when a pattern did not match, which is "unknown", not "known false" — so a `False` from regex is treated as a gap the LLM may fill. `founded_year`, `owner_name`, `street_address` are `None` when unknown.

- [ ] **Step 4: Run to verify pass** — `pytest tests/pipeline/test_extract_llm.py -v` → 4 PASS

- [ ] **Step 5: Lint, log time, commit**

Append: `| 2026-09-17 | 12 LLM extraction stage + merge | 20 | — | measured |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(pipeline): gated LLM extraction with validated merge policy"
```

### Task 13: Event bus, API output schemas, `build_facts`

**Spec:** §5.8 (events), §9 (lead payload shape), §5.7 (`LeadFacts` assembly).

**Files:**
- Create: `api/app/services/__init__.py`, `api/app/services/events.py`, `api/app/schemas.py`, `api/tests/services/__init__.py`, `api/tests/services/test_events.py`, `api/tests/test_schemas.py`

**Interfaces:**
- Produces (`events.py`): `Event = dict` with keys `type` (`status|lead|lead_updated|done|error`) and `data`; `class EventBus` with `publish(search_id: str, type: str, data: dict) -> None`, `subscribe(search_id) -> asyncio.Queue[Event | None]` (replays buffered events first), `close(search_id)` (puts `None` sentinel to all subscribers, keeps the buffer for late subscribers for 10 minutes), `bus = EventBus()` module singleton.
- Produces (`schemas.py`): `AddressOut`, `ContactOut`, `SignalOut`, `FactorScoreOut`, `LeadOut`, `SearchOut`, `SearchCreate` (request body: `industry_key`, `location`, `limit: int = 60`, `weight_preset: str = "balanced"`, `nl_query: str | None`), `IntentRequest(text: str)`, `lead_to_out(lead, contacts, signals, factor_rows) -> LeadOut`, `build_facts(lead, contacts, signals, industry) -> LeadFacts`.

- [ ] **Step 1: Write the failing event-bus test `api/tests/services/test_events.py`**

```python
import asyncio

from app.services.events import EventBus


async def test_publish_before_subscribe_is_replayed_then_live_then_closed():
    bus = EventBus()
    bus.publish("s1", "status", {"stage": "geocode"})
    q = bus.subscribe("s1")
    bus.publish("s1", "lead", {"id": "l1"})
    bus.close("s1")
    got = []
    while (ev := await asyncio.wait_for(q.get(), 1)) is not None:
        got.append(ev["type"])
    assert got == ["status", "lead"]
    # a late subscriber after close still gets the buffer and an immediate sentinel
    q2 = bus.subscribe("s1")
    types = []
    while (ev := q2.get_nowait()) is not None:
        types.append(ev["type"])
    assert types == ["status", "lead"]
```

- [ ] **Step 2: Write `api/app/services/events.py`**

```python
import asyncio
import time
from collections import defaultdict

Event = dict
BUFFER_TTL_S = 600
BUFFER_MAX = 1000


class EventBus:
    """Per-search fan-out with a replay buffer so an SSE client that connects a moment after
    POST /searches still sees every event (spec §5.8)."""

    def __init__(self) -> None:
        self._subs: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._buffer: dict[str, list[Event]] = defaultdict(list)
        self._closed: dict[str, float] = {}

    def publish(self, search_id: str, type: str, data: dict) -> None:
        ev: Event = {"type": type, "data": data}
        buf = self._buffer[search_id]
        if len(buf) < BUFFER_MAX:
            buf.append(ev)
        for q in self._subs.get(search_id, []):
            q.put_nowait(ev)

    def subscribe(self, search_id: str) -> asyncio.Queue:
        self._gc()
        q: asyncio.Queue = asyncio.Queue()
        for ev in self._buffer.get(search_id, []):
            q.put_nowait(ev)
        if search_id in self._closed:
            q.put_nowait(None)
        else:
            self._subs[search_id].append(q)
        return q

    def close(self, search_id: str) -> None:
        for q in self._subs.pop(search_id, []):
            q.put_nowait(None)
        self._closed[search_id] = time.monotonic()

    def _gc(self) -> None:
        cutoff = time.monotonic() - BUFFER_TTL_S
        for sid in [s for s, t in self._closed.items() if t < cutoff]:
            self._closed.pop(sid, None)
            self._buffer.pop(sid, None)


bus = EventBus()
```

Run: `pytest tests/services/test_events.py -v` → PASS. Create empty `api/app/services/__init__.py`, `api/tests/services/__init__.py`.

- [ ] **Step 3: Write the failing schema test `api/tests/test_schemas.py`**

```python
from app.models import Contact, Lead, Signal, new_id
from app.pipeline.industries import INDUSTRIES
from app.schemas import build_facts, lead_to_out


def make_lead(**over):
    base = dict(id=new_id(), search_id="s", osm_type="node", osm_id=1, name="Dental Clinic", display_name="Dental Clinic",
                normalized_name="dental clinic", lat=1.0, lon=2.0, website="https://x.com", normalized_domain="x.com",
                street="1 Main St", city="Austin", enrichment_status="ok", is_chain_suspected=False,
                osm_tags={"addr:housenumber": "1", "addr:street": "Main St", "addr:city": "Austin",
                          "addr:postcode": "78701", "opening_hours": "Mo-Fr", "phone": "+15125550100"})
    return Lead(**{**base, **over})


def test_build_facts_maps_rows_to_flat_facts():
    lead = make_lead()
    contacts = [Contact(lead_id=lead.id, kind="email", value="a@x.com", normalized_value="a@x.com", source="website",
                        verification_status="unverified"),
                Contact(lead_id=lead.id, kind="email", value="b@x.com", normalized_value="b@x.com", source="website",
                        verification_status="verified"),
                Contact(lead_id=lead.id, kind="phone", value="+15125550100", normalized_value="+15125550100",
                        source="osm", verification_status="valid")]
    signals = [Signal(lead_id=lead.id, key="founded_year", value="1998", source="regex"),
               Signal(lead_id=lead.id, key="owner_name", value="Karen Chen", source="llm", confidence=0.9),
               Signal(lead_id=lead.id, key="family_owned", value="true", source="regex"),
               Signal(lead_id=lead.id, key="site_builder", value="wix", source="regex"),
               Signal(lead_id=lead.id, key="copyright_year", value="2021", source="regex"),
               Signal(lead_id=lead.id, key="contact_page_found", value="true", source="regex")]
    f = build_facts(lead, contacts, signals, INDUSTRIES["dentist"])
    assert f.best_email_status == "verified" and f.best_phone_status == "valid"
    assert f.founded_year == 1998 and f.owner_name_found and f.family_owned and f.owner_operated is True
    assert f.osm_full_address and f.osm_opening_hours and f.osm_has_contact and f.has_physical_address
    assert f.site_builder == "wix" and f.copyright_year == 2021 and f.contact_page_found
    assert f.generic_name is True  # "Dental Clinic" is a category word
    assert f.has_website and f.site_reachable


def test_lead_to_out_shape():
    lead = make_lead()
    out = lead_to_out(lead, [], [], [])
    d = out.model_dump()
    assert d["address"] == {"street": "1 Main St", "housenumber": None, "city": "Austin", "state": None,
                            "postcode": None, "country": None}
    assert d["domain"] == "x.com" and d["contacts"] == [] and d["factor_scores"] == []
```

- [ ] **Step 4: Write `api/app/schemas.py`**

```python
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import Contact, FactorScoreRow, Lead, Search, Signal
from app.pipeline.industries import Industry
from app.pipeline.normalize import is_generic_name
from app.pipeline.score import LeadFacts

EMAIL_RANK = {"verified": 3, "unverified": 2, "invalid": 1}
PHONE_RANK = {"valid": 3, "possible": 2, "invalid": 1}


class SearchCreate(BaseModel):
    industry_key: str
    location: str = Field(min_length=2, max_length=120)
    limit: int = Field(default=60, ge=5, le=100)
    weight_preset: str = "balanced"
    nl_query: str | None = None


class IntentRequest(BaseModel):
    text: str = Field(min_length=3, max_length=500)


class AddressOut(BaseModel):
    street: str | None
    housenumber: str | None
    city: str | None
    state: str | None
    postcode: str | None
    country: str | None


class ContactOut(BaseModel):
    kind: str
    value: str
    source: str
    verification_status: str


class SignalOut(BaseModel):
    key: str
    value: str
    source: str
    confidence: float


class FactorScoreOut(BaseModel):
    factor: str
    points: float
    max_points: float
    reasons: list[str]


class LeadOut(BaseModel):
    id: str
    name: str
    display_name: str
    address: AddressOut
    address_source: str
    lat: float
    lon: float
    website: str | None
    domain: str | None
    is_chain_suspected: bool
    enrichment_status: str
    llm_status: str
    score: float | None
    tier: str | None
    contacts: list[ContactOut]
    signals: list[SignalOut]
    factor_scores: list[FactorScoreOut]


class SearchOut(BaseModel):
    id: str
    industry_key: str
    location_query: str
    geocoded_name: str | None
    weight_preset: str
    status: str
    lead_count: int
    llm_pending: int
    error: str | None
    created_at: datetime
    finished_at: datetime | None

    @classmethod
    def from_row(cls, s: Search) -> "SearchOut":
        return cls(**{k: getattr(s, k) for k in cls.model_fields})


def lead_to_out(lead: Lead, contacts: list[Contact], signals: list[Signal], factors: list[FactorScoreRow]) -> LeadOut:
    return LeadOut(
        id=lead.id, name=lead.name, display_name=lead.display_name,
        address=AddressOut(street=lead.street, housenumber=lead.housenumber, city=lead.city, state=lead.state,
                           postcode=lead.postcode, country=lead.country),
        address_source=lead.address_source, lat=lead.lat, lon=lead.lon, website=lead.website,
        domain=lead.normalized_domain, is_chain_suspected=lead.is_chain_suspected,
        enrichment_status=lead.enrichment_status, llm_status=lead.llm_status, score=lead.score, tier=lead.tier,
        contacts=[ContactOut(kind=c.kind, value=c.value, source=c.source, verification_status=c.verification_status)
                  for c in contacts],
        signals=[SignalOut(key=s.key, value=s.value, source=s.source, confidence=s.confidence) for s in signals],
        factor_scores=[FactorScoreOut(factor=f.factor, points=f.points, max_points=f.max_points, reasons=list(f.reasons))
                       for f in factors],
    )


def _best(contacts: list[Contact], kind: str, rank: dict[str, int]) -> str:
    statuses = [c.verification_status for c in contacts if c.kind == kind and c.verification_status in rank]
    return max(statuses, key=rank.__getitem__) if statuses else "none"


def _int(v: str | None) -> int | None:
    try:
        return int(v) if v is not None else None
    except ValueError:
        return None


def _bool(v: str | None) -> bool | None:
    return None if v is None else v.lower() == "true"


def build_facts(lead: Lead, contacts: list[Contact], signals: list[Signal], industry: Industry) -> LeadFacts:
    sig = {s.key: s.value for s in signals}
    tags = lead.osm_tags or {}
    owner_name_found = bool(sig.get("owner_name"))
    family_owned = _bool(sig.get("family_owned")) or False
    owner_operated = _bool(sig.get("owner_operated"))
    if owner_operated is None and (owner_name_found or family_owned):
        owner_operated = True
    return LeadFacts(
        industry_key=industry.key,
        has_website=bool(lead.website),
        site_reachable=lead.enrichment_status == "ok",
        contact_page_found=_bool(sig.get("contact_page_found")) or False,
        best_email_status=_best(contacts, "email", EMAIL_RANK),
        best_phone_status=_best(contacts, "phone", PHONE_RANK),
        founded_year=_int(sig.get("founded_year")),
        owner_name_found=owner_name_found,
        owner_operated=owner_operated,
        family_owned=family_owned,
        is_chain_suspected=lead.is_chain_suspected or (_bool(sig.get("is_chain")) or False),
        has_physical_address=bool(lead.street and lead.city),
        osm_full_address=all(tags.get(k) for k in ("addr:housenumber", "addr:street", "addr:city", "addr:postcode")),
        osm_opening_hours="opening_hours" in tags,
        osm_has_contact=any(k in tags for k in ("phone", "contact:phone", "website", "contact:website")),
        site_builder=sig.get("site_builder"),
        has_booking=_bool(sig.get("has_booking")) or False,
        has_chat=_bool(sig.get("has_chat")) or False,
        copyright_year=_int(sig.get("copyright_year")),
        generic_name=is_generic_name(lead.name, industry),
    )
```

- [ ] **Step 5: Run to verify pass** — `pytest tests/test_schemas.py tests/services -v` → all PASS

- [ ] **Step 6: Lint, log time, commit**

Append: `| 2026-09-17 | 13 event bus, schemas, build_facts | 20 | — | measured |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(api): event bus with replay, output schemas and LeadFacts assembly"
```

### Task 14: Pipeline runner — fast path, persistence, LLM queue, late updates

**Spec:** §5.8, §5.4 (concurrency 8, one in-flight request per domain), §7.3 (per-search cap 40), §8 (enrichment cache).

**Files:**
- Create: `api/app/pipeline/runner.py`, `api/tests/pipeline/test_runner.py`

**Interfaces:**
- Consumes: everything from Tasks 4–13.
- Produces: `async def run_search(search_id: str, *, bus: EventBus, pool: LLMPool, client: httpx.AsyncClient | None = None, reference_year: int | None = None) -> None`; `FAST_DONE_GRACE_S = 90`; `LLM_PER_SEARCH_CAP = 40`; `CRAWL_CONCURRENCY = 8`. Events published exactly as spec §9: `status {stage, message, count}`, `lead {LeadOut}`, `lead_updated {lead_id, display_name, address, address_source, signals, factor_scores, score, tier, llm_status}`, `done {lead_count, llm_pending}`, `error {message}`.

- [ ] **Step 1: Write the failing end-to-end test `api/tests/pipeline/test_runner.py`**

```python
import asyncio
import json
from pathlib import Path

import httpx
import respx
from sqlmodel import select

from app.config import Settings
from app.db import session_scope
from app.llm.client import LLMPool
from app.models import Contact, FactorScoreRow, Lead, Search, Signal, new_id
from app.pipeline import runner
from app.services.events import EventBus
from tests.llm.test_client import FakeGroq

FIX = Path(__file__).parent.parent / "fixtures"
OVERPASS = json.loads((FIX / "overpass_dentists.json").read_text())
HOME = (FIX / "site_home.html").read_text(encoding="utf-8")
CONTACT = (FIX / "site_contact.html").read_text(encoding="utf-8")
AUSTIN = [{"display_name": "Austin, Texas, United States", "boundingbox": ["30.09", "30.51", "-97.93", "-97.56"],
           "lat": "30.27", "lon": "-97.74", "address": {"country_code": "us"}}]


def mock_world():
    respx.get("https://nominatim.openstreetmap.org/search").mock(return_value=httpx.Response(200, json=AUSTIN))
    respx.post("https://overpass-api.de/api/interpreter").mock(return_value=httpx.Response(200, json=OVERPASS))
    respx.get("https://www.kcdentalaustin.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://www.kcdentalaustin.com/").mock(return_value=httpx.Response(200, html=HOME))
    respx.get("https://www.kcdentalaustin.com/contact").mock(return_value=httpx.Response(200, html=CONTACT))
    respx.get("https://www.kcdentalaustin.com/about-us").mock(return_value=httpx.Response(404))


def new_search():
    with session_scope() as s:
        row = Search(id=new_id(), industry_key="dentist", location_query="Austin, TX", limit=60)
        s.add(row)
        return row.id


async def drain(q):
    events = []
    while (ev := await asyncio.wait_for(q.get(), 10)) is not None:
        events.append(ev)
    return events


@respx.mock
async def test_fast_path_streams_persists_and_scores(db, monkeypatch):
    mock_world()

    async def fake_verify(addr, resolver=None):
        return "verified" if addr.endswith("kcdental.com") else "invalid"
    monkeypatch.setattr(runner, "verify_email", fake_verify)

    sid = new_search()
    bus = EventBus()
    q = bus.subscribe(sid)
    pool = LLMPool(Settings(groq_api_key=None))  # AI disabled
    async with httpx.AsyncClient() as c:
        await runner.run_search(sid, bus=bus, pool=pool, client=c, reference_year=2026)
    events = await drain(q)
    types = [e["type"] for e in events]
    assert types[0] == "status" and types[-1] == "done" and types.count("lead") == 2
    done = events[-1]["data"]
    assert done == {"lead_count": 2, "llm_pending": 0}
    kc = next(e["data"] for e in events if e["type"] == "lead" and e["data"]["name"] == "KC Dental")
    assert kc["enrichment_status"] == "ok" and kc["llm_status"] == "disabled"
    assert kc["tier"] in ("A", "B") and kc["score"] >= 55
    assert any(c["kind"] == "email" and c["verification_status"] == "verified" for c in kc["contacts"])
    assert any(s["key"] == "founded_year" and s["value"] == "1998" and s["source"] == "regex" for s in kc["signals"])
    assert {f["factor"] for f in kc["factor_scores"]} == {"reachability", "establishment", "digital_gap", "buybox", "succession"}
    castle = next(e["data"] for e in events if e["type"] == "lead" and e["data"]["name"] == "Castle Dental")
    assert castle["enrichment_status"] == "no_website" and castle["llm_status"] == "not_needed"
    assert next(f for f in castle["factor_scores"] if f["factor"] == "digital_gap")["points"] == 20
    with session_scope() as s:
        row = s.get(Search, sid)
        assert row.status == "done" and row.lead_count == 2 and row.finished_at is not None
        assert len(s.exec(select(Lead).where(Lead.search_id == sid)).all()) == 2
        assert s.exec(select(FactorScoreRow)).all() and s.exec(select(Contact)).all() and s.exec(select(Signal)).all()


@respx.mock
async def test_llm_queue_refines_lead_and_fills_address(db, monkeypatch):
    mock_world()

    async def fake_verify(addr, resolver=None):
        return "verified"
    monkeypatch.setattr(runner, "verify_email", fake_verify)
    # Make regex leave a gap so the LLM gate opens: strip the owner sentence from the fixture.
    respx.get("https://www.kcdentalaustin.com/").mock(
        return_value=httpx.Response(200, html=HOME.replace("Dr. Karen Chen, owner, has served North Austin for 25 years.", "")))
    respx.get("https://www.kcdentalaustin.com/contact").mock(return_value=httpx.Response(200, html="<html><body><p>Call us.</p></body></html>"))
    llm_json = json.dumps({"display_name": "KC Dental", "founded_year": 1998, "owner_operated": True, "owner_name": None,
                           "family_owned": True, "is_chain": False, "hiring": False, "services": ["cleanings"],
                           "address": {"street": "12400 West Parmer Lane", "city": "Austin", "state": "TX", "postcode": "78727"},
                           "confidence": 0.9})
    fake = FakeGroq({"m1": [llm_json]})
    pool = LLMPool(Settings(groq_api_key="k", groq_models=["m1"]), groq_client=fake)
    sid = new_search()
    bus = EventBus()
    q = bus.subscribe(sid)
    async with httpx.AsyncClient() as c:
        await runner.run_search(sid, bus=bus, pool=pool, client=c, reference_year=2026)
    events = await drain(q)
    upd = [e["data"] for e in events if e["type"] == "lead_updated"]
    assert len(upd) == 1 and upd[0]["llm_status"] == "done"
    assert upd[0]["address"]["street"] == "12400 West Parmer Lane" and upd[0]["address_source"] == "llm"
    assert any(s["key"] == "services" and s["source"] == "llm" for s in upd[0]["signals"])
    assert events[-1]["data"]["llm_pending"] == 0
    with session_scope() as s:
        lead = s.exec(select(Lead).where(Lead.name == "KC Dental")).one()
        assert lead.street == "12400 West Parmer Lane" and lead.llm_status == "done"


@respx.mock
async def test_geocode_failure_marks_search_failed(db):
    respx.get("https://nominatim.openstreetmap.org/search").mock(return_value=httpx.Response(200, json=[]))
    sid = new_search()
    bus = EventBus()
    q = bus.subscribe(sid)
    async with httpx.AsyncClient() as c:
        await runner.run_search(sid, bus=bus, pool=LLMPool(Settings(groq_api_key=None)), client=c)
    events = await drain(q)
    assert events[-1]["type"] == "error"
    with session_scope() as s:
        assert s.get(Search, sid).status == "failed"
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/pipeline/test_runner.py -v` → FAIL (module missing)

- [ ] **Step 3: Write `api/app/pipeline/runner.py`**

```python
import asyncio
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta

import httpx
from pydantic import BaseModel
from sqlmodel import Session, delete, select

from app.config import get_settings
from app.db import session_scope
from app.llm.client import LLMPool
from app.llm.schemas import ExtractionResult
from app.models import Contact, EnrichmentCache, FactorScoreRow, Lead, Search, Signal, new_id, utcnow
from app.pipeline.crawl import PageBundle, PageText, crawl_site, quality
from app.pipeline.dedupe import Candidate, dedupe_and_flag
from app.pipeline.discover import OverpassUnavailable, fetch_places
from app.pipeline.extract_llm import SignalValue, build_llm_input, extract_with_llm, merge_signals, needs_llm
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


class LLMJob(BaseModel):
    lead_id: str
    bundle: PageBundle
    regex: RegexSignals


def _lead_from_candidate(search: Search, c: Candidate) -> Lead:
    t = c.place.tags
    street = t.get("addr:street")
    return Lead(id=new_id(), search_id=search.id, osm_type=c.place.osm_type, osm_id=c.place.osm_id, name=c.place.name,
                display_name=c.display, normalized_name=c.norm_name, lat=c.place.lat, lon=c.place.lon, street=street,
                housenumber=t.get("addr:housenumber"), city=t.get("addr:city"), state=t.get("addr:state"),
                postcode=t.get("addr:postcode"), country=t.get("addr:country") or search.country_code,
                address_source="osm" if street else "none", website=t.get("website") or t.get("contact:website"),
                normalized_domain=c.domain, osm_tags=t, is_chain_suspected=c.is_chain_suspected,
                enrichment_status="pending" if c.domain else "no_website")


def _osm_contacts(c: Candidate) -> list[RawContact]:
    out = []
    if c.phone_e164:
        out.append(RawContact(kind="phone", value=c.phone_e164))
    email = c.place.tags.get("email") or c.place.tags.get("contact:email")
    if email:
        out.append(RawContact(kind="email", value=email.lower()))
    return out


def _synthetic_bundle(domain: str, text: str) -> PageBundle:
    return PageBundle(domain=domain, fetched_at=utcnow(),
                      pages=[PageText(url=f"https://{domain}/", visible_text=text, text_quality=quality(text))])


async def _enrich(c: Candidate, client: httpx.AsyncClient, year: int, region: str) -> Enriched:
    if not c.domain or not (c.place.tags.get("website") or c.place.tags.get("contact:website")):
        return Enriched(status="no_website")
    settings = get_settings()
    with session_scope() as s:
        cached = s.get(EnrichmentCache, c.domain)
        if cached and cached.expires_at > utcnow():
            if cached.robots_blocked:
                return Enriched(status="blocked_by_robots")
            return Enriched(status="ok", regex=RegexSignals(**cached.regex_signals),
                            contacts=[RawContact(**x) for x in cached.contacts],
                            bundle=_synthetic_bundle(c.domain, cached.text_excerpt))
    url = c.place.tags.get("website") or c.place.tags.get("contact:website")
    res = await crawl_site(url, client)
    ttl = timedelta(days=settings.enrich_cache_ttl_days)
    if res.status == "blocked_by_robots":
        with session_scope() as s:
            s.merge(EnrichmentCache(domain=c.domain, robots_blocked=True, expires_at=utcnow() + ttl))
        return Enriched(status="blocked_by_robots")
    if res.status != "ok" or res.bundle is None:
        return Enriched(status="unreachable")
    regex = extract_signals(res.bundle, year)
    contacts = extract_contacts(res.bundle, region)
    with session_scope() as s:
        s.merge(EnrichmentCache(domain=c.domain, text_excerpt=build_llm_input(res.bundle),
                                regex_signals=regex.model_dump(), contacts=[x.model_dump() for x in contacts],
                                robots_blocked=False, expires_at=utcnow() + ttl))
    return Enriched(status="ok", regex=regex, contacts=contacts, bundle=res.bundle)


async def _verified_contacts(lead_id: str, raw: list[tuple[RawContact, str]], region: str) -> list[Contact]:
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
        out.append(Contact(lead_id=lead_id, kind=rc.kind, value=rc.value, normalized_value=norm, source=source,
                           verification_status=status))
    return out


def _apply_signals_and_score(s: Session, lead: Lead, contacts: list[Contact], values: list[SignalValue],
                             industry: Industry, weights: dict[str, float], year: int) -> None:
    s.execute(delete(Signal).where(Signal.lead_id == lead.id))
    s.execute(delete(FactorScoreRow).where(FactorScoreRow.lead_id == lead.id))
    rows = [Signal(lead_id=lead.id, key=v.key, value=v.value, source=v.source, confidence=v.confidence) for v in values]
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
        s.add(FactorScoreRow(lead_id=lead.id, factor=f.factor, points=f.points, max_points=f.max_points, reasons=f.reasons))


def _load_out(s: Session, lead_id: str):
    lead = s.get(Lead, lead_id)
    contacts = s.exec(select(Contact).where(Contact.lead_id == lead_id)).all()
    signals = s.exec(select(Signal).where(Signal.lead_id == lead_id)).all()
    factors = s.exec(select(FactorScoreRow).where(FactorScoreRow.lead_id == lead_id)).all()
    return lead, contacts, signals, factors


async def _process_candidate(search: Search, c: Candidate, industry: Industry, weights: dict[str, float], year: int,
                             client: httpx.AsyncClient, pool: LLMPool, bus: EventBus, sem: asyncio.Semaphore,
                             domain_locks: dict[str, asyncio.Lock]) -> LLMJob | None:
    lead = _lead_from_candidate(search, c)
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
        if not pool.enabled:
            lead.llm_status = "disabled"
        elif needs_llm(regex, bool(lead.street), enriched.bundle.pages[0].text_quality):
            lead.llm_status = "queued"
            job = LLMJob(lead_id=lead.id, bundle=enriched.bundle, regex=regex)
    with session_scope() as s:
        s.add(lead)
        for ct in contacts:
            s.add(ct)
        s.flush()
        _apply_signals_and_score(s, lead, contacts, values, industry, weights, year)
        s.flush()
        out = lead_to_out(*_load_out(s, lead.id))
    bus.publish(search.id, "lead", out.model_dump())
    return job


async def _run_llm_job(search: Search, job: LLMJob, industry: Industry, weights: dict[str, float], year: int,
                       pool: LLMPool, bus: EventBus) -> None:
    result, status = await extract_with_llm(pool, job.bundle, job.bundle.pages[0].title or "", search.country_code or "US", year)
    with session_scope() as s:
        lead, contacts, _, _ = _load_out(s, job.lead_id)
        lead.llm_status = "done" if status == "ok" else status
        values = merge_signals(job.regex, result if isinstance(result, ExtractionResult) else None)
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
    bus.publish(search.id, "lead_updated", {"lead_id": out["id"], "display_name": out["display_name"],
                                            "address": out["address"], "address_source": out["address_source"],
                                            "signals": out["signals"], "factor_scores": out["factor_scores"],
                                            "score": out["score"], "tier": out["tier"], "llm_status": out["llm_status"]})


def _fail(search_id: str, bus: EventBus, message: str) -> None:
    with session_scope() as s:
        row = s.get(Search, search_id)
        row.status, row.error, row.finished_at = "failed", message, utcnow()
        s.add(row)
    bus.publish(search_id, "error", {"message": message})
    bus.close(search_id)


async def run_search(search_id: str, *, bus: EventBus, pool: LLMPool, client: httpx.AsyncClient | None = None,
                     reference_year: int | None = None) -> None:
    year = reference_year or datetime.now(UTC).year
    own_client = client is None
    client = client or httpx.AsyncClient()
    try:
        with session_scope() as s:
            search = s.get(Search, search_id)
            industry = INDUSTRIES.get(search.industry_key)
        if industry is None:
            return _fail(search_id, bus, f"Unknown industry '{search.industry_key}'")
        weights = WEIGHT_PRESETS.get(search.weight_preset, WEIGHT_PRESETS["balanced"])
        bus.publish(search_id, "status", {"stage": "geocode", "message": f"Locating {search.location_query}…", "count": 0})
        with session_scope() as s:
            box = await geocode(search.location_query, client, s)
            if box is None:
                return _fail(search_id, bus, f"Could not find a place called '{search.location_query}'.")
            search = s.get(Search, search_id)
            search.geocoded_name, search.country_code = box.name, box.country_code
            search.bbox_s, search.bbox_w, search.bbox_n, search.bbox_e = box.s, box.w, box.n, box.e
            s.add(search)
        if box.shrunk:
            bus.publish(search_id, "status", {"stage": "geocode", "message": "Large area — searching the centre.", "count": 0})
        bus.publish(search_id, "status", {"stage": "discover", "message": f"Finding {industry.label.lower()} in {box.name.split(',')[0]}…", "count": 0})
        try:
            with session_scope() as s:
                places = await fetch_places(industry, box, search.limit, client, s)
        except OverpassUnavailable:
            return _fail(search_id, bus, "OpenStreetMap's Overpass API is unavailable right now. Please retry in a minute.")
        candidates = dedupe_and_flag(places, box.country_code or "US")[: search.limit]
        bus.publish(search_id, "status", {"stage": "enrich", "message": f"Checking {len(candidates)} businesses…", "count": len(candidates)})
        sem = asyncio.Semaphore(CRAWL_CONCURRENCY)
        locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        with session_scope() as s:
            search = s.get(Search, search_id)
        jobs = await asyncio.gather(*[_process_candidate(search, c, industry, weights, year, client, pool, bus, sem, locks)
                                      for c in candidates])
        queue = [j for j in jobs if j is not None][:LLM_PER_SEARCH_CAP]
        with session_scope() as s:
            row = s.get(Search, search_id)
            row.lead_count, row.llm_pending = len(candidates), len(queue)
            s.add(row)
        if queue:
            bus.publish(search_id, "status", {"stage": "refine", "message": f"Refining {len(queue)} leads with AI…", "count": len(queue)})

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
            await drain_task  # keep refining after the stream closed; updates persist for polling clients
    except Exception as e:  # noqa: BLE001
        log.exception("search.failed", extra={"search_id": search_id})
        _fail(search_id, bus, f"Search failed: {type(e).__name__}")
    finally:
        if own_client:
            await client.aclose()
```

Two SQLAlchemy notes: `_apply_signals_and_score` issues DELETE statements — use `s.execute(delete(...))`, not `s.exec(...)` (SQLModel's `exec` is for SELECT and warns otherwise). `from sqlmodel import delete` re-exports SQLAlchemy's `delete`.

- [ ] **Step 4: Run to verify pass** — `pytest tests/pipeline/test_runner.py -v` → 3 PASS. Common failures: (a) `FakeGroq` import path — the test imports the helper class from `tests/llm/test_client.py`; ensure `tests/__init__.py` and `tests/llm/__init__.py` exist so it is importable as `tests.llm.test_client`. (b) SQLite "database is locked" under `gather` — the `db` fixture's engine must use `check_same_thread=False` (Task 2) and each unit of work must be a short `session_scope()`; do not hold a session across an `await`. (c) If `lead_updated` never fires in test 2, print `needs_llm(...)` inputs: with the owner sentence removed, `owner_name` is `None` → gate opens.

- [ ] **Step 5: Lint, log time, commit**

Append: `| 2026-09-17 | 14 pipeline runner | 30 | — | measured |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(pipeline): streaming runner with enrichment cache, scoring and LLM refinement queue"
```

### Task 15: Routers — industries, searches (create, read, SSE stream), leads

**Spec:** §9.

**Files:**
- Create: `api/app/routers/industries.py`, `api/app/routers/searches.py`, `api/app/routers/leads.py`, `api/app/deps.py`, `api/tests/routers/__init__.py`, `api/tests/routers/test_searches.py`
- Modify: `api/app/main.py`

**Interfaces:**
- Produces (`deps.py`): `get_pool() -> LLMPool` (app-lifetime singleton built from settings), `get_http() -> httpx.AsyncClient` (app-lifetime), `get_bus() -> EventBus` (returns `services.events.bus`), and `start_search_task(search_id)` which schedules `run_search` with `asyncio.create_task` and keeps a reference in `app.state.tasks`.
- Routes: `GET /api/industries` → `{ industries: [{key,label}], presets: {name: weights} }`; `POST /api/searches` → 202 `{id}`; `GET /api/searches/{id}` → `SearchOut`; `GET /api/searches/{id}/leads` → `list[LeadOut]`; `GET /api/searches/{id}/stream` → SSE with `event:` names `status|lead|lead_updated|done|error`; `GET /api/leads/{id}` → `LeadOut`. 404 JSON `{error:{code:"not_found",message}}`; 422 on bad body (FastAPI default) is acceptable.

- [ ] **Step 1: Write the failing tests `api/tests/routers/test_searches.py`**

```python
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import deps
from app.db import session_scope
from app.main import create_app
from app.models import Lead, Search, new_id
from app.services.events import bus


@pytest.fixture
def client(db, monkeypatch):
    # Routers only *schedule* the pipeline; the runner is tested in test_runner.py.
    monkeypatch.setattr(deps, "start_search_task", MagicMock())
    return TestClient(create_app())


def test_industries_lists_keys_and_presets(client):
    r = client.get("/api/industries")
    assert r.status_code == 200
    body = r.json()
    assert {"key": "dentist", "label": "Dentists"} in body["industries"]
    assert set(body["presets"]) == {"balanced", "succession", "digital_upside", "reachability_first"}


def test_create_search_persists_and_schedules(client):
    r = client.post("/api/searches", json={"industry_key": "dentist", "location": "Austin, TX", "limit": 20})
    assert r.status_code == 202
    sid = r.json()["id"]
    with session_scope() as s:
        row = s.get(Search, sid)
        assert row.status == "running" and row.limit == 20 and row.weight_preset == "balanced"
    deps.start_search_task.assert_called_once_with(sid)
    got = client.get(f"/api/searches/{sid}").json()
    assert got["id"] == sid and got["llm_pending"] == 0


def test_create_search_rejects_unknown_industry_and_bad_limit(client):
    assert client.post("/api/searches", json={"industry_key": "nope", "location": "Austin"}).status_code == 400
    assert client.post("/api/searches", json={"industry_key": "dentist", "location": "Austin", "limit": 500}).status_code == 422


def test_stream_replays_events_then_ends(client):
    sid = new_id()
    with session_scope() as s:
        s.add(Search(id=sid, industry_key="dentist", location_query="Austin", limit=5))
    bus.publish(sid, "status", {"stage": "geocode", "message": "x", "count": 0})
    bus.publish(sid, "done", {"lead_count": 0, "llm_pending": 0})
    bus.close(sid)
    with client.stream("GET", f"/api/searches/{sid}/stream") as r:
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
        text = "".join(r.iter_text())
    assert "event: status" in text and 'event: done' in text and '"lead_count": 0' in text


def test_leads_endpoints_and_404s(client):
    sid = new_id()
    with session_scope() as s:
        s.add(Search(id=sid, industry_key="dentist", location_query="Austin", limit=5))
        s.add(Lead(id="L1", search_id=sid, osm_type="node", osm_id=1, name="KC Dental", display_name="KC Dental",
                   normalized_name="kc dental", lat=1.0, lon=2.0, osm_tags={}))
    leads = client.get(f"/api/searches/{sid}/leads").json()
    assert [x["id"] for x in leads] == ["L1"] and leads[0]["contacts"] == []
    assert client.get("/api/leads/L1").json()["name"] == "KC Dental"
    assert client.get("/api/leads/nope").status_code == 404
    assert client.get("/api/searches/nope").json() == {"error": {"code": "not_found", "message": "Search not found"}}
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/routers/test_searches.py -v` → FAIL (`app.deps` missing)

- [ ] **Step 3: Write `api/app/deps.py`**

```python
import asyncio

import httpx
from fastapi import Request

from app.config import get_settings
from app.llm.client import LLMPool
from app.pipeline.runner import run_search  # re-exported so tests can monkeypatch deps.run_search
from app.services.events import EventBus, bus

_pool: LLMPool | None = None
_http: httpx.AsyncClient | None = None
_tasks: set[asyncio.Task] = set()


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
    task = asyncio.create_task(run_search(search_id, bus=get_bus(), pool=get_pool(), client=get_http()))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def shutdown() -> None:
    global _pool, _http
    for t in list(_tasks):
        t.cancel()
    if _http is not None:
        await _http.aclose()
    _pool, _http = None, None


def reset_for_tests() -> None:
    global _pool, _http
    _pool, _http = None, None


def request_settings(request: Request):
    return get_settings()
```

- [ ] **Step 4: Write the routers**

`api/app/routers/industries.py`:
```python
from fastapi import APIRouter

from app.pipeline.industries import list_industries
from app.pipeline.score import WEIGHT_PRESETS

router = APIRouter(prefix="/api")


@router.get("/industries")
def industries() -> dict:
    return {"industries": list_industries(), "presets": WEIGHT_PRESETS}
```

`api/app/routers/searches.py`:
```python
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
    return HTTPException(status_code=404, detail={"code": "not_found", "message": f"{what} not found"})


@router.post("", status_code=202)
def create_search(body: SearchCreate, s: Session = Depends(get_session)) -> dict:
    if body.industry_key not in INDUSTRIES:
        raise HTTPException(status_code=400, detail={"code": "unknown_industry", "message": f"Unknown industry '{body.industry_key}'"})
    preset = body.weight_preset if body.weight_preset in WEIGHT_PRESETS else "balanced"
    row = Search(id=new_id(), industry_key=body.industry_key, location_query=body.location.strip(), limit=body.limit,
                 weight_preset=preset, nl_query=body.nl_query)
    s.add(row)
    s.commit()
    deps.start_search_task(row.id)
    return {"id": row.id}


@router.get("/{search_id}", response_model=SearchOut)
def get_search(search_id: str, s: Session = Depends(get_session)) -> SearchOut:
    row = s.get(Search, search_id)
    if not row:
        raise not_found("Search")
    return SearchOut.from_row(row)


def leads_for(s: Session, search_id: str) -> list[LeadOut]:
    leads = s.exec(select(Lead).where(Lead.search_id == search_id).order_by(Lead.score.desc().nulls_last())).all()
    ids = [x.id for x in leads]
    contacts = s.exec(select(Contact).where(Contact.lead_id.in_(ids))).all() if ids else []
    signals = s.exec(select(Signal).where(Signal.lead_id.in_(ids))).all() if ids else []
    factors = s.exec(select(FactorScoreRow).where(FactorScoreRow.lead_id.in_(ids))).all() if ids else []
    by = lambda rows: {i: [r for r in rows if r.lead_id == i] for i in ids}  # noqa: E731
    c, g, f = by(contacts), by(signals), by(factors)
    return [lead_to_out(x, c[x.id], g[x.id], f[x.id]) for x in leads]


@router.get("/{search_id}/leads", response_model=list[LeadOut])
def get_leads(search_id: str, s: Session = Depends(get_session)) -> list[LeadOut]:
    if not s.get(Search, search_id):
        raise not_found("Search")
    return leads_for(s, search_id)


@router.get("/{search_id}/stream")
async def stream(search_id: str, s: Session = Depends(get_session)):
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
```

`api/app/routers/leads.py`:
```python
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.models import Contact, FactorScoreRow, Lead, Signal
from app.routers.searches import not_found
from app.schemas import LeadOut, lead_to_out

router = APIRouter(prefix="/api/leads")


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: str, s: Session = Depends(get_session)) -> LeadOut:
    lead = s.get(Lead, lead_id)
    if not lead:
        raise not_found("Lead")
    return lead_to_out(lead,
                       s.exec(select(Contact).where(Contact.lead_id == lead_id)).all(),
                       s.exec(select(Signal).where(Signal.lead_id == lead_id)).all(),
                       s.exec(select(FactorScoreRow).where(FactorScoreRow.lead_id == lead_id)).all())
```

- [ ] **Step 5: Wire routers and the JSON error shape in `api/app/main.py`**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import deps
from app.config import get_settings
from app.routers import health, industries, leads, searches


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await deps.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    deps.reset_for_tests()
    app = FastAPI(title="SquatchScout API", version=settings.app_version, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=settings.frontend_origins,
                       allow_origin_regex=r"https://.*\.vercel\.app", allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "http_error", "message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content={"error": detail})

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):  # keeps CORS headers on 500s (spec §9)
        return JSONResponse(status_code=500, content={"error": {"code": "internal", "message": type(exc).__name__}})

    for r in (health, industries, searches, leads):
        app.include_router(r.router)
    return app


app = create_app()
```

- [ ] **Step 6: Run to verify pass** — `pytest tests/routers -v` → 5 PASS; then the full suite `pytest -q` → all PASS.

- [ ] **Step 7: Lint, log time, commit**

Append: `| 2026-09-17 | 15 search/lead routers + SSE | 25 | — | measured |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(api): search, lead and SSE stream endpoints with JSON error envelope"
```

### Task 16: Export — generic CSV and HubSpot-shaped CSV

**Spec:** §9 (export columns, attribution placement), §15.

**Files:**
- Create: `api/app/services/export.py`, `api/app/routers/export.py`, `api/tests/services/test_export.py`
- Modify: `api/app/main.py` (include router)

**Interfaces:**
- Produces: `to_csv(leads: list[LeadOut], weights: dict[str, float]) -> str`; `to_hubspot_csv(leads, weights) -> str`; `ATTRIBUTION = "data © OpenStreetMap contributors (ODbL) + business websites"`; `HUBSPOT_COLUMNS` (exact order below). Route: `GET /api/searches/{id}/export?format=csv|hubspot&ids=a,b&weights=25,20,20,20,15` → `text/csv` attachment `squatchscout-<search_id[:8]>-<format>.csv`. When `weights` is supplied the score column is **recomputed** with those weights (client re-rank must survive into the file); otherwise the stored score is used.

- [ ] **Step 1: Write the failing tests `api/tests/services/test_export.py`**

```python
import csv
import io

from app.schemas import AddressOut, ContactOut, FactorScoreOut, LeadOut, SignalOut
from app.services.export import HUBSPOT_COLUMNS, to_csv, to_hubspot_csv

W = {"reachability": 25, "establishment": 20, "digital_gap": 20, "buybox": 20, "succession": 15}


def lead(**over):
    base = dict(id="L1", name="KC DENTAL", display_name="KC Dental", lat=1.0, lon=2.0, website="https://kcdental.com",
                domain="kcdental.com", is_chain_suspected=False, enrichment_status="ok", llm_status="done", score=81.5, tier="A",
                address=AddressOut(street="12400 W Parmer Ln", housenumber=None, city="Austin", state="TX", postcode="78727", country="US"),
                address_source="llm",
                contacts=[ContactOut(kind="email", value="hello@kcdental.com", source="website", verification_status="verified"),
                          ContactOut(kind="phone", value="+15129180888", source="osm", verification_status="valid")],
                signals=[SignalOut(key="founded_year", value="1998", source="regex", confidence=1.0),
                         SignalOut(key="owner_operated", value="true", source="llm", confidence=0.9)],
                factor_scores=[FactorScoreOut(factor="reachability", points=25, max_points=25, reasons=["verified email (MX ok) +12"]),
                               FactorScoreOut(factor="establishment", points=20, max_points=20, reasons=["founded 1998"]),
                               FactorScoreOut(factor="digital_gap", points=10, max_points=20, reasons=["no chat widget +3"]),
                               FactorScoreOut(factor="buybox", points=20, max_points=20, reasons=["independent"]),
                               FactorScoreOut(factor="succession", points=15, max_points=15, reasons=["owner named"])])
    return LeadOut(**{**base, **over})


def test_generic_csv_has_comment_header_and_flat_columns():
    out = to_csv([lead()], W)
    first, rest = out.split("\n", 1)
    assert first.startswith("# SquatchScout export") and "weights R/E/D/B/S=25/20/20/20/15" in first and "OpenStreetMap" in first
    rows = list(csv.DictReader(io.StringIO(rest)))
    assert rows[0]["display_name"] == "KC Dental" and rows[0]["emails"] == "hello@kcdental.com"
    assert rows[0]["phones"] == "+15129180888" and rows[0]["founded_year"] == "1998" and rows[0]["tier"] == "A"


def test_hubspot_csv_columns_and_attribution_column():
    out = to_hubspot_csv([lead()], W)
    rows = list(csv.DictReader(io.StringIO(out)))
    assert list(rows[0].keys()) == HUBSPOT_COLUMNS
    r = rows[0]
    assert r["Company name"] == "KC Dental" and r["Company Domain Name"] == "kcdental.com" and r["Phone Number"] == "+15129180888"
    assert r["Street Address"] == "12400 W Parmer Ln" and r["State/Region"] == "TX" and r["Postal Code"] == "78727"
    assert "verified email" in r["Description"] and "; " in r["Description"]
    assert r["Verified Email"] == "hello@kcdental.com" and r["Founded Year"] == "1998" and r["Owner Operated"] == "true"
    assert "OpenStreetMap" in r["Data Sources"] and "25/20/20/20/15" in r["Data Sources"]
    assert not out.startswith("#")  # HubSpot's importer does not skip comment rows


def test_score_recomputed_from_weights():
    heavy = {"reachability": 100, "establishment": 0, "digital_gap": 0, "buybox": 0, "succession": 0}
    rows = list(csv.DictReader(io.StringIO(to_hubspot_csv([lead()], heavy))))
    assert rows[0]["SquatchScout Score"] == "100.0" and rows[0]["Tier"] == "A"
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/services/test_export.py -v` → FAIL (module missing)

- [ ] **Step 3: Write `api/app/services/export.py`**

```python
import csv
import io

from app.pipeline.score import FACTORS, FactorScore, tier, total
from app.schemas import LeadOut

ATTRIBUTION = "data © OpenStreetMap contributors (ODbL) + business websites"
HUBSPOT_COLUMNS = ["Company name", "Company Domain Name", "Phone Number", "Street Address", "City", "State/Region",
                   "Postal Code", "Country/Region", "Industry", "Website URL", "Description", "SquatchScout Score", "Tier",
                   "Verified Email", "Founded Year", "Owner Operated", "Chain Suspected", "Data Sources"]
CSV_COLUMNS = ["id", "display_name", "name", "score", "tier", "street", "city", "state", "postcode", "country",
               "address_source", "website", "domain", "emails", "phones", "socials", "is_chain_suspected",
               "enrichment_status", "llm_status", "founded_year", "owner_operated", "owner_name", "family_owned",
               "site_builder", "has_booking", "has_chat", "reasons"]


def _weights_str(w: dict[str, float]) -> str:
    return "/".join(str(int(w.get(f, 0))) for f in FACTORS)


def _rescore(lead: LeadOut, weights: dict[str, float] | None) -> tuple[float | None, str | None]:
    if not weights or not lead.factor_scores:
        return lead.score, lead.tier
    fs = [FactorScore(**f.model_dump()) for f in lead.factor_scores]
    t = total(fs, weights)
    return t, tier(t)


def _sig(lead: LeadOut, key: str) -> str:
    return next((s.value for s in lead.signals if s.key == key), "")


def _contacts(lead: LeadOut, kind: str, statuses: set[str] | None = None) -> list[str]:
    return [c.value for c in lead.contacts if c.kind == kind and (statuses is None or c.verification_status in statuses)]


def _reasons(lead: LeadOut) -> str:
    return "; ".join(r for f in lead.factor_scores for r in f.reasons)


def to_csv(leads: list[LeadOut], weights: dict[str, float] | None) -> str:
    buf = io.StringIO()
    buf.write(f"# SquatchScout export · weights R/E/D/B/S={_weights_str(weights or {})} · {ATTRIBUTION}\n")
    w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    w.writeheader()
    for lead in leads:
        score, tr = _rescore(lead, weights)
        a = lead.address
        w.writerow({"id": lead.id, "display_name": lead.display_name, "name": lead.name, "score": score, "tier": tr,
                    "street": a.street or "", "city": a.city or "", "state": a.state or "", "postcode": a.postcode or "",
                    "country": a.country or "", "address_source": lead.address_source, "website": lead.website or "",
                    "domain": lead.domain or "", "emails": " ".join(_contacts(lead, "email")),
                    "phones": " ".join(_contacts(lead, "phone")), "socials": " ".join(_contacts(lead, "social")),
                    "is_chain_suspected": lead.is_chain_suspected, "enrichment_status": lead.enrichment_status,
                    "llm_status": lead.llm_status, "founded_year": _sig(lead, "founded_year"),
                    "owner_operated": _sig(lead, "owner_operated"), "owner_name": _sig(lead, "owner_name"),
                    "family_owned": _sig(lead, "family_owned"), "site_builder": _sig(lead, "site_builder"),
                    "has_booking": _sig(lead, "has_booking"), "has_chat": _sig(lead, "has_chat"), "reasons": _reasons(lead)})
    return buf.getvalue()


def to_hubspot_csv(leads: list[LeadOut], weights: dict[str, float] | None, industry_label: str = "") -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=HUBSPOT_COLUMNS, lineterminator="\n")
    w.writeheader()
    sources = f"SquatchScout · weights R/E/D/B/S={_weights_str(weights or {})} · {ATTRIBUTION}"
    for lead in leads:
        score, tr = _rescore(lead, weights)
        a = lead.address
        phones = _contacts(lead, "phone")
        verified = _contacts(lead, "email", {"verified"})
        w.writerow({"Company name": lead.display_name, "Company Domain Name": lead.domain or "",
                    "Phone Number": phones[0] if phones else "", "Street Address": a.street or "", "City": a.city or "",
                    "State/Region": a.state or "", "Postal Code": a.postcode or "", "Country/Region": a.country or "",
                    "Industry": industry_label, "Website URL": lead.website or "", "Description": _reasons(lead),
                    "SquatchScout Score": score, "Tier": tr, "Verified Email": verified[0] if verified else "",
                    "Founded Year": _sig(lead, "founded_year"), "Owner Operated": _sig(lead, "owner_operated"),
                    "Chain Suspected": lead.is_chain_suspected, "Data Sources": sources})
    return buf.getvalue()
```

- [ ] **Step 4: Write `api/app/routers/export.py`** and include it in `main.py`'s router loop

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlmodel import Session

from app.db import get_session
from app.models import Search
from app.pipeline.industries import INDUSTRIES
from app.pipeline.score import FACTORS
from app.routers.searches import leads_for, not_found
from app.services.export import to_csv, to_hubspot_csv

router = APIRouter(prefix="/api/searches")


def parse_weights(raw: str | None) -> dict[str, float] | None:
    if not raw:
        return None
    parts = raw.split(",")
    if len(parts) != 5:
        raise HTTPException(status_code=400, detail={"code": "bad_weights", "message": "weights must be 5 comma-separated numbers"})
    try:
        return dict(zip(FACTORS, (float(p) for p in parts), strict=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "bad_weights", "message": "weights must be numeric"}) from e


@router.get("/{search_id}/export")
def export(search_id: str, format: str = Query("csv", pattern="^(csv|hubspot)$"), ids: str | None = None,
           weights: str | None = None, s: Session = Depends(get_session)) -> Response:
    search = s.get(Search, search_id)
    if not search:
        raise not_found("Search")
    leads = leads_for(s, search_id)
    if ids:
        wanted = set(ids.split(","))
        leads = [x for x in leads if x.id in wanted]
    w = parse_weights(weights)
    label = INDUSTRIES[search.industry_key].label if search.industry_key in INDUSTRIES else search.industry_key
    body = to_hubspot_csv(leads, w, label) if format == "hubspot" else to_csv(leads, w)
    fname = f"squatchscout-{search_id[:8]}-{format}.csv"
    return Response(content=body, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})
```

In `main.py`, import `export` and add it to the `for r in (...)` tuple.

- [ ] **Step 5: Add a router test** to `api/tests/routers/test_searches.py`:

```python
def test_export_endpoint_filters_ids_and_sets_attachment(client):
    sid = new_id()
    with session_scope() as s:
        s.add(Search(id=sid, industry_key="dentist", location_query="Austin", limit=5))
        for i in (1, 2):
            s.add(Lead(id=f"L{i}", search_id=sid, osm_type="node", osm_id=i, name=f"Biz {i}", display_name=f"Biz {i}",
                       normalized_name=f"biz {i}", lat=1.0, lon=2.0, osm_tags={}, score=50.0 + i, tier="C"))
    r = client.get(f"/api/searches/{sid}/export?format=hubspot&ids=L2")
    assert r.status_code == 200 and r.headers["content-disposition"].endswith('-hubspot.csv"')
    assert "Biz 2" in r.text and "Biz 1" not in r.text and r.text.startswith("Company name,")
    assert client.get(f"/api/searches/{sid}/export?format=xml").status_code == 422
    assert client.get(f"/api/searches/{sid}/export?weights=1,2").status_code == 400
```

- [ ] **Step 6: Run to verify pass** — `pytest tests/services/test_export.py tests/routers -v` → all PASS

- [ ] **Step 7: Lint, log time, commit**

Append: `| 2026-09-17 | 16 CSV + HubSpot export | 20 | — | measured |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(api): CSV and HubSpot-shaped exports with weights and attribution"
```

### Task 17: Intent and call-opener endpoints

**Spec:** §7.2 (uses 1 and 3), §9.

**Files:**
- Create: `api/app/routers/intent.py`, `api/tests/routers/test_intent.py`
- Modify: `api/app/routers/leads.py`, `api/app/main.py`

**Interfaces:**
- Routes: `POST /api/intent` `{text}` → `IntentResult` JSON, or 503 `{error:{code:"llm_disabled"}}`, or 503 `{error:{code:"llm_unavailable"}}` when the pool returns a skip/error status. `POST /api/leads/{id}/opener` → `{opener}` with the same 503 semantics. Both read the pool via `deps.get_pool()`.

- [ ] **Step 1: Write the failing tests `api/tests/routers/test_intent.py`**

```python
import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import deps
from app.config import Settings
from app.db import session_scope
from app.llm.client import LLMPool
from app.main import create_app
from app.models import Lead, Search, Signal, new_id
from tests.llm.test_client import FakeGroq


@pytest.fixture
def make_client(db, monkeypatch):
    monkeypatch.setattr(deps, "start_search_task", MagicMock())

    def _make(script: dict | None):
        if script is None:
            pool = LLMPool(Settings(groq_api_key=None))
        else:
            pool = LLMPool(Settings(groq_api_key="k", groq_models=["m1"]), groq_client=FakeGroq(script))
        monkeypatch.setattr(deps, "get_pool", lambda: pool)
        return TestClient(create_app())
    return _make


def test_intent_disabled_returns_503(make_client):
    c = make_client(None)
    r = c.post("/api/intent", json={"text": "dentists in Austin"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "llm_disabled"


def test_intent_returns_structured_result(make_client):
    c = make_client({"m1": [json.dumps({"industry_key": "dentist", "location": "Austin, TX", "limit": None,
                                        "weight_preset": "succession", "rationale": "retirement mentioned"})]})
    r = c.post("/api/intent", json={"text": "dentists in Austin whose owners are near retirement"})
    assert r.status_code == 200
    assert r.json() == {"industry_key": "dentist", "location": "Austin, TX", "limit": None,
                        "weight_preset": "succession", "rationale": "retirement mentioned"}


def test_intent_rejects_unknown_industry_from_model(make_client):
    c = make_client({"m1": [json.dumps({"industry_key": "spaceports", "location": "Austin", "limit": None,
                                        "weight_preset": "balanced", "rationale": ""})]})
    assert c.post("/api/intent", json={"text": "spaceports in Austin"}).json()["industry_key"] is None


def test_opener_grounded_in_signals(make_client):
    c = make_client({"m1": [json.dumps({"opener": "Hi Karen,\nline two\nline three"})]})
    sid, lid = new_id(), new_id()
    with session_scope() as s:
        s.add(Search(id=sid, industry_key="dentist", location_query="Austin", limit=5))
        s.add(Lead(id=lid, search_id=sid, osm_type="node", osm_id=1, name="KC Dental", display_name="KC Dental",
                   normalized_name="kc dental", lat=1.0, lon=2.0, osm_tags={}, city="Austin"))
        s.add(Signal(lead_id=lid, key="founded_year", value="1998", source="regex"))
    r = c.post(f"/api/leads/{lid}/opener")
    assert r.status_code == 200 and r.json()["opener"].count("\n") == 2
    assert c.post("/api/leads/nope/opener").status_code == 404
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/routers/test_intent.py -v` → FAIL (404 / module missing)

- [ ] **Step 3: Write `api/app/routers/intent.py`**

```python
from fastapi import APIRouter, HTTPException

from app import deps
from app.llm.prompts import intent_messages
from app.llm.schemas import INTENT_SCHEMA, PRESETS, IntentResult
from app.pipeline.industries import INDUSTRIES, list_industries
from app.schemas import IntentRequest

router = APIRouter(prefix="/api")


def llm_unavailable(status: str) -> HTTPException:
    code = "llm_disabled" if status == "disabled" else "llm_unavailable"
    return HTTPException(status_code=503, detail={"code": code, "message": f"AI features unavailable ({status})"})


@router.post("/intent", response_model=IntentResult)
async def intent(body: IntentRequest) -> IntentResult:
    pool = deps.get_pool()
    system, user = intent_messages(body.text, list_industries(), PRESETS)
    data, status = await pool.complete_json(schema_name="intent", schema=INTENT_SCHEMA, system=system, user=user,
                                            max_tokens=200)
    if status != "ok" or data is None:
        raise llm_unavailable(status)
    result = IntentResult(**data)
    if result.industry_key not in INDUSTRIES:
        result.industry_key = None
    if result.limit is not None:
        result.limit = max(5, min(100, result.limit))
    return result
```

- [ ] **Step 4: Add the opener route to `api/app/routers/leads.py`**

```python
from app import deps
from app.llm.prompts import opener_messages
from app.llm.schemas import OPENER_SCHEMA
from app.routers.intent import llm_unavailable

# … existing imports and get_lead …


@router.post("/{lead_id}/opener")
async def opener(lead_id: str, s: Session = Depends(get_session)) -> dict:
    lead = s.get(Lead, lead_id)
    if not lead:
        raise not_found("Lead")
    signals = {x.key: x.value for x in s.exec(select(Signal).where(Signal.lead_id == lead_id)).all()}
    search = s.get(Search, lead.search_id)
    industry = INDUSTRIES.get(search.industry_key) if search else None
    summary = {"business": lead.display_name, "city": lead.city, "industry": industry.label if industry else None,
               "facts": {k: signals[k] for k in ("founded_year", "owner_name", "family_owned", "services", "hiring",
                                                 "site_builder", "has_booking") if k in signals}}
    system, user = opener_messages(summary)
    data, status = await deps.get_pool().complete_json(schema_name="opener", schema=OPENER_SCHEMA, system=system,
                                                       user=user, max_tokens=160)
    if status != "ok" or not data or not data.get("opener"):
        raise llm_unavailable(status)
    return {"opener": data["opener"].strip()}
```

Add the needed imports at the top of `leads.py`: `from app.models import Contact, FactorScoreRow, Lead, Search, Signal` and `from app.pipeline.industries import INDUSTRIES`. Register `intent.router` in `main.py`'s router tuple.

- [ ] **Step 5: Run to verify pass** — `pytest tests/routers -v` → all PASS; full suite `pytest -q` green.

- [ ] **Step 6: Lint, log time, commit**

Append: `| 2026-09-17 | 17 intent + opener endpoints | 15 | — | measured |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api docs/time-log.md
git commit -m "feat(api): NL search intent and grounded call-opener endpoints"
```

### Task 18: Housekeeping task, JSON logging, Dockerfile, Compose, Caddyfile, `.env.example`

**Spec:** §8 (retention), §12.1–12.2, §13.

**Files:**
- Create: `api/app/services/housekeeping.py`, `api/app/logging_setup.py`, `api/tests/services/test_housekeeping.py`, `api/Dockerfile`, `api/.dockerignore`, `deploy/docker-compose.yml`, `deploy/Caddyfile`, `deploy/.env.example`, `deploy/docker-compose.local.yml`
- Modify: `api/app/main.py` (lifespan: logging + housekeeping task)

**Interfaces:**
- Produces: `purge_old(session, now, purge_after_days) -> dict[str, int]` (counts deleted per table); `async def run_daily(stop: asyncio.Event)` (runs `purge_old` at start and every 24 h); `configure_logging(level: str)` installing a JSON formatter on the root logger.

- [ ] **Step 1: Write the failing test `api/tests/services/test_housekeeping.py`**

```python
from datetime import timedelta

from sqlmodel import select

from app.db import session_scope
from app.models import Contact, EnrichmentCache, Lead, OverpassCache, Search, new_id, utcnow
from app.services.housekeeping import purge_old


def test_purge_removes_old_searches_children_and_expired_caches(db):
    now = utcnow()
    with session_scope() as s:
        old = Search(id=new_id(), industry_key="dentist", location_query="x", limit=5, created_at=now - timedelta(days=40))
        new = Search(id=new_id(), industry_key="dentist", location_query="y", limit=5, created_at=now - timedelta(days=2))
        s.add(old); s.add(new); s.flush()
        for sr in (old, new):
            lead = Lead(id=new_id(), search_id=sr.id, osm_type="node", osm_id=1, name="a", display_name="a",
                        normalized_name="a", lat=0, lon=0, osm_tags={})
            s.add(lead); s.flush()
            s.add(Contact(lead_id=lead.id, kind="phone", value="1", normalized_value="1", source="osm"))
        s.add(OverpassCache(key="k1", payload={}, expires_at=now - timedelta(hours=1)))
        s.add(OverpassCache(key="k2", payload={}, expires_at=now + timedelta(hours=1)))
        s.add(EnrichmentCache(domain="dead.com", expires_at=now - timedelta(days=1)))
    with session_scope() as s:
        counts = purge_old(s, now, purge_after_days=30)
    assert counts["searches"] == 1 and counts["leads"] == 1 and counts["contacts"] == 1
    assert counts["overpass_cache"] == 1 and counts["enrichment_cache"] == 1
    with session_scope() as s:
        assert [x.location_query for x in s.exec(select(Search)).all()] == ["y"]
        assert [x.key for x in s.exec(select(OverpassCache)).all()] == ["k2"]
```

- [ ] **Step 2: Write `api/app/services/housekeeping.py`**

```python
import asyncio
import logging
from datetime import datetime, timedelta

from sqlmodel import Session, col, delete, select

from app.config import get_settings
from app.db import session_scope
from app.models import Contact, EnrichmentCache, FactorScoreRow, Lead, OverpassCache, Search, Signal, utcnow

log = logging.getLogger(__name__)
DAY_S = 24 * 3600


def purge_old(session: Session, now: datetime, purge_after_days: int) -> dict[str, int]:
    cutoff = now - timedelta(days=purge_after_days)
    old_ids = [r for r in session.exec(select(Search.id).where(Search.created_at < cutoff)).all()]
    counts = {"searches": 0, "leads": 0, "contacts": 0, "signals": 0, "factor_scores": 0,
              "overpass_cache": 0, "enrichment_cache": 0}
    if old_ids:
        lead_ids = list(session.exec(select(Lead.id).where(col(Lead.search_id).in_(old_ids))).all())
        if lead_ids:
            for table, key in ((Contact, "contacts"), (Signal, "signals"), (FactorScoreRow, "factor_scores")):
                counts[key] = session.execute(delete(table).where(col(table.lead_id).in_(lead_ids))).rowcount
            counts["leads"] = session.execute(delete(Lead).where(col(Lead.id).in_(lead_ids))).rowcount
        counts["searches"] = session.execute(delete(Search).where(col(Search.id).in_(old_ids))).rowcount
    counts["overpass_cache"] = session.execute(delete(OverpassCache).where(OverpassCache.expires_at < now)).rowcount
    counts["enrichment_cache"] = session.execute(delete(EnrichmentCache).where(EnrichmentCache.expires_at < now)).rowcount
    return counts


async def run_daily(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            with session_scope() as s:
                counts = purge_old(s, utcnow(), get_settings().purge_after_days)
            log.info("housekeeping.purged", extra={"counts": counts})
        except Exception:  # noqa: BLE001
            log.exception("housekeeping.failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=DAY_S)
        except TimeoutError:
            continue
```

Run: `pytest tests/services/test_housekeeping.py -v` → PASS.

- [ ] **Step 3: Write `api/app/logging_setup.py`** and hook both into `main.py`'s lifespan

```python
import json
import logging
import sys
from datetime import UTC, datetime

_STD = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"ts": datetime.now(UTC).isoformat(timespec="milliseconds"), "level": record.levelname,
                   "logger": record.name, "msg": record.getMessage()}
        payload.update({k: v for k, v in record.__dict__.items() if k not in _STD and not k.startswith("_")})
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    for noisy in ("httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(noisy).setLevel("WARNING")
```

In `main.py`:
```python
import asyncio
from app.logging_setup import configure_logging
from app.services.housekeeping import run_daily


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(get_settings().log_level)
    stop = asyncio.Event()
    task = asyncio.create_task(run_daily(stop))
    yield
    stop.set()
    task.cancel()
    await deps.shutdown()
```

Run the whole suite: `pytest -q` → green (TestClient triggers lifespan; the purge runs against the test DB and finds nothing old).

- [ ] **Step 4: Write `api/Dockerfile` and `api/.dockerignore`**

```dockerfile
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION
WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
RUN pip install --upgrade pip && pip install .
RUN useradd -m appuser && chown -R appuser /app
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
```

`.dockerignore`:
```
.venv
__pycache__
*.pyc
.pytest_cache
.ruff_cache
tests
*.db
.env
```

- [ ] **Step 5: Write `deploy/docker-compose.yml`, `deploy/Caddyfile`, `deploy/.env.example`, `deploy/docker-compose.local.yml`**

`deploy/docker-compose.yml`:
```yaml
services:
  api:
    build:
      context: ../api
      args:
        APP_VERSION: ${APP_VERSION:-dev}
    env_file: .env
    environment:
      DATABASE_URL: postgresql+psycopg://squatch:${POSTGRES_PASSWORD}@postgres:5432/squatchscout
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "3" }

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: squatch
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: squatchscout
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U squatch -d squatchscout"]
      interval: 5s
      timeout: 3s
      retries: 10
    restart: unless-stopped

  caddy:
    image: caddy:2
    ports: ["80:80", "443:443"]
    environment:
      API_HOST: ${API_HOST}
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on: [api]
    restart: unless-stopped

volumes:
  pgdata:
  caddy_data:
  caddy_config:
```

`deploy/Caddyfile` (two lines, spec §12.1; `flush_interval -1` keeps SSE unbuffered):
```
{$API_HOST} {
	reverse_proxy api:8000 {
		flush_interval -1
	}
}
```

`deploy/.env.example` (every var from spec §11; copy to `.env` on the server):
```
# --- required ---
POSTGRES_PASSWORD=change-me
API_HOST=api.203.0.113.10.sslip.io
FRONTEND_ORIGINS=https://squatchscout.vercel.app,http://localhost:5173
PUBLIC_URL=https://squatchscout.vercel.app
# --- optional: AI features (Groq free tier) ---
GROQ_API_KEY=
GROQ_MODELS=openai/gpt-oss-20b,qwen/qwen3.8-27b
LLM_DAILY_SOFT_CAP=600
# --- crawler identity ---
CRAWLER_USER_AGENT=SquatchScoutBot/0.1 (+{public_url}/about)
CRAWLER_CONTACT=
# --- tuning (defaults shown) ---
OVERPASS_ENDPOINTS=https://overpass-api.de/api/interpreter,https://overpass.kumi.systems/api/interpreter
NOMINATIM_ENDPOINT=https://nominatim.openstreetmap.org
MAX_LEADS_PER_SEARCH=60
PURGE_AFTER_DAYS=30
ENRICH_CACHE_TTL_DAYS=7
OVERPASS_CACHE_TTL_HOURS=24
LOG_LEVEL=INFO
```

`deploy/docker-compose.local.yml` (override for laptop testing — no Caddy/TLS, API on localhost:8000):
```yaml
services:
  api:
    ports: ["8000:8000"]
  caddy:
    profiles: ["prod"]   # excluded locally
```

- [ ] **Step 6: Verify the stack locally**

```bash
cd deploy && cp .env.example .env
# edit .env: POSTGRES_PASSWORD=localdev, FRONTEND_ORIGINS=http://localhost:5173, leave GROQ_API_KEY empty
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
curl -s localhost:8000/healthz         # → {"status":"ok","db":"ok","llm_enabled":false,"version":"dev"}
curl -s localhost:8000/api/industries | head -c 200
docker compose -f docker-compose.yml -f docker-compose.local.yml logs api --tail 20   # JSON lines, alembic ran
docker compose -f docker-compose.yml -f docker-compose.local.yml down
```
Expected: health shows `"db":"ok"`; logs show `alembic` upgrade to `0001` and one `housekeeping.purged` line. Fix any Postgres-specific migration issue here (this is the first time the migration runs on Postgres — e.g. `JSONB` variant import).

- [ ] **Step 7: Lint, log time, commit (Phase A complete)**

Append: `| 2026-09-17 | 18 housekeeping, logging, Docker/Compose | 30 | — | measured — Phase A done |`

```bash
cd api && ruff check . && ruff format . && cd ..
git add api deploy docs/time-log.md
git commit -m "feat: housekeeping task, JSON logging, Docker image and Compose stack"
```

---

## Phase B — UI core

Working directory for all Phase B commands: `web/`. Node 24, pnpm.

### Task 19: Web scaffold — Vite + React + TS + Tailwind v4, config, types, API client, `rank.ts`

**Spec:** §10 (stack, tokens), §6 (client re-rank), §9 (payload types).

**Files:**
- Create: `web/` (scaffold), `web/vite.config.ts`, `web/vercel.json`, `web/src/styles/index.css`, `web/src/config.ts`, `web/src/api/types.ts`, `web/src/api/client.ts`, `web/src/lib/rank.ts`, `web/src/lib/rank.test.ts`
- Delete scaffold noise: `web/src/App.css`, `web/src/assets/react.svg`, `web/public/vite.svg`

**Interfaces:**
- Produces (`types.ts`): `Lead`, `Contact`, `Signal`, `FactorScore`, `Address`, `SearchRow`, `Industry`, `Weights` (`Record<Factor, number>`), `Factor` union, `IntentResult`, SSE payload types `StatusEvent`, `LeadUpdatedEvent`, `DoneEvent`, `ErrorEvent` — field names identical to the Python `LeadOut`/`SearchOut`/events.
- Produces (`client.ts`): `api.industries()`, `api.createSearch(body)`, `api.getSearch(id)`, `api.getLeads(id)`, `api.intent(text)`, `api.opener(leadId)`, `api.exportUrl(id, format, ids, weights)`, `api.health()`; every call throws `ApiError {status, code, message}` on non-2xx.
- Produces (`rank.ts`): `FACTORS`, `MAX_POINTS`, `WEIGHT_PRESETS`, `total(factorScores, weights): number`, `tier(total): "A"|"B"|"C"|"D"`, `normalizeWeights(w): Weights` — mirrors `api/app/pipeline/score.py` exactly.

- [ ] **Step 1: Scaffold and install**

From repo root:
```bash
pnpm create vite@latest web -- --template react-ts
cd web
pnpm add @tanstack/react-table lucide-react
pnpm add -D tailwindcss @tailwindcss/vite vitest @types/node
rm -f src/App.css src/assets/react.svg public/vite.svg
```

- [ ] **Step 2: `web/vite.config.ts`, `web/vercel.json`, tsconfig, package scripts**

`vite.config.ts`:
```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { "/api": "http://localhost:8000", "/healthz": "http://localhost:8000" } },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
```
Add `/// <reference types="vitest/config" />` as the first line so the `test` key type-checks.

`vercel.json`:
```json
{ "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }
```

In `tsconfig.app.json` `compilerOptions` ensure: `"resolveJsonModule": true`, `"strict": true`, `"noUnusedLocals": true`. In `package.json` scripts: `"dev": "vite"`, `"build": "tsc -b && vite build"`, `"preview": "vite preview"`, `"test": "vitest run"`, `"typecheck": "tsc -b --noEmit"`.

- [ ] **Step 3: `web/src/styles/index.css` — tokens (spec §10) and base**

```css
@import "tailwindcss";

@theme {
  --color-bg: #0b1220;
  --color-surface: #111a2e;
  --color-surface-2: #16223a;
  --color-border: #1f2a44;
  --color-text: #e6edf7;
  --color-muted: #8b9bb4;
  --color-accent: #14b8a6;
  --color-accent-2: #3b82f6;
  --color-tier-a: #34d399;
  --color-tier-b: #38bdf8;
  --color-tier-c: #fbbf24;
  --color-tier-d: #64748b;
  --font-sans: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}

html, body, #root { height: 100%; }
body { @apply bg-bg text-text font-sans antialiased; font-feature-settings: "tnum"; }
.btn-primary { @apply rounded-lg px-4 py-2 font-medium text-white shadow-sm disabled:opacity-50;
  background-image: linear-gradient(90deg, var(--color-accent), var(--color-accent-2)); }
.card { @apply rounded-xl border border-border bg-surface; }
.input { @apply w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-text placeholder:text-muted
  focus:outline-none focus:ring-2 focus:ring-accent; }
```

Replace `src/main.tsx` to import `./styles/index.css` (delete the `index.css` import the scaffold generated and remove `src/index.css`).

- [ ] **Step 4: `web/src/config.ts`**

```ts
const raw = (import.meta.env.VITE_API_URL as string | undefined) ?? "";
/** API origin. Empty string → same-origin (Vite dev proxy or a reverse proxy). Never throws at import. */
export const API_BASE = raw.replace(/\/+$/, "");
export const APP_NAME = "SquatchScout";
export const OSM_ATTRIBUTION = "© OpenStreetMap contributors";
```

- [ ] **Step 5: `web/src/api/types.ts`**

```ts
export type Factor = "reachability" | "establishment" | "digital_gap" | "buybox" | "succession";
export type Weights = Record<Factor, number>;
export type Tier = "A" | "B" | "C" | "D";

export interface Address { street: string | null; housenumber: string | null; city: string | null;
  state: string | null; postcode: string | null; country: string | null; }
export interface Contact { kind: "email" | "phone" | "social"; value: string; source: string; verification_status: string; }
export interface Signal { key: string; value: string; source: "osm" | "regex" | "llm"; confidence: number; }
export interface FactorScore { factor: Factor; points: number; max_points: number; reasons: string[]; }

export interface Lead {
  id: string; name: string; display_name: string; address: Address; address_source: string;
  lat: number; lon: number; website: string | null; domain: string | null; is_chain_suspected: boolean;
  enrichment_status: string; llm_status: string; score: number | null; tier: Tier | null;
  contacts: Contact[]; signals: Signal[]; factor_scores: FactorScore[];
}

export interface SearchRow { id: string; industry_key: string; location_query: string; geocoded_name: string | null;
  weight_preset: string; status: "running" | "done" | "failed"; lead_count: number; llm_pending: number;
  error: string | null; created_at: string; finished_at: string | null; }

export interface Industry { key: string; label: string; }
export interface IndustriesResponse { industries: Industry[]; presets: Record<string, Weights>; }
export interface SearchCreate { industry_key: string; location: string; limit: number; weight_preset?: string; nl_query?: string | null; }
export interface IntentResult { industry_key: string | null; location: string | null; limit: number | null;
  weight_preset: string; rationale: string; }

export interface StatusEvent { stage: string; message: string; count: number; }
export interface LeadUpdatedEvent { lead_id: string; display_name: string; address: Address; address_source: string;
  signals: Signal[]; factor_scores: FactorScore[]; score: number | null; tier: Tier | null; llm_status: string; }
export interface DoneEvent { lead_count: number; llm_pending: number; }
export interface ErrorEvent { message: string; }
export interface HealthResponse { status: string; db: string; llm_enabled: boolean; version: string; }
```

- [ ] **Step 6: `web/src/api/client.ts`**

```ts
import { API_BASE } from "../config";
import type { HealthResponse, IndustriesResponse, IntentResult, Lead, SearchCreate, SearchRow, Weights } from "./types";
import { FACTORS } from "../lib/rank";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) } });
  } catch {
    throw new ApiError(0, "network", "Cannot reach the API. It may be waking up — retry in a moment.");
  }
  if (!res.ok) {
    let code = "http_error", message = res.statusText;
    try { const body = await res.json(); code = body?.error?.code ?? code; message = body?.error?.message ?? message; } catch { /* keep defaults */ }
    throw new ApiError(res.status, code, message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>("/healthz"),
  industries: () => request<IndustriesResponse>("/api/industries"),
  createSearch: (body: SearchCreate) => request<{ id: string }>("/api/searches", { method: "POST", body: JSON.stringify(body) }),
  getSearch: (id: string) => request<SearchRow>(`/api/searches/${id}`),
  getLeads: (id: string) => request<Lead[]>(`/api/searches/${id}/leads`),
  intent: (text: string) => request<IntentResult>("/api/intent", { method: "POST", body: JSON.stringify({ text }) }),
  opener: (leadId: string) => request<{ opener: string }>(`/api/leads/${leadId}/opener`, { method: "POST" }),
  streamUrl: (id: string) => `${API_BASE}/api/searches/${id}/stream`,
  exportUrl: (id: string, format: "csv" | "hubspot", ids: string[], weights: Weights) => {
    const q = new URLSearchParams({ format, weights: FACTORS.map((f) => String(Math.round(weights[f]))).join(",") });
    if (ids.length) q.set("ids", ids.join(","));
    return `${API_BASE}/api/searches/${id}/export?${q.toString()}`;
  },
};
```

- [ ] **Step 7: Write the failing test `web/src/lib/rank.test.ts`**

```ts
import { describe, expect, it } from "vitest";
import gold from "../../../api/tests/fixtures/golden_scores.json";
import { FACTORS, MAX_POINTS, WEIGHT_PRESETS, normalizeWeights, tier, total } from "./rank";
import type { Factor, FactorScore } from "../api/types";

describe("rank.ts mirrors score.py", () => {
  for (const c of gold.cases) {
    it(`golden: ${c.name}`, () => {
      const fs: FactorScore[] = FACTORS.map((f) => ({
        factor: f, points: (c.expected_points as Record<Factor, number>)[f], max_points: MAX_POINTS[f], reasons: [] }));
      const t = total(fs, WEIGHT_PRESETS.balanced);
      expect(t).toBeCloseTo(c.expected_total_balanced, 1);
      expect(tier(t)).toBe(c.expected_tier);
    });
  }
  it("tier boundaries", () => {
    expect([tier(70), tier(69.9), tier(55), tier(54.9), tier(40), tier(39.9)]).toEqual(["A", "B", "B", "C", "C", "D"]);
  });
  it("weights normalise and a single factor can dominate", () => {
    const fs: FactorScore[] = FACTORS.map((f) => ({ factor: f, points: f === "reachability" ? 25 : 0, max_points: MAX_POINTS[f], reasons: [] }));
    expect(total(fs, normalizeWeights({ reachability: 7, establishment: 0, digital_gap: 0, buybox: 0, succession: 0 }))).toBe(100);
    expect(Object.values(WEIGHT_PRESETS.succession).reduce((a, b) => a + b, 0)).toBe(100);
  });
});
```

Run: `pnpm test` → FAIL (`./rank` not found).

- [ ] **Step 8: Write `web/src/lib/rank.ts`**

```ts
import type { Factor, FactorScore, Tier, Weights } from "../api/types";

export const FACTORS: Factor[] = ["reachability", "establishment", "digital_gap", "buybox", "succession"];
export const MAX_POINTS: Record<Factor, number> = { reachability: 25, establishment: 20, digital_gap: 20, buybox: 20, succession: 15 };
export const FACTOR_LABELS: Record<Factor, string> = {
  reachability: "Reachability", establishment: "Establishment", digital_gap: "Digital-maturity gap",
  buybox: "Buy-box fit", succession: "Succession signals" };
export const WEIGHT_PRESETS: Record<string, Weights> = {
  balanced: { reachability: 25, establishment: 20, digital_gap: 20, buybox: 20, succession: 15 },
  succession: { reachability: 25, establishment: 15, digital_gap: 10, buybox: 20, succession: 30 },
  digital_upside: { reachability: 25, establishment: 10, digital_gap: 35, buybox: 20, succession: 10 },
  reachability_first: { reachability: 40, establishment: 15, digital_gap: 15, buybox: 20, succession: 10 },
};

export function normalizeWeights(w: Weights): Weights {
  const sum = FACTORS.reduce((a, f) => a + (w[f] ?? 0), 0) || 1;
  return Object.fromEntries(FACTORS.map((f) => [f, ((w[f] ?? 0) / sum) * 100])) as Weights;
}

/** Same formula as api/app/pipeline/score.py::total — Σ (points/max) × weight share × 100, 1 dp. */
export function total(factorScores: FactorScore[], weights: Weights): number {
  const sum = FACTORS.reduce((a, f) => a + (weights[f] ?? 0), 0) || 1;
  const t = factorScores.reduce((acc, fs) => acc + (fs.points / fs.max_points) * ((weights[fs.factor] ?? 0) / sum) * 100, 0);
  return Math.round(t * 10) / 10;
}

export function tier(t: number): Tier { return t >= 70 ? "A" : t >= 55 ? "B" : t >= 40 ? "C" : "D"; }
```

- [ ] **Step 9: Verify** — `pnpm test` → all PASS; `pnpm typecheck` → clean; `pnpm build` → succeeds (App.tsx is still the scaffold — fine for now).

- [ ] **Step 10: Log time, commit**

Append: `| 2026-09-17 | 19 web scaffold, types, client, rank.ts | 20 | — | measured |`

```bash
git add web docs/time-log.md
git commit -m "feat(web): Vite/React/Tailwind scaffold, typed API client and shared re-rank math"
```

### Task 20: Session state — reducer, SSE wrapper, `useSearchSession` with post-done polling

**Spec:** §10 (state, late LLM updates), §9 (SSE events).

**Files:**
- Create: `web/src/state/searchReducer.ts`, `web/src/state/searchReducer.test.ts`, `web/src/api/sse.ts`, `web/src/state/useSearchSession.ts`

**Interfaces:**
- Produces (`searchReducer.ts`): `SessionState`, `SessionAction`, `initialState`, `reducer(state, action)`, selectors `rankedLeads(state): RankedLead[]` (`Lead & { computedScore: number; computedTier: Tier }`, sorted desc), `summary(state)` → `{ found, verifiedEmailPct, tiers: Record<Tier, number>, refined }`.
- Produces (`sse.ts`): `openStream(url, handlers: StreamHandlers): () => void` where `StreamHandlers = { onStatus, onLead, onLeadUpdated, onDone, onError }`.
- Produces (`useSearchSession.ts`): `useSearchSession()` → `{ state, start(body: SearchCreate), setWeights, applyPreset, toggleSelect, selectAll, clearSelection, reset }`.

- [ ] **Step 1: Write the failing test `web/src/state/searchReducer.test.ts`**

```ts
import { describe, expect, it } from "vitest";
import { initialState, rankedLeads, reducer, summary } from "./searchReducer";
import type { Lead } from "../api/types";
import { WEIGHT_PRESETS } from "../lib/rank";

const lead = (id: string, points: Record<string, number>, extra: Partial<Lead> = {}): Lead => ({
  id, name: id, display_name: id, address: { street: null, housenumber: null, city: null, state: null, postcode: null, country: null },
  address_source: "none", lat: 0, lon: 0, website: null, domain: null, is_chain_suspected: false, enrichment_status: "ok",
  llm_status: "not_needed", score: null, tier: null, contacts: [], signals: [],
  factor_scores: (["reachability", "establishment", "digital_gap", "buybox", "succession"] as const).map((f) => ({
    factor: f, points: points[f] ?? 0, max_points: { reachability: 25, establishment: 20, digital_gap: 20, buybox: 20, succession: 15 }[f], reasons: [] })),
  ...extra,
});

describe("searchReducer", () => {
  it("streams leads, ranks client-side and re-ranks on weight change", () => {
    let s = reducer(initialState, { type: "search_started", id: "s1" });
    s = reducer(s, { type: "lead", lead: lead("A", { reachability: 25 }) });
    s = reducer(s, { type: "lead", lead: lead("B", { succession: 15 }) });
    expect(s.phase).toBe("streaming");
    expect(rankedLeads(s).map((l) => l.id)).toEqual(["A", "B"]);           // balanced: 25 > 15
    s = reducer(s, { type: "set_weights", weights: WEIGHT_PRESETS.succession });
    expect(rankedLeads(s).map((l) => l.id)).toEqual(["B", "A"]);           // succession 30 > reachability 25
    expect(rankedLeads(s)[0].computedTier).toBe("D");
  });

  it("applies lead_updated in place and tracks refine phase", () => {
    let s = reducer(initialState, { type: "search_started", id: "s1" });
    s = reducer(s, { type: "lead", lead: lead("A", {}, { llm_status: "queued" }) });
    s = reducer(s, { type: "done", lead_count: 1, llm_pending: 1 });
    expect(s.phase).toBe("refining");
    s = reducer(s, { type: "lead_updated", update: { lead_id: "A", display_name: "A Co", address: lead("A", {}).address, address_source: "llm",
      signals: [{ key: "founded_year", value: "1990", source: "llm", confidence: 0.9 }], factor_scores: lead("A", { establishment: 20 }).factor_scores,
      score: 20, tier: "D", llm_status: "done" } });
    expect(s.leads.A.display_name).toBe("A Co");
    expect(s.leads.A.signals[0].value).toBe("1990");
    s = reducer(s, { type: "llm_pending", n: 0 });
    expect(s.phase).toBe("done");
    expect(summary(s).refined).toBe(1);
  });

  it("selection, summary and error", () => {
    let s = reducer(initialState, { type: "search_started", id: "s1" });
    s = reducer(s, { type: "lead", lead: lead("A", {}, { contacts: [{ kind: "email", value: "a@x.com", source: "website", verification_status: "verified" }] }) });
    s = reducer(s, { type: "lead", lead: lead("B", {}) });
    s = reducer(s, { type: "toggle_select", id: "A" });
    expect(s.selected).toEqual(["A"]);
    s = reducer(s, { type: "select_all" });
    expect(s.selected.sort()).toEqual(["A", "B"]);
    expect(summary(s).found).toBe(2);
    expect(summary(s).verifiedEmailPct).toBe(50);
    s = reducer(s, { type: "error", message: "boom" });
    expect(s.phase).toBe("error");
    expect(reducer(s, { type: "reset" })).toEqual(initialState);
  });
});
```

- [ ] **Step 2: Run to verify failure** — `pnpm test` → FAIL (module missing)

- [ ] **Step 3: Write `web/src/state/searchReducer.ts`**

```ts
import type { Lead, LeadUpdatedEvent, StatusEvent, Tier, Weights } from "../api/types";
import { WEIGHT_PRESETS, tier, total } from "../lib/rank";

export type Phase = "idle" | "starting" | "streaming" | "refining" | "done" | "error";

export interface SessionState {
  searchId: string | null;
  phase: Phase;
  status: StatusEvent | null;
  leads: Record<string, Lead>;
  order: string[];
  weights: Weights;
  preset: string;
  selected: string[];
  llmPending: number;
  error: string | null;
}

export type SessionAction =
  | { type: "search_starting" }
  | { type: "search_started"; id: string }
  | { type: "status"; status: StatusEvent }
  | { type: "lead"; lead: Lead }
  | { type: "lead_updated"; update: LeadUpdatedEvent }
  | { type: "leads_replaced"; leads: Lead[] }
  | { type: "done"; lead_count: number; llm_pending: number }
  | { type: "llm_pending"; n: number }
  | { type: "error"; message: string }
  | { type: "set_weights"; weights: Weights; preset?: string }
  | { type: "toggle_select"; id: string }
  | { type: "select_all" }
  | { type: "clear_selection" }
  | { type: "reset" };

export const initialState: SessionState = {
  searchId: null, phase: "idle", status: null, leads: {}, order: [], weights: WEIGHT_PRESETS.balanced,
  preset: "balanced", selected: [], llmPending: 0, error: null,
};

export function reducer(state: SessionState, action: SessionAction): SessionState {
  switch (action.type) {
    case "search_starting":
      return { ...initialState, weights: state.weights, preset: state.preset, phase: "starting" };
    case "search_started":
      return { ...state, searchId: action.id, phase: "streaming" };
    case "status":
      return { ...state, status: action.status };
    case "lead":
      return { ...state, leads: { ...state.leads, [action.lead.id]: action.lead },
        order: state.order.includes(action.lead.id) ? state.order : [...state.order, action.lead.id] };
    case "lead_updated": {
      const cur = state.leads[action.update.lead_id];
      if (!cur) return state;
      const { lead_id, ...rest } = action.update;
      return { ...state, leads: { ...state.leads, [lead_id]: { ...cur, ...rest } } };
    }
    case "leads_replaced": {
      const leads = Object.fromEntries(action.leads.map((l) => [l.id, l]));
      return { ...state, leads, order: action.leads.map((l) => l.id) };
    }
    case "done":
      return { ...state, llmPending: action.llm_pending, phase: action.llm_pending > 0 ? "refining" : "done" };
    case "llm_pending":
      return { ...state, llmPending: action.n, phase: action.n > 0 && state.phase !== "error" ? "refining" : state.phase === "refining" ? "done" : state.phase };
    case "error":
      return { ...state, phase: "error", error: action.message };
    case "set_weights":
      return { ...state, weights: action.weights, preset: action.preset ?? "custom" };
    case "toggle_select":
      return { ...state, selected: state.selected.includes(action.id) ? state.selected.filter((x) => x !== action.id) : [...state.selected, action.id] };
    case "select_all":
      return { ...state, selected: [...state.order] };
    case "clear_selection":
      return { ...state, selected: [] };
    case "reset":
      return initialState;
  }
}

export type RankedLead = Lead & { computedScore: number; computedTier: Tier };

export function rankedLeads(state: SessionState): RankedLead[] {
  return state.order
    .map((id) => state.leads[id])
    .filter(Boolean)
    .map((l) => { const s = total(l.factor_scores, state.weights); return { ...l, computedScore: s, computedTier: tier(s) }; })
    .sort((a, b) => b.computedScore - a.computedScore || a.display_name.localeCompare(b.display_name));
}

export function summary(state: SessionState) {
  const ranked = rankedLeads(state);
  const found = ranked.length;
  const withVerified = ranked.filter((l) => l.contacts.some((c) => c.kind === "email" && c.verification_status === "verified")).length;
  const tiers: Record<Tier, number> = { A: 0, B: 0, C: 0, D: 0 };
  for (const l of ranked) tiers[l.computedTier]++;
  const refined = ranked.filter((l) => l.llm_status === "done").length;
  return { found, verifiedEmailPct: found ? Math.round((withVerified / found) * 100) : 0, tiers, refined };
}
```

- [ ] **Step 4: Run to verify pass** — `pnpm test` → all PASS

- [ ] **Step 5: Write `web/src/api/sse.ts`**

```ts
import type { DoneEvent, ErrorEvent, Lead, LeadUpdatedEvent, StatusEvent } from "./types";

export interface StreamHandlers {
  onStatus: (e: StatusEvent) => void;
  onLead: (l: Lead) => void;
  onLeadUpdated: (u: LeadUpdatedEvent) => void;
  onDone: (d: DoneEvent) => void;
  onError: (e: ErrorEvent) => void;
}

/** Opens the SSE stream. Returns a disposer. Named events match the API's `event:` field exactly. */
export function openStream(url: string, h: StreamHandlers): () => void {
  const es = new EventSource(url);
  const parse = <T,>(ev: MessageEvent) => JSON.parse(ev.data as string) as T;
  es.addEventListener("status", (ev) => h.onStatus(parse<StatusEvent>(ev as MessageEvent)));
  es.addEventListener("lead", (ev) => h.onLead(parse<Lead>(ev as MessageEvent)));
  es.addEventListener("lead_updated", (ev) => h.onLeadUpdated(parse<LeadUpdatedEvent>(ev as MessageEvent)));
  es.addEventListener("done", (ev) => { h.onDone(parse<DoneEvent>(ev as MessageEvent)); es.close(); });
  es.addEventListener("error", (ev) => {
    // A named `error` event from the server carries JSON; a transport failure does not.
    const data = (ev as MessageEvent).data as string | undefined;
    if (data) { h.onError(parse<ErrorEvent>(ev as MessageEvent)); es.close(); return; }
    if (es.readyState === EventSource.CLOSED) h.onError({ message: "Connection to the API was lost." });
  });
  return () => es.close();
}
```

- [ ] **Step 6: Write `web/src/state/useSearchSession.ts`**

```ts
import { useCallback, useEffect, useReducer, useRef } from "react";
import { api, ApiError } from "../api/client";
import { openStream } from "../api/sse";
import type { SearchCreate, Weights } from "../api/types";
import { WEIGHT_PRESETS } from "../lib/rank";
import { initialState, reducer } from "./searchReducer";

const POLL_MS = 10_000;
const POLL_MAX_MS = 8 * 60_000;

export function useSearchSession() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const dispose = useRef<() => void>(() => {});

  useEffect(() => () => dispose.current(), []);

  // Spec §10 "Late LLM updates": after `done` with llm_pending > 0, poll the search row every 10 s and
  // refresh leads when the pending count drops. Stop at 0 or after 8 minutes.
  useEffect(() => {
    if (state.phase !== "refining" || !state.searchId) return;
    const id = state.searchId;
    const startedAt = Date.now();
    let lastPending = state.llmPending;
    const timer = setInterval(async () => {
      try {
        const row = await api.getSearch(id);
        if (row.llm_pending !== lastPending) {
          lastPending = row.llm_pending;
          dispatch({ type: "leads_replaced", leads: await api.getLeads(id) });
          dispatch({ type: "llm_pending", n: row.llm_pending });
        }
        if (row.llm_pending === 0 || Date.now() - startedAt > POLL_MAX_MS) { dispatch({ type: "llm_pending", n: 0 }); clearInterval(timer); }
      } catch { /* transient; try again next tick */ }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [state.phase, state.searchId]); // eslint-disable-line react-hooks/exhaustive-deps

  const start = useCallback(async (body: SearchCreate) => {
    dispose.current();
    dispatch({ type: "search_starting" });
    try {
      const { id } = await api.createSearch(body);
      dispatch({ type: "search_started", id });
      dispose.current = openStream(api.streamUrl(id), {
        onStatus: (status) => dispatch({ type: "status", status }),
        onLead: (lead) => dispatch({ type: "lead", lead }),
        onLeadUpdated: (update) => dispatch({ type: "lead_updated", update }),
        onDone: (d) => dispatch({ type: "done", lead_count: d.lead_count, llm_pending: d.llm_pending }),
        onError: (e) => dispatch({ type: "error", message: e.message }),
      });
    } catch (e) {
      dispatch({ type: "error", message: e instanceof ApiError ? e.message : "Could not start the search." });
    }
  }, []);

  const setWeights = useCallback((weights: Weights) => dispatch({ type: "set_weights", weights }), []);
  const applyPreset = useCallback((name: string) => {
    const w = WEIGHT_PRESETS[name];
    if (w) dispatch({ type: "set_weights", weights: w, preset: name });
  }, []);
  const toggleSelect = useCallback((id: string) => dispatch({ type: "toggle_select", id }), []);
  const selectAll = useCallback(() => dispatch({ type: "select_all" }), []);
  const clearSelection = useCallback(() => dispatch({ type: "clear_selection" }), []);
  const reset = useCallback(() => { dispose.current(); dispatch({ type: "reset" }); }, []);

  return { state, start, setWeights, applyPreset, toggleSelect, selectAll, clearSelection, reset };
}
```

- [ ] **Step 7: Verify** — `pnpm test && pnpm typecheck` → clean.

- [ ] **Step 8: Log time, commit**

Append: `| 2026-09-17 | 20 session reducer, SSE, polling hook | 20 | — | measured |`

```bash
git add web docs/time-log.md
git commit -m "feat(web): search session reducer with client re-rank, SSE stream and LLM polling"
```

### Task 21: App shell, `SearchBar` (NL + manual), `StatusStrip`, `EmptyState`, `AttributionFooter`

**Spec:** §3 (flow steps 1–2), §10 (layout, components, states, accessibility), §15 (attribution).

**Files:**
- Create: `web/src/components/SearchBar.tsx`, `web/src/components/StatusStrip.tsx`, `web/src/components/EmptyState.tsx`, `web/src/components/AttributionFooter.tsx`, `web/src/hooks/useBootstrap.ts`
- Modify: `web/src/App.tsx` (replace scaffold), `web/src/main.tsx`

**Interfaces:**
- `useBootstrap()` → `{ industries: Industry[], presets: Record<string, Weights>, llmEnabled: boolean, apiDown: boolean, version: string, retry() }` (fetches `/healthz` and `/api/industries` once; `apiDown` true on network error).
- `SearchBar` props: `{ industries, llmEnabled, busy: boolean, onSubmit(body: SearchCreate, preset?: string): void }`. Emits the preset chosen by the intent parser so the session can apply it.
- `StatusStrip` props: `{ phase, status, found: number, llmPending: number, error: string | null }`; renders with `role="status" aria-live="polite"`.
- `EmptyState` props: `{ onExample(text: string): void, llmEnabled }`.
- Until Task 22, `App.tsx` renders ranked leads as a plain list so the shell is testable end-to-end against the local API.

- [ ] **Step 1: `web/src/hooks/useBootstrap.ts`**

```ts
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { Industry, Weights } from "../api/types";

export function useBootstrap() {
  const [industries, setIndustries] = useState<Industry[]>([]);
  const [presets, setPresets] = useState<Record<string, Weights>>({});
  const [llmEnabled, setLlmEnabled] = useState(false);
  const [version, setVersion] = useState("");
  const [apiDown, setApiDown] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [h, i] = await Promise.all([api.health(), api.industries()]);
        if (cancelled) return;
        setLlmEnabled(h.llm_enabled); setVersion(h.version); setIndustries(i.industries); setPresets(i.presets); setApiDown(false);
      } catch { if (!cancelled) setApiDown(true); }
    })();
    return () => { cancelled = true; };
  }, [tick]);

  return { industries, presets, llmEnabled, version, apiDown, retry: useCallback(() => setTick((t) => t + 1), []) };
}
```

- [ ] **Step 2: `web/src/components/SearchBar.tsx`**

```tsx
import { Loader2, Search, Sparkles } from "lucide-react";
import { useState } from "react";
import { api, ApiError } from "../api/client";
import type { Industry, SearchCreate } from "../api/types";

interface Props { industries: Industry[]; llmEnabled: boolean; busy: boolean; onSubmit: (body: SearchCreate, preset?: string) => void; }

export function SearchBar({ industries, llmEnabled, busy, onSubmit }: Props) {
  const [nl, setNl] = useState("");
  const [industry, setIndustry] = useState("");
  const [location, setLocation] = useState("");
  const [limit, setLimit] = useState(60);
  const [preset, setPreset] = useState<string | undefined>();
  const [rationale, setRationale] = useState<string | null>(null);
  const [parsing, setParsing] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const canRun = industry !== "" && location.trim().length >= 2 && !busy;

  async function parseIntent() {
    if (!nl.trim()) return;
    setParsing(true); setErr(null); setRationale(null);
    try {
      const r = await api.intent(nl.trim());
      if (r.industry_key) setIndustry(r.industry_key);
      if (r.location) setLocation(r.location);
      if (r.limit) setLimit(r.limit);
      setPreset(r.weight_preset);
      setRationale(r.rationale || null);
      if (!r.industry_key) setErr("I couldn't map that to one of the supported industries — pick one below.");
    } catch (e) {
      setErr(e instanceof ApiError && e.code.startsWith("llm") ? "AI parsing is unavailable right now — fill the form instead." : "Could not parse that request.");
    } finally { setParsing(false); }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!canRun) return;
    onSubmit({ industry_key: industry, location: location.trim(), limit, weight_preset: preset, nl_query: nl.trim() || null }, preset);
  }

  return (
    <form onSubmit={submit} className="card p-4 flex flex-col gap-3" aria-label="Search for businesses">
      {llmEnabled && (
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Sparkles className="absolute left-3 top-2.5 size-4 text-accent" aria-hidden />
            <input className="input pl-9" value={nl} onChange={(e) => setNl(e.target.value)} placeholder='Describe it: "dentists in Austin, ideally owners near retirement"'
              aria-label="Describe your search in plain language" onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); void parseIntent(); } }} />
          </div>
          <button type="button" onClick={parseIntent} disabled={parsing || !nl.trim()} className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm hover:bg-border disabled:opacity-50">
            {parsing ? <Loader2 className="size-4 animate-spin" aria-label="Parsing" /> : "Fill form"}
          </button>
        </div>
      )}
      {rationale && <p className="text-xs text-muted"><span className="text-accent">AI:</span> {rationale}</p>}
      <div className="grid gap-2 sm:grid-cols-[1fr_1fr_110px_auto]">
        <select className="input" value={industry} onChange={(e) => setIndustry(e.target.value)} aria-label="Industry" required>
          <option value="">Industry…</option>
          {industries.map((i) => <option key={i.key} value={i.key}>{i.label}</option>)}
        </select>
        <input className="input" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="City, state or country" aria-label="Location" required minLength={2} />
        <input className="input" type="number" min={5} max={100} value={limit} onChange={(e) => setLimit(Number(e.target.value))} aria-label="Maximum results" />
        <button type="submit" disabled={!canRun} className="btn-primary flex items-center justify-center gap-2">
          {busy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Search className="size-4" aria-hidden />} Scout
        </button>
      </div>
      {err && <p className="text-sm text-tier-c" role="alert">{err}</p>}
    </form>
  );
}
```

- [ ] **Step 3: `StatusStrip.tsx`, `EmptyState.tsx`, `AttributionFooter.tsx`**

```tsx
// web/src/components/StatusStrip.tsx
import { Loader2 } from "lucide-react";
import type { StatusEvent } from "../api/types";
import type { Phase } from "../state/searchReducer";

interface Props { phase: Phase; status: StatusEvent | null; found: number; llmPending: number; error: string | null; }

export function StatusStrip({ phase, status, found, llmPending, error }: Props) {
  if (phase === "idle") return null;
  const text =
    phase === "error" ? error ?? "Something went wrong." :
    phase === "starting" ? "Starting…" :
    phase === "streaming" ? `${status?.message ?? "Working…"} ${found ? `· ${found} found` : ""}` :
    phase === "refining" ? `Refining ${llmPending} lead${llmPending === 1 ? "" : "s"} with AI… · ${found} found` :
    `Done · ${found} lead${found === 1 ? "" : "s"}`;
  const live = phase === "starting" || phase === "streaming" || phase === "refining";
  return (
    <div role="status" aria-live="polite" className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${phase === "error" ? "border-tier-c/50 text-tier-c" : "border-border text-muted"}`}>
      {live && <Loader2 className="size-4 animate-spin text-accent" aria-hidden />}
      <span>{text}</span>
    </div>
  );
}
```

```tsx
// web/src/components/EmptyState.tsx
import { Compass } from "lucide-react";

const EXAMPLES = ["Plumbers in Austin, TX with owners near retirement", "Independent pharmacies in Columbus, Ohio with outdated websites"];

export function EmptyState({ onExample, llmEnabled }: { onExample: (text: string) => void; llmEnabled: boolean }) {
  return (
    <div className="card flex flex-col items-center gap-3 px-6 py-14 text-center">
      <Compass className="size-8 text-accent" aria-hidden />
      <h2 className="text-lg font-semibold">Find the businesses worth calling first</h2>
      <p className="max-w-md text-sm text-muted">
        Pick an industry and a place. SquatchScout finds independent businesses on OpenStreetMap, checks their websites,
        verifies contacts, and ranks each one with a score you can read the reasons for.
      </p>
      {llmEnabled && (
        <div className="flex flex-wrap justify-center gap-2 pt-2">
          {EXAMPLES.map((t) => (
            <button key={t} type="button" onClick={() => onExample(t)} className="rounded-full border border-border bg-surface-2 px-3 py-1 text-xs text-muted hover:text-text">“{t}”</button>
          ))}
        </div>
      )}
    </div>
  );
}
```

```tsx
// web/src/components/AttributionFooter.tsx
import { OSM_ATTRIBUTION } from "../config";

export function AttributionFooter({ version, llmEnabled }: { version: string; llmEnabled: boolean }) {
  return (
    <footer className="mt-auto border-t border-border px-4 py-3 text-center text-xs text-muted">
      Business data {OSM_ATTRIBUTION} (ODbL) and the businesses' own websites, collected with robots.txt respected.
      {!llmEnabled && " AI features are off on this deployment."} {version && <span className="ml-2 opacity-60">v{version}</span>}
    </footer>
  );
}
```

- [ ] **Step 4: `web/src/App.tsx` (shell; results are a plain list until Task 22)**

```tsx
import { useState } from "react";
import { AttributionFooter } from "./components/AttributionFooter";
import { EmptyState } from "./components/EmptyState";
import { SearchBar } from "./components/SearchBar";
import { StatusStrip } from "./components/StatusStrip";
import { APP_NAME } from "./config";
import { useBootstrap } from "./hooks/useBootstrap";
import { rankedLeads } from "./state/searchReducer";
import { useSearchSession } from "./state/useSearchSession";

export default function App() {
  const boot = useBootstrap();
  const session = useSearchSession();
  const [exampleText, setExampleText] = useState<string | null>(null);
  const { state } = session;
  const ranked = rankedLeads(state);
  const busy = state.phase === "starting" || state.phase === "streaming";

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-baseline gap-2">
          <span className="bg-gradient-to-r from-accent to-accent-2 bg-clip-text text-lg font-bold text-transparent">{APP_NAME}</span>
          <span className="text-xs text-muted">ranked · verified · explained</span>
        </div>
        {boot.apiDown && (
          <button onClick={boot.retry} className="rounded-md border border-tier-c/50 px-2 py-1 text-xs text-tier-c">API unreachable — retry</button>
        )}
      </header>
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-4 px-4 py-6">
        <SearchBar key={exampleText ?? "bar"} industries={boot.industries} llmEnabled={boot.llmEnabled} busy={busy}
          onSubmit={(body, preset) => { if (preset) session.applyPreset(preset); void session.start(body); }} />
        <StatusStrip phase={state.phase} status={state.status} found={ranked.length} llmPending={state.llmPending} error={state.error} />
        {state.phase === "idle" ? (
          <EmptyState llmEnabled={boot.llmEnabled} onExample={(t) => setExampleText(t)} />
        ) : (
          <ol className="card divide-y divide-border">
            {ranked.map((l) => (
              <li key={l.id} className="flex justify-between px-4 py-2 text-sm"><span>{l.display_name}</span><span className="tabular-nums">{l.computedScore} · {l.computedTier}</span></li>
            ))}
          </ol>
        )}
      </main>
      <AttributionFooter version={boot.version} llmEnabled={boot.llmEnabled} />
    </div>
  );
}
```

The `key={exampleText}` trick remounts `SearchBar` when an example chip is clicked; make `SearchBar` accept an optional `initialText?: string` prop and pass `initialText={exampleText ?? undefined}` (use it as `useState(initialText ?? "")` for `nl`). Add that prop now.

- [ ] **Step 5: Verify against the local API**

Terminal 1 (from `api/`): `uvicorn app.main:app --reload --port 8000` (with `DATABASE_URL=sqlite:///./dev.db`; run `alembic upgrade head` first).
Terminal 2 (from `web/`): `pnpm dev` → open http://localhost:5173.
Expected: header + empty state render; choose **Dentists** / `Austin, TX` / 20 → **Scout** → status strip animates, list fills with names and scores within ~10–30 s, ends "Done · N leads". With `GROQ_API_KEY` unset the NL box is hidden and the footer says AI features are off. `pnpm typecheck && pnpm build` → clean.

- [ ] **Step 6: Log time, commit**

Append: `| 2026-09-17 | 21 app shell, search bar, status, empty state | 25 | — | measured |`

```bash
git add web docs/time-log.md
git commit -m "feat(web): app shell with NL/manual search bar, live status strip and attribution"
```

### Task 22: `ResultsTable`, `ScoreChip`, badges, selection

**Spec:** §3 (steps 2–3), §10 (ResultsTable, ScoreChip, states, accessibility).

**Files:**
- Create: `web/src/components/ScoreChip.tsx`, `web/src/components/ResultsTable.tsx`
- Modify: `web/src/App.tsx` (replace the plain list)

**Interfaces:**
- `ScoreChip` props: `{ score: number; tier: Tier; size?: "sm" | "md" }`.
- `ResultsTable` props: `{ leads: RankedLead[]; selected: string[]; onToggle(id): void; onSelectAll(): void; onClear(): void; onOpen(id): void; phase: Phase }`. Sortable by score (default), name, city. Row click → `onOpen`; checkbox click does not open. Shows "no results" and "partial failure" states (leads with `enrichment_status` of `unreachable`/`blocked_by_robots` are shown with a badge, never hidden).

- [ ] **Step 1: `web/src/components/ScoreChip.tsx`**

```tsx
import type { Tier } from "../api/types";

const TIER_CLASS: Record<Tier, string> = {
  A: "bg-tier-a/15 text-tier-a border-tier-a/40", B: "bg-tier-b/15 text-tier-b border-tier-b/40",
  C: "bg-tier-c/15 text-tier-c border-tier-c/40", D: "bg-tier-d/15 text-tier-d border-tier-d/40" };

export function ScoreChip({ score, tier, size = "md" }: { score: number; tier: Tier; size?: "sm" | "md" }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border font-semibold tabular-nums ${TIER_CLASS[tier]} ${size === "sm" ? "px-1.5 py-0.5 text-xs" : "px-2 py-1 text-sm"}`}
      aria-label={`Score ${score}, tier ${tier}`}>
      <span>{tier}</span><span className="opacity-80">{score.toFixed(0)}</span>
    </span>
  );
}
```

- [ ] **Step 2: `web/src/components/ResultsTable.tsx`**

```tsx
import { flexRender, getCoreRowModel, getSortedRowModel, useReactTable, type ColumnDef, type SortingState } from "@tanstack/react-table";
import { ArrowDown, ArrowUp, Building2, MailCheck, ShieldAlert, Sparkles, Store } from "lucide-react";
import { useMemo, useState } from "react";
import type { RankedLead, Phase } from "../state/searchReducer";
import { ScoreChip } from "./ScoreChip";

interface Props { leads: RankedLead[]; selected: string[]; onToggle: (id: string) => void; onSelectAll: () => void;
  onClear: () => void; onOpen: (id: string) => void; phase: Phase; }

function Badge({ children, title, tone = "muted" }: { children: React.ReactNode; title: string; tone?: "muted" | "good" | "warn" }) {
  const cls = tone === "good" ? "text-tier-a border-tier-a/40" : tone === "warn" ? "text-tier-c border-tier-c/40" : "text-muted border-border";
  return <span title={title} className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[11px] ${cls}`}>{children}</span>;
}

export function ResultsTable({ leads, selected, onToggle, onSelectAll, onClear, onOpen, phase }: Props) {
  const [sorting, setSorting] = useState<SortingState>([{ id: "computedScore", desc: true }]);
  const allSelected = leads.length > 0 && selected.length === leads.length;

  const columns = useMemo<ColumnDef<RankedLead>[]>(() => [
    { id: "select", enableSorting: false, size: 36,
      header: () => <input type="checkbox" aria-label="Select all" checked={allSelected} onChange={() => (allSelected ? onClear() : onSelectAll())} />,
      cell: ({ row }) => <input type="checkbox" aria-label={`Select ${row.original.display_name}`} checked={selected.includes(row.original.id)}
        onChange={() => onToggle(row.original.id)} onClick={(e) => e.stopPropagation()} /> },
    { id: "computedScore", accessorKey: "computedScore", header: "Score", size: 90,
      cell: ({ row }) => <ScoreChip score={row.original.computedScore} tier={row.original.computedTier} size="sm" /> },
    { id: "name", accessorKey: "display_name", header: "Business",
      cell: ({ row }) => {
        const l = row.original;
        const verified = l.contacts.some((c) => c.kind === "email" && c.verification_status === "verified");
        return (
          <div className="flex flex-col gap-1">
            <span className="font-medium">{l.display_name}</span>
            <div className="flex flex-wrap gap-1">
              {verified && <Badge tone="good" title="Email verified via MX lookup"><MailCheck className="size-3" /> verified email</Badge>}
              {l.is_chain_suspected ? <Badge tone="warn" title="Name repeats or has a brand tag"><Building2 className="size-3" /> chain?</Badge>
                : <Badge title="Single independent listing"><Store className="size-3" /> independent</Badge>}
              {l.enrichment_status === "no_website" && <Badge title="No website found — high digital upside">no website</Badge>}
              {(l.enrichment_status === "unreachable" || l.enrichment_status === "blocked_by_robots") &&
                <Badge tone="warn" title={l.enrichment_status === "blocked_by_robots" ? "Site's robots.txt disallows crawling" : "Website did not respond"}><ShieldAlert className="size-3" /> {l.enrichment_status.replace("_", " ")}</Badge>}
              {l.llm_status === "done" && <Badge title="Refined with AI extraction"><Sparkles className="size-3 text-accent" /> refined</Badge>}
            </div>
          </div>
        );
      } },
    { id: "city", accessorFn: (l) => l.address.city ?? "", header: "City", size: 140, cell: ({ getValue }) => <span className="text-muted">{getValue<string>() || "—"}</span> },
    { id: "phone", enableSorting: false, header: "Phone", size: 150,
      cell: ({ row }) => { const p = row.original.contacts.find((c) => c.kind === "phone"); return <span className="tabular-nums text-muted">{p?.value ?? "—"}</span>; } },
  ], [selected, allSelected, onToggle, onSelectAll, onClear]);

  const table = useReactTable({ data: leads, columns, state: { sorting }, onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel() });

  if (leads.length === 0 && (phase === "done" || phase === "error")) {
    return <div className="card px-6 py-10 text-center text-sm text-muted">No businesses found here. Try a larger city, a nearby one, or a different industry.</div>;
  }

  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-xs uppercase tracking-wide text-muted">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} className="border-b border-border">
              {hg.headers.map((h) => (
                <th key={h.id} style={{ width: h.getSize() }} className="px-3 py-2 font-medium">
                  {h.column.getCanSort() ? (
                    <button type="button" onClick={h.column.getToggleSortingHandler()} className="inline-flex items-center gap-1 hover:text-text">
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      {h.column.getIsSorted() === "asc" ? <ArrowUp className="size-3" /> : h.column.getIsSorted() === "desc" ? <ArrowDown className="size-3" /> : null}
                    </button>
                  ) : flexRender(h.column.columnDef.header, h.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} tabIndex={0} onClick={() => onOpen(row.original.id)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen(row.original.id); } }}
              className="cursor-pointer border-b border-border/60 hover:bg-surface-2 focus:bg-surface-2 focus:outline-none">
              {row.getVisibleCells().map((cell) => <td key={cell.id} className="px-3 py-2 align-top">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      {phase === "streaming" && <div className="px-3 py-2 text-xs text-muted">More results arriving…</div>}
    </div>
  );
}
```

- [ ] **Step 3: Replace the plain list in `App.tsx`**

```tsx
import { ResultsTable } from "./components/ResultsTable";
// …
const [openId, setOpenId] = useState<string | null>(null);
// … in place of the <ol>:
<ResultsTable leads={ranked} selected={state.selected} onToggle={session.toggleSelect} onSelectAll={session.selectAll}
  onClear={session.clearSelection} onOpen={setOpenId} phase={state.phase} />
```
`openId` is consumed by the drawer in Task 24; until then it is unused — add `void openId;` after the state line so `noUnusedLocals` passes, and remove it in Task 24.

- [ ] **Step 4: Verify** — `pnpm typecheck && pnpm build`; run a search in the browser: rows appear as they stream, sort by clicking headers, checkboxes select without opening, Enter on a focused row calls `onOpen` (log it for now). Narrow the window under 640 px — the table scrolls inside its card; the page does not scroll horizontally.

- [ ] **Step 5: Log time, commit**

Append: `| 2026-09-17 | 22 results table + badges | 25 | — | measured |`

```bash
git add web docs/time-log.md
git commit -m "feat(web): sortable results table with score chips, badges and selection"
```

### Task 23: `WeightsPanel` with presets, `SummaryTiles`, right rail layout

**Spec:** §3 (step 3), §6 (presets), §10 (WeightsPanel, SummaryTiles, layout with 320 px rail, < 1024 px collapse).

**Files:**
- Create: `web/src/components/WeightsPanel.tsx`, `web/src/components/SummaryTiles.tsx`
- Modify: `web/src/App.tsx` (two-column grid; rail becomes a bottom section on small screens)

**Interfaces:**
- `WeightsPanel` props: `{ weights: Weights; preset: string; onChange(weights): void; onPreset(name): void }`. Sliders are native `<input type="range" min=0 max=50>` per factor with visible label + value; a "Reset" applies `balanced`.
- `SummaryTiles` props: `{ found: number; verifiedEmailPct: number; tiers: Record<Tier, number>; refined: number; llmEnabled: boolean }`.

- [ ] **Step 1: `web/src/components/WeightsPanel.tsx`**

```tsx
import { RotateCcw } from "lucide-react";
import type { Factor, Weights } from "../api/types";
import { FACTORS, FACTOR_LABELS, WEIGHT_PRESETS } from "../lib/rank";

const PRESET_LABELS: Record<string, string> = { balanced: "Balanced", succession: "Succession", digital_upside: "Digital upside", reachability_first: "Reachability" };

export function WeightsPanel({ weights, preset, onChange, onPreset }: { weights: Weights; preset: string; onChange: (w: Weights) => void; onPreset: (n: string) => void }) {
  const sum = FACTORS.reduce((a, f) => a + weights[f], 0) || 1;
  return (
    <section className="card p-4 flex flex-col gap-3" aria-labelledby="weights-h">
      <div className="flex items-center justify-between">
        <h2 id="weights-h" className="text-sm font-semibold">Ranking weights</h2>
        <button type="button" onClick={() => onPreset("balanced")} className="inline-flex items-center gap-1 text-xs text-muted hover:text-text" aria-label="Reset weights"><RotateCcw className="size-3" /> reset</button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {Object.keys(WEIGHT_PRESETS).map((name) => (
          <button key={name} type="button" onClick={() => onPreset(name)} aria-pressed={preset === name}
            className={`rounded-full border px-2.5 py-1 text-xs ${preset === name ? "border-accent text-accent" : "border-border text-muted hover:text-text"}`}>{PRESET_LABELS[name]}</button>
        ))}
      </div>
      {FACTORS.map((f: Factor) => (
        <label key={f} className="flex flex-col gap-1 text-xs">
          <span className="flex justify-between"><span>{FACTOR_LABELS[f]}</span><span className="tabular-nums text-muted">{Math.round((weights[f] / sum) * 100)}%</span></span>
          <input type="range" min={0} max={50} step={1} value={weights[f]} aria-label={`${FACTOR_LABELS[f]} weight`}
            onChange={(e) => onChange({ ...weights, [f]: Number(e.target.value) })} className="accent-[var(--color-accent)]" />
        </label>
      ))}
      <p className="text-[11px] text-muted">Re-ranks instantly in your browser — no requests sent. Exports carry these weights.</p>
    </section>
  );
}
```

- [ ] **Step 2: `web/src/components/SummaryTiles.tsx`**

```tsx
import type { Tier } from "../api/types";

const ORDER: Tier[] = ["A", "B", "C", "D"];
const BAR: Record<Tier, string> = { A: "bg-tier-a", B: "bg-tier-b", C: "bg-tier-c", D: "bg-tier-d" };

export function SummaryTiles({ found, verifiedEmailPct, tiers, refined, llmEnabled }: { found: number; verifiedEmailPct: number; tiers: Record<Tier, number>; refined: number; llmEnabled: boolean }) {
  const total = Math.max(found, 1);
  return (
    <section className="card p-4 grid grid-cols-2 gap-3" aria-label="Search summary">
      <div><div className="text-2xl font-semibold tabular-nums">{found}</div><div className="text-xs text-muted">leads found</div></div>
      <div><div className="text-2xl font-semibold tabular-nums">{verifiedEmailPct}%</div><div className="text-xs text-muted">with verified email</div></div>
      <div className="col-span-2">
        <div className="mb-1 flex justify-between text-xs text-muted"><span>Tier mix</span><span className="tabular-nums">{ORDER.map((t) => `${t}${tiers[t]}`).join(" · ")}</span></div>
        <div className="flex h-2 overflow-hidden rounded-full bg-surface-2" role="img" aria-label={`Tiers: ${ORDER.map((t) => `${tiers[t]} ${t}`).join(", ")}`}>
          {ORDER.map((t) => <div key={t} className={BAR[t]} style={{ width: `${(tiers[t] / total) * 100}%` }} />)}
        </div>
      </div>
      {llmEnabled && <div className="col-span-2 text-xs text-muted"><span className="text-accent">{refined}</span> refined with AI</div>}
    </section>
  );
}
```

- [ ] **Step 3: Two-column layout in `App.tsx`**

Replace the `<ResultsTable …/>` placement with:
```tsx
import { SummaryTiles } from "./components/SummaryTiles";
import { WeightsPanel } from "./components/WeightsPanel";
import { summary } from "./state/searchReducer";
// …
const sum = summary(state);
// …
<div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
  <section className="min-w-0">
    <ResultsTable … />
  </section>
  <aside className="flex flex-col gap-4">
    <WeightsPanel weights={state.weights} preset={state.preset} onChange={session.setWeights} onPreset={session.applyPreset} />
    <SummaryTiles found={sum.found} verifiedEmailPct={sum.verifiedEmailPct} tiers={sum.tiers} refined={sum.refined} llmEnabled={boot.llmEnabled} />
  </aside>
</div>
```
Below 1024 px the grid collapses to one column with the rail under the table (spec's "bottom sheet" simplified to a stacked section — acceptable).

- [ ] **Step 4: Verify** — `pnpm typecheck && pnpm build`; in the browser drag a slider: order changes with no network request (check DevTools Network); preset chips highlight; tiles update as rows stream.

- [ ] **Step 5: Log time, commit**

Append: `| 2026-09-17 | 23 weights panel + summary tiles | 20 | — | measured |`

```bash
git add web docs/time-log.md
git commit -m "feat(web): live weight sliders with presets and summary tiles"
```

### Task 24: `LeadDrawer` — factor bars with reasons, contacts, signals with provenance, opener

**Spec:** §3 (step 5), §10 (LeadDrawer, focus trap, keyboard), §7.2 (opener).

**Files:**
- Create: `web/src/components/LeadDrawer.tsx`, `web/src/components/FactorBars.tsx`, `web/src/components/ContactsList.tsx`, `web/src/components/SignalsList.tsx`, `web/src/components/OpenerPanel.tsx`
- Modify: `web/src/App.tsx`

**Interfaces:**
- `LeadDrawer` props: `{ lead: RankedLead | null; weights: Weights; llmEnabled: boolean; onClose(): void }`. Renders nothing when `lead` is null. `Escape` closes; focus moves into the drawer on open and returns on close; `role="dialog" aria-modal="true"`.
- `FactorBars` props: `{ factorScores: FactorScore[]; weights: Weights }` — each bar shows points/max, its weight share, and the reasons list.
- `ContactsList` props: `{ contacts: Contact[] }`; `SignalsList` props: `{ signals: Signal[] }` (source pill: osm / regex / llm with confidence); `OpenerPanel` props: `{ leadId: string }`.

- [ ] **Step 1: `FactorBars.tsx`, `ContactsList.tsx`, `SignalsList.tsx`**

```tsx
// web/src/components/FactorBars.tsx
import type { FactorScore, Weights } from "../api/types";
import { FACTOR_LABELS, FACTORS } from "../lib/rank";

export function FactorBars({ factorScores, weights }: { factorScores: FactorScore[]; weights: Weights }) {
  const sum = FACTORS.reduce((a, f) => a + (weights[f] ?? 0), 0) || 1;
  return (
    <ul className="flex flex-col gap-3">
      {factorScores.map((fs) => (
        <li key={fs.factor}>
          <div className="flex justify-between text-xs">
            <span className="font-medium">{FACTOR_LABELS[fs.factor]}</span>
            <span className="tabular-nums text-muted">{fs.points}/{fs.max_points} · weight {Math.round(((weights[fs.factor] ?? 0) / sum) * 100)}%</span>
          </div>
          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2" role="progressbar" aria-valuenow={fs.points} aria-valuemax={fs.max_points} aria-label={FACTOR_LABELS[fs.factor]}>
            <div className="h-full bg-gradient-to-r from-accent to-accent-2" style={{ width: `${(fs.points / fs.max_points) * 100}%` }} />
          </div>
          <ul className="mt-1 list-disc pl-4 text-xs text-muted">{fs.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
        </li>
      ))}
    </ul>
  );
}
```

```tsx
// web/src/components/ContactsList.tsx
import { Globe, Mail, Phone } from "lucide-react";
import type { Contact } from "../api/types";

const STATUS: Record<string, string> = { verified: "text-tier-a", valid: "text-tier-a", unverified: "text-tier-c", possible: "text-tier-c", invalid: "text-tier-d line-through", not_checked: "text-muted" };

export function ContactsList({ contacts }: { contacts: Contact[] }) {
  if (!contacts.length) return <p className="text-xs text-muted">No contacts found on OSM or the website.</p>;
  return (
    <ul className="flex flex-col gap-1.5 text-sm">
      {contacts.map((c) => (
        <li key={`${c.kind}:${c.value}`} className="flex items-center gap-2">
          {c.kind === "email" ? <Mail className="size-4 text-muted" /> : c.kind === "phone" ? <Phone className="size-4 text-muted" /> : <Globe className="size-4 text-muted" />}
          {c.kind === "social" ? <a href={c.value} target="_blank" rel="noreferrer" className="truncate text-accent-2 hover:underline">{c.value}</a>
            : <a href={c.kind === "email" ? `mailto:${c.value}` : `tel:${c.value}`} className="truncate hover:underline">{c.value}</a>}
          <span className={`ml-auto text-[11px] ${STATUS[c.verification_status] ?? "text-muted"}`}>{c.verification_status.replace("_", " ")}</span>
          <span className="text-[11px] text-muted">{c.source}</span>
        </li>
      ))}
    </ul>
  );
}
```

```tsx
// web/src/components/SignalsList.tsx
import type { Signal } from "../api/types";

const PILL: Record<Signal["source"], string> = { osm: "border-border text-muted", regex: "border-accent-2/40 text-accent-2", llm: "border-accent/40 text-accent" };
const HIDE = new Set(["contact_page_found"]);

export function SignalsList({ signals }: { signals: Signal[] }) {
  const rows = signals.filter((s) => !HIDE.has(s.key)).sort((a, b) => a.key.localeCompare(b.key));
  if (!rows.length) return <p className="text-xs text-muted">No website signals (no site, blocked, or unreachable).</p>;
  return (
    <dl className="grid grid-cols-[auto_1fr_auto] gap-x-3 gap-y-1 text-xs">
      {rows.map((s) => (
        <div key={s.key} className="contents">
          <dt className="text-muted">{s.key.replaceAll("_", " ")}</dt>
          <dd className="truncate">{s.value}</dd>
          <dd><span className={`rounded border px-1 py-px text-[10px] ${PILL[s.source]}`} title={s.source === "llm" ? `AI extraction, confidence ${s.confidence.toFixed(2)}` : s.source}>{s.source}</span></dd>
        </div>
      ))}
    </dl>
  );
}
```

- [ ] **Step 2: `OpenerPanel.tsx`**

```tsx
import { Copy, Loader2, Sparkles } from "lucide-react";
import { useState } from "react";
import { api, ApiError } from "../api/client";

export function OpenerPanel({ leadId }: { leadId: string }) {
  const [text, setText] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function draft() {
    setBusy(true); setErr(null);
    try { setText((await api.opener(leadId)).opener); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not draft an opener."); }
    finally { setBusy(false); }
  }

  return (
    <div className="flex flex-col gap-2">
      {text ? (
        <>
          <pre className="whitespace-pre-wrap rounded-lg border border-border bg-surface-2 p-3 text-sm">{text}</pre>
          <div className="flex gap-2">
            <button type="button" onClick={() => navigator.clipboard?.writeText(text)} className="inline-flex items-center gap-1 text-xs text-muted hover:text-text"><Copy className="size-3" /> copy</button>
            <button type="button" onClick={draft} disabled={busy} className="text-xs text-muted hover:text-text">redraft</button>
          </div>
        </>
      ) : (
        <button type="button" onClick={draft} disabled={busy} className="inline-flex items-center gap-2 rounded-lg border border-accent/40 px-3 py-2 text-sm text-accent hover:bg-accent/10 disabled:opacity-50">
          {busy ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />} Draft call opener
        </button>
      )}
      {err && <p className="text-xs text-tier-c" role="alert">{err}</p>}
      <p className="text-[11px] text-muted">Grounded only in the signals above — nothing invented.</p>
    </div>
  );
}
```

- [ ] **Step 3: `LeadDrawer.tsx`**

```tsx
import { ExternalLink, X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { Weights } from "../api/types";
import type { RankedLead } from "../state/searchReducer";
import { ContactsList } from "./ContactsList";
import { FactorBars } from "./FactorBars";
import { OpenerPanel } from "./OpenerPanel";
import { ScoreChip } from "./ScoreChip";
import { SignalsList } from "./SignalsList";

export function LeadDrawer({ lead, weights, llmEnabled, onClose }: { lead: RankedLead | null; weights: Weights; llmEnabled: boolean; onClose: () => void }) {
  const panel = useRef<HTMLDivElement>(null);
  const restore = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!lead) return;
    restore.current = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab" && panel.current) {  // simple focus trap
        const els = panel.current.querySelectorAll<HTMLElement>('button, a[href], input, [tabindex]:not([tabindex="-1"])');
        if (!els.length) return;
        const first = els[0], last = els[els.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); restore.current?.focus(); };
  }, [lead, onClose]);

  if (!lead) return null;
  const a = lead.address;
  const addr = [a.street && `${a.housenumber ?? ""} ${a.street}`.trim(), a.city, a.state, a.postcode].filter(Boolean).join(", ");
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/50" onClick={onClose}>
      <div ref={panel} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="drawer-title" onClick={(e) => e.stopPropagation()}
        className="flex h-full w-full max-w-lg flex-col gap-5 overflow-y-auto border-l border-border bg-surface p-5 shadow-2xl focus:outline-none">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="drawer-title" className="text-lg font-semibold">{lead.display_name}</h2>
            <p className="text-xs text-muted">{addr || "Address unknown"}{lead.address_source !== "osm" && lead.address_source !== "none" && <span> · address via {lead.address_source}</span>}</p>
            {lead.website && <a href={lead.website} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 text-xs text-accent-2 hover:underline">{lead.domain} <ExternalLink className="size-3" /></a>}
          </div>
          <div className="flex items-center gap-2">
            <ScoreChip score={lead.computedScore} tier={lead.computedTier} />
            <button type="button" onClick={onClose} aria-label="Close" className="rounded-md p-1 text-muted hover:bg-surface-2 hover:text-text"><X className="size-5" /></button>
          </div>
        </div>
        <section aria-labelledby="why-h"><h3 id="why-h" className="mb-2 text-sm font-semibold">Why this score</h3><FactorBars factorScores={lead.factor_scores} weights={weights} /></section>
        <section aria-labelledby="contacts-h"><h3 id="contacts-h" className="mb-2 text-sm font-semibold">Contacts</h3><ContactsList contacts={lead.contacts} /></section>
        <section aria-labelledby="signals-h"><h3 id="signals-h" className="mb-2 text-sm font-semibold">Signals</h3><SignalsList signals={lead.signals} /></section>
        {llmEnabled && <section aria-labelledby="opener-h"><h3 id="opener-h" className="mb-2 text-sm font-semibold">Outreach</h3><OpenerPanel leadId={lead.id} /></section>}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Mount in `App.tsx`** — remove `void openId;`, add:
```tsx
import { LeadDrawer } from "./components/LeadDrawer";
// …
<LeadDrawer lead={ranked.find((l) => l.id === openId) ?? null} weights={state.weights} llmEnabled={boot.llmEnabled} onClose={() => setOpenId(null)} />
```
Because the drawer reads from `ranked`, a `lead_updated` event refreshes an open drawer in place.

- [ ] **Step 5: Verify** — `pnpm typecheck && pnpm build`; click a row → drawer with five bars and reasons, contacts with statuses, signals with source pills; `Esc` closes and focus returns to the row; with `GROQ_API_KEY` set locally, "Draft call opener" returns three lines.

- [ ] **Step 6: Log time, commit**

Append: `| 2026-09-17 | 24 lead drawer | 25 | — | measured |`

```bash
git add web docs/time-log.md
git commit -m "feat(web): lead drawer with explainable factor bars, contacts, signal provenance and opener"
```

### Task 25: `ExportMenu`, `ErrorToast`, API-down banner, responsive pass, production build

**Spec:** §3 (step 6), §9 (export), §10 (states, responsive).

**Files:**
- Create: `web/src/components/ExportMenu.tsx`, `web/src/components/ErrorToast.tsx`
- Modify: `web/src/App.tsx`

**Interfaces:**
- `ExportMenu` props: `{ searchId: string | null; selected: string[]; total: number; weights: Weights; disabled: boolean }` — two buttons (CSV, HubSpot CSV) that open `api.exportUrl(...)` via a hidden anchor download; label shows "all N" or "N selected".
- `ErrorToast` props: `{ message: string | null; onDismiss(): void }`; auto-dismisses after 8 s.

- [ ] **Step 1: `ExportMenu.tsx` and `ErrorToast.tsx`**

```tsx
// web/src/components/ExportMenu.tsx
import { Download } from "lucide-react";
import { api } from "../api/client";
import type { Weights } from "../api/types";

export function ExportMenu({ searchId, selected, total, weights, disabled }: { searchId: string | null; selected: string[]; total: number; weights: Weights; disabled: boolean }) {
  const scope = selected.length ? `${selected.length} selected` : `all ${total}`;
  function download(format: "csv" | "hubspot") {
    if (!searchId) return;
    const a = document.createElement("a");
    a.href = api.exportUrl(searchId, format, selected, weights);
    a.download = "";
    document.body.appendChild(a); a.click(); a.remove();
  }
  return (
    <section className="card p-4 flex flex-col gap-2" aria-labelledby="export-h">
      <h2 id="export-h" className="text-sm font-semibold">Export {total > 0 && <span className="text-muted">({scope})</span>}</h2>
      <div className="grid grid-cols-2 gap-2">
        <button type="button" disabled={disabled || !total} onClick={() => download("csv")} className="inline-flex items-center justify-center gap-1 rounded-lg border border-border px-3 py-2 text-sm hover:bg-surface-2 disabled:opacity-50"><Download className="size-4" /> CSV</button>
        <button type="button" disabled={disabled || !total} onClick={() => download("hubspot")} className="btn-primary inline-flex items-center justify-center gap-1 text-sm"><Download className="size-4" /> HubSpot CSV</button>
      </div>
      <p className="text-[11px] text-muted">HubSpot file uses its company-import column names. Both carry your current weights and OSM attribution.</p>
    </section>
  );
}
```

```tsx
// web/src/components/ErrorToast.tsx
import { X } from "lucide-react";
import { useEffect } from "react";

export function ErrorToast({ message, onDismiss }: { message: string | null; onDismiss: () => void }) {
  useEffect(() => { if (!message) return; const t = setTimeout(onDismiss, 8000); return () => clearTimeout(t); }, [message, onDismiss]);
  if (!message) return null;
  return (
    <div role="alert" className="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-lg border border-tier-c/50 bg-surface px-4 py-2 text-sm shadow-xl">
      <span>{message}</span>
      <button type="button" onClick={onDismiss} aria-label="Dismiss" className="text-muted hover:text-text"><X className="size-4" /></button>
    </div>
  );
}
```

- [ ] **Step 2: Wire into `App.tsx`** — add `<ExportMenu searchId={state.searchId} selected={state.selected} total={ranked.length} weights={state.weights} disabled={state.phase === "starting"} />` as the third rail card, and `<ErrorToast message={toast} onDismiss={() => setToast(null)} />` driven by a `useEffect` that sets `toast` whenever `state.error` changes to a non-null value (the status strip also shows it; the toast is for errors that happen while the strip is scrolled away). Add the API-down banner under the header when `boot.apiDown`: a full-width `bg-tier-c/10 text-tier-c` bar with the text "The API is not reachable. If it was just deployed it may still be starting — retry in a few seconds." and a retry button.

- [ ] **Step 3: Responsive and accessibility pass** (spec §10, Global "Responsive")

Check at 400 px, 768 px, 1280 px in DevTools: no horizontal page scroll (table scrolls inside its card); search form stacks; rail stacks under the table below 1024 px; drawer is full-width on phones (`max-w-lg` is already fluid). Tab through: search form → table rows → rail controls; drawer traps focus; every icon-only button has `aria-label`. Contrast: `text-muted` (#8b9bb4) on `bg` (#0b1220) is ≈ 6.9:1 — fine.

- [ ] **Step 4: Production build check** — `pnpm test && pnpm typecheck && pnpm build`; `pnpm preview` and load the built app against the local API with `VITE_API_URL=http://localhost:8000 pnpm build` to confirm the env-driven base works cross-origin (CORS from `FRONTEND_ORIGINS` must include `http://localhost:4173`).

- [ ] **Step 5: Log time, commit (Phase B complete)**

Append: `| 2026-09-17 | 25 export, toast, responsive, build | 20 | — | measured — Phase B done |`

```bash
git add web docs/time-log.md
git commit -m "feat(web): export menu, error toast, API-down banner and responsive polish"
```

---

## Phase C — Ship

### Task 26: Server scripts, CI workflow, deploy workflow with rollback, GitHub repo

**Spec:** §12.1 (`setup-ubuntu.sh`), §12.3 (CI/CD, `deploy.sh`), Global constraints (LF).

**Files:**
- Create: `deploy/setup-ubuntu.sh`, `deploy/deploy.sh`, `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`, `LICENSE` (MIT), `README.md` (stub — full README is Task 30)

**Interfaces:**
- `deploy.sh <git-sha|branch>` exits 0 only if `/healthz` reports the new version; otherwise restores the previous SHA and exits 1. Reads `API_HOST` from `deploy/.env`. Writes `deploy/.deployed_sha`.
- GitHub secrets consumed by `deploy.yml`: `DEPLOY_HOST` (public IP or hostname), `DEPLOY_USER` (`ubuntu`), `DEPLOY_SSH_KEY` (private key, PEM).

- [ ] **Step 1: `deploy/setup-ubuntu.sh`** (run once on a fresh Ubuntu 24.04 VM as `ubuntu`)

```bash
#!/usr/bin/env bash
# One-time server setup for SquatchScout on Ubuntu 24.04. Idempotent. Usage:
#   curl -fsSL https://raw.githubusercontent.com/<owner>/squatchscout/main/deploy/setup-ubuntu.sh | bash -s -- https://github.com/<owner>/squatchscout.git
set -euo pipefail
REPO_URL="${1:?usage: setup-ubuntu.sh <repo-url>}"
APP_DIR=/opt/squatchscout

echo "→ packages"
sudo apt-get update -qq
sudo apt-get install -y -qq ca-certificates curl git gnupg

if ! command -v docker >/dev/null; then
  echo "→ docker engine + compose plugin (official repo)"
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo usermod -aG docker "$USER"
fi

if ! swapon --show | grep -q swapfile; then
  echo "→ 1 GB swap (image builds on a 1 GB instance can OOM without it)"
  sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

if [ ! -d "$APP_DIR/.git" ]; then
  echo "→ clone"
  sudo mkdir -p "$APP_DIR" && sudo chown "$USER":"$USER" "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR/deploy"
[ -f .env ] || { cp .env.example .env; echo "!! edit $APP_DIR/deploy/.env (POSTGRES_PASSWORD, API_HOST, FRONTEND_ORIGINS, PUBLIC_URL, GROQ_API_KEY) then run: ./deploy.sh main"; }
echo "✓ setup complete. Log out/in once so the docker group applies."
```

- [ ] **Step 2: `deploy/deploy.sh`**

```bash
#!/usr/bin/env bash
# Deploy a git ref (sha or branch) and roll back automatically if /healthz does not come up.
# Usage: ./deploy.sh <sha|branch>        (run from anywhere; operates on /opt/squatchscout)
set -euo pipefail
TARGET="${1:?usage: deploy.sh <sha|branch>}"
APP_DIR=/opt/squatchscout
cd "$APP_DIR"
set -a; . deploy/.env; set +a
COMPOSE=(docker compose -f deploy/docker-compose.yml --project-directory deploy)
PREV="$(cat deploy/.deployed_sha 2>/dev/null || git rev-parse HEAD)"

deploy_ref() {
  local ref="$1"
  git fetch --quiet origin
  git checkout --quiet --detach "$ref"
  local sha; sha="$(git rev-parse --short HEAD)"
  echo "→ building and starting api @ $sha"
  APP_VERSION="$sha" "${COMPOSE[@]}" up -d --build api caddy postgres
  echo "→ waiting for https://$API_HOST/healthz to report $sha"
  for i in $(seq 1 30); do
    if curl -fsS --max-time 5 "https://$API_HOST/healthz" 2>/dev/null | grep -q "\"version\": *\"$sha\""; then
      echo "✓ healthy @ $sha"; git rev-parse HEAD > deploy/.deployed_sha; return 0
    fi
    sleep 2
  done
  return 1
}

if deploy_ref "$TARGET"; then
  "${COMPOSE[@]}" image prune -f >/dev/null 2>&1 || true
  exit 0
fi
echo "!! health check failed — rolling back to $PREV"
"${COMPOSE[@]}" logs api --tail 40 || true
deploy_ref "$PREV" && { echo "✓ rolled back to $PREV"; exit 1; }
echo "!! rollback also failed — manual intervention needed"; exit 2
```

Make both executable in git: `git update-index --chmod=+x deploy/setup-ubuntu.sh deploy/deploy.sh` (Windows cannot set the bit on disk; this sets it in the index).

- [ ] **Step 3: `.github/workflows/ci.yml`**

```yaml
name: ci
on:
  push: { branches: [main] }
  pull_request:
jobs:
  api:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: api } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13", cache: pip, cache-dependency-path: api/pyproject.toml }
      - run: pip install -e ".[dev]"
      - run: ruff check . && ruff format --check .
      - run: pytest -q
        env: { DATABASE_URL: "sqlite:///./ci.db" }
  web:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: web } }
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with: { version: 9 }
      - uses: actions/setup-node@v4
        with: { node-version: 24, cache: pnpm, cache-dependency-path: web/pnpm-lock.yaml }
      - run: pnpm install --frozen-lockfile
      - run: pnpm typecheck && pnpm test && pnpm build
```

- [ ] **Step 4: `.github/workflows/deploy.yml`**

```yaml
name: deploy
on:
  workflow_run:
    workflows: [ci]
    types: [completed]
    branches: [main]
concurrency: { group: deploy, cancel-in-progress: false }
jobs:
  api:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy ${{ github.event.workflow_run.head_sha }} to the Ubuntu VM
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          command_timeout: 15m
          script: /opt/squatchscout/deploy/deploy.sh ${{ github.event.workflow_run.head_sha }}
```

- [ ] **Step 5: `LICENSE` (MIT, owner's name, 2026) and a `README.md` stub**

README stub content (replaced in Task 30):
```markdown
# SquatchScout
Ranked, verified, explained — which small businesses a searcher should call first.
Built for Caprae Capital's Full Stack Developer handbook. Full README lands with the first deploy.
```

- [ ] **Step 6: Create the GitHub repo and push**

```bash
gh repo create squatchscout --public --source . --remote origin --description "Ranked, verified, explained lead discovery for acquisition entrepreneurs — Caprae Capital take-home" --push
gh run watch   # CI must be green before Task 27
```
Fix anything red (typically: `pnpm-lock.yaml` missing → run `pnpm install` locally and commit it; ruff format drift → `ruff format .`).

- [ ] **Step 7: Log time, commit**

Append: `| 2026-09-17 | 26 server scripts, CI/CD, repo | 25 | — | measured |`

```bash
git add deploy .github LICENSE README.md docs/time-log.md
git commit -m "ci: test workflow, SSH deploy with health-checked rollback, server setup scripts"
git push
```

### Task 27: First deployment — EC2, TLS hostname, Vercel, wiring, verification

**Spec:** §12.1, §12.4, §12.5. This task is mostly **manual steps by the owner** (it touches their AWS, Vercel and GitHub accounts); the plan lists them so nothing is forgotten. Record actual time.

**Files:**
- Modify: `deploy/.env` on the server (not committed), Vercel project settings, GitHub secrets. No code changes expected; if a bug surfaces, fix it in a normal commit and let the pipeline redeploy.

- [ ] **Step 1: Launch the VM (owner, AWS console)**
  - EC2 → Launch instance → Ubuntu Server 24.04 LTS, **t3.micro**, 16 GB gp3. Key pair: create `squatchscout-deploy`, download the `.pem`.
  - Security group inbound: SSH 22 from **My IP**; HTTP 80 and HTTPS 443 from `0.0.0.0/0`.
  - Allocate an **Elastic IP** and associate it (so the hostname survives restarts). Note the IP, e.g. `203.0.113.10`.

- [ ] **Step 2: Pick the API hostname** — own domain: create an `A` record `api.<domain>` → Elastic IP. No domain: use `api.203-0-113-10.sslip.io` (dashes, not dots, in the IP — sslip.io accepts both `api.203.0.113.10.sslip.io` and the dashed form; use dashed to avoid confusion). This is `API_HOST`.

- [ ] **Step 3: Provision** (owner, from a terminal with the `.pem`)
```bash
ssh -i squatchscout-deploy.pem ubuntu@203.0.113.10
curl -fsSL https://raw.githubusercontent.com/<owner>/squatchscout/main/deploy/setup-ubuntu.sh | bash -s -- https://github.com/<owner>/squatchscout.git
exit && ssh -i squatchscout-deploy.pem ubuntu@203.0.113.10     # re-login so the docker group applies
nano /opt/squatchscout/deploy/.env
```
Set: `POSTGRES_PASSWORD` (random, `openssl rand -hex 16`), `API_HOST`, `FRONTEND_ORIGINS=https://<vercel-project>.vercel.app,http://localhost:5173`, `PUBLIC_URL=https://<vercel-project>.vercel.app`, `GROQ_API_KEY`, `CRAWLER_CONTACT=<your email>`. Then:
```bash
/opt/squatchscout/deploy/deploy.sh main
curl -s https://$API_HOST/healthz     # expect {"status":"ok","db":"ok","llm_enabled":true,"version":"<sha>"}
```
Caddy obtains the certificate on first request; if `curl` fails with a TLS error in the first ~30 s, wait and retry. If it never succeeds: `docker compose -f /opt/squatchscout/deploy/docker-compose.yml --project-directory /opt/squatchscout/deploy logs caddy` — the usual cause is port 80/443 not open in the security group.

- [ ] **Step 4: GitHub secrets for auto-deploy** — repo → Settings → Secrets → Actions: `DEPLOY_HOST` = Elastic IP, `DEPLOY_USER` = `ubuntu`, `DEPLOY_SSH_KEY` = contents of the `.pem`. Settings → Environments → create `production` (no protection rules needed). Push an empty commit (`git commit --allow-empty -m "chore: trigger deploy" && git push`) and watch **Actions → deploy** go green; `curl /healthz` shows the new SHA.

- [ ] **Step 5: Vercel** — `cd web && npx vercel link` (create project `squatchscout`, root `web/`), then in the dashboard: Settings → Environment Variables → `VITE_API_URL=https://<API_HOST>` (Production); Settings → Deployment Protection → **Disabled**; Git → connect the GitHub repo with root directory `web` so pushes to `main` deploy. `npx vercel --prod` for the first deploy. Note the production URL.

- [ ] **Step 6: Wire CORS** — if the Vercel URL differs from what you put in `FRONTEND_ORIGINS`, edit `/opt/squatchscout/deploy/.env` and `docker compose … up -d api` (env change only; no rebuild needed — use `--force-recreate api`).

- [ ] **Step 7: Verification checklist (spec §12.5)** — tick each:
  - [ ] `curl -s https://$API_HOST/healthz` → `db: ok`, correct `version`
  - [ ] `curl -s -X OPTIONS https://$API_HOST/api/searches -H "Origin: https://<vercel>.vercel.app" -H "Access-Control-Request-Method: POST" -i | grep -i access-control-allow-origin` → present
  - [ ] Open the Vercel URL → empty state renders, footer shows version, NL box visible (LLM enabled)
  - [ ] Run **Dentists / Austin, TX / 30** → rows stream, "Refining N leads with AI…", rows get the *refined* badge over the next minutes
  - [ ] Drag a slider → re-rank with no network requests
  - [ ] Open a drawer → factor bars, verified email badge, **Draft call opener** returns 3 lines
  - [ ] Export HubSpot CSV → downloads, opens, `Data Sources` column has OSM attribution
  - [ ] Repeat the same search → completes in < 2 s (Overpass + enrichment cache hits) — this is the caching demo for the video
  - [ ] `docker compose … logs api --tail 50` → JSON lines, no tracebacks

- [ ] **Step 8: Log time (Phase C complete — core budget closes here)**

Append: `| 2026-09-17 | 27 first deploy + verification | 30 | — | measured — Phase C done; core total = <sum> |`. Compute and write the core total. Commit `docs/time-log.md`.

---

## Phase D — Extended (outside the 5-hour core; unbounded)

### Task 28: Extraction eval harness — regex vs regex+LLM on a golden set

**Spec:** §7.4, §14 (eval).

**Files:**
- Create: `evals/golden/<slug>.html` × 10, `evals/labels.json`, `evals/extraction_eval.py`, `evals/results.md` (generated), `evals/README.md`

**Interfaces:**
- `python evals/extraction_eval.py [--llm]` prints and writes a per-field accuracy table. Runs from repo root with `api/.venv` active (`PYTHONPATH=api`). Without `--llm` it evaluates regex only; with `--llm` it needs `GROQ_API_KEY`.

- [ ] **Step 1: Build the golden set** — pick 10 real small-business homepages found by running the app (mix of industries; include ≥ 2 with no founded year, ≥ 2 family-owned, ≥ 1 chain, ≥ 2 DIY builders). Save each with `curl -sL <url> -o evals/golden/<slug>.html` (only the HTML — under 300 KB each; strip nothing). Hand-label `evals/labels.json`:

```json
{
  "kc-dental": {"url": "https://www.kcdentalaustin.com/", "osm_name": "KC Dental", "country": "US",
                 "founded_year": 1998, "owner_operated": true, "family_owned": true, "is_chain": false},
  "…": {}
}
```
Use `null` where the page genuinely does not say. Labels are the ground truth — spend the time to get them right; a wrong label makes the eval lie.

- [ ] **Step 2: `evals/extraction_eval.py`**

```python
"""Compare regex-only vs regex+LLM extraction against hand-labelled pages (spec §7.4).
Usage: PYTHONPATH=api python evals/extraction_eval.py [--llm]
"""
import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.config import Settings
from app.llm.client import LLMPool
from app.pipeline.crawl import PageBundle, PageText, clean_html, quality
from app.pipeline.extract_llm import extract_with_llm, merge_signals
from app.pipeline.extract_regex import extract_signals

ROOT = Path(__file__).parent
FIELDS = ["founded_year", "owner_operated", "family_owned", "is_chain"]
YEAR = datetime.now().year


def bundle_for(slug: str, url: str) -> PageBundle:
    html = (ROOT / "golden" / f"{slug}.html").read_text(encoding="utf-8", errors="ignore")
    title, meta, text, links, head = clean_html(html)
    return PageBundle(domain=slug, fetched_at=datetime.now(), pages=[
        PageText(url=url, title=title, meta_description=meta, visible_text=text, text_quality=quality(text), raw_head=head, links=links)])


def as_label(v: str | None):
    if v is None:
        return None
    if v in ("true", "false"):
        return v == "true"
    try:
        return int(v)
    except ValueError:
        return v


async def main(use_llm: bool) -> None:
    labels = json.loads((ROOT / "labels.json").read_text())
    pool = LLMPool(Settings()) if use_llm else None
    rows, correct = [], {"regex": dict.fromkeys(FIELDS, 0), "merged": dict.fromkeys(FIELDS, 0)}
    for slug, lab in labels.items():
        b = bundle_for(slug, lab["url"])
        regex = extract_signals(b, YEAR)
        regex_vals = {f: as_label(v.value) for v in merge_signals(regex, None) for f in [v.key] if f in FIELDS}
        llm = None
        if pool and pool.enabled:
            llm, status = await extract_with_llm(pool, b, lab["osm_name"], lab["country"], YEAR)
            if status != "ok":
                print(f"  {slug}: llm {status}")
        merged_vals = {v.key: as_label(v.value) for v in merge_signals(regex, llm) if v.key in FIELDS}
        for f in FIELDS:
            truth = lab.get(f)
            correct["regex"][f] += regex_vals.get(f) == truth
            correct["merged"][f] += merged_vals.get(f) == truth
        rows.append((slug, {f: (lab.get(f), regex_vals.get(f), merged_vals.get(f)) for f in FIELDS}))
    n = len(labels)
    out = ["# Extraction eval", "", f"{n} hand-labelled homepages · fields: {', '.join(FIELDS)} · "
           f"{'regex + LLM (' + ','.join(Settings().groq_models) + ')' if use_llm else 'regex only'}", "",
           "| Field | Regex only | Regex + LLM |", "|---|---|---|"]
    for f in FIELDS:
        out.append(f"| {f} | {correct['regex'][f]}/{n} | {correct['merged'][f] if use_llm else '—'}/{n} |")
    out += ["", "## Per page (truth / regex / merged)", "", "| Page | " + " | ".join(FIELDS) + " |", "|---|" + "---|" * len(FIELDS)]
    for slug, vals in rows:
        out.append(f"| {slug} | " + " | ".join(f"{t} / {r} / {m}" for t, r, m in vals.values()) + " |")
    (ROOT / "results.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true")
    asyncio.run(main(ap.parse_args().llm))
```

- [ ] **Step 3: Run both modes and commit the results**

```bash
cd api && .venv/Scripts/activate && cd ..
PYTHONPATH=api python evals/extraction_eval.py          # regex only — offline
PYTHONPATH=api GROQ_API_KEY=... python evals/extraction_eval.py --llm
```
Expected: `evals/results.md` with the two-column table. Read it critically: if regex+LLM is *worse* on a field, look at the per-page rows — a wrong LLM override with `confidence ≥ 0.85` is a real finding and belongs in the README as-is. Do not tune the threshold to make the table look better without saying so.

`evals/README.md`: three lines — what it measures, how to run, and that pages are snapshots taken on <date> for reproducibility.

```bash
git add evals
git commit -m "feat(evals): regex vs LLM extraction eval on a hand-labelled golden set"
```

### Task 29: Jupyter notebook demo and sample dataset

**Spec:** §17 (notebook, `data/`), handbook "Demo Link (optional but recommended): Jupyter Notebook walkthrough".

**Files:**
- Create: `notebooks/demo.ipynb`, `notebooks/requirements.txt`, `data/sample-search-austin-dentist.csv`, `data/README.md`

**Interfaces:**
- The notebook talks to the **live API** (so it doubles as an API demo) via `API_BASE` env var (default `https://<API_HOST>`), and to the local dev DB for the SQL cells via `DATABASE_URL` (optional section).

- [ ] **Step 1: `notebooks/requirements.txt`** — `pandas~=2.3`, `matplotlib~=3.10`, `httpx~=0.28`, `sqlalchemy~=2.0`, `psycopg[binary]~=3.2`, `jupyter`.

- [ ] **Step 2: Notebook cells** (create with `jupyter notebook` or by writing the `.ipynb` JSON; keep outputs **saved** so GitHub renders them):

1. **Markdown** — title, one paragraph: what SquatchScout does, link to the live app and repo.
2. **Code** — config: `API_BASE = os.getenv("API_BASE", "https://<API_HOST>")`; `httpx.get(f"{API_BASE}/healthz").json()`.
3. **Code** — start a search and consume the SSE stream with `httpx.stream("GET", …)`, parsing `event:`/`data:` lines into a list; print the status messages as they arrive; stop at `done`.
4. **Code** — `df = pd.json_normalize(leads)`; select `display_name, address.city, score, tier, enrichment_status, llm_status`; show `df.sort_values("score", ascending=False).head(15)`.
5. **Code** — score histogram (`df.score.plot.hist(bins=10)`) and tier bar chart. Title both; label axes.
6. **Code** — re-rank in pandas with the `succession` preset to show the client-side math: expand `factor_scores` to columns, compute `Σ (points/max) × weight/100 × 100`, compare top-5 under `balanced` vs `succession`.
7. **Code** — verified-email rate by contact source: explode `contacts`, `groupby(["source", "verification_status"]).size().unstack(fill_value=0)`.
8. **Markdown + Code (optional, local DB)** — two SQL queries via SQLAlchemy against `DATABASE_URL`: tier distribution by industry across all searches; average `llm` vs `regex` signal counts per lead. Skip gracefully if the env var is unset.
9. **Markdown** — "What the numbers say": 3 bullets written after running (coverage of websites in OSM, % verified emails, how many leads the LLM refined).

Use the dataviz conventions already in the app: one accent colour, tier colours for the tier chart, no gridlines clutter.

- [ ] **Step 3: Sample dataset** — from the live app, run **Dentists / Austin, TX / 60**, wait for refinement to finish, export **CSV**, save as `data/sample-search-austin-dentist.csv`. `data/README.md`: what the file is, when it was generated, the weights used, the attribution line, and a note that phone/email values are public business contacts from OSM and the businesses' own sites.

- [ ] **Step 4: Verify** — `jupyter nbconvert --execute --to notebook --inplace notebooks/demo.ipynb` runs end-to-end against the live API (needs network; ~1–2 min). Open on GitHub after pushing: outputs render.

```bash
git add notebooks data
git commit -m "docs: Jupyter API walkthrough with score analysis and a sample export"
```

### Task 30: README, architecture doc, runbook, video script

**Spec:** §17 (README sections in order), §12.7, §13 (runbook contents), §15 (data & ethics).

**Files:**
- Create: `docs/architecture.md`, `docs/runbook.md`, `docs/video-script.md`, `docs/screenshots/` (2–3 PNGs + one GIF of the stream)
- Modify: `README.md` (replace stub)

**Interfaces:** none — documentation. Every claim in the README must be true of the deployed app *at the time of writing*; re-read `/healthz` and the eval table before publishing.

- [ ] **Step 1: Capture media** — with the live app: `docs/screenshots/01-empty.png` (empty state), `02-results.png` (table + rail mid-stream), `03-drawer.png` (drawer with bars). Record a 10–15 s GIF of a search streaming (Windows: ScreenToGif; keep under 4 MB) → `docs/screenshots/stream.gif`.

- [ ] **Step 2: `README.md`** — sections **in this order** (spec §17), each 3–10 lines, no marketing tone:

1. `# SquatchScout` + one-line pitch + the GIF.
2. **Live demo** — Vercel URL, API `/healthz` URL, notebook link. Note: free-tier AI quota; if "refining" stalls, the table is still complete.
3. **The problem and who it's for** — searchers; SaaSquatch returns lists, this returns a ranked, explained list. One sentence on why "no website" is a *signal* (link to §Scoring).
4. **What it does in 60 seconds** — the 6-step flow from spec §3, as a numbered list.
5. **Architecture** — the ASCII diagram from spec §4 and the "why this split" paragraph.
6. **Stack** — a table with exact versions copied from `api/pyproject.toml` and `web/package.json` (`pnpm list --depth 0`).
7. **Data sources & ethics** — OSM (ODbL, attribution), Nominatim/Overpass usage policy, businesses' own sites with robots.txt, named UA, no LinkedIn/people scraping, 30-day retention. Honest coverage note: "in our Austin dentist sample, N of M OSM records had a website tag".
8. **Scoring model** — the §6 table verbatim + tiers + "weights re-rank client-side; `score.py` and `rank.ts` are tested against the same `golden_scores.json`".
9. **AI design** — three uses, gating, throttle/pool/caps, validation and grounding, then paste `evals/results.md`'s summary table, then the "why not more AI" paragraph (spec §7.5).
10. **Database** — table list with one line each; Alembic; SQLite/Postgres via `DATABASE_URL`; the three caches.
11. **Caching & performance** — repeat-search latency you measured (Task 27 step 7), enrichment cache TTL, concurrency limits.
12. **Hosting & deployment** — EC2 t3.micro Ubuntu 24.04 on AWS, Compose (api/postgres/caddy), Caddy auto-TLS, GitHub Actions → SSH → `deploy.sh` with health-checked rollback, Vercel for the static UI; the static-vs-serverless-vs-persistent paragraph; then the "production would differ" paragraph (spec §12.7). Link `docs/runbook.md`.
13. **Local setup** — the exact commands (venv, `alembic upgrade head`, `uvicorn`, `pnpm dev`; or `docker compose … local.yml`).
14. **Tests** — `pytest -q` and `pnpm test`; what is covered; what deliberately is not (E2E).
15. **Time log** — "Core build: <N> minutes across Tasks 1–27 (see `docs/time-log.md`). Everything under *Extended* was built outside that budget." Be exact.
16. **What I'd build next** — 4–5 bullets (job queue, second discovery provider, saved searches, HubSpot API push, people enrichment from team pages).
17. **Disclosure** — one sentence: "Built with AI-assisted tooling (Claude Code) for scaffolding, boilerplate and test generation; the architecture, scoring model, review, deployment and testing are mine." Adjust the wording to what is actually true for you.

- [ ] **Step 3: `docs/architecture.md`** — expands README §5: a Mermaid sequence diagram of one search (browser → POST → runner stages → SSE events → LLM queue → polling), the event contract table from spec §9, and the module map from the plan's File Structure with one line per module.

- [ ] **Step 4: `docs/runbook.md`** — for each item in spec §13, a heading, the exact command(s), and what "healthy" looks like:
  - Status: `docker compose -f /opt/squatchscout/deploy/docker-compose.yml --project-directory /opt/squatchscout/deploy ps`
  - Logs: `… logs -f api` (JSON; filter with `| grep '"level": "ERROR"'`)
  - Restart api: `… restart api`
  - Deploy/roll back: `/opt/squatchscout/deploy/deploy.sh <sha>`; `cat deploy/.deployed_sha`
  - Migrations: `… exec api alembic current` / `alembic history`; new migration workflow locally
  - Restore backup (if `backup.sh` installed): `gunzip -c backups/<date>.sql.gz | … exec -T postgres psql -U squatch squatchscout`
  - Rotate `GROQ_API_KEY`: edit `.env`, `… up -d --force-recreate api`
  - Disk full: `docker system df`, `… image prune -f`, check `backups/`
  - Ubuntu updates: `sudo unattended-upgrade -d` monthly; reboot → containers return via `restart: unless-stopped`
  - TLS: Caddy renews automatically; `… logs caddy | grep -i certificate`
  - Known limits: Groq free tier numbers; Overpass flakiness; t3.micro memory

- [ ] **Step 5: `docs/video-script.md`** — 2 minutes, 6 shots, word count ≈ 260 (spoken at a normal pace):

| Time | Shot | Say |
|---|---|---|
| 0:00–0:20 | Slide/title, then SaaSquatch's Search page | Who a searcher is; SaaSquatch finds businesses — the question is *which ones to call first*. |
| 0:20–0:55 | Live app: type the NL query, form fills, press Scout, rows stream | Discovery from OpenStreetMap, website checks, MX-verified emails, dedupe; each row scored 0–100 across five factors. |
| 0:55–1:15 | Drag the succession slider; open a drawer | Re-ranks instantly in the browser; every point has a reason; "no website" is upside, not noise. |
| 1:15–1:40 | Architecture slide (README diagram) | FastAPI on an Ubuntu EC2 box in Docker Compose behind Caddy; Postgres with Alembic; static UI on Vercel; GitHub Actions deploy with health-checked rollback. |
| 1:40–1:55 | Terminal: repeat search finishes in <2 s; eval table | Three caches; Groq extraction gated, throttled, validated — and measured against a labelled set. |
| 1:55–2:00 | Export to HubSpot CSV | What I'd build next; thanks. |

Include a "before recording" checklist: warm the API with the exact search, clear browser zoom to 100 %, 1920×1080, hide bookmarks bar, close other tabs.

- [ ] **Step 6: Commit and push**

```bash
git add README.md docs
git commit -m "docs: README, architecture, runbook and video script"
git push
```
Open the repo on GitHub and read the README top to bottom as an evaluator would: every link works, the GIF plays, versions match the lockfiles.

### Task 31: Ops extra — nightly backup script; final review

**Spec:** §12.6 (`backup.sh`), §18.

**Files:**
- Create: `deploy/backup.sh`
- Modify: `docs/runbook.md` (backup section becomes "installed"), `docs/time-log.md` (final line)

- [ ] **Step 1: `deploy/backup.sh`**

```bash
#!/usr/bin/env bash
# Nightly Postgres dump, keep 7. Install: (crontab -l; echo "0 3 * * * /opt/squatchscout/deploy/backup.sh") | crontab -
set -euo pipefail
cd /opt/squatchscout/deploy
mkdir -p backups
docker compose exec -T postgres pg_dump -U squatch squatchscout | gzip > "backups/$(date +%F).sql.gz"
ls -1t backups/*.sql.gz | tail -n +8 | xargs -r rm --
```
`git update-index --chmod=+x deploy/backup.sh`. On the server: pull, install the cron line, run it once by hand, confirm a file appears and `gunzip -t` passes.

- [ ] **Step 2: Final review pass** — run the whole quality gate one more time from a clean clone:
```bash
git clone https://github.com/<owner>/squatchscout /tmp/ss && cd /tmp/ss
cd api && python -m venv .venv && .venv/Scripts/pip install -e ".[dev]" && .venv/Scripts/ruff check . && .venv/Scripts/pytest -q && cd ..
cd web && pnpm install --frozen-lockfile && pnpm typecheck && pnpm test && pnpm build && cd ..
```
Then `grep -rn "TODO\|FIXME\|XXX" api/app web/src` → nothing. `git log --format=%B | grep -c "Co-Authored-By"` → `0`.

- [ ] **Step 3: Close the time log** — final row summarising core minutes (Tasks 1–27) and extended minutes (28–31) separately. Commit and push.

```bash
git add deploy/backup.sh docs
git commit -m "chore: nightly backup script and final time log"
git push
```

---

## Deliverables outside this repo (done in chat with the owner after Task 30)

- Essay answers (3 × 3–4 paragraphs) and short HR answers — drafted from the owner's own notes, in their voice.
- Submission email — subject **exactly** `Full Stack Developer - Handbook Submission - <Name>` (the handbook's format), body linking repo, live demo, video, notebook; resume attached.
- Video recording — owner records from `docs/video-script.md`; upload unlisted to YouTube or Loom.

## Plan self-review (author's notes)

- **Spec coverage:** §5.1–5.8 → Tasks 4–14; §6 → 10, 19; §7 → 11, 12, 17, 28; §8 → 2, 18; §9 → 13, 15, 16, 17; §10 → 19–25; §11 → 1, 18; §12 → 18, 26, 27, 31; §13 → 18, 30; §14 → tests inside each task + 28; §15 → 7, 16, 21, 30; §16 → File Structure; §17 → 29, 30; §18 → Global Constraints + every task's log step; §19–20 → 30 ("next").
- **Known simplifications vs spec:** rail on small screens stacks rather than a bottom sheet (§10) — documented in Task 23; TanStack Query dropped (spec updated).
- **Type consistency spot-checks:** `LeadOut` fields ↔ `types.ts` `Lead` ↔ `lead_to_out` (Tasks 13/19); `LLMStatus` values ↔ `Lead.llm_status` strings (Tasks 2/11/14); event names `status|lead|lead_updated|done|error` (Tasks 13/14/15/20); weights order `R/E/D/B/S` everywhere (Tasks 10/16/19).

