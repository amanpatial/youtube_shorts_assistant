"""Human-in-the-loop review node + routing (Phase 13)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from langgraph.errors import GraphInterrupt
from langgraph.types import interrupt

from .config import settings
from .failures import clear_error_fields, failure_update
from .observability import log_event
from .state import HumanDecision, WorkflowState, WorkflowStatus


def _preview(state: WorkflowState) -> dict[str, Any]:
    script = state.generated_script or state.best_script
    return {
        "execution_id": state.execution_id,
        "trace_id": state.trace_id,
        "status": WorkflowStatus.AWAITING_HUMAN.value,
        "best_score": state.best_score,
        "iteration": state.iteration,
        "human_revision_count": state.human_revision_count,
        "hook": script.hook if script else None,
        "title": script.title if script else None,
        "evaluation_summary": (state.evaluation.summary if state.evaluation is not None else None),
    }


def human_review_node(state: WorkflowState) -> dict:
    """Purpose: pause for human approve/reject/request_changes (or auto-approve).

    When ``HITL_REQUIRED=false``, auto-approves so CI/eval never block.
    When true, uses LangGraph ``interrupt``; resume payload is a decision dict.
    """
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

        # reject / request_changes → revise if rounds remain
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
    except Exception as exc:  # noqa: BLE001 — map to FAILED for invoke safety
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


def route_after_human(state: WorkflowState) -> str:
    """Purpose: map human review status to continue | revise | fail."""
    if state.status == WorkflowStatus.FAILED:
        return "fail"
    if state.status == WorkflowStatus.APPROVED:
        return "continue"
    if state.status == WorkflowStatus.SCRIPTING:
        return "revise"
    return "fail"


def validate_decision_payload(
    decision: str,
    feedback: str | None = None,
) -> dict[str, Any]:
    """Purpose: CLI/API validation before Command(resume=...)."""
    d, fb, _ = _parse_resume({"decision": decision, "feedback": feedback, "reviewer": "local"})
    return {"decision": d, "feedback": fb}
