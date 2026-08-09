"""LangGraph checkpointer factory (MemorySaver / SqliteSaver / PostgresSaver)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from .config import PROJECT_ROOT, settings

logger = logging.getLogger(__name__)

_memory: MemorySaver | None = None
_sqlite_cm: Any = None
_sqlite_saver: Any = None
_pg_cm: Any = None
_pg_saver: Any = None


def get_checkpointer():
    """Purpose: return process-scoped checkpointer for ``compile(checkpointer=...)``.

    ``CHECKPOINT_BACKEND``:
    - ``sqlite`` (default) → durable local file (CLI HITL pause/approve across processes)
    - ``memory`` → MemorySaver (ephemeral; fine for single-process tests)
    - ``postgres`` → PostgresSaver
    """
    global _memory, _sqlite_cm, _sqlite_saver, _pg_cm, _pg_saver
    backend = (settings.checkpoint_backend or "sqlite").strip().lower()
    if backend in {"memory", "mem"}:
        if _memory is None:
            _memory = MemorySaver()
        return _memory
    if backend in {"sqlite", "sqlite3"}:
        if _sqlite_saver is None:
            from langgraph.checkpoint.sqlite import SqliteSaver

            path = (settings.checkpoint_sqlite_path or "").strip()
            if not path:
                path = str(PROJECT_ROOT / "data" / "checkpoints.sqlite")
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            _sqlite_cm = SqliteSaver.from_conn_string(path)
            _sqlite_saver = _sqlite_cm.__enter__()
            _sqlite_saver.setup()
            logger.info("SqliteSaver checkpointer ready path=%s", path)
        return _sqlite_saver
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
    global _memory, _sqlite_cm, _sqlite_saver, _pg_cm, _pg_saver
    if _sqlite_cm is not None and _sqlite_saver is not None:
        try:
            _sqlite_cm.__exit__(None, None, None)
        except Exception:  # noqa: BLE001
            pass
    if _pg_cm is not None and _pg_saver is not None:
        try:
            _pg_cm.__exit__(None, None, None)
        except Exception:  # noqa: BLE001
            pass
    _memory = None
    _sqlite_cm = None
    _sqlite_saver = None
    _pg_cm = None
    _pg_saver = None
