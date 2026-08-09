"""Integration: HITL pause / approve / request_changes (offline demo producers)."""

from __future__ import annotations

import pytest

from shorts_assistant.checkpointer import reset_checkpointer_for_tests
from shorts_assistant.config import get_settings
from shorts_assistant.persistence.session import ensure_schema, reset_engine_cache
from shorts_assistant.run import resume_with_decision, run_until_human
from shorts_assistant.state import WorkflowStatus


@pytest.fixture()
def hitl_env(tmp_path, monkeypatch):
    db = tmp_path / "hitl.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db}")
    monkeypatch.setenv("CHECKPOINT_BACKEND", "memory")
    monkeypatch.setenv("HITL_REQUIRED", "true")
    monkeypatch.setenv("MAX_HUMAN_ROUNDS", "2")
    get_settings.cache_clear()
    reset_engine_cache()
    reset_checkpointer_for_tests()
    import shorts_assistant.checkpointer as cp
    import shorts_assistant.config as cfg
    import shorts_assistant.hitl as hitl
    import shorts_assistant.persistence.session as sess

    monkeypatch.setattr(cfg, "settings", get_settings())
    monkeypatch.setattr(sess, "settings", get_settings())
    monkeypatch.setattr(cp, "settings", get_settings())
    monkeypatch.setattr(hitl, "settings", get_settings())
    ensure_schema()
    yield
    reset_engine_cache()
    reset_checkpointer_for_tests()
    get_settings.cache_clear()


def test_hitl_pause_then_approve(hitl_env):
    paused = run_until_human("HITL approve topic")
    assert paused.status == WorkflowStatus.AWAITING_HUMAN
    assert paused.execution_id
    assert paused.generated_script is not None
    assert paused.visual_concepts is None

    final = resume_with_decision(paused.execution_id, decision="approve")
    assert final.status == WorkflowStatus.COMPLETED
    assert final.human_decision == "approve"
    assert final.visual_concepts is not None
    assert final.final_short_concept is not None


def test_hitl_request_changes_then_approve(hitl_env):
    paused = run_until_human("HITL revise topic")
    assert paused.status == WorkflowStatus.AWAITING_HUMAN

    mid = resume_with_decision(
        paused.execution_id,
        decision="request_changes",
        feedback="Make the CTA sharper",
    )
    # May pause again after rewrite+gate, or complete if auto path — with HITL on, pause again
    assert mid.status == WorkflowStatus.AWAITING_HUMAN
    assert mid.human_revision_count == 1
    assert mid.human_feedback == "Make the CTA sharper"

    final = resume_with_decision(mid.execution_id, decision="approve")
    assert final.status == WorkflowStatus.COMPLETED
    assert final.human_decision == "approve"


def test_hitl_disabled_auto_approves(tmp_path, monkeypatch):
    db = tmp_path / "nohitl.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db}")
    monkeypatch.setenv("CHECKPOINT_BACKEND", "memory")
    monkeypatch.setenv("HITL_REQUIRED", "false")
    get_settings.cache_clear()
    reset_engine_cache()
    reset_checkpointer_for_tests()
    import shorts_assistant.checkpointer as cp
    import shorts_assistant.config as cfg
    import shorts_assistant.hitl as hitl
    import shorts_assistant.persistence.session as sess

    monkeypatch.setattr(cfg, "settings", get_settings())
    monkeypatch.setattr(sess, "settings", get_settings())
    monkeypatch.setattr(cp, "settings", get_settings())
    monkeypatch.setattr(hitl, "settings", get_settings())
    ensure_schema()

    final = run_until_human("no human needed")
    assert final.status == WorkflowStatus.COMPLETED
    assert final.human_decision == "approve"
    assert final.human_reviewer == "auto"
