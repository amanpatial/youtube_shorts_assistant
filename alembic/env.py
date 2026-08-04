"""Alembic environment for shorts_assistant domain tables."""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure src/ is importable when running alembic from repo root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shorts_assistant.config import settings  # noqa: E402
from shorts_assistant.persistence.models import Base  # noqa: E402
from shorts_assistant.persistence.session import _resolve_database_url  # noqa: E402

config = context.config
if config.config_file_name is not None:
    # Keep pytest / app loggers intact (default fileConfig disables them).
    fileConfig(config.config_file_name, disable_existing_loggers=False)


target_metadata = Base.metadata


def get_url() -> str:
    """Purpose: prefer runtime DATABASE_URL over alembic.ini placeholder."""
    return _resolve_database_url() or settings.database_url


def run_migrations_offline() -> None:
    """Purpose: emit SQL without a live DB connection."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Purpose: run migrations against a live engine."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=get_url().startswith("sqlite"),
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
