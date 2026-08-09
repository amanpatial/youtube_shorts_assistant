"""Bridge claimed jobs to LangGraph run/resume (Phase 16/17)."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from contextlib import contextmanager
from typing import Any, TypeVar

from ..config import settings
from ..failures import classify_exception
from ..persistence.jobs import (
    JOB_AWAITING_HUMAN,
    JOB_FAILED,
    JOB_SUCCEEDED,
    TYPE_APPROVE,
    TYPE_REVISE,
    TYPE_RUN,
    JobRepository,
)
from ..persistence.repository import WorkflowRepository
from ..persistence.session import ensure_schema, session_scope
from ..run import resume_with_decision, run_with_execution
from ..security.output_policy import check_output_policy
from ..security.redact import safe_api_error
from ..state import FailureClass, WorkflowState, WorkflowStatus

logger = logging.getLogger(__name__)

T = TypeVar("T")


@contextmanager
def _hitl_override(enabled: bool | None) -> Iterator[None]:
    """Purpose: temporarily set HITL_REQUIRED for one job."""
    if enabled is None:
        yield
        return
    prev = settings.hitl_required
    settings.hitl_required = bool(enabled)
    try:
        yield
    finally:
        settings.hitl_required = prev


def process_one_job() -> bool:
    """Purpose: claim and process at most one job. Returns True if work ran."""
    ensure_schema()
    with session_scope() as session:
        jobs = JobRepository(session)
        job = jobs.claim_next()
        if job is None:
            return False
        job_id = str(job.id)
        workflow_id = str(job.workflow_id)
        job_type = job.job_type
        payload = dict(job.payload or {})
        execution_id = str(job.execution_id) if job.execution_id else None

    try:
        if job_type == TYPE_RUN:
            _run_pipeline(job_id, workflow_id, payload)
        elif job_type in {TYPE_APPROVE, TYPE_REVISE}:
            _resume(job_id, workflow_id, payload, execution_id=execution_id)
        else:
            _fail(job_id, workflow_id, f"unknown job_type: {job_type}")
    except Exception as exc:  # noqa: BLE001 — classify for retry
        _handle_failure(job_id, workflow_id, exc)
    return True


def _run_with_timeout(fn: Callable[[], T]) -> T:
    """Purpose: enforce JOB_TIMEOUT_SEC wall clock around graph work."""
    timeout = float(settings.job_timeout_sec)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeout as exc:
            future.cancel()
            raise TimeoutError(f"job exceeded JOB_TIMEOUT_SEC={timeout}") from exc


def _run_pipeline(job_id: str, workflow_id: str, payload: dict[str, Any]) -> None:
    topic = str(payload.get("topic") or "").strip()
    if not topic:
        with session_scope() as session:
            wf = WorkflowRepository(session).get_workflow(workflow_id)
            topic = (wf.request if wf else "") or ""
    if not topic:
        _fail(job_id, workflow_id, "missing topic")
        return

    max_iterations = int(payload.get("max_iterations") or 3)
    hitl = payload.get("hitl_required")
    hitl_flag = bool(hitl) if hitl is not None else None

    with session_scope() as session:
        wf_repo = WorkflowRepository(session)
        execution_id = wf_repo.start_execution(workflow_id, max_iterations=max_iterations)
        JobRepository(session).set_execution(job_id, execution_id)

    def _invoke() -> WorkflowState:
        with _hitl_override(hitl_flag):
            return run_with_execution(
                topic,
                execution_id=execution_id,
                max_iterations=max_iterations,
                persist=True,
            )

    try:
        final = _run_with_timeout(_invoke)
    except TimeoutError as exc:
        _fail(job_id, workflow_id, safe_api_error(exc))
        return
    _finalize_job(job_id, workflow_id, final)


def _resume(
    job_id: str,
    workflow_id: str,
    payload: dict[str, Any],
    *,
    execution_id: str | None,
) -> None:
    exe_id = execution_id or payload.get("execution_id")
    if not exe_id:
        _fail(job_id, workflow_id, "missing execution_id for resume")
        return
    decision = str(payload.get("decision") or "approve")
    feedback = payload.get("feedback")
    reviewer = str(payload.get("reviewer") or "api")

    def _invoke() -> WorkflowState:
        return resume_with_decision(
            str(exe_id),
            decision=decision,
            feedback=feedback,
            reviewer=reviewer,
            persist=True,
        )

    try:
        final = _run_with_timeout(_invoke)
    except TimeoutError as exc:
        _fail(job_id, workflow_id, safe_api_error(exc))
        return
    _finalize_job(job_id, workflow_id, final)


def _finalize_job(
    job_id: str, workflow_id: str, final: WorkflowState | WorkflowStatus | str
) -> None:
    if isinstance(final, WorkflowState):
        status_val = final.status.value if hasattr(final.status, "value") else str(final.status)
        if status_val == WorkflowStatus.COMPLETED.value:
            policy = check_output_policy(
                final.generated_script or final.best_script,
                final.final_short_concept,
            )
            if not policy.allowed:
                _fail(
                    job_id,
                    workflow_id,
                    "output_policy_blocked:" + ",".join(policy.reasons[:3]),
                )
                return
    else:
        status_val = final.value if hasattr(final, "value") else str(final)

    with session_scope() as session:
        jobs = JobRepository(session)
        if status_val == WorkflowStatus.AWAITING_HUMAN.value:
            jobs.complete(job_id, status=JOB_AWAITING_HUMAN)
            jobs.update_workflow_status(workflow_id, WorkflowStatus.AWAITING_HUMAN.value)
        elif status_val == WorkflowStatus.COMPLETED.value:
            jobs.complete(job_id, status=JOB_SUCCEEDED)
            jobs.update_workflow_status(workflow_id, "COMPLETED")
        elif status_val == WorkflowStatus.FAILED.value:
            jobs.complete(job_id, status=JOB_FAILED)
            jobs.update_workflow_status(workflow_id, "FAILED")
        else:
            jobs.complete(job_id, status=JOB_SUCCEEDED, last_error=f"status={status_val}")
            jobs.update_workflow_status(workflow_id, status_val)


def _fail(job_id: str, workflow_id: str, error: str) -> None:
    with session_scope() as session:
        jobs = JobRepository(session)
        jobs.complete(job_id, status=JOB_FAILED, last_error=error)
        jobs.update_workflow_status(workflow_id, "FAILED")


def _handle_failure(job_id: str, workflow_id: str, exc: BaseException) -> None:
    failure = classify_exception(exc)
    msg = f"{type(exc).__name__}: {exc}"
    logger.warning("job %s failed class=%s: %s", job_id, failure.value, msg)
    with session_scope() as session:
        jobs = JobRepository(session)
        if failure == FailureClass.TRANSIENT:
            requeued = jobs.retry_later(job_id, error=msg, delay_seconds=1.0)
            if not requeued:
                jobs.update_workflow_status(workflow_id, "FAILED")
            else:
                jobs.update_workflow_status(workflow_id, "QUEUED")
        else:
            jobs.complete(job_id, status=JOB_FAILED, last_error=msg)
            jobs.update_workflow_status(workflow_id, "FAILED")
