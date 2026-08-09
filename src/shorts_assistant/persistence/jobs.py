"""Job queue: enqueue / claim / complete (Phase 16)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .models import JobRow, WorkflowRow

JOB_QUEUED = "queued"
JOB_RUNNING = "running"
JOB_AWAITING_HUMAN = "awaiting_human"
JOB_SUCCEEDED = "succeeded"
JOB_FAILED = "failed"
JOB_CANCELLED = "cancelled"

TYPE_RUN = "run_pipeline"
TYPE_APPROVE = "resume_approve"
TYPE_REVISE = "resume_revise"


class JobRepository:
    """Purpose: durable job queue operations for API + worker."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_idempotency(self, key: str) -> JobRow | None:
        """Purpose: find prior job for Idempotency-Key replay."""
        return self.session.scalar(select(JobRow).where(JobRow.idempotency_key == key))

    def enqueue(
        self,
        *,
        workflow_id: str,
        job_type: str,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        max_attempts: int = 3,
        execution_id: str | None = None,
    ) -> JobRow:
        """Purpose: insert a queued job; return the row."""
        row = JobRow(
            workflow_id=uuid.UUID(workflow_id),
            execution_id=uuid.UUID(execution_id) if execution_id else None,
            job_type=job_type,
            payload=payload or {},
            status=JOB_QUEUED,
            idempotency_key=idempotency_key,
            max_attempts=max_attempts,
            next_run_at=datetime.now(UTC),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def claim_next(self) -> JobRow | None:
        """Purpose: claim one due queued job (PG SKIP LOCKED; SQLite UPDATE)."""
        now = datetime.now(UTC)
        bind = self.session.get_bind()
        dialect = bind.dialect.name if bind is not None else "sqlite"

        if dialect == "postgresql":
            result = self.session.execute(
                text(
                    """
                    SELECT id FROM jobs
                    WHERE status = :queued
                      AND (next_run_at IS NULL OR next_run_at <= :now)
                    ORDER BY created_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                    """
                ),
                {"queued": JOB_QUEUED, "now": now},
            )
            job_id = result.scalar_one_or_none()
            if job_id is None:
                return None
            row = self.session.get(JobRow, job_id)
        else:
            # SQLite / tests: pick oldest queued row then mark running.
            row = self.session.scalar(
                select(JobRow)
                .where(JobRow.status == JOB_QUEUED)
                .where((JobRow.next_run_at.is_(None)) | (JobRow.next_run_at <= now))
                .order_by(JobRow.created_at)
                .limit(1)
            )
            if row is None:
                return None

        if row is None:
            return None
        row.status = JOB_RUNNING
        row.attempts = int(row.attempts) + 1
        row.updated_at = now
        self.session.flush()
        return row

    def set_execution(self, job_id: str, execution_id: str) -> None:
        row = self.session.get(JobRow, uuid.UUID(job_id))
        if row is None:
            raise ValueError(f"unknown job_id: {job_id}")
        row.execution_id = uuid.UUID(execution_id)
        row.updated_at = datetime.now(UTC)
        self.session.flush()

    def complete(
        self,
        job_id: str,
        *,
        status: str,
        last_error: str | None = None,
    ) -> None:
        row = self.session.get(JobRow, uuid.UUID(job_id))
        if row is None:
            raise ValueError(f"unknown job_id: {job_id}")
        row.status = status
        row.last_error = last_error
        row.updated_at = datetime.now(UTC)
        self.session.flush()

    def retry_later(
        self,
        job_id: str,
        *,
        error: str,
        delay_seconds: float = 2.0,
    ) -> bool:
        """Purpose: requeue if attempts remain; else mark failed. Returns True if requeued."""
        row = self.session.get(JobRow, uuid.UUID(job_id))
        if row is None:
            raise ValueError(f"unknown job_id: {job_id}")
        row.last_error = error
        row.updated_at = datetime.now(UTC)
        if row.attempts < row.max_attempts:
            row.status = JOB_QUEUED
            row.next_run_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
            self.session.flush()
            return True
        row.status = JOB_FAILED
        self.session.flush()
        return False

    def latest_for_workflow(self, workflow_id: str) -> JobRow | None:
        return self.session.scalar(
            select(JobRow)
            .where(JobRow.workflow_id == uuid.UUID(workflow_id))
            .order_by(JobRow.created_at.desc())
            .limit(1)
        )

    def update_workflow_status(self, workflow_id: str, status: str) -> None:
        wf = self.session.get(WorkflowRow, uuid.UUID(workflow_id))
        if wf is not None:
            wf.status = status
            self.session.flush()
