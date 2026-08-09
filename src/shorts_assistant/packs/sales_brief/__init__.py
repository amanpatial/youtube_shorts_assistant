"""Sales brief vertical pack (Phase 23 — live graph when PACK_ID=sales_brief)."""

from __future__ import annotations

from pathlib import Path

from ...config import PROJECT_ROOT
from ..protocol import VerticalPack

_DIR = Path(__file__).resolve().parent


def build_pack() -> VerticalPack:
    """Purpose: live sales-brief pack metadata + graph wiring."""
    return VerticalPack(
        pack_id="sales_brief",
        display_name="Sales account / opportunity brief",
        schemas_module="shorts_assistant.packs.sales_brief.schemas",
        prompts_dir=_DIR / "prompts",
        eval_dataset=None,
        smoke_dataset=PROJECT_ROOT / "evals" / "packs" / "sales_brief_v1_smoke.json",
        mcp_tool_allowlist=(),
        active_graph=True,
        description=(
            "Live pack: BriefDraft graph (research→write↔eval↔gate→HITL→format). "
            "Select with PACK_ID=sales_brief. Default Pack 0 remains youtube_shorts."
        ),
    )


PACK = build_pack()
