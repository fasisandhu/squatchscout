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
    # pending | ok | no_website | blocked_by_robots | unreachable
    enrichment_status: str = "pending"
    # not_needed | queued | done | skipped_rate_limit | skipped_budget | disabled
    llm_status: str = "not_needed"
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
    # verified | unverified | invalid | valid | possible | not_checked
    verification_status: str = "not_checked"
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
