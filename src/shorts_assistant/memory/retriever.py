"""Retrieve top-k memories for a topic."""

from __future__ import annotations

from ..config import settings
from ..eval_flags import memory_retrieval_enabled
from .store import MemoryHit, MemoryStore, get_memory_store


def retrieve_memories(
    topic: str,
    *,
    k: int | None = None,
    store: MemoryStore | None = None,
) -> list[MemoryHit]:
    """Purpose: semantic top-k lookup; empty when retrieval disabled or no rows."""
    override = memory_retrieval_enabled()
    enabled = settings.memory_retrieval if override is None else override
    if not enabled:
        return []
    top_k = settings.memory_top_k if k is None else k
    backend = store or get_memory_store()
    return backend.search(topic.strip(), k=top_k)
