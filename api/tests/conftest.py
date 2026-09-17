import os

import pytest

# Tests never touch a real DB or network. Force SQLite + no LLM before app import.
# GROQ_API_KEY is set to "" (not popped) so a developer's local api/.env cannot
# flip llm_enabled in tests.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ["GROQ_API_KEY"] = ""


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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
