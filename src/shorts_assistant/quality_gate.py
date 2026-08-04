"""Deterministic quality gate: PASS / RETRY / EXHAUSTED / FAIL for the script loop.

Purpose: decide whether to rewrite the script, continue to visuals, or stop —
using structured evaluation + iteration limits, not the LLM's opinion alone.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from .config import settings
from .contracts import ContractValidationError, guard_evaluation, guard_script
from .failures import clear_error_fields, failure_update
from .observability import log_event
from .schemas import ShortScript
from .state import WorkflowState, WorkflowStatus


class GateDecision(StrEnum):
    """Purpose: routing outcome after one quality-gate evaluation."""

    PASS = "PASS"
    RETRY = "RETRY"
    EXHAUSTED = "EXHAUSTED"
    FAIL = "FAIL"


def apply_quality_gate(
    state: WorkflowState,
    *,
    threshold: float | None = None,
) -> tuple[GateDecision, dict[str, Any]]:
    """Purpose: pure gate policy — update best/iteration and choose next route.

    Why it exists: AI loops must hard-stop and keep best-so-far; this function
    is unit-tested without LangGraph.

    Returns: (decision, partial state update dict for the node to apply).
    """
    thresh = (
        settings.quality_threshold if threshold is None else threshold
    )

    try:
        script = guard_script(state.generated_script, agent="quality_gate")
        evaluation = guard_evaluation(state.evaluation, agent="quality_gate")
    except ContractValidationError as exc:
        log_event(
            "gate_decision",
            agent="quality_gate",
            decision="FAIL",
            iteration=state.iteration,
            error=str(exc),
        )
        return GateDecision.FAIL, failure_update("quality_gate", exc)

    score = float(evaluation.overall_score)
    updates: dict[str, Any] = {**clear_error_fields()}

    # Track best-so-far before deciding (never lose a better version).
    best_score = state.best_score
    best_script: ShortScript | None = state.best_script
    if best_score is None or score > best_score:
        best_score = score
        best_script = script
        updates["best_score"] = best_score
        updates["best_script"] = best_script

    iteration = state.iteration + 1
    updates["iteration"] = iteration

    passed = bool(evaluation.approved) and score >= thresh

    if passed:
        updates["status"] = WorkflowStatus.PASSED
        updates["generated_script"] = script
        log_event(
            "gate_decision",
            agent="quality_gate",
            decision="PASS",
            iteration=iteration,
            evaluation_score=score,
            best_score=best_score,
            approved=evaluation.approved,
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
        )
        return GateDecision.RETRY, updates

    updates["status"] = WorkflowStatus.EXHAUSTED
    if best_script is not None:
        updates["generated_script"] = best_script
    log_event(
        "gate_decision",
        agent="quality_gate",
        decision="EXHAUSTED",
        iteration=iteration,
        evaluation_score=score,
        best_score=best_score,
        approved=evaluation.approved,
    )
    return GateDecision.EXHAUSTED, updates


def quality_gate_node(state: WorkflowState) -> dict:
    """Purpose: LangGraph node wrapper around ``apply_quality_gate``."""
    if state.status == WorkflowStatus.FAILED:
        return {}
    try:
        _decision, updates = apply_quality_gate(state)
        return updates
    except Exception as exc:  # noqa: BLE001 — map to FAILED for invoke safety
        return failure_update("quality_gate", exc)


def route_after_gate(state: WorkflowState) -> str:
    """Purpose: map gate status to graph edge key: retry | continue | fail."""
    if state.status == WorkflowStatus.FAILED:
        return "fail"
    if state.status == WorkflowStatus.SCRIPTING:
        return "retry"
    if state.status in (WorkflowStatus.PASSED, WorkflowStatus.EXHAUSTED):
        return "continue"
    # Defensive default — do not loop forever
    return "fail"
