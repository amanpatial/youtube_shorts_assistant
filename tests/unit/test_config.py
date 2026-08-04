"""Tests for application settings."""

import pytest

from shorts_assistant.config import Settings


def test_settings_defaults(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")
    s = Settings(_env_file=None)
    assert s.model_name == "gemini-2.0-flash-001"
    assert s.app_name == "youtube_shorts_app"
    assert s.max_input_length == 2000
    assert s.llm_timeout_seconds == 30.0
    assert s.llm_max_attempts == 3
    assert s.live_judge_fallback is True


def test_validate_for_runtime_requires_api_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")
    s = Settings(_env_file=None)
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        s.validate_for_runtime()


def test_validate_for_runtime_allows_vertex_without_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    s = Settings(_env_file=None)
    s.validate_for_runtime()  # should not raise


def test_model_name_from_env(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "gemini-2.5-flash")
    s = Settings(_env_file=None)
    assert s.model_name == "gemini-2.5-flash"
