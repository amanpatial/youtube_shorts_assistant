"""SQLAlchemy sync engine / session factory from DATABASE_URL."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ..config import PROJECT_ROOT, settings


def _resolve_database_url() -> str:
    """Purpose: prefer DATABASE_URL; fall back to deprecated SESSION_DB_URL."""
    url = (settings.database_url or "").strip()
    legacy = (settings.session_db_url or "").strip()
    # If SESSION_DB_URL is set and DATABASE_URL is still the baked-in default,
    # prefer the explicit legacy override for local/dev continuity.
    default_sqlite = f"sqlite+pysqlite:///{PROJECT_ROOT / 'data' / 'shorts.db'}"
    if legacy and (not url or url == default_sqlite):
        if legacy.startswith("sqlite+aiosqlite://"):
            return "sqlite+pysqlite://" + legacy.removeprefix("sqlite+aiosqlite://")
        return legacy
    if url:
        return url
    return default_sqlite


@lru_cache
def get_engine(url: str | None = None) -> Engine:
    """Purpose: one cached engine per process (or explicit URL for tests)."""
    resolved = url or _resolve_database_url()
    kwargs: dict = {"future": True}
    if resolved.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in resolved:
            kwargs["poolclass"] = StaticPool
    engine = create_engine(resolved, **kwargs)

    if resolved.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _sqlite_fk(dbapi_conn, _connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def reset_engine_cache() -> None:
    """Purpose: clear cached engine (tests that change DATABASE_URL)."""
    get_engine.cache_clear()


def get_session_factory(url: str | None = None) -> sessionmaker[Session]:
    """Purpose: bound Session factory for the given / default URL."""
    return sessionmaker(bind=get_engine(url), autoflush=False, autocommit=False)


def ensure_schema(url: str | None = None) -> None:
    """Purpose: create tables if missing (SQLite/local DX; prod uses Alembic)."""
    from .models import Base

    Base.metadata.create_all(bind=get_engine(url))


@contextmanager
def session_scope(url: str | None = None) -> Iterator[Session]:
    """Purpose: commit on success, rollback on error, always close."""
    factory = get_session_factory(url)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
