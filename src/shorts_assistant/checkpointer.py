"""LangGraph checkpointer factory (MemorySaver vs PostgresSaver)."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from .config import settings

logger = logging.getLogger(__name__)

_memory: MemorySaver | None = None
_pg_cm: Any = None
_pg_saver: Any = None


def get_checkpointer():
    """Purpose: return process-scoped checkpointer for ``compile(checkpointer=...)``.

    ``CHECKPOINT_BACKEND=memory`` (default) → MemorySaver (CI/local).
    ``CHECKPOINT_BACKEND=postgres`` → PostgresSaver (requires psycopg URL).
    """
    global _memory, _pg_cm, _pg_saver
    backend = (settings.checkpoint_backend or "memory").strip().lower()
    if backend in {"memory", "mem", ""}:
        if _memory is None:
            _memory = MemorySaver()
        return _memory
    if backend == "postgres":
        if _pg_saver is None:
            from langgraph.checkpoint.postgres import PostgresSaver

            url = (
                settings.checkpoint_postgres_url or settings.database_url or settings.session_db_url
            )
            if not url or url.startswith("sqlite"):
                raise ValueError(
                    "CHECKPOINT_BACKEND=postgres requires CHECKPOINT_POSTGRES_URL "
                    "or a postgresql DATABASE_URL"
                )
            # PostgresSaver wants psycopg form (postgresql:// or postgresql+psycopg://)
            conn = url.replace("postgresql+psycopg://", "postgresql://", 1)
            _pg_cm = PostgresSaver.from_conn_string(conn)
            _pg_saver = _pg_cm.__enter__()
            _pg_saver.setup()
            logger.info("PostgresSaver checkpointer ready")
        return _pg_saver
    raise ValueError(f"Unknown CHECKPOINT_BACKEND: {backend!r}")


def reset_checkpointer_for_tests() -> None:
    """Purpose: drop cached savers between tests."""
    global _memory, _pg_cm, _pg_saver
    if _pg_cm is not None and _pg_saver is not None:
        try:
            _pg_cm.__exit__(None, None, None)
        except Exception:  # noqa: BLE001
            pass
    _memory = None
    _pg_cm = None
    _pg_saver = None
