"""Vertical pack contract (Phase 22) — metadata for GTM / multi-vertical prototypes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class VerticalPack:
    """Purpose: describe a customer vertical without owning the LangGraph runtime.

    Packs with ``active_graph=True`` expose a runnable LangGraph. ``PACK_ID``
    selects which wired pack ``run_until_human`` dispatches to (default Pack 0
    ``youtube_shorts``). Stub packs keep ``active_graph=False`` until wired.
    """

    pack_id: str
    display_name: str
    schemas_module: str
    prompts_dir: Path
    eval_dataset: Path | None = None
    smoke_dataset: Path | None = None
    mcp_tool_allowlist: tuple[str, ...] = ()
    active_graph: bool = False
    description: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Purpose: JSON-friendly pack summary for CLI / docs."""
        return {
            "pack_id": self.pack_id,
            "display_name": self.display_name,
            "schemas_module": self.schemas_module,
            "prompts_dir": str(self.prompts_dir),
            "eval_dataset": str(self.eval_dataset) if self.eval_dataset else None,
            "smoke_dataset": str(self.smoke_dataset) if self.smoke_dataset else None,
            "mcp_tool_allowlist": list(self.mcp_tool_allowlist),
            "active_graph": self.active_graph,
            "description": self.description,
        }
