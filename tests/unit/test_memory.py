"""Unit: Phase 11 memory embeddings, context, writer, retrieve (no live LLM)."""

from __future__ import annotations

from shorts_assistant.demo_producers import demo_script
from shorts_assistant.eval_flags import memory_retrieval_mode
from shorts_assistant.memory.context import build_memory_context
from shorts_assistant.memory.embeddings import cosine_similarity, embed_query
from shorts_assistant.memory.retriever import retrieve_memories
from shorts_assistant.memory.store import InMemoryMemoryStore, MemoryHit, MemoryRecord
from shorts_assistant.memory.writer import maybe_persist_memory
from shorts_assistant.state import WorkflowState, WorkflowStatus


def test_similar_topics_rank_higher():
    store = InMemoryMemoryStore()
    store.upsert(
        MemoryRecord(
            kind="successful_hook",
            topic="LangGraph agent workflows",
            text="Stop overcomplicating LangGraph agents.",
            summary="typed state tip",
            overall_score=8.5,
        )
    )
    store.upsert(
        MemoryRecord(
            kind="successful_hook",
            topic="baking sourdough bread",
            text="Preheat the Dutch oven first.",
            summary="bread tip",
            overall_score=8.0,
        )
    )
    hits = store.search("build LangGraph multi-agent graphs", k=2)
    assert hits[0].topic == "LangGraph agent workflows"
    assert hits[0].similarity > hits[1].similarity


def test_context_respects_max_chars_and_min_score():
    hits = [
        MemoryHit(
            id="1",
            kind="successful_hook",
            topic="a",
            text="x" * 200,
            summary="x" * 200,
            overall_score=9.0,
            similarity=0.9,
        ),
        MemoryHit(
            id="2",
            kind="successful_hook",
            topic="b",
            text="low",
            summary="low",
            overall_score=3.0,
            similarity=0.8,
        ),
    ]
    ctx = build_memory_context(hits, max_chars=120, min_score=7.0)
    assert "low" not in ctx
    assert len(ctx) <= 120
    assert ctx.startswith("Past Shorts memory")


def test_writer_skips_below_threshold():
    store = InMemoryMemoryStore()
    script = demo_script("topic")
    state = WorkflowState.initial("topic").apply_update(
        status=WorkflowStatus.COMPLETED,
        generated_script=script,
        best_script=script,
        best_score=5.0,
    )
    ids = maybe_persist_memory(state, store=store)
    assert ids == []
    assert store.count() == 0


def test_writer_persists_and_redacts_secrets_in_metadata_path():
    store = InMemoryMemoryStore()
    script = demo_script("pytest fixtures")
    state = WorkflowState.initial("pytest fixtures").apply_update(
        status=WorkflowStatus.COMPLETED,
        generated_script=script,
        best_script=script,
        best_score=8.5,
        execution_id="11111111-1111-1111-1111-111111111111",
    )
    ids = maybe_persist_memory(state, store=store)
    assert len(ids) >= 2
    assert store.count() >= 2
    # Secret-like topic skipped
    bad = state.apply_update(request="leak api_key=supersecret value")
    assert maybe_persist_memory(bad, store=store) == []


def test_retrieve_respects_eval_override(monkeypatch):
    store = InMemoryMemoryStore()
    store.upsert(
        MemoryRecord(
            kind="successful_hook",
            topic="agents",
            text="hook",
            overall_score=8.0,
        )
    )
    monkeypatch.setattr("shorts_assistant.memory.retriever.get_memory_store", lambda: store)
    monkeypatch.setattr("shorts_assistant.memory.retriever.settings.memory_retrieval", True)
    with memory_retrieval_mode(False):
        assert retrieve_memories("agents") == []
    with memory_retrieval_mode(True):
        assert len(retrieve_memories("agents")) == 1


def test_embed_deterministic():
    a = embed_query("same text")
    b = embed_query("same text")
    assert a == b
    assert cosine_similarity(a, b) > 0.99
