"""Phase 19: /healthz and /readyz behavior."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from shorts_assistant.api.app import create_app
from shorts_assistant.api.health import readiness_payload
from shorts_assistant.config import get_settings
from shorts_assistant.runtime_lifecycle import request_shutdown, reset_for_tests


@pytest.fixture(autouse=True)
def _reset_lifecycle(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "local")
    get_settings.cache_clear()
    import shorts_assistant.config as cfg

    s = get_settings()
    monkeypatch.setattr(cfg, "settings", s)
    reset_for_tests()
    yield
    reset_for_tests()
    get_settings.cache_clear()


def test_healthz_ok_without_db() -> None:
    client = TestClient(create_app())
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert client.get("/health").status_code == 200


def test_readyz_503_when_db_down() -> None:
    with patch("shorts_assistant.api.health.ping_database", return_value=False):
        client = TestClient(create_app())
        r = client.get("/readyz")
        assert r.status_code == 503
        assert r.json()["reason"] == "database_unavailable"


def test_readyz_503_when_shutting_down() -> None:
    with patch("shorts_assistant.api.health.ping_database", return_value=True):
        request_shutdown()
        body, code = readiness_payload()
        assert code == 503
        assert body["reason"] == "shutting_down"


def test_readyz_200_when_db_ok() -> None:
    with patch("shorts_assistant.api.health.ping_database", return_value=True):
        client = TestClient(create_app())
        r = client.get("/readyz")
        assert r.status_code == 200
        assert r.json()["status"] == "ready"
