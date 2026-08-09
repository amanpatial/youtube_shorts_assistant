"""HITL review for sales_brief pack."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from langgraph.errors import GraphInterrupt
from langgraph.types import interrupt

from ...config import settings
from ...failures import clear_error_fields, failure_update
from ...hitl import validate_decision_payload
from ...observability import log_event
from ...state import HumanDecision, WorkflowStatus
from .state import BriefWorkflowState

__all__ = [
    "human_review_node",
    "route_after_human",
    "validate_decision_payload",
]


def _preview(state: BriefWorkflowState) -> dict[str, Any]:
    draft = state.generated_draft or state.best_draft
    return {
        "pack_id": "sales_brief",
        "execution_id": state.execution_id,
        "trace_id": state.trace_id,
        "status": WorkflowStatus.AWAITING_HUMAN.value,
        "best_score": state.best_score,
        "iteration": state.iteration,
        "human_revision_count": state.human_revision_count,
        "account_name": draft.account_name if draft else None,
        "opportunity": draft.opportunity if draft else None,
        "recommended_next_step": draft.recommended_next_step if draft else None,
        "evaluation_summary": (
            state.evaluation.summary if state.evaluation is not None else None
        ),
    }


def human_review_node(state: BriefWorkflowState) -> dict:
    """Purpose: pause for human approve/reject/request_changes (or auto-approve)."""
    if state.status == WorkflowStatus.FAILED:
        return {}
    try:
        if not settings.hitl_required:
            now = datetime.now(UTC)
            log_event(
                "human_decision",
                agent="human_review",
                decision="approve",
                reviewer="auto",
                feedback_len=0,
                execution_id=state.execution_id,
                pack_id="sales_brief",
            )
            return {
                "status": WorkflowStatus.APPROVED,
                "human_decision": "approve",
                "human_reviewer": "auto",
                "human_reviewed_at": now,
                "human_feedback": None,
                **clear_error_fields(),
            }

        raw = interrupt(_preview(state))
        decision, feedback, reviewer = _parse_resume(raw)
        now = datetime.now(UTC)
        log_event(
            "human_decision",
            agent="human_review",
            decision=decision,
            reviewer=reviewer,
            feedback_len=len(feedback or ""),
            execution_id=state.execution_id,
            pack_id="sales_brief",
        )

        if decision == "approve":
            return {
                "status": WorkflowStatus.APPROVED,
                "human_decision": decision,
                "human_feedback": feedback,
                "human_reviewer": reviewer,
                "human_reviewed_at": now,
                **clear_error_fields(),
            }

        rounds = state.human_revision_count + 1
        if rounds > settings.max_human_rounds:
            return {
                **failure_update(
                    "human_review",
                    RuntimeError(f"max_human_rounds ({settings.max_human_rounds}) exhausted"),
                ),
                "human_decision": decision,
                "human_feedback": feedback,
                "human_reviewer": reviewer,
                "human_reviewed_at": now,
                "human_revision_count": rounds,
            }

        return {
            "status": WorkflowStatus.SCRIPTING,
            "human_decision": decision,
            "human_feedback": feedback,
            "human_reviewer": reviewer,
            "human_reviewed_at": now,
            "human_revision_count": rounds,
            **clear_error_fields(),
        }
    except GraphInterrupt:
        raise
    except Exception as exc:  # noqa: BLE001
        return failure_update("human_review", exc)


def _parse_resume(raw: Any) -> tuple[HumanDecision, str | None, str]:
    if isinstance(raw, str):
        decision = raw.strip().lower()
        feedback = None
        reviewer = "local"
    elif isinstance(raw, dict):
        decision = str(raw.get("decision", "")).strip().lower()
        feedback = raw.get("feedback")
        if feedback is not None:
            feedback = str(feedback).strip() or None
        reviewer = str(raw.get("reviewer") or "local").strip() or "local"
    else:
        raise ValueError("resume payload must be str or dict")

    if decision not in {"approve", "reject", "request_changes"}:
        raise ValueError("decision must be approve|reject|request_changes")
    if decision == "request_changes" and not feedback:
        raise ValueError("feedback is required for request_changes")
    return decision, feedback, reviewer  # type: ignore[return-value]


def route_after_human(state: BriefWorkflowState) -> str:
    if state.status == WorkflowStatus.FAILED:
        return "fail"
    if state.status == WorkflowStatus.APPROVED:
        return "continue"
    if state.status == WorkflowStatus.SCRIPTING:
        return "revise"
    return "fail"
