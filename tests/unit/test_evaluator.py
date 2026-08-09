"""Unit: deterministic checks, merge, synthetic judge (no live LLM)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from tests.helpers import load_script_fixture

from shorts_assistant.contracts import ContractValidationError, parse_contract
from shorts_assistant.evaluation_checks import (
    deterministic_checks,
    merge_evaluation,
)
from shorts_assistant.judge import judge_script, synthetic_judge
from shorts_assistant.nodes import evaluator_node
from shorts_assistant.schemas import ScriptEvaluation
from shorts_assistant.state import WorkflowState, WorkflowStatus


def test_high_quality_script_approved_after_merge():
    script = load_script_fixture("high_quality.json")
    det = deterministic_checks(script)
    assert not any(i.hard_fail for i in det)

    judgment = synthetic_judge(script, "LangGraph state")
    merged = merge_evaluation(judgment, det)
    assert merged.approved is True
    assert 0 <= merged.overall_score <= 10
    assert merged.factual_correctness >= 0
    assert merged.duration_score >= 0
    assert merged.cta_score >= 0

    final = judge_script(script, "LangGraph state", research="notes")
    assert final.approved is True


def test_poor_script_deterministic_hard_fail():
    script = load_script_fixture("poor_quality.json")
    det = deterministic_checks(script)
    assert any(i.hard_fail for i in det)
    messages = " ".join(i.message for i in det)
    assert any(key in messages for key in ("hook too short", "cta too short", "body too short"))
    assert "missing required label 'cta'" in messages

    generous = ScriptEvaluation(
        overall_score=9.0,
        hook_score=9.0,
        clarity_score=9.0,
        pacing_score=9.0,
        technical_accuracy=9.0,
        factual_correctness=9.0,
        developer_value=9.0,
        duration_score=9.0,
        cta_score=9.0,
        tone_score=9.0,
        issues=[],
        approved=True,
        summary="overly kind",
    )
    merged = merge_evaluation(generous, det)
    assert merged.approved is False
    assert merged.issues


def test_malformed_evaluation_rejected():
    with pytest.raises(ValidationError):
        ScriptEvaluation(
            overall_score=11,
            hook_score=8,
            clarity_score=8,
            pacing_score=8,
            technical_accuracy=8,
            factual_correctness=8,
            developer_value=8,
            duration_score=8,
            cta_score=8,
            tone_score=8,
            approved=True,
        )
    with pytest.raises(ContractValidationError):
        parse_contract(
            ScriptEvaluation,
            {"overall_score": 8, "approved": True},
            agent="evaluator",
        )


def test_missing_script_fail_closed():
    state = WorkflowState.initial("topic without script")
    assert state.generated_script is None
    update = evaluator_node(state)
    assert update["status"] == WorkflowStatus.FAILED
    assert "generated_script" in update["error"]
    assert update.get("evaluation") is None
