import csv
import io
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import deps
from app.db import session_scope
from app.main import create_app
from app.models import FactorScoreRow, Lead, Search, new_id
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


def test_create_search_clamps_limit_to_max_leads_per_search(client):
    r = client.post(
        "/api/searches", json={"industry_key": "dentist", "location": "Austin", "limit": 100}
    )
    assert r.status_code == 202
    sid = r.json()["id"]
    with session_scope() as s:
        assert s.get(Search, sid).limit == 60


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


def test_export_endpoint_filters_ids_and_sets_attachment(client):
    sid = new_id()
    with session_scope() as s:
        s.add(Search(id=sid, industry_key="dentist", location_query="Austin", limit=5))
        for i in (1, 2):
            s.add(
                Lead(
                    id=f"L{i}",
                    search_id=sid,
                    osm_type="node",
                    osm_id=i,
                    name=f"Biz {i}",
                    display_name=f"Biz {i}",
                    normalized_name=f"biz {i}",
                    lat=1.0,
                    lon=2.0,
                    osm_tags={},
                    score=50.0 + i,
                    tier="C",
                )
            )
    r = client.get(f"/api/searches/{sid}/export?format=hubspot&ids=L2")
    assert r.status_code == 200 and r.headers["content-disposition"].endswith('-hubspot.csv"')
    assert "Biz 2" in r.text and "Biz 1" not in r.text and r.text.startswith("Company name,")
    assert client.get(f"/api/searches/{sid}/export?format=xml").status_code == 422
    assert client.get(f"/api/searches/{sid}/export?weights=1,2").status_code == 400


def test_export_weights_query_param_maps_factors_in_order(client):
    # A lead scoring 100% on `reachability` only and 0% on everything else: a transposed
    # FACTORS<->weights zip would silently swap which query value drives the score.
    sid = new_id()
    with session_scope() as s:
        s.add(Search(id=sid, industry_key="dentist", location_query="Austin", limit=5))
        s.add(
            Lead(
                id="L1",
                search_id=sid,
                osm_type="node",
                osm_id=1,
                name="Biz 1",
                display_name="Biz 1",
                normalized_name="biz 1",
                lat=1.0,
                lon=2.0,
                osm_tags={},
                score=50.0,
                tier="C",
            )
        )
        for factor, points, max_points in (
            ("reachability", 25, 25),
            ("establishment", 0, 20),
            ("digital_gap", 0, 20),
            ("buybox", 0, 20),
            ("succession", 0, 15),
        ):
            s.add(
                FactorScoreRow(
                    lead_id="L1", factor=factor, points=points, max_points=max_points, reasons=[]
                )
            )

    def score_for(weights_qs):
        r = client.get(f"/api/searches/{sid}/export?format=csv&weights={weights_qs}")
        _, rest = r.text.split("\n", 1)
        rows = list(csv.DictReader(io.StringIO(rest)))
        return rows[0]["score"]

    assert score_for("100,0,0,0,0") == "100.0"  # all weight on reachability, which is maxed
    assert score_for("0,0,0,0,100") == "0.0"  # all weight on succession, which is zero


def test_generic_export_has_utf8_bom_hubspot_does_not(client):
    sid = new_id()
    with session_scope() as s:
        s.add(Search(id=sid, industry_key="dentist", location_query="Austin", limit=5))
        s.add(
            Lead(
                id="L1",
                search_id=sid,
                osm_type="node",
                osm_id=1,
                name="Biz 1",
                display_name="Biz 1",
                normalized_name="biz 1",
                lat=1.0,
                lon=2.0,
                osm_tags={},
                score=50.0,
                tier="C",
            )
        )
    csv_r = client.get(f"/api/searches/{sid}/export?format=csv")
    hub_r = client.get(f"/api/searches/{sid}/export?format=hubspot")
    assert csv_r.content.startswith(b"\xef\xbb\xbf")
    assert not hub_r.content.startswith(b"\xef\xbb\xbf")
    decoded = csv_r.content.decode("utf-8-sig")
    first, rest = decoded.split("\n", 1)
    assert first.startswith("# SquatchScout export")
    rows = list(csv.DictReader(io.StringIO(rest)))
    assert rows[0]["display_name"] == "Biz 1"
