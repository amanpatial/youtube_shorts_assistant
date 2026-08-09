"""MemoryStore protocol + SQLAlchemy-backed JSON-vector store (CI-safe)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..persistence.models import MemoryItemRow
from ..persistence.session import ensure_schema, get_session_factory, session_scope
from .embeddings import cosine_similarity, embed_query


@dataclass
class MemoryHit:
    """Purpose: one retrieved memory row with similarity score."""

    id: str
    kind: str
    topic: str
    text: str
    summary: str | None
    overall_score: float | None
    similarity: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryRecord:
    """Purpose: payload to insert into long-term memory."""

    kind: str
    topic: str
    text: str
    summary: str | None = None
    overall_score: float | None = None
    execution_id: str | None = None
    metadata: dict[str, Any] | None = None
    embedding: list[float] | None = None


class MemoryStore(Protocol):
    """Purpose: swappable long-term memory backend (SQLite JSON or pgvector later)."""

    def upsert(self, record: MemoryRecord) -> str: ...

    def search(self, query: str, *, k: int = 3) -> list[MemoryHit]: ...

    def count(self) -> int: ...


_BANNED_META_KEYS = frozenset(
    {"api_key", "google_api_key", "password", "token", "secret", "authorization"}
)


def _clean_metadata(meta: dict[str, Any] | None) -> dict[str, Any]:
    if not meta:
        return {}
    return {k: v for k, v in meta.items() if k.lower() not in _BANNED_META_KEYS}


class SqlAlchemyMemoryStore:
    """Purpose: store embeddings as JSON; brute-force cosine (CI + local SQLite)."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def upsert(self, record: MemoryRecord) -> str:
        ensure_schema()
        emb = record.embedding or embed_query(f"{record.topic}\n{record.text}")
        row = MemoryItemRow(
            kind=record.kind,
            topic=record.topic.strip(),
            text=record.text.strip(),
            summary=(record.summary or "").strip() or None,
            embedding=list(emb),
            overall_score=record.overall_score,
            execution_id=uuid.UUID(record.execution_id) if record.execution_id else None,
            metadata_json=_clean_metadata(record.metadata),
        )
        if self._session is not None:
            self._session.add(row)
            self._session.flush()
            return str(row.id)
        with session_scope() as session:
            session.add(row)
            session.flush()
            return str(row.id)

    def search(self, query: str, *, k: int = 3) -> list[MemoryHit]:
        ensure_schema()
        q = embed_query(query)
        if self._session is not None:
            rows = list(self._session.scalars(select(MemoryItemRow)).all())
            return _rank(rows, q, k)
        with session_scope() as session:
            rows = list(session.scalars(select(MemoryItemRow)).all())
            return _rank(rows, q, k)

    def count(self) -> int:
        ensure_schema()
        if self._session is not None:
            return len(list(self._session.scalars(select(MemoryItemRow)).all()))
        with session_scope() as session:
            return len(list(session.scalars(select(MemoryItemRow)).all()))


def _rank(rows: list[MemoryItemRow], query_vec: list[float], k: int) -> list[MemoryHit]:
    scored: list[MemoryHit] = []
    for row in rows:
        emb = row.embedding or []
        sim = cosine_similarity(query_vec, emb)
        scored.append(
            MemoryHit(
                id=str(row.id),
                kind=row.kind,
                topic=row.topic,
                text=row.text,
                summary=row.summary,
                overall_score=row.overall_score,
                similarity=sim,
                metadata=dict(row.metadata_json or {}),
            )
        )
    scored.sort(key=lambda h: h.similarity, reverse=True)
    return scored[: max(0, k)]


class InMemoryMemoryStore:
    """Purpose: process-local store for unit tests (no DB)."""

    def __init__(self) -> None:
        self._items: list[tuple[str, MemoryRecord, list[float]]] = []

    def upsert(self, record: MemoryRecord) -> str:
        emb = record.embedding or embed_query(f"{record.topic}\n{record.text}")
        item_id = uuid.uuid4().hex
        cleaned = MemoryRecord(
            kind=record.kind,
            topic=record.topic,
            text=record.text,
            summary=record.summary,
            overall_score=record.overall_score,
            execution_id=record.execution_id,
            metadata=_clean_metadata(record.metadata),
            embedding=list(emb),
        )
        self._items.append((item_id, cleaned, list(emb)))
        return item_id

    def search(self, query: str, *, k: int = 3) -> list[MemoryHit]:
        q = embed_query(query)
        hits: list[MemoryHit] = []
        for item_id, rec, emb in self._items:
            hits.append(
                MemoryHit(
                    id=item_id,
                    kind=rec.kind,
                    topic=rec.topic,
                    text=rec.text,
                    summary=rec.summary,
                    overall_score=rec.overall_score,
                    similarity=cosine_similarity(q, emb),
                    metadata=dict(rec.metadata or {}),
                )
            )
        hits.sort(key=lambda h: h.similarity, reverse=True)
        return hits[: max(0, k)]

    def count(self) -> int:
        return len(self._items)


_store: MemoryStore | None = None


def get_memory_store() -> MemoryStore:
    """Purpose: process-scoped default SQLAlchemy memory store."""
    global _store
    if _store is None:
        ensure_schema()
        # Touch factory so engine is ready; store opens short sessions per call.
        get_session_factory()
        _store = SqlAlchemyMemoryStore()
    return _store


def reset_memory_store_for_tests() -> None:
    """Purpose: drop cached store between tests."""
    global _store
    _store = None


def set_memory_store_for_tests(store: MemoryStore | None) -> None:
    """Purpose: inject an InMemoryMemoryStore in unit tests."""
    global _store
    _store = store
