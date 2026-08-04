"""Unit: observability correlation, cost, redaction, fail-open (no LLM)."""

from __future__ import annotations

import logging

import pytest

from shorts_assistant.observability import (
    WorkflowTrace,
    configure_logging,
    estimate_cost_usd,
    finalize_trace,
    get_trace_id,
    log_event,
    observe_node,
    redact_text,
    reset_logging_for_tests,
    safe_error_message,
)
from shorts_assistant.state import WorkflowState, WorkflowStatus
from shorts_assistant.telemetry import setup_telemetry


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture(autouse=True)
def _fresh_logging():
    reset_logging_for_tests()
    yield
    reset_logging_for_tests()


def test_estimate_cost_math():
    cost = estimate_cost_usd(1_000_000, 1_000_000, input_rate=0.10, output_rate=0.40)
    assert cost == 0.5
    assert estimate_cost_usd(None, None) is None


def test_redaction_strips_key_material():
    text = safe_error_message(RuntimeError("api_key=supersecret sk-abcdefghijklmnop"))
    assert "supersecret" not in text
    assert "sk-abcdefghijklmnop" not in text
    assert "REDACTED" in text
    assert "abcdefghijklmnop" not in redact_text("AIzaSyD-testkeyvalue123456789012")


def test_trace_id_on_nested_events():
    handler = _ListHandler()
    logging.getLogger("shorts_assistant.obs").addHandler(handler)
    logging.getLogger("shorts_assistant.obs").setLevel(logging.INFO)
    try:
        with WorkflowTrace(trace_id="wf_test_123") as trace:
            assert get_trace_id() == "wf_test_123"
            log_event("agent_end", agent="evaluator", evaluation_score=6.8, iteration=1)
            log_event("agent_end", agent="evaluator", evaluation_score=8.2, iteration=2)
            final = WorkflowState.initial("topic").apply_update(
                trace_id=trace.trace_id,
                iteration=2,
                status=WorkflowStatus.COMPLETED,
                evaluation=None,
            )
            # attach fake evaluation via apply would need full model — use note_score
            trace.note_score(6.8)
            trace.note_score(8.2)
            finalize_trace(trace, final)
        assert get_trace_id() is None
        events = [
            getattr(r, "obs_event", {})
            for r in handler.records
            if getattr(r, "obs_event", None)
        ]
        assert any(e.get("trace_id") == "wf_test_123" for e in events)
        scores = [
            e.get("evaluation_score")
            for e in events
            if e.get("event") == "agent_end"
        ]
        assert 6.8 in scores and 8.2 in scores
        summary = next(e for e in events if e.get("event") == "workflow_summary")
        assert summary.get("final_status") == "COMPLETED"
        assert summary.get("evaluation_scores") == [6.8, 8.2]
    finally:
        logging.getLogger("shorts_assistant.obs").removeHandler(handler)


def test_observe_node_fail_open_on_logger(monkeypatch):
    def boom_log(*_a, **_k):
        raise RuntimeError("logger down")

    monkeypatch.setattr(
        "shorts_assistant.observability.log_event", boom_log
    )

    def node(_state):
        return {"status": WorkflowStatus.RESEARCHING}

    wrapped = observe_node("research", node)
    # Even if end logging raises inside observe_node's try, fail-open catches it
    # Restore real log_event for the wrapper's internal call path:
    # The wrapper catches log_event failures — monkeypatch makes log_event raise,
    # which is caught in finally. Node result must still return.
    out = wrapped(WorkflowState.initial("x"))
    assert out["status"] == WorkflowStatus.RESEARCHING


def test_setup_telemetry_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(
        "shorts_assistant.telemetry.settings.enable_otel", False
    )
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
    setup_telemetry()  # should not raise


def test_configure_logging_idempotent():
    configure_logging("INFO")
    configure_logging("DEBUG")
