"""Traced workflow entrypoint for CLI and eval.

Purpose: one place that binds trace_id, persistence, checkpointer, and graph invoke.
"""

from __future__ import annotations

import logging

from .graph import get_compiled_graph
from .observability import (
    WorkflowTrace,
    configure_logging,
    finalize_trace,
    get_trace_id,
)
from .persistence.repository import WorkflowRepository
from .persistence.session import session_scope
from .state import WorkflowState
from .telemetry import setup_telemetry

logger = logging.getLogger(__name__)


def invoke_workflow(
    request: str,
    *,
    trace_id: str | None = None,
    max_iterations: int = 3,
    persist: bool = True,
) -> WorkflowState:
    """Purpose: run the Shorts graph once under a WorkflowTrace.

    Creates domain workflow/execution rows when ``persist`` is True, compiles
    with a checkpointer, and uses ``thread_id=execution_id`` for resume.

    Returns: final ``WorkflowState`` (includes ``trace_id`` / ``execution_id``).
    """
    configure_logging()
    setup_telemetry()
    initial = WorkflowState.initial(request, max_iterations=max_iterations)
    trace_kwargs = {}
    if trace_id:
        trace_kwargs["trace_id"] = trace_id

    with WorkflowTrace(**trace_kwargs) as trace:
        seeded = initial.apply_update(trace_id=trace.trace_id)
        execution_id: str | None = None
        workflow_id: str | None = None

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

        config = None
        if execution_id is not None:
            config = {"configurable": {"thread_id": execution_id}}

        graph = get_compiled_graph()
        result = graph.invoke(seeded.to_dict(), config) if config else graph.invoke(
            seeded.to_dict()
        )
        final = WorkflowState.from_dict(result)

        if final.evaluation is not None:
            trace.note_score(float(final.evaluation.overall_score))
        finalize_trace(trace, final)

        if final.trace_id is None:
            final = final.apply_update(trace_id=get_trace_id())
        if execution_id and final.execution_id is None:
            final = final.apply_update(execution_id=execution_id)

        if persist and execution_id:
            _persist_final(execution_id, final)

        return final


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
