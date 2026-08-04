"""Structural regression: fixture scripts stay valid and gate-stable (no LLM)."""

from tests.helpers import load_script_fixture

from shorts_assistant.quality_gate import GateDecision, apply_quality_gate
from shorts_assistant.schemas import ScriptEvaluation
from shorts_assistant.state import WorkflowState, WorkflowStatus


def _eval(score: float, *, approved: bool) -> ScriptEvaluation:
    return ScriptEvaluation(
        overall_score=score,
        hook_score=score,
        clarity_score=score,
        pacing_score=score,
        technical_accuracy=score,
        factual_correctness=score,
        developer_value=score,
        duration_score=score,
        cta_score=score,
        tone_score=score,
        issues=[] if approved else ["needs work"],
        approved=approved,
        summary=f"score={score}",
    )


def test_high_quality_fixture_still_validates():
    script = load_script_fixture("high_quality.json")
    assert script.hook
    assert script.cta
    assert len(script.sections) >= 3


def test_poor_quality_fixture_still_validates_shape():
    script = load_script_fixture("poor_quality.json")
    assert script.title
    # Intentionally weak content for hard-fail checks elsewhere.


def test_high_quality_fixture_still_passes_gate_at_threshold():
    script = load_script_fixture("high_quality.json")
    state = WorkflowState.initial("regression").apply_update(
        generated_script=script,
        evaluation=_eval(8.5, approved=True),
        status=WorkflowStatus.EVALUATING,
    )
    decision, updates = apply_quality_gate(state, threshold=7.0)
    assert decision == GateDecision.PASS
    assert updates["status"] == WorkflowStatus.PASSED
