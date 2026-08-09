"""Phase 19: shutdown flag + production config validation."""

from __future__ import annotations

import pytest

from shorts_assistant.config import Settings
from shorts_assistant.runtime_lifecycle import (
    is_shutting_down,
    request_shutdown,
    reset_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_lifecycle():
    reset_for_tests()
    yield
    reset_for_tests()


def test_request_shutdown_sets_flag() -> None:
    assert is_shutting_down() is False
    request_shutdown()
    assert is_shutting_down() is True


def test_validate_for_production_skips_local() -> None:
    s = Settings(
        APP_ENV="local",
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        API_KEY="",
        GOOGLE_API_KEY="",
    )
    s.validate_for_production()  # no raise


def test_validate_for_production_rejects_sqlite() -> None:
    s = Settings(
        APP_ENV="production",
        DATABASE_URL="sqlite+pysqlite:///./data/shorts.db",
        API_KEY="k",
        GOOGLE_API_KEY="g",
    )
    with pytest.raises(ValueError, match="PostgreSQL"):
        s.validate_for_production()


def test_validate_for_production_requires_api_key() -> None:
    s = Settings(
        APP_ENV="staging",
        DATABASE_URL="postgresql+psycopg://u:p@localhost:5432/shorts",
        API_KEY="",
        API_KEYS="",
        GOOGLE_API_KEY="g",
    )
    with pytest.raises(ValueError, match="API_KEY"):
        s.validate_for_production()


def test_validate_for_production_requires_gemini_or_vertex() -> None:
    s = Settings(
        APP_ENV="production",
        DATABASE_URL="postgresql+psycopg://u:p@localhost:5432/shorts",
        API_KEY="k",
        GOOGLE_API_KEY="",
        GOOGLE_GENAI_USE_VERTEXAI="FALSE",
    )
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        s.validate_for_production()


def test_validate_for_production_ok() -> None:
    s = Settings(
        APP_ENV="production",
        DATABASE_URL="postgresql+psycopg://u:p@localhost:5432/shorts",
        API_KEY="k",
        GOOGLE_API_KEY="g",
    )
    s.validate_for_production()
