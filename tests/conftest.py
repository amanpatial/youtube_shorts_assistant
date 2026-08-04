"""Shared pytest fixtures and LLM marker policy for the Shorts test pyramid.

Purpose: one place for fixture loaders and opt-in live-LLM skip rules so CI
stays offline by default (``pytest -m "not llm"``).
"""

from __future__ import annotations

import os

import pytest

from tests.helpers import load_script_fixture

# Re-export for convenience in tests that prefer conftest import paths.
__all__ = ["load_script_fixture", "script_fixture"]


def pytest_configure(config: pytest.Config) -> None:
    """Purpose: register the ``llm`` marker (also declared in pyproject.toml)."""
    config.addinivalue_line(
        "markers",
        "llm: calls a real LLM; excluded from default CI via -m 'not llm'",
    )


@pytest.fixture
def script_fixture():
    """Purpose: pytest fixture wrapper around ``load_script_fixture``."""

    def _load(name: str = "high_quality.json"):
        return load_script_fixture(name)

    return _load


def _has_live_credentials() -> bool:
    key = (os.environ.get("GOOGLE_API_KEY") or "").strip()
    use_vertex = (os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") or "").upper() in {
        "TRUE",
        "1",
        "YES",
    }
    return bool(key) or use_vertex


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Purpose: skip ``@pytest.mark.llm`` tests when no Gemini/Vertex credentials."""
    if item.get_closest_marker("llm") is not None and not _has_live_credentials():
        pytest.skip(
            "llm test requires GOOGLE_API_KEY or GOOGLE_GENAI_USE_VERTEXAI=TRUE"
        )
