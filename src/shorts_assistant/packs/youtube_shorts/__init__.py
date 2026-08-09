"""Pack 0 — YouTube Shorts (live LangGraph pipeline)."""

from __future__ import annotations

from pathlib import Path

from ...config import PROJECT_ROOT
from ..protocol import VerticalPack

# Live prompts still live next to the package root (historical path).
_PROMPTS = Path(__file__).resolve().parents[2] / "prompts"


def build_pack() -> VerticalPack:
    """Purpose: metadata for the active Shorts product pack."""
    return VerticalPack(
        pack_id="youtube_shorts",
        display_name="YouTube Shorts concept",
        schemas_module="shorts_assistant.schemas",
        prompts_dir=_PROMPTS,
        eval_dataset=PROJECT_ROOT / "evals" / "shorts_v1_dataset.json",
        smoke_dataset=PROJECT_ROOT / "evals" / "shorts_v1_smoke.json",
        mcp_tool_allowlist=(
            "list_recent_shorts",
            "search_shorts",
            "get_short",
        ),
        active_graph=True,
        description="Reference GTM pack: topic → research → script ↔ eval ↔ HITL → visuals.",
    )


PACK = build_pack()
