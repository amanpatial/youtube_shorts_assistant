"""Phase 16: FastAPI job API + worker (offline demo producers)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from shorts_assistant.api.app import create_app
from shorts_assistant.checkpointer import reset_checkpointer_for_tests
from shorts_assistant.config import get_settings
from shorts_assistant.persistence.session import ensure_schema, reset_engine_cache
from shorts_assistant.worker.bridge import process_one_job


@pytest.fixture()
def api_env(tmp_path, monkeypatch):
    db = tmp_path / "api.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db}")
    monkeypatch.setenv("CHECKPOINT_BACKEND", "memory")
    monkeypatch.setenv("API_KEY", "test-secret")
    monkeypatch.setenv("API_KEYS", "other-secret")
    monkeypatch.setenv("HITL_REQUIRED", "false")
    monkeypatch.setenv("A2A_RESEARCH_ENABLED", "false")
    monkeypatch.setenv("API_RATE_LIMIT_PER_MIN", "1000")
    monkeypatch.setenv("APP_ENV", "local")
    get_settings.cache_clear()
    reset_engine_cache()
    reset_checkpointer_for_tests()
    from shorts_assistant.runtime_lifecycle import reset_for_tests
    from shorts_assistant.security.rate_limit import reset_rate_limiter_for_tests

    reset_rate_limiter_for_tests()
    reset_for_tests()
    import shorts_assistant.api.service as svc
    import shorts_assistant.checkpointer as cp
    import shorts_assistant.config as cfg
    import shorts_assistant.persistence.session as sess
    import shorts_assistant.security.auth as sec_auth
    import shorts_assistant.security.input_guard as ig
    import shorts_assistant.security.output_policy as op
    import shorts_assistant.worker.bridge as bridge

    s = get_settings()
    monkeypatch.setattr(cfg, "settings", s)
    monkeypatch.setattr(sess, "settings", s)
    monkeypatch.setattr(cp, "settings", s)
    monkeypatch.setattr(svc, "settings", s)
    monkeypatch.setattr(bridge, "settings", s)
    monkeypatch.setattr(sec_auth, "settings", s)
    monkeypatch.setattr(ig, "settings", s)
    monkeypatch.setattr(op, "settings", s)
    ensure_schema()
    client = TestClient(create_app())
    yield client
    reset_rate_limiter_for_tests()
    reset_for_tests()
    reset_engine_cache()
    reset_checkpointer_for_tests()
    get_settings.cache_clear()


def _headers(key: str = "test-secret", idem: str | None = None) -> dict[str, str]:
    h = {"X-API-Key": key}
    if idem:
        h["Idempotency-Key"] = idem
    return h


def test_post_shorts_202(api_env):
    client = api_env
    r = client.post(
        "/shorts",
        json={"topic": "Async API Shorts"},
        headers=_headers(idem="key-1"),
    )
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "queued"
    assert body["workflow_id"]


def test_idempotent_post(api_env):
    client = api_env
    a = client.post(
        "/shorts",
        json={"topic": "same"},
        headers=_headers(idem="same-key"),
    ).json()
    b = client.post(
        "/shorts",
        json={"topic": "same"},
        headers=_headers(idem="same-key"),
    ).json()
    assert a["workflow_id"] == b["workflow_id"]


def test_unauthorized(api_env):
    client = api_env
    r = client.post("/shorts", json={"topic": "x"}, headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_bearer_auth_works(api_env):
    client = api_env
    r = client.post(
        "/shorts",
        json={"topic": "bearer topic"},
        headers={"Authorization": "Bearer test-secret"},
    )
    assert r.status_code == 202


def test_owner_forbidden(api_env):
    client = api_env
    wid = client.post(
        "/shorts",
        json={"topic": "owned"},
        headers=_headers("test-secret"),
    ).json()["workflow_id"]
    r = client.get(f"/shorts/{wid}", headers=_headers("other-secret"))
    assert r.status_code == 403


def test_status_queued_and_result_409(api_env):
    client = api_env
    wid = client.post(
        "/shorts",
        json={"topic": "pending"},
        headers=_headers(),
    ).json()["workflow_id"]
    st = client.get(f"/shorts/{wid}", headers=_headers())
    assert st.status_code == 200
    assert st.json()["status"] == "queued"
    res = client.get(f"/shorts/{wid}/result", headers=_headers())
    assert res.status_code == 409


def test_worker_runs_to_succeeded(api_env):
    client = api_env
    wid = client.post(
        "/shorts",
        json={"topic": "Worker completes"},
        headers=_headers(),
    ).json()["workflow_id"]
    assert process_one_job() is True
    st = client.get(f"/shorts/{wid}", headers=_headers()).json()
    assert st["status"] == "succeeded"
    assert st["execution_id"]
    agents = {row["id"]: row["state"] for row in st["agents"]}
    assert agents["research"] == "done"
    assert agents["formatter"] == "done"
    assert len(st["agents"]) == 8
    res = client.get(f"/shorts/{wid}/result", headers=_headers())
    assert res.status_code == 200
    body = res.json()
    assert body["final_short_concept"] is not None
    assert body["generated_script"] is not None
    assert body["research"]
    assert body["evaluation"] is not None
    assert body["evaluation"]["overall_score"] is not None
    assert body["visual_concepts"] is not None
    assert body["visual_concepts"]["shots"]


def test_list_shorts_owner_scoped(api_env):
    client = api_env
    a = client.post(
        "/shorts",
        json={"topic": "Owner A topic"},
        headers=_headers("test-secret", idem="list-a"),
    ).json()["workflow_id"]
    b = client.post(
        "/shorts",
        json={"topic": "Owner B topic"},
        headers=_headers("other-secret", idem="list-b"),
    ).json()["workflow_id"]

    mine = client.get("/shorts?limit=20", headers=_headers("test-secret"))
    assert mine.status_code == 200
    ids = [row["workflow_id"] for row in mine.json()["items"]]
    assert a in ids
    assert b not in ids
    assert mine.json()["items"][0]["topic"]


def test_cors_preflight_allows_vite_origin(api_env):
    client = api_env
    r = client.options(
        "/shorts",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-api-key",
        },
    )
    assert r.status_code in {200, 204}
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_approve_when_awaiting(api_env, monkeypatch):
    client = api_env
    import shorts_assistant.hitl as hitl
    import shorts_assistant.worker.bridge as bridge

    monkeypatch.setattr(bridge.settings, "hitl_required", True)
    monkeypatch.setattr(hitl, "settings", bridge.settings)

    wid = client.post(
        "/shorts",
        json={"topic": "HITL via API", "hitl_required": True},
        headers=_headers(),
    ).json()["workflow_id"]
    assert process_one_job() is True
    st = client.get(f"/shorts/{wid}", headers=_headers()).json()
    assert st["status"] == "awaiting_human"

    ap = client.post(
        f"/shorts/{wid}/approve",
        json={"reviewer": "tester"},
        headers=_headers(),
    )
    assert ap.status_code == 202
    assert process_one_job() is True
    st2 = client.get(f"/shorts/{wid}", headers=_headers()).json()
    assert st2["status"] == "succeeded"
