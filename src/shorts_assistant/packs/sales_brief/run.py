"""Traced entrypoints for the sales_brief pack graph."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.types import Command

from ...hitl import validate_decision_payload
from ...observability import (
    WorkflowTrace,
    configure_logging,
    finalize_trace,
    get_trace_id,
    log_event,
)
from ...persistence.repository import WorkflowRepository
from ...persistence.session import session_scope
from ...state import WorkflowStatus
from ...telemetry import setup_telemetry
from .graph import get_compiled_sales_brief_graph
from .state import BriefWorkflowState

logger = logging.getLogger(__name__)


def invoke_workflow(
    request: str,
    *,
    trace_id: str | None = None,
    max_iterations: int = 3,
    persist: bool = True,
) -> BriefWorkflowState:
    return run_until_human(
        request,
        trace_id=trace_id,
        max_iterations=max_iterations,
        persist=persist,
    )


def run_until_human(
    request: str,
    *,
    trace_id: str | None = None,
    max_iterations: int = 3,
    persist: bool = True,
) -> BriefWorkflowState:
    """Purpose: invoke until COMPLETED/FAILED or pause at AWAITING_HUMAN."""
    configure_logging()
    setup_telemetry()
    initial = BriefWorkflowState.initial(request, max_iterations=max_iterations)
    trace_kwargs = {}
    if trace_id:
        trace_kwargs["trace_id"] = trace_id

    with WorkflowTrace(**trace_kwargs) as trace:
        seeded = initial.apply_update(trace_id=trace.trace_id)
        execution_id: str | None = None

        if persist:
            from ...persistence.session import ensure_schema

            ensure_schema()
            with session_scope() as session:
                repo = WorkflowRepository(session)
                workflow_id = repo.create_workflow(request)
                execution_id = repo.start_execution(
                    workflow_id,
                    max_iterations=max_iterations,
                    trace_id=trace.trace_id,
                )
            seeded = seeded.apply_update(execution_id=execution_id)

        config = (
            {"configurable": {"thread_id": execution_id}}
            if execution_id is not None
            else {"configurable": {"thread_id": trace.trace_id}}
        )

        graph = get_compiled_sales_brief_graph()
        result = graph.invoke(seeded.to_dict(), config)
        final = _state_from_invoke(result, execution_id=execution_id)

        if final.status == WorkflowStatus.AWAITING_HUMAN:
            log_event(
                "hitl_pause",
                agent="runner",
                execution_id=final.execution_id,
                iteration=final.iteration,
                pack_id="sales_brief",
            )
            if persist and execution_id:
                _checkpoint_only(execution_id, final)
            return final

        return _finalize_run(trace, final, execution_id=execution_id, persist=persist)


def resume_with_decision(
    execution_id: str,
    *,
    decision: str,
    feedback: str | None = None,
    reviewer: str = "local",
    persist: bool = True,
) -> BriefWorkflowState:
    """Purpose: resume a paused sales_brief HITL run."""
    configure_logging()
    setup_telemetry()
    payload = validate_decision_payload(decision, feedback)
    payload["reviewer"] = reviewer

    config = {"configurable": {"thread_id": execution_id}}
    graph = get_compiled_sales_brief_graph()

    with WorkflowTrace() as trace:
        result = graph.invoke(Command(resume=payload), config)
        final = _state_from_invoke(result, execution_id=execution_id)
        if final.trace_id is None:
            final = final.apply_update(trace_id=trace.trace_id)

        if final.status == WorkflowStatus.AWAITING_HUMAN:
            if persist:
                _checkpoint_only(execution_id, final)
            return final

        return _finalize_run(trace, final, execution_id=execution_id, persist=persist)


def _state_from_invoke(
    result: dict[str, Any],
    *,
    execution_id: str | None,
) -> BriefWorkflowState:
    data = {k: v for k, v in result.items() if k != "__interrupt__"}
    if "__interrupt__" in result:
        data["status"] = WorkflowStatus.AWAITING_HUMAN.value
    final = BriefWorkflowState.from_dict(data)
    if execution_id and final.execution_id is None:
        final = final.apply_update(execution_id=execution_id)
    if final.trace_id is None:
        final = final.apply_update(trace_id=get_trace_id())
    return final


def _finalize_run(
    trace: WorkflowTrace,
    final: BriefWorkflowState,
    *,
    execution_id: str | None,
    persist: bool,
) -> BriefWorkflowState:
    if final.evaluation is not None:
        trace.note_score(float(final.evaluation.overall_score))
    finalize_trace(trace, final)

    if persist and execution_id:
        _persist_final(execution_id, final)

    return final


def _checkpoint_only(execution_id: str, state: BriefWorkflowState) -> None:
    try:
        with session_scope() as session:
            WorkflowRepository(session).checkpoint(execution_id, state.to_dict())
    except Exception:  # noqa: BLE001
        logger.warning("HITL checkpoint failed for %s", execution_id, exc_info=True)


def _persist_final(execution_id: str, final: BriefWorkflowState) -> None:
    """Purpose: checkpoint + finish (skip Shorts script_version tables)."""
    try:
        with session_scope() as session:
            repo = WorkflowRepository(session)
            repo.checkpoint(execution_id, final.to_dict())
            status_val = (
                final.status.value if hasattr(final.status, "value") else str(final.status)
            )
            repo.finish_execution(
                execution_id,
                final_status=status_val,
                error=final.error,
            )
            try:
                repo.record_agent_execution(
                    execution_id,
                    agent_name="sales_brief_runner",
                    iteration=final.iteration,
                    status=status_val,
                    error=final.error,
                )
            except Exception:  # noqa: BLE001
                logger.warning("record_agent_execution failed", exc_info=True)
    except Exception:  # noqa: BLE001
        logger.exception("persistence finish path failed for %s", execution_id)
        raise
