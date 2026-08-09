"""API 429 rate limit integration test."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from shorts_assistant.api.app import create_app
from shorts_assistant.checkpointer import reset_checkpointer_for_tests
from shorts_assistant.config import get_settings
from shorts_assistant.persistence.session import ensure_schema, reset_engine_cache
from shorts_assistant.security.rate_limit import reset_rate_limiter_for_tests


@pytest.fixture()
def limited_client(tmp_path, monkeypatch):
    db = tmp_path / "rl.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db}")
    monkeypatch.setenv("CHECKPOINT_BACKEND", "memory")
    monkeypatch.setenv("API_KEY", "rl-key")
    monkeypatch.setenv("API_RATE_LIMIT_PER_MIN", "2")
    monkeypatch.setenv("APP_ENV", "local")
    get_settings.cache_clear()
    reset_engine_cache()
    reset_checkpointer_for_tests()
    reset_rate_limiter_for_tests()
    import shorts_assistant.api.service as svc
    import shorts_assistant.config as cfg
    import shorts_assistant.persistence.session as sess
    import shorts_assistant.security.auth as sec_auth
    import shorts_assistant.security.input_guard as ig
    from shorts_assistant.runtime_lifecycle import reset_for_tests

    reset_for_tests()
    s = get_settings()
    for mod in (cfg, sess, svc, sec_auth, ig):
        monkeypatch.setattr(mod, "settings", s)
    ensure_schema()
    client = TestClient(create_app())
    yield client
    reset_rate_limiter_for_tests()
    reset_for_tests()
    reset_engine_cache()
    get_settings.cache_clear()


def test_post_shorts_429(limited_client):
    headers = {"X-API-Key": "rl-key"}
    assert limited_client.post("/shorts", json={"topic": "a"}, headers=headers).status_code == 202
    assert limited_client.post("/shorts", json={"topic": "b"}, headers=headers).status_code == 202
    r = limited_client.post("/shorts", json={"topic": "c"}, headers=headers)
    assert r.status_code == 429
    assert "Retry-After" in r.headers
