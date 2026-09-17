from fastapi.testclient import TestClient

from app.main import create_app


def test_healthz_reports_status_and_llm_flag(db, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    client = TestClient(create_app())
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["llm_enabled"] is False
    assert body["db"] == "ok"
    assert "version" in body
