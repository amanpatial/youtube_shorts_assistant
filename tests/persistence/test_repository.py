"""Persistence: repository + checkpoint round-trip on SQLite (no Postgres)."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text

from shorts_assistant.checkpointer import reset_checkpointer_for_tests
from shorts_assistant.config import get_settings
from shorts_assistant.demo_producers import demo_script
from shorts_assistant.persistence.models import ScriptVersionRow
from shorts_assistant.persistence.repository import WorkflowRepository
from shorts_assistant.persistence.session import (
    ensure_schema,
    get_engine,
    reset_engine_cache,
    session_scope,
)
from shorts_assistant.schemas import ScriptEvaluation
from shorts_assistant.state import WorkflowState, WorkflowStatus


@pytest.fixture()
def sqlite_url(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    url = f"sqlite+pysqlite:///{db}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("CHECKPOINT_BACKEND", "memory")
    get_settings.cache_clear()
    reset_engine_cache()
    reset_checkpointer_for_tests()
    import shorts_assistant.config as cfg
    import shorts_assistant.persistence.session as sess

    monkeypatch.setattr(cfg, "settings", get_settings())
    monkeypatch.setattr(sess, "settings", get_settings())
    ensure_schema(url)
    yield url
    reset_engine_cache()
    reset_checkpointer_for_tests()
    get_settings.cache_clear()


def test_schema_tables_exist(sqlite_url):
    insp = inspect(get_engine(sqlite_url))
    tables = set(insp.get_table_names())
    assert {
        "workflows",
        "executions",
        "agent_executions",
        "script_versions",
        "evaluations",
    } <= tables


def test_alembic_upgrade_creates_tables(tmp_path, monkeypatch):
    """Purpose: Alembic head creates the five domain tables on a fresh SQLite file."""
    db = tmp_path / "alembic.db"
    url = f"sqlite+pysqlite:///{db}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    reset_engine_cache()
    import shorts_assistant.config as cfg
    import shorts_assistant.persistence.session as sess

    monkeypatch.setattr(cfg, "settings", get_settings())
    monkeypatch.setattr(sess, "settings", get_settings())

    root = Path(__file__).resolve().parents[2]
    alembic_cfg = Config(str(root / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic_cfg, "head")

    insp = inspect(get_engine(url))
    assert "workflows" in insp.get_table_names()
    assert "evaluations" in insp.get_table_names()


def test_create_execution_checkpoint_round_trip(sqlite_url):
    with session_scope(sqlite_url) as session:
        repo = WorkflowRepository(session)
        wf = repo.create_workflow("persist me")
        ex = repo.start_execution(wf, max_iterations=3, trace_id="wf_test")
        state = WorkflowState.initial("persist me").apply_update(
            trace_id="wf_test",
            execution_id=ex,
            status=WorkflowStatus.COMPLETED,
            research="notes",
            iteration=1,
            best_score=8.0,
        )
        repo.checkpoint(ex, state)
        execution_id = ex

    with session_scope(sqlite_url) as session:
        repo = WorkflowRepository(session)
        loaded = repo.load_checkpoint(execution_id)
        assert loaded is not None
        assert loaded.request == "persist me"
        assert loaded.research == "notes"
        assert loaded.best_score == 8.0
        assert loaded.trace_id == "wf_test"
        assert loaded.execution_id == execution_id


def test_script_versions_immutable_and_best_flag(sqlite_url):
    script_a = demo_script("a")
    script_b = demo_script("b")
    with session_scope(sqlite_url) as session:
        repo = WorkflowRepository(session)
        wf = repo.create_workflow("versions")
        ex = repo.start_execution(wf, trace_id="wf_v")
        v1 = repo.add_script_version(ex, iteration=1, script=script_a, is_best=True)
        v2 = repo.add_script_version(ex, iteration=2, script=script_b, is_best=True)
        rows = session.scalars(
            select(ScriptVersionRow).where(ScriptVersionRow.execution_id == UUID(ex))
        ).all()
        assert len(rows) == 2
        best = [r for r in rows if r.is_best]
        assert len(best) == 1
        assert str(best[0].id) == v2
        assert {str(r.id) for r in rows} == {v1, v2}


def test_evaluation_linked_and_finish(sqlite_url):
    script = demo_script("topic")
    evaluation = ScriptEvaluation(
        overall_score=8.5,
        hook_score=8.0,
        clarity_score=8.0,
        pacing_score=8.0,
        technical_accuracy=8.0,
        factual_correctness=8.0,
        developer_value=8.0,
        duration_score=8.0,
        cta_score=8.0,
        tone_score=8.0,
        issues=[],
        approved=True,
        summary="solid",
    )
    with session_scope(sqlite_url) as session:
        repo = WorkflowRepository(session)
        wf = repo.create_workflow("eval")
        ex = repo.start_execution(wf, trace_id="wf_e")
        sv = repo.add_script_version(ex, iteration=1, script=script, is_best=True)
        ev = repo.add_evaluation(ex, script_version_id=sv, evaluation=evaluation, iteration=1)
        repo.finish_execution(ex, final_status="COMPLETED")
        assert ev
        row = session.execute(text("SELECT final_status, finished_at FROM executions")).one()
        assert row[0] == "COMPLETED"
        assert row[1] is not None
