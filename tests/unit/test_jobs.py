"""Unit tests for Phase 16 job queue."""

from __future__ import annotations

from uuid import UUID

import pytest

from shorts_assistant.checkpointer import reset_checkpointer_for_tests
from shorts_assistant.config import get_settings
from shorts_assistant.persistence.jobs import JOB_FAILED, TYPE_RUN, JobRepository
from shorts_assistant.persistence.models import JobRow
from shorts_assistant.persistence.repository import WorkflowRepository
from shorts_assistant.persistence.session import ensure_schema, reset_engine_cache, session_scope


@pytest.fixture()
def db_env(tmp_path, monkeypatch):
    db = tmp_path / "jobs.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db}")
    get_settings.cache_clear()
    reset_engine_cache()
    reset_checkpointer_for_tests()
    import shorts_assistant.config as cfg
    import shorts_assistant.persistence.session as sess

    monkeypatch.setattr(cfg, "settings", get_settings())
    monkeypatch.setattr(sess, "settings", get_settings())
    ensure_schema()
    yield
    reset_engine_cache()
    get_settings.cache_clear()


def test_enqueue_claim_complete(db_env):
    with session_scope() as session:
        wf = WorkflowRepository(session).create_workflow("topic", status="QUEUED")
        jobs = JobRepository(session)
        job = jobs.enqueue(workflow_id=wf, job_type=TYPE_RUN, payload={"topic": "topic"})
        job_id = str(job.id)

    with session_scope() as session:
        jobs = JobRepository(session)
        claimed = jobs.claim_next()
        assert claimed is not None
        assert str(claimed.id) == job_id
        assert claimed.attempts == 1
        assert claimed.status == "running"
        jobs.complete(job_id, status="succeeded")

    with session_scope() as session:
        assert JobRepository(session).claim_next() is None


def test_retry_then_fail(db_env):
    with session_scope() as session:
        wf = WorkflowRepository(session).create_workflow("t", status="QUEUED")
        job = JobRepository(session).enqueue(
            workflow_id=wf,
            job_type=TYPE_RUN,
            payload={},
            max_attempts=2,
        )
        job_id = str(job.id)

    with session_scope() as session:
        jobs = JobRepository(session)
        jobs.claim_next()
        assert jobs.retry_later(job_id, error="blip", delay_seconds=0) is True

    with session_scope() as session:
        jobs = JobRepository(session)
        jobs.claim_next()
        assert jobs.retry_later(job_id, error="blip2", delay_seconds=0) is False

    with session_scope() as session:
        row = session.get(JobRow, UUID(job_id))
        assert row is not None
        assert row.status == JOB_FAILED
