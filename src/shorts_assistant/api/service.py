"""API orchestration helpers: enqueue, status, result, HITL enqueue."""

from __future__ import annotations

from typing import Any

from ..config import settings
from ..persistence.jobs import (
    JOB_AWAITING_HUMAN,
    JOB_FAILED,
    JOB_QUEUED,
    JOB_SUCCEEDED,
    TYPE_APPROVE,
    TYPE_REVISE,
    TYPE_RUN,
    JobRepository,
)
from ..persistence.repository import WorkflowRepository
from ..persistence.session import ensure_schema, session_scope
from ..security.auth import AuthContext
from ..security.input_guard import InputGuardError, guard_topic, strip_pii_for_storage
from ..security.output_policy import check_output_policy
from ..state import WorkflowStatus
from .pipeline import infer_agent_pipeline, live_checkpoint
from .schemas import (
    ApiStatus,
    CreateShortRequest,
    CreateShortResponse,
    EnqueueResponse,
    ResultResponse,
    StatusResponse,
    WorkflowListItem,
    WorkflowListResponse,
)


class ForbiddenError(PermissionError):
    """Purpose: authenticated but not owner of workflow."""


def _require_owner(wf: Any, auth: AuthContext) -> None:
    owner = getattr(wf, "owner_key_id", None)
    if owner and owner != auth.key_id:
        raise ForbiddenError("not owner of workflow")


def _map_status(
    *,
    workflow_status: str | None,
    job_status: str | None,
    execution_final: str | None,
    checkpoint_status: str | None,
) -> ApiStatus:
    """Purpose: collapse job/workflow/execution into one API status."""
    for candidate in (job_status, execution_final, checkpoint_status, workflow_status):
        if not candidate:
            continue
        c = candidate.lower()
        if c in {"queued", "created"}:
            return "queued"
        if c in {"awaiting_human", JOB_AWAITING_HUMAN}:
            return "awaiting_human"
        if c in {
            "running",
            "researching",
            "scripting",
            "evaluating",
            "visualizing",
            "formatting",
            "approved",
            "passed",
            "exhausted",
        }:
            return "running"
        if c in {"completed", "succeeded", JOB_SUCCEEDED}:
            return "succeeded"
        if c in {"failed", JOB_FAILED}:
            return "failed"
        if c == "cancelled":
            return "cancelled"
    return "queued"


def enqueue_short(
    body: CreateShortRequest,
    *,
    auth: AuthContext,
    idempotency_key: str | None,
) -> CreateShortResponse:
    """Purpose: create workflow + queued run_pipeline job; return 202 payload."""
    try:
        guarded = guard_topic(body.topic)
    except InputGuardError as exc:
        raise ValueError(str(exc)) from exc

    topic_for_storage = (
        strip_pii_for_storage(guarded.topic) if guarded.pii_detected else guarded.topic
    )
    hitl_required = bool(body.hitl_required or guarded.force_hitl)

    ensure_schema()
    with session_scope() as session:
        jobs = JobRepository(session)
        if idempotency_key:
            existing = jobs.get_by_idempotency(idempotency_key)
            if existing is not None:
                wf = WorkflowRepository(session).get_workflow(str(existing.workflow_id))
                if wf is not None:
                    _require_owner(wf, auth)
                return CreateShortResponse(
                    workflow_id=str(existing.workflow_id),
                    status="queued"
                    if existing.status == JOB_QUEUED
                    else _map_status(
                        workflow_status=None,
                        job_status=existing.status,
                        execution_final=None,
                        checkpoint_status=None,
                    ),
                )

        wf_repo = WorkflowRepository(session)
        workflow_id = wf_repo.create_workflow(
            topic_for_storage,
            status="QUEUED",
            owner_key_id=auth.key_id,
        )
        jobs.enqueue(
            workflow_id=workflow_id,
            job_type=TYPE_RUN,
            payload={
                "topic": guarded.topic,
                "fenced_topic": guarded.fenced_topic,
                "audience": body.audience,
                "hitl_required": hitl_required,
                "max_iterations": body.max_iterations,
                "injection_suspected": guarded.injection_suspected,
                "pii_detected": guarded.pii_detected,
            },
            idempotency_key=idempotency_key,
            max_attempts=settings.job_max_attempts,
        )
        return CreateShortResponse(workflow_id=workflow_id, status="queued")


def get_status(workflow_id: str, *, auth: AuthContext) -> StatusResponse:
    ensure_schema()
    with session_scope() as session:
        wf_repo = WorkflowRepository(session)
        wf = wf_repo.get_workflow(workflow_id)
        if wf is None:
            raise KeyError(workflow_id)
        _require_owner(wf, auth)
        jobs = JobRepository(session)
        job = jobs.latest_for_workflow(workflow_id)
        exe = wf_repo.latest_execution(workflow_id)
        checkpoint_status = None
        iteration = None
        best_score = None
        error = None
        execution_id = None
        if exe is not None:
            execution_id = str(exe.id)
            iteration = exe.iteration
            best_score = exe.best_score
            error = exe.error
            if exe.state_checkpoint:
                checkpoint_status = exe.state_checkpoint.get("status")
            if exe.final_status:
                checkpoint_status = exe.final_status
        status = _map_status(
            workflow_status=wf.status,
            job_status=job.status if job else None,
            execution_final=exe.final_status if exe else None,
            checkpoint_status=checkpoint_status,
        )
        terminal = {
            WorkflowStatus.COMPLETED.value,
            "COMPLETED",
            JOB_SUCCEEDED,
            JOB_FAILED,
            "FAILED",
            WorkflowStatus.FAILED.value,
        }
        exe_terminal = (exe.final_status if exe else None) in terminal or (
            job and job.status in {JOB_SUCCEEDED, JOB_FAILED}
        )
        if not exe_terminal:
            if checkpoint_status == WorkflowStatus.AWAITING_HUMAN.value:
                status = "awaiting_human"
            if job and job.status == JOB_AWAITING_HUMAN:
                status = "awaiting_human"
        elif exe and exe.final_status == WorkflowStatus.COMPLETED.value:
            status = "succeeded"
        elif exe and exe.final_status == WorkflowStatus.FAILED.value:
            status = "failed"
        elif job and job.status == JOB_SUCCEEDED:
            status = "succeeded"
        elif job and job.status == JOB_FAILED:
            status = "failed"
        created_at = None
        if getattr(wf, "created_at", None) is not None:
            created_at = wf.created_at.isoformat()
        domain_cp = exe.state_checkpoint if exe is not None else None
        live_cp, next_nodes = live_checkpoint(execution_id, domain_cp)
        agents = infer_agent_pipeline(
            checkpoint=live_cp,
            api_status=status,
            next_nodes=next_nodes,
            error_node=(live_cp or {}).get("error_node") if isinstance(live_cp, dict) else None,
        )
        return StatusResponse(
            workflow_id=workflow_id,
            status=status,
            execution_id=execution_id,
            iteration=iteration,
            best_score=best_score,
            error=error or (job.last_error if job else None),
            topic=getattr(wf, "request", None),
            created_at=created_at,
            agents=agents,
        )


def list_shorts(
    *,
    auth: AuthContext,
    limit: int = 20,
    offset: int = 0,
) -> WorkflowListResponse:
    """Purpose: owner-scoped run history for the web UI."""
    ensure_schema()
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    with session_scope() as session:
        wf_repo = WorkflowRepository(session)
        jobs = JobRepository(session)
        rows = wf_repo.list_workflows(
            owner_key_id=auth.key_id,
            limit=limit,
            offset=offset,
        )
        items: list[WorkflowListItem] = []
        for wf in rows:
            exe = wf_repo.latest_execution(str(wf.id))
            job = jobs.latest_for_workflow(str(wf.id))
            checkpoint_status = None
            iteration = None
            best_score = None
            execution_id = None
            if exe is not None:
                execution_id = str(exe.id)
                iteration = exe.iteration
                best_score = exe.best_score
                if exe.state_checkpoint:
                    checkpoint_status = exe.state_checkpoint.get("status")
                if exe.final_status:
                    checkpoint_status = exe.final_status
            status = _map_status(
                workflow_status=wf.status,
                job_status=job.status if job else None,
                execution_final=exe.final_status if exe else None,
                checkpoint_status=checkpoint_status,
            )
            terminal = {
                WorkflowStatus.COMPLETED.value,
                "COMPLETED",
                JOB_SUCCEEDED,
                JOB_FAILED,
                "FAILED",
                WorkflowStatus.FAILED.value,
            }
            exe_terminal = (exe.final_status if exe else None) in terminal or (
                job and job.status in {JOB_SUCCEEDED, JOB_FAILED}
            )
            if not exe_terminal:
                if checkpoint_status == WorkflowStatus.AWAITING_HUMAN.value:
                    status = "awaiting_human"
                if job and job.status == JOB_AWAITING_HUMAN:
                    status = "awaiting_human"
            elif exe and exe.final_status == WorkflowStatus.COMPLETED.value:
                status = "succeeded"
            elif exe and exe.final_status == WorkflowStatus.FAILED.value:
                status = "failed"
            elif job and job.status == JOB_SUCCEEDED:
                status = "succeeded"
            elif job and job.status == JOB_FAILED:
                status = "failed"
            created_at = wf.created_at.isoformat() if wf.created_at else None
            items.append(
                WorkflowListItem(
                    workflow_id=str(wf.id),
                    topic=wf.request,
                    status=status,
                    execution_id=execution_id,
                    iteration=iteration,
                    best_score=best_score,
                    created_at=created_at,
                )
            )
        return WorkflowListResponse(items=items, limit=limit, offset=offset)


def get_result(workflow_id: str, *, auth: AuthContext) -> ResultResponse:
    status = get_status(workflow_id, auth=auth)
    if status.status in {"queued", "running"}:
        raise LookupError("not_ready")
    if status.status not in {"succeeded", "awaiting_human"}:
        raise LookupError(status.status)
    with session_scope() as session:
        wf_repo = WorkflowRepository(session)
        exe = wf_repo.latest_execution(workflow_id)
        if exe is None or not exe.state_checkpoint:
            raise LookupError("not_ready")
        cp = exe.state_checkpoint
        concept = cp.get("final_short_concept")
        script = cp.get("generated_script") or cp.get("best_script")
        if status.status == "succeeded" and not concept:
            raise LookupError("not_ready")
        policy = check_output_policy(script, concept)
        if not policy.allowed:
            raise LookupError("output_policy_blocked")
        mem_ids = cp.get("retrieved_memory_ids") or []
        if not isinstance(mem_ids, list):
            mem_ids = []
        live_cp, next_nodes = live_checkpoint(str(exe.id), cp)
        agents = infer_agent_pipeline(
            checkpoint=live_cp or cp,
            api_status=status.status,
            next_nodes=next_nodes,
            error_node=(live_cp or cp).get("error_node"),
        )
        return ResultResponse(
            workflow_id=workflow_id,
            status=status.status,
            final_short_concept=concept,
            generated_script=script,
            research=cp.get("research"),
            evaluation=cp.get("evaluation"),
            visual_concepts=cp.get("visual_concepts"),
            memory_context=cp.get("memory_context"),
            retrieved_memory_ids=[str(x) for x in mem_ids],
            trace_id=cp.get("trace_id"),
            execution_id=str(exe.id),
            script_version=cp.get("script_version"),
            max_iterations=cp.get("max_iterations"),
            human_decision=cp.get("human_decision"),
            human_feedback=cp.get("human_feedback"),
            human_reviewer=cp.get("human_reviewer"),
            human_revision_count=cp.get("human_revision_count"),
            error_class=cp.get("error_class"),
            error_node=cp.get("error_node"),
            agents=agents,
        )


def enqueue_approve(
    workflow_id: str,
    *,
    auth: AuthContext,
    reviewer: str,
    feedback: str | None,
) -> EnqueueResponse:
    return _enqueue_resume(
        workflow_id,
        auth=auth,
        job_type=TYPE_APPROVE,
        payload={
            "decision": "approve",
            "feedback": feedback,
            "reviewer": reviewer,
        },
    )


def enqueue_revise(
    workflow_id: str,
    *,
    auth: AuthContext,
    decision: str,
    feedback: str,
    reviewer: str,
) -> EnqueueResponse:
    return _enqueue_resume(
        workflow_id,
        auth=auth,
        job_type=TYPE_REVISE,
        payload={
            "decision": decision,
            "feedback": feedback,
            "reviewer": reviewer,
        },
    )


def _enqueue_resume(
    workflow_id: str,
    *,
    auth: AuthContext,
    job_type: str,
    payload: dict[str, Any],
) -> EnqueueResponse:
    ensure_schema()
    with session_scope() as session:
        wf_repo = WorkflowRepository(session)
        wf = wf_repo.get_workflow(workflow_id)
        if wf is None:
            raise KeyError(workflow_id)
        _require_owner(wf, auth)
        exe = wf_repo.latest_execution(workflow_id)
        if exe is None:
            raise LookupError("no_execution")
        cp_status = None
        if exe.state_checkpoint:
            cp_status = exe.state_checkpoint.get("status")
        if (
            cp_status != WorkflowStatus.AWAITING_HUMAN.value
            and exe.final_status != WorkflowStatus.AWAITING_HUMAN.value
        ):
            raise LookupError("not_awaiting_human")
        jobs = JobRepository(session)
        job = jobs.enqueue(
            workflow_id=workflow_id,
            job_type=job_type,
            payload={**payload, "execution_id": str(exe.id)},
            execution_id=str(exe.id),
            max_attempts=settings.job_max_attempts,
        )
        jobs.update_workflow_status(workflow_id, "QUEUED")
        return EnqueueResponse(
            workflow_id=workflow_id,
            job_id=str(job.id),
            status="queued",
        )
