"""Traced workflow entrypoint for CLI and eval.

Purpose: one place that binds trace_id, persistence, checkpointer, and graph invoke.
Phase 13: ``run_until_human`` / ``resume_with_decision`` for HITL pause/resume.
Phase 23: ``PACK_ID`` dispatches to Shorts (default) or sales_brief pack graph.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.types import Command

from .graph import get_compiled_graph
from .graph_ops import (
    get_thread_state,
    list_state_history,
    stream_workflow,
)
from .hitl import validate_decision_payload
from .observability import (
    WorkflowTrace,
    configure_logging,
    finalize_trace,
    get_trace_id,
    log_event,
)
from .packs import get_pack
from .packs.sales_brief.state import BriefWorkflowState
from .persistence.repository import WorkflowRepository
from .persistence.session import session_scope
from .state import WorkflowState, WorkflowStatus
from .telemetry import setup_telemetry

logger = logging.getLogger(__name__)

RunResult = WorkflowState | BriefWorkflowState


def invoke_workflow(
    request: str,
    *,
    trace_id: str | None = None,
    max_iterations: int = 3,
    persist: bool = True,
) -> RunResult:
    """Purpose: run the pack graph selected by ``PACK_ID`` (default Shorts)."""
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
) -> RunResult:
    """Purpose: invoke until COMPLETED/FAILED or pause at AWAITING_HUMAN.

    Dispatches on ``settings.pack_id`` / ``PACK_ID``:
    - ``youtube_shorts`` (default) → Shorts StateGraph
    - ``sales_brief`` → pack-local brief StateGraph
    """
    pack = get_pack()
    if pack.pack_id == "sales_brief":
        from .packs.sales_brief.run import run_until_human as brief_run

        return brief_run(
            request,
            trace_id=trace_id,
            max_iterations=max_iterations,
            persist=persist,
        )
    return _run_shorts_until_human(
        request,
        trace_id=trace_id,
        max_iterations=max_iterations,
        persist=persist,
    )


def _run_shorts_until_human(
    request: str,
    *,
    trace_id: str | None = None,
    max_iterations: int = 3,
    persist: bool = True,
) -> WorkflowState:
    """Purpose: Shorts Pack 0 invoke path (unchanged behavior)."""
    configure_logging()
    setup_telemetry()
    initial = WorkflowState.initial(request, max_iterations=max_iterations)
    trace_kwargs = {}
    if trace_id:
        trace_kwargs["trace_id"] = trace_id

    with WorkflowTrace(**trace_kwargs) as trace:
        seeded = initial.apply_update(trace_id=trace.trace_id)
        execution_id: str | None = None

        if persist:
            from .persistence.session import ensure_schema

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

        graph = get_compiled_graph()
        result = graph.invoke(seeded.to_dict(), config)
        final = _state_from_invoke(result, execution_id=execution_id)

        if final.status == WorkflowStatus.AWAITING_HUMAN:
            log_event(
                "hitl_pause",
                agent="runner",
                execution_id=final.execution_id,
                iteration=final.iteration,
            )
            if persist and execution_id:
                _checkpoint_only(execution_id, final)
            return final

        return _finalize_run(trace, final, execution_id=execution_id, persist=persist)


def run_with_execution(
    request: str,
    *,
    execution_id: str,
    max_iterations: int = 3,
    persist: bool = True,
) -> WorkflowState:
    """Purpose: run graph for a pre-created execution (API worker path)."""
    configure_logging()
    setup_telemetry()
    initial = WorkflowState.initial(request, max_iterations=max_iterations)

    with WorkflowTrace() as trace:
        seeded = initial.apply_update(
            trace_id=trace.trace_id,
            execution_id=execution_id,
        )
        config = {"configurable": {"thread_id": execution_id}}
        graph = get_compiled_graph()
        result = graph.invoke(seeded.to_dict(), config)
        final = _state_from_invoke(result, execution_id=execution_id)

        if final.status == WorkflowStatus.AWAITING_HUMAN:
            log_event(
                "hitl_pause",
                agent="runner",
                execution_id=final.execution_id,
                iteration=final.iteration,
            )
            if persist:
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
) -> RunResult:
    """Purpose: resume a paused HITL run with approve|reject|request_changes.

    Uses the same ``PACK_ID`` as the original run (keep env consistent for resume).
    """
    pack = get_pack()
    if pack.pack_id == "sales_brief":
        from .packs.sales_brief.run import resume_with_decision as brief_resume

        return brief_resume(
            execution_id,
            decision=decision,
            feedback=feedback,
            reviewer=reviewer,
            persist=persist,
        )

    configure_logging()
    setup_telemetry()
    payload = validate_decision_payload(decision, feedback)
    payload["reviewer"] = reviewer

    config = {"configurable": {"thread_id": execution_id}}
    graph = get_compiled_graph()

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
) -> WorkflowState:
    data = {k: v for k, v in result.items() if k != "__interrupt__"}
    if "__interrupt__" in result:
        data["status"] = WorkflowStatus.AWAITING_HUMAN.value
    final = WorkflowState.from_dict(data)
    if execution_id and final.execution_id is None:
        final = final.apply_update(execution_id=execution_id)
    if final.trace_id is None:
        final = final.apply_update(trace_id=get_trace_id())
    return final


def _finalize_run(
    trace: WorkflowTrace,
    final: WorkflowState,
    *,
    execution_id: str | None,
    persist: bool,
) -> WorkflowState:
    if final.evaluation is not None:
        trace.note_score(float(final.evaluation.overall_score))
    finalize_trace(trace, final)

    if persist and execution_id:
        _persist_final(execution_id, final)

    try:
        from .memory.writer import maybe_persist_memory

        maybe_persist_memory(final)
    except Exception:  # noqa: BLE001 — never break a good short
        logger.warning("memory persist hook failed", exc_info=True)

    return final


def _checkpoint_only(execution_id: str, state: WorkflowState) -> None:
    try:
        with session_scope() as session:
            WorkflowRepository(session).checkpoint(execution_id, state)
    except Exception:  # noqa: BLE001
        logger.warning("HITL checkpoint failed for %s", execution_id, exc_info=True)


def _persist_final(execution_id: str, final: WorkflowState) -> None:
    """Purpose: write checkpoint, versions, eval, and finish after invoke."""
    try:
        with session_scope() as session:
            repo = WorkflowRepository(session)
            repo.checkpoint(execution_id, final)
            script_version_id = None
            script = final.generated_script or final.best_script
            if script is not None:
                is_best = final.best_script is not None and script == final.best_script
                script_version_id = repo.add_script_version(
                    execution_id,
                    iteration=final.iteration,
                    script=script,
                    is_best=is_best or final.best_script is None,
                    version=final.script_version or None,
                )
            if final.evaluation is not None and script_version_id is not None:
                repo.add_evaluation(
                    execution_id,
                    script_version_id=script_version_id,
                    evaluation=final.evaluation,
                    iteration=final.iteration,
                )
            status_val = final.status.value if hasattr(final.status, "value") else str(final.status)
            repo.finish_execution(
                execution_id,
                final_status=status_val,
                error=final.error,
            )
            try:
                repo.record_agent_execution(
                    execution_id,
                    agent_name="runner",
                    iteration=final.iteration,
                    status=status_val,
                    error=final.error,
                )
            except Exception:  # noqa: BLE001 — fail-open on history
                logger.warning("record_agent_execution failed", exc_info=True)
    except Exception:  # noqa: BLE001 — surface in logs; do not hide finish failure
        logger.exception("persistence finish path failed for %s", execution_id)
        raise


def load_execution_state(execution_id: str) -> WorkflowState | None:
    """Purpose: reload domain checkpoint JSON into WorkflowState (restart survival)."""
    with session_scope() as session:
        repo = WorkflowRepository(session)
        return repo.load_checkpoint(execution_id)


# Phase 20: re-export stream / time-travel helpers for a single import surface.
__all__ = [
    "RunResult",
    "get_thread_state",
    "invoke_workflow",
    "list_state_history",
    "load_execution_state",
    "resume_with_decision",
    "run_until_human",
    "run_with_execution",
    "stream_workflow",
]
