import logging

from fastapi.testclient import TestClient

from app.main import create_app


def test_unhandled_exception_returns_500_and_logs_request_failed(monkeypatch, caplog):
    import app.routers.industries as industries_router

    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(industries_router, "list_industries", boom)
    client = TestClient(create_app())
    with caplog.at_level(logging.ERROR):
        r = client.get("/api/industries")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal"
    assert any(rec.message == "request.failed" for rec in caplog.records)
