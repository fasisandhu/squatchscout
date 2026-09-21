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
            pool = LLMPool(
                Settings(groq_api_key="k", groq_models=["m1"]), groq_client=FakeGroq(script)
            )
        monkeypatch.setattr(deps, "get_pool", lambda: pool)
        return TestClient(create_app())

    return _make


def test_intent_disabled_returns_503(make_client):
    c = make_client(None)
    r = c.post("/api/intent", json={"text": "dentists in Austin"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "llm_disabled"


def test_intent_returns_structured_result(make_client):
    c = make_client(
        {
            "m1": [
                json.dumps(
                    {
                        "industry_key": "dentist",
                        "location": "Austin, TX",
                        "limit": None,
                        "weight_preset": "succession",
                        "rationale": "retirement mentioned",
                    }
                )
            ]
        }
    )
    r = c.post("/api/intent", json={"text": "dentists in Austin whose owners are near retirement"})
    assert r.status_code == 200
    assert r.json() == {
        "industry_key": "dentist",
        "location": "Austin, TX",
        "limit": None,
        "weight_preset": "succession",
        "rationale": "retirement mentioned",
    }


def test_intent_rejects_unknown_industry_from_model(make_client):
    c = make_client(
        {
            "m1": [
                json.dumps(
                    {
                        "industry_key": "spaceports",
                        "location": "Austin",
                        "limit": None,
                        "weight_preset": "balanced",
                        "rationale": "",
                    }
                )
            ]
        }
    )
    assert (
        c.post("/api/intent", json={"text": "spaceports in Austin"}).json()["industry_key"] is None
    )


def test_opener_grounded_in_signals(make_client):
    c = make_client({"m1": [json.dumps({"opener": "Hi Karen,\nline two\nline three"})]})
    sid, lid = new_id(), new_id()
    with session_scope() as s:
        s.add(Search(id=sid, industry_key="dentist", location_query="Austin", limit=5))
        s.flush()
        s.add(
            Lead(
                id=lid,
                search_id=sid,
                osm_type="node",
                osm_id=1,
                name="KC Dental",
                display_name="KC Dental",
                normalized_name="kc dental",
                lat=1.0,
                lon=2.0,
                osm_tags={},
                city="Austin",
            )
        )
        s.flush()
        s.add(Signal(lead_id=lid, key="founded_year", value="1998", source="regex"))
    r = c.post(f"/api/leads/{lid}/opener")
    assert r.status_code == 200 and r.json()["opener"].count("\n") == 2
    assert c.post("/api/leads/nope/opener").status_code == 404


def _seed_lead(sid: str, lid: str) -> None:
    with session_scope() as s:
        s.add(Search(id=sid, industry_key="dentist", location_query="Austin", limit=5))
        s.flush()
        s.add(
            Lead(
                id=lid,
                search_id=sid,
                osm_type="node",
                osm_id=1,
                name="KC Dental",
                display_name="KC Dental",
                normalized_name="kc dental",
                lat=1.0,
                lon=2.0,
                osm_tags={},
                city="Austin",
            )
        )
        s.flush()
        s.add(Signal(lead_id=lid, key="founded_year", value="1998", source="regex"))


def test_opener_rejects_a_truncated_draft(make_client):
    """Regression: a starved generation returns a *successful* half-sentence.

    Groq's strict-JSON decoder force-closes the string when the completion nears its token
    budget, so the call reports finish_reason "stop" and the route used to hand the caller
    two lines ending mid-word. The stray C0 character is the only in-band evidence, so the
    route treats it as a failure instead of rendering it.
    """
    truncated = "Hi Dr. Chen, KC Dental has served Austin since 1998.\nI noticed you are not\x02"
    c = make_client({"m1": [json.dumps({"opener": truncated})]})
    sid, lid = new_id(), new_id()
    _seed_lead(sid, lid)
    r = c.post(f"/api/leads/{lid}/opener")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "llm_unavailable"


def test_opener_asks_for_enough_tokens_to_finish(make_client):
    """A three-line opener costs 74-90 completion tokens; 160 truncated all five leads tested."""
    c = make_client({"m1": [json.dumps({"opener": "one\ntwo\nthree."})]})
    sid, lid = new_id(), new_id()
    _seed_lead(sid, lid)
    assert c.post(f"/api/leads/{lid}/opener").status_code == 200
    pool = deps.get_pool()
    sent = pool._client.kwargs[0]  # FakeGroq records the kwargs it was called with
    assert sent["max_completion_tokens"] >= 400
