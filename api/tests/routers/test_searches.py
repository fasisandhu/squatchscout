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
    assert set(body["presets"]) == {
        "balanced",
        "succession",
        "digital_upside",
        "reachability_first",
    }


def test_create_search_persists_and_schedules(client):
    r = client.post(
        "/api/searches", json={"industry_key": "dentist", "location": "Austin, TX", "limit": 20}
    )
    assert r.status_code == 202
    sid = r.json()["id"]
    with session_scope() as s:
        row = s.get(Search, sid)
        assert row.status == "running" and row.limit == 20 and row.weight_preset == "balanced"
    deps.start_search_task.assert_called_once_with(sid)
    got = client.get(f"/api/searches/{sid}").json()
    assert got["id"] == sid and got["llm_pending"] == 0


def test_create_search_rejects_unknown_industry_and_bad_limit(client):
    assert (
        client.post(
            "/api/searches", json={"industry_key": "nope", "location": "Austin"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/searches", json={"industry_key": "dentist", "location": "Austin", "limit": 500}
        ).status_code
        == 422
    )


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
    assert "event: status" in text and "event: done" in text and '"lead_count": 0' in text


def test_leads_endpoints_and_404s(client):
    sid = new_id()
    with session_scope() as s:
        s.add(Search(id=sid, industry_key="dentist", location_query="Austin", limit=5))
        s.add(
            Lead(
                id="L1",
                search_id=sid,
                osm_type="node",
                osm_id=1,
                name="KC Dental",
                display_name="KC Dental",
                normalized_name="kc dental",
                lat=1.0,
                lon=2.0,
                osm_tags={},
            )
        )
    leads = client.get(f"/api/searches/{sid}/leads").json()
    assert [x["id"] for x in leads] == ["L1"] and leads[0]["contacts"] == []
    assert client.get("/api/leads/L1").json()["name"] == "KC Dental"
    assert client.get("/api/leads/nope").status_code == 404
    assert client.get("/api/searches/nope").json() == {
        "error": {"code": "not_found", "message": "Search not found"}
    }
