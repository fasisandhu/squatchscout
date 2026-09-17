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
