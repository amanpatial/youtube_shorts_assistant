"""Unit: typed WorkflowState (no live LLM, no graph invoke)."""

import pytest
from pydantic import ValidationError

from shorts_assistant.demo_producers import demo_script
from shorts_assistant.schemas import ScriptEvaluation
from shorts_assistant.state import WorkflowState, WorkflowStatus


def test_initial_state():
    state = WorkflowState.initial("  Build AI agents  ")
    assert state.request == "Build AI agents"
    assert state.raw_idea == "Build AI agents"
    assert state.research is None
    assert state.generated_script is None
    assert state.script_version == 0
    assert state.evaluation is None
    assert state.visual_concepts is None
    assert state.final_short_concept is None
    assert state.iteration == 0
    assert state.max_iterations == 3
    assert state.best_script is None
    assert state.best_score is None
    assert state.status == WorkflowStatus.INITIALIZED
    assert state.error is None
    assert state.error_class is None
    assert state.error_node is None
    assert state.trace_id is None
    assert state.execution_id is None
    assert state.memory_context is None
    assert state.retrieved_memory_ids == []


def test_initial_rejects_empty_request():
    with pytest.raises(ValueError, match="non-empty"):
        WorkflowState.initial("   ")


def test_valid_apply_update():
    script = demo_script("idea")
    state = WorkflowState.initial("idea")
    updated = state.apply_update(
        generated_script=script,
        script_version=1,
        status=WorkflowStatus.SCRIPTING,
    )
    assert updated.generated_script is not None
    assert updated.generated_script.hook
    assert updated.script_version == 1
    assert updated.status == WorkflowStatus.SCRIPTING
    assert state.generated_script is None
    assert state.status == WorkflowStatus.INITIALIZED


def test_from_dict_missing_request_raises():
    with pytest.raises(ValidationError):
        WorkflowState.from_dict({})


def test_invalid_iteration_negative():
    with pytest.raises(ValidationError):
        WorkflowState.initial("idea").apply_update(iteration=-1)


def test_invalid_max_iterations_zero():
    with pytest.raises(ValidationError):
        WorkflowState.initial("idea", max_iterations=0)


def test_invalid_best_score_out_of_range():
    with pytest.raises(ValidationError):
        WorkflowState.initial("idea").apply_update(best_score=11.0)


def test_invalid_status_string():
    with pytest.raises(ValidationError):
        WorkflowState.from_dict(
            {
                "request": "x",
                "raw_idea": "x",
                "status": "NOT_A_REAL_STATUS",
            }
        )


def test_round_trip_dict():
    state = WorkflowState.initial("round trip").apply_update(
        evaluation=ScriptEvaluation(
            overall_score=8.0,
            hook_score=8.0,
            clarity_score=8.0,
            pacing_score=8.0,
            technical_accuracy=8.0,
            factual_correctness=8.0,
            developer_value=8.0,
            duration_score=8.0,
            cta_score=8.0,
            tone_score=8.0,
            approved=True,
            summary="ok",
        ),
        best_score=8.0,
        status=WorkflowStatus.EVALUATING,
    )
    restored = WorkflowState.from_dict(state.to_dict())
    assert restored == state
