def test_settings_parse_csv_lists_and_llm_flag(monkeypatch):
    monkeypatch.setenv("GROQ_MODELS", "modelA, modelB")
    monkeypatch.setenv("FRONTEND_ORIGINS", "http://a.test,http://b.test")
    monkeypatch.setenv("OVERPASS_ENDPOINTS", "https://o1.test/api,https://o2.test/api")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    from app.config import Settings

    s = Settings(_env_file=None)
    assert s.groq_models == ["modelA", "modelB"]
    assert s.frontend_origins == ["http://a.test", "http://b.test"]
    assert s.overpass_endpoints == ["https://o1.test/api", "https://o2.test/api"]
    assert s.llm_enabled is True


def test_settings_parse_single_value_csv_list(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "http://a.test")
    from app.config import Settings

    s = Settings(_env_file=None)
    assert s.frontend_origins == ["http://a.test"]
