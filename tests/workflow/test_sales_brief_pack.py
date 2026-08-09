"""Phase 23: sales_brief live pack (offline demo producers)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shorts_assistant.checkpointer import reset_checkpointer_for_tests
from shorts_assistant.config import PROJECT_ROOT, get_settings
from shorts_assistant.demo_producers import REJECT_MARKER, RETRY_PASS_MARKER
from shorts_assistant.packs.sales_brief.demo_producers import parse_account_opportunity
from shorts_assistant.packs.sales_brief.graph import get_compiled_sales_brief_graph
from shorts_assistant.packs.sales_brief.quality_gate import GateDecision, apply_quality_gate
from shorts_assistant.packs.sales_brief.schemas import BriefDraft, BriefEvaluation
from shorts_assistant.packs.sales_brief.state import BriefWorkflowState
from shorts_assistant.persistence.session import ensure_schema, reset_engine_cache
from shorts_assistant.run import resume_with_decision, run_until_human
from shorts_assistant.state import WorkflowStatus


@pytest.fixture()
def brief_env(tmp_path, monkeypatch):
    db = tmp_path / "brief.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db}")
    monkeypatch.setenv("CHECKPOINT_BACKEND", "memory")
    monkeypatch.setenv("HITL_REQUIRED", "false")
    monkeypatch.setenv("PACK_ID", "sales_brief")
    get_settings.cache_clear()
    reset_engine_cache()
    reset_checkpointer_for_tests()
    import shorts_assistant.checkpointer as cp
    import shorts_assistant.config as cfg
    import shorts_assistant.packs.sales_brief.hitl as brief_hitl
    import shorts_assistant.packs.sales_brief.nodes as brief_nodes
    import shorts_assistant.packs.sales_brief.quality_gate as brief_gate
    import shorts_assistant.persistence.session as sess

    s = get_settings()
    monkeypatch.setattr(cfg, "settings", s)
    monkeypatch.setattr(sess, "settings", s)
    monkeypatch.setattr(cp, "settings", s)
    monkeypatch.setattr(brief_hitl, "settings", s)
    monkeypatch.setattr(brief_nodes, "settings", s)
    monkeypatch.setattr(brief_gate, "settings", s)
    ensure_schema()
    yield
    reset_engine_cache()
    reset_checkpointer_for_tests()
    get_settings.cache_clear()


def test_parse_account_opportunity() -> None:
    account, opp = parse_account_opportunity(
        "Acme Corp — expand existing analytics seat into full platform"
    )
    assert account == "Acme Corp"
    assert "expand" in opp


def test_quality_gate_pass() -> None:
    draft = BriefDraft(
        account_name="Acme",
        opportunity="Expansion",
        executive_summary="A" * 90,
        recommended_next_step="Book discovery with champion.",
    )
    state = BriefWorkflowState.initial("Acme — Expansion").apply_update(
        generated_draft=draft,
        evaluation=BriefEvaluation(
            overall_score=8.5,
            clarity_score=8.5,
            relevance_score=8.5,
            actionability_score=8.5,
            approved=True,
            summary="ok",
        ),
        status=WorkflowStatus.EVALUATING,
    )
    decision, updates = apply_quality_gate(state, threshold=7.0)
    assert decision == GateDecision.PASS
    assert updates["status"] == WorkflowStatus.PASSED


def test_offline_complete_path(brief_env) -> None:
    final = run_until_human("Acme Corp — expand analytics into platform")
    assert final.status == WorkflowStatus.COMPLETED
    assert isinstance(final, BriefWorkflowState)
    assert final.generated_draft is not None
    assert final.final_brief_concept is not None
    assert final.final_brief_concept.draft.account_name == "Acme Corp"
    assert final.human_decision == "approve"
    assert final.human_reviewer == "auto"


def test_retry_pass_marker(brief_env) -> None:
    final = run_until_human(f"{RETRY_PASS_MARKER} Globex — displace BI tool")
    assert final.status == WorkflowStatus.COMPLETED
    assert final.iteration >= 2
    assert final.evaluation is not None
    assert final.evaluation.approved is True


def test_reject_marker_exhausted_still_formats(brief_env) -> None:
    final = run_until_human(f"{REJECT_MARKER} Thin account — inbound demo")
    assert final.status == WorkflowStatus.COMPLETED
    assert final.iteration == 3
    assert final.final_brief_concept is not None


def test_hitl_pause_then_approve(tmp_path, monkeypatch) -> None:
    db = tmp_path / "brief_hitl.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db}")
    monkeypatch.setenv("CHECKPOINT_BACKEND", "memory")
    monkeypatch.setenv("HITL_REQUIRED", "true")
    monkeypatch.setenv("PACK_ID", "sales_brief")
    get_settings.cache_clear()
    reset_engine_cache()
    reset_checkpointer_for_tests()
    import shorts_assistant.checkpointer as cp
    import shorts_assistant.config as cfg
    import shorts_assistant.packs.sales_brief.hitl as brief_hitl
    import shorts_assistant.packs.sales_brief.nodes as brief_nodes
    import shorts_assistant.packs.sales_brief.quality_gate as brief_gate
    import shorts_assistant.persistence.session as sess

    s = get_settings()
    monkeypatch.setattr(cfg, "settings", s)
    monkeypatch.setattr(sess, "settings", s)
    monkeypatch.setattr(cp, "settings", s)
    monkeypatch.setattr(brief_hitl, "settings", s)
    monkeypatch.setattr(brief_nodes, "settings", s)
    monkeypatch.setattr(brief_gate, "settings", s)
    ensure_schema()

    paused = run_until_human("Northwind Bank — fraud detection POC")
    assert paused.status == WorkflowStatus.AWAITING_HUMAN
    assert paused.generated_draft is not None
    assert paused.final_brief_concept is None

    final = resume_with_decision(paused.execution_id, decision="approve")
    assert final.status == WorkflowStatus.COMPLETED
    assert final.human_decision == "approve"
    assert final.final_brief_concept is not None


def test_smoke_dataset_demo_invoke(brief_env) -> None:
    path = Path(PROJECT_ROOT) / "evals" / "packs" / "sales_brief_v1_smoke.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(payload["cases"]) == 5
    for case in payload["cases"]:
        topic = case["input"]["topic"]
        final = run_until_human(topic, persist=False)
        assert final.status == WorkflowStatus.COMPLETED, case["case_id"]
        assert final.final_brief_concept is not None


def test_ephemeral_graph_no_checkpointer() -> None:
    graph = get_compiled_sales_brief_graph(with_checkpointer=False)
    seeded = BriefWorkflowState.initial("Initech renewal — usage down").to_dict()
    result = graph.invoke(seeded)
    final = BriefWorkflowState.from_dict(
        {k: v for k, v in result.items() if k != "__interrupt__"}
    )
    assert final.status == WorkflowStatus.COMPLETED
