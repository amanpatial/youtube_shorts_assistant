"""Phase 5: quality gate loop control (no live LLM)."""

from __future__ import annotations

from tests.helpers import load_script_fixture

from shorts_assistant.demo_producers import REJECT_MARKER, RETRY_PASS_MARKER
from shorts_assistant.graph import build_graph, get_compiled_graph
from shorts_assistant.quality_gate import GateDecision, apply_quality_gate
from shorts_assistant.schemas import ScriptEvaluation
from shorts_assistant.state import WorkflowState, WorkflowStatus


def _script(name: str = "high_quality.json"):
    return load_script_fixture(name)


def _eval(
    score: float,
    *,
    approved: bool,
    summary: str = "",
) -> ScriptEvaluation:
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
        summary=summary or f"score={score}",
    )


def test_1_first_attempt_passes():
    script = _script()
    state = WorkflowState.initial("idea").apply_update(
        generated_script=script,
        evaluation=_eval(8.5, approved=True),
        status=WorkflowStatus.EVALUATING,
    )
    decision, updates = apply_quality_gate(state, threshold=7.0)
    assert decision == GateDecision.PASS
    assert updates["iteration"] == 1
    assert updates["status"] == WorkflowStatus.PASSED
    assert updates["best_score"] == 8.5
    assert updates["best_script"] == script


def test_2_fail_then_would_retry():
    script = _script()
    state = WorkflowState.initial("idea").apply_update(
        generated_script=script,
        evaluation=_eval(5.0, approved=False),
        status=WorkflowStatus.EVALUATING,
        iteration=0,
        max_iterations=3,
    )
    decision, updates = apply_quality_gate(state, threshold=7.0)
    assert decision == GateDecision.RETRY
    assert updates["iteration"] == 1
    assert updates["status"] == WorkflowStatus.SCRIPTING
    assert updates["best_score"] == 5.0


def test_3_all_fail_exhausted_restores_best():
    weak = _script("poor_quality.json")
    mid = _script()
    # Simulate third failure with mid as best from earlier
    state = WorkflowState.initial("idea").apply_update(
        generated_script=weak,
        evaluation=_eval(4.0, approved=False),
        best_script=mid,
        best_score=6.0,
        iteration=2,
        max_iterations=3,
        status=WorkflowStatus.EVALUATING,
    )
    decision, updates = apply_quality_gate(state, threshold=7.0)
    assert decision == GateDecision.EXHAUSTED
    assert updates["iteration"] == 3
    assert updates["status"] == WorkflowStatus.EXHAUSTED
    # best remains mid (score 6) — current 4 does not beat it
    assert updates.get("best_score", state.best_score) == 6.0
    assert updates["generated_script"] == mid


def test_4_max_iterations_no_retry():
    script = _script()
    state = WorkflowState.initial("idea", max_iterations=3).apply_update(
        generated_script=script,
        evaluation=_eval(5.0, approved=False),
        iteration=2,
        status=WorkflowStatus.EVALUATING,
    )
    decision, updates = apply_quality_gate(state, threshold=7.0)
    assert decision == GateDecision.EXHAUSTED
    assert updates["iteration"] == 3
    assert decision != GateDecision.RETRY


def test_5_evaluator_failure_missing_evaluation():
    script = _script()
    state = WorkflowState.initial("idea").apply_update(
        generated_script=script,
        evaluation=None,
        best_script=script,
        best_score=8.0,
        status=WorkflowStatus.EVALUATING,
    )
    decision, updates = apply_quality_gate(state, threshold=7.0)
    assert decision == GateDecision.FAIL
    assert updates["status"] == WorkflowStatus.FAILED
    # best preserved on state (gate does not clear it)
    assert state.best_script == script
    assert "best_script" not in updates or updates.get("best_script") == script


def test_6_malformed_path_via_missing_script():
    state = WorkflowState.initial("idea").apply_update(
        generated_script=None,
        evaluation=_eval(8.0, approved=True),
        status=WorkflowStatus.EVALUATING,
    )
    decision, updates = apply_quality_gate(state, threshold=7.0)
    assert decision == GateDecision.FAIL
    assert updates["status"] == WorkflowStatus.FAILED


def test_7_best_version_preserved_across_worse_scores():
    s6 = _script()
    s4 = _script("poor_quality.json")
    state = WorkflowState.initial("idea").apply_update(
        generated_script=s6,
        evaluation=_eval(6.0, approved=False),
        status=WorkflowStatus.EVALUATING,
    )
    _, u1 = apply_quality_gate(state, threshold=7.0)
    state = state.apply_update(**u1)

    state = state.apply_update(
        generated_script=s4,
        evaluation=_eval(4.0, approved=False),
        status=WorkflowStatus.EVALUATING,
    )
    _, u2 = apply_quality_gate(state, threshold=7.0)
    state = state.apply_update(**u2)

    state = state.apply_update(
        generated_script=s4,
        evaluation=_eval(5.0, approved=False),
        status=WorkflowStatus.EVALUATING,
    )
    decision, u3 = apply_quality_gate(state, threshold=7.0)
    final = state.apply_update(**u3)
    assert decision == GateDecision.EXHAUSTED
    assert final.best_score == 6.0
    assert final.best_script == s6
    assert final.generated_script == s6


def test_graph_has_quality_gate_and_max_iterations_default():
    g = build_graph()
    assert "quality_gate" in g.nodes
    assert "memory_retrieve" in g.nodes
    state = WorkflowState.initial("x")
    assert state.max_iterations == 3


def test_graph_retry_pass_marker():
    result = get_compiled_graph(with_checkpointer=False).invoke(
        WorkflowState.initial(f"Topic {RETRY_PASS_MARKER}").to_dict()
    )
    final = WorkflowState.from_dict(result)
    assert final.status == WorkflowStatus.COMPLETED
    assert final.iteration == 2  # fail once, pass on second
    assert final.final_short_concept is not None
    assert "Addressed feedback" in (final.generated_script.body if final.generated_script else "")


def test_graph_reject_exhausts_then_formats_best():
    result = get_compiled_graph(with_checkpointer=False).invoke(
        WorkflowState.initial(f"Weak {REJECT_MARKER}").to_dict()
    )
    final = WorkflowState.from_dict(result)
    assert final.iteration == 3
    assert final.status == WorkflowStatus.COMPLETED
    assert final.best_score is not None
    assert final.final_short_concept is not None
