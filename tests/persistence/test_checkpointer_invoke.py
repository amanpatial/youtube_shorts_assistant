"""Persistence wiring: MemorySaver + domain reload via invoke_workflow."""

from __future__ import annotations

import pytest

from shorts_assistant.checkpointer import reset_checkpointer_for_tests
from shorts_assistant.config import get_settings
from shorts_assistant.persistence.session import ensure_schema, reset_engine_cache
from shorts_assistant.run import invoke_workflow, load_execution_state
from shorts_assistant.state import WorkflowStatus


@pytest.fixture()
def persist_env(tmp_path, monkeypatch):
    db = tmp_path / "invoke.db"
    url = f"sqlite+pysqlite:///{db}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("CHECKPOINT_BACKEND", "memory")
    get_settings.cache_clear()
    reset_engine_cache()
    reset_checkpointer_for_tests()
    import shorts_assistant.checkpointer as cp
    import shorts_assistant.config as cfg
    import shorts_assistant.persistence.session as sess

    monkeypatch.setattr(cfg, "settings", get_settings())
    monkeypatch.setattr(sess, "settings", get_settings())
    monkeypatch.setattr(cp, "settings", get_settings())
    ensure_schema(url)
    yield url
    reset_engine_cache()
    reset_checkpointer_for_tests()
    get_settings.cache_clear()


def test_invoke_persists_and_reloads(persist_env):
    final = invoke_workflow("LangGraph persistence", persist=True)
    assert final.status == WorkflowStatus.COMPLETED
    assert final.trace_id and final.trace_id.startswith("wf_")
    assert final.execution_id

    loaded = load_execution_state(final.execution_id)
    assert loaded is not None
    assert loaded.status == WorkflowStatus.COMPLETED
    assert loaded.request == "LangGraph persistence"
    assert loaded.generated_script is not None
    assert loaded.trace_id == final.trace_id
