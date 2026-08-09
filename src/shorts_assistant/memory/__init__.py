"""Long-term memory / RAG for Shorts generation context (Phase 11)."""

from .context import build_memory_context
from .retriever import retrieve_memories
from .store import (
    InMemoryMemoryStore,
    MemoryHit,
    MemoryRecord,
    MemoryStore,
    get_memory_store,
    reset_memory_store_for_tests,
    set_memory_store_for_tests,
)
from .writer import maybe_persist_memory

__all__ = [
    "InMemoryMemoryStore",
    "MemoryHit",
    "MemoryRecord",
    "MemoryStore",
    "build_memory_context",
    "get_memory_store",
    "maybe_persist_memory",
    "reset_memory_store_for_tests",
    "retrieve_memories",
    "set_memory_store_for_tests",
]
