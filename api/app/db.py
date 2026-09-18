from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import JSON, event
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
        is_sqlite = url.startswith("sqlite")
        kwargs = {"connect_args": {"check_same_thread": False}} if is_sqlite else {}
        _engine = create_engine(url, pool_pre_ping=True, **kwargs)
        if is_sqlite:
            # SQLite has FK enforcement off by default (per-connection, not per-database), unlike
            # Postgres — without this, dev/test would silently accept a delete order that violates
            # a foreign key and only find out in production. Match production's semantics here.
            @event.listens_for(_engine, "connect")
            def _enable_sqlite_fk(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    return _engine


def reset_engine() -> None:
    """Test helper: drop the cached engine so a new DATABASE_URL takes effect."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


@contextmanager
def session_scope() -> Iterator[Session]:
    # expire_on_commit=False: objects committed in one session_scope block stay usable
    # (e.g. reading generated ids) after the block exits and the session is closed.
    session = Session(get_engine(), expire_on_commit=False)
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
