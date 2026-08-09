"""Phase 22/23: vertical pack registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from shorts_assistant.packs import (
    UnknownPackError,
    active_graph_pack,
    get_pack,
    list_packs,
)
from shorts_assistant.packs.sales_brief.schemas import BriefDraft, BriefEvaluation


def test_list_packs_includes_pack0_and_sales_brief() -> None:
    ids = {p.pack_id for p in list_packs()}
    assert ids == {"youtube_shorts", "sales_brief"}


def test_youtube_shorts_is_active_graph() -> None:
    pack = get_pack("youtube_shorts")
    assert pack.active_graph is True
    assert pack.prompts_dir.is_dir()
    assert pack.smoke_dataset is not None
    assert Path(pack.smoke_dataset).is_file()
    assert "search_shorts" in pack.mcp_tool_allowlist
    assert active_graph_pack().pack_id == "youtube_shorts"


def test_sales_brief_is_active_graph() -> None:
    pack = get_pack("sales_brief")
    assert pack.active_graph is True
    assert pack.prompts_dir.is_dir()
    assert (pack.prompts_dir / "writer.txt").is_file()
    assert pack.smoke_dataset is not None
    assert Path(pack.smoke_dataset).is_file()


def test_unknown_pack_fails_closed() -> None:
    with pytest.raises(UnknownPackError, match="unknown PACK_ID"):
        get_pack("not_a_pack")


def test_sales_brief_schemas_validate() -> None:
    draft = BriefDraft(
        account_name="Acme",
        opportunity="Platform expansion",
        executive_summary="Expand seats into full platform.",
        pain_points=["Siloed analytics"],
        value_props=["Unified warehouse"],
        recommended_next_step="Book technical discovery with data lead.",
    )
    ev = BriefEvaluation(
        overall_score=8.0,
        clarity_score=8.0,
        relevance_score=8.0,
        actionability_score=8.0,
        approved=True,
        summary="Solid",
    )
    assert draft.account_name == "Acme"
    assert ev.approved is True


def test_get_pack_and_active_respect_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PACK_ID", "sales_brief")
    from shorts_assistant.config import get_settings

    get_settings.cache_clear()
    import shorts_assistant.config as cfg

    s = get_settings()
    monkeypatch.setattr(cfg, "settings", s)
    assert get_pack().pack_id == "sales_brief"
    assert active_graph_pack().pack_id == "sales_brief"
    get_settings.cache_clear()
