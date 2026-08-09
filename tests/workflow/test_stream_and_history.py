"""Phase 20: stream updates + checkpoint history (offline demo graph)."""

from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import MemorySaver

from shorts_assistant.config import get_settings
from shorts_assistant.graph import get_compiled_graph
from shorts_assistant.graph_ops import (
    get_thread_state,
    list_state_history,
    node_names_from_updates,
    stream_workflow,
)
from shorts_assistant.state import WorkflowStatus


@pytest.fixture(autouse=True)
def _hitl_off(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HITL_REQUIRED", "false")
    monkeypatch.setenv("A2A_RESEARCH_ENABLED", "false")
    get_settings.cache_clear()
    import shorts_assistant.config as cfg
    import shorts_assistant.hitl as hitl

    s = get_settings()
    monkeypatch.setattr(cfg, "settings", s)
    monkeypatch.setattr(hitl, "settings", s)
    yield
    get_settings.cache_clear()


def test_stream_yields_node_updates() -> None:
    saver = MemorySaver()
    graph = get_compiled_graph(checkpointer=saver)
    thread_id = "test-stream-1"
    chunks = stream_workflow(
        "How to use pytest fixtures",
        thread_id=thread_id,
        graph=graph,
    )
    assert chunks, "expected at least one stream chunk"
    names = node_names_from_updates(chunks)
    assert "research" in names
    assert "scriptwriter" in names
    assert "quality_gate" in names
    assert "formatter" in names


def test_state_history_after_stream() -> None:
    saver = MemorySaver()
    graph = get_compiled_graph(checkpointer=saver)
    thread_id = "test-history-1"
    stream_workflow("FastAPI lifespan hooks", thread_id=thread_id, graph=graph)
    history = list_state_history(thread_id, limit=50, graph=graph)
    assert len(history) >= 2
    snap = get_thread_state(thread_id, graph=graph)
    values = getattr(snap, "values", {}) or {}
    assert values.get("request") == "FastAPI lifespan hooks"
    status = values.get("status")
    status_val = status.value if hasattr(status, "value") else status
    assert status_val in {
        WorkflowStatus.COMPLETED.value,
        WorkflowStatus.AWAITING_HUMAN.value,
        "COMPLETED",
        "AWAITING_HUMAN",
    }


def test_loop_still_reaches_formatter_on_happy_path() -> None:
    """Regression: hardening helpers must not break quality-loop termination."""
    saver = MemorySaver()
    graph = get_compiled_graph(checkpointer=saver)
    names = node_names_from_updates(
        stream_workflow("LangGraph conditional edges", thread_id="test-loop-1", graph=graph)
    )
    assert names.index("quality_gate") < names.index("formatter")
