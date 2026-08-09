"""Quality gate for sales_brief draft loop."""

from __future__ import annotations

from typing import Any

from ...config import settings
from ...failures import clear_error_fields, failure_update
from ...observability import log_event
from ...quality_gate import GateDecision
from ...state import WorkflowStatus
from .contracts import ContractValidationError, guard_draft, guard_evaluation
from .schemas import BriefDraft
from .state import BriefWorkflowState


def apply_quality_gate(
    state: BriefWorkflowState,
    *,
    threshold: float | None = None,
) -> tuple[GateDecision, dict[str, Any]]:
    """Purpose: PASS / RETRY / EXHAUSTED / FAIL for BriefDraft evaluations."""
    thresh = settings.quality_threshold if threshold is None else threshold

    try:
        draft = guard_draft(state.generated_draft, agent="quality_gate")
        evaluation = guard_evaluation(state.evaluation, agent="quality_gate")
    except ContractValidationError as exc:
        log_event(
            "gate_decision",
            agent="quality_gate",
            decision="FAIL",
            iteration=state.iteration,
            error=str(exc),
            pack_id="sales_brief",
        )
        return GateDecision.FAIL, failure_update("quality_gate", exc)

    score = float(evaluation.overall_score)
    updates: dict[str, Any] = {**clear_error_fields()}

    best_score = state.best_score
    best_draft: BriefDraft | None = state.best_draft
    if best_score is None or score > best_score:
        best_score = score
        best_draft = draft
        updates["best_score"] = best_score
        updates["best_draft"] = best_draft

    iteration = state.iteration + 1
    updates["iteration"] = iteration
    passed = bool(evaluation.approved) and score >= thresh

    if passed:
        updates["status"] = WorkflowStatus.PASSED
        updates["generated_draft"] = draft
        log_event(
            "gate_decision",
            agent="quality_gate",
            decision="PASS",
            iteration=iteration,
            evaluation_score=score,
            best_score=best_score,
            approved=evaluation.approved,
            pack_id="sales_brief",
        )
        return GateDecision.PASS, updates

    if iteration < state.max_iterations:
        updates["status"] = WorkflowStatus.SCRIPTING
        log_event(
            "gate_decision",
            agent="quality_gate",
            decision="RETRY",
            iteration=iteration,
            evaluation_score=score,
            best_score=best_score,
            approved=evaluation.approved,
            pack_id="sales_brief",
        )
        return GateDecision.RETRY, updates

    updates["status"] = WorkflowStatus.EXHAUSTED
    if best_draft is not None:
        updates["generated_draft"] = best_draft
    log_event(
        "gate_decision",
        agent="quality_gate",
        decision="EXHAUSTED",
        iteration=iteration,
        evaluation_score=score,
        best_score=best_score,
        approved=evaluation.approved,
        pack_id="sales_brief",
    )
    return GateDecision.EXHAUSTED, updates


def quality_gate_node(state: BriefWorkflowState) -> dict:
    if state.status == WorkflowStatus.FAILED:
        return {}
    try:
        _decision, updates = apply_quality_gate(state)
        return updates
    except Exception as exc:  # noqa: BLE001
        return failure_update("quality_gate", exc)


def route_after_gate(state: BriefWorkflowState) -> str:
    if state.status == WorkflowStatus.FAILED:
        return "fail"
    if state.status == WorkflowStatus.SCRIPTING:
        return "retry"
    if state.status in (WorkflowStatus.PASSED, WorkflowStatus.EXHAUSTED):
        return "continue"
    return "fail"
