"""Unit tests for HITL decision parsing and routing."""

from __future__ import annotations

import pytest

from shorts_assistant.hitl import route_after_human, validate_decision_payload
from shorts_assistant.state import WorkflowState, WorkflowStatus


def test_validate_approve():
    assert validate_decision_payload("approve") == {
        "decision": "approve",
        "feedback": None,
    }


def test_validate_request_changes_requires_feedback():
    with pytest.raises(ValueError, match="feedback"):
        validate_decision_payload("request_changes", feedback=None)
    assert (
        validate_decision_payload("request_changes", feedback="tighten CTA")["feedback"]
        == "tighten CTA"
    )


def test_validate_rejects_unknown_decision():
    with pytest.raises(ValueError, match="decision"):
        validate_decision_payload("maybe")


def test_route_after_human():
    base = WorkflowState.initial("topic")
    assert route_after_human(base.apply_update(status=WorkflowStatus.APPROVED)) == "continue"
    assert route_after_human(base.apply_update(status=WorkflowStatus.SCRIPTING)) == "revise"
    assert route_after_human(base.apply_update(status=WorkflowStatus.FAILED)) == "fail"
