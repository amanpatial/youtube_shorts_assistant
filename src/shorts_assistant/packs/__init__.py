"""Vertical pack registry (Phase 22)."""

from __future__ import annotations

from .protocol import VerticalPack
from .sales_brief import PACK as SALES_BRIEF_PACK
from .youtube_shorts import PACK as YOUTUBE_SHORTS_PACK

_REGISTRY: dict[str, VerticalPack] = {
    YOUTUBE_SHORTS_PACK.pack_id: YOUTUBE_SHORTS_PACK,
    SALES_BRIEF_PACK.pack_id: SALES_BRIEF_PACK,
}


class UnknownPackError(KeyError):
    """Purpose: fail closed when PACK_ID is not registered."""


def list_packs() -> list[VerticalPack]:
    """Purpose: return all registered packs (stable order by pack_id)."""
    return [_REGISTRY[k] for k in sorted(_REGISTRY)]


def get_pack(pack_id: str | None = None) -> VerticalPack:
    """Purpose: resolve pack by id (default: settings.pack_id)."""
    if pack_id is None or not str(pack_id).strip():
        from ..config import settings

        pack_id = settings.pack_id
    key = str(pack_id).strip()
    try:
        return _REGISTRY[key]
    except KeyError as exc:
        known = ", ".join(sorted(_REGISTRY))
        raise UnknownPackError(f"unknown PACK_ID={key!r}; known: {known}") from exc


def active_graph_pack() -> VerticalPack:
    """Purpose: pack selected for live invoke (settings.PACK_ID if wired).

    Multiple packs may have ``active_graph=True``; ``PACK_ID`` chooses which
    graph ``run_until_human`` dispatches to. Default remains ``youtube_shorts``.
    """
    pack = get_pack()
    if pack.active_graph:
        return pack
    raise RuntimeError(
        f"pack {pack.pack_id!r} has active_graph=False; "
        "set PACK_ID to a wired pack (e.g. youtube_shorts)"
    )


__all__ = [
    "UnknownPackError",
    "VerticalPack",
    "active_graph_pack",
    "get_pack",
    "list_packs",
]
