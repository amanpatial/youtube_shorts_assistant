"""Phase 17 output policy unit tests."""

from __future__ import annotations

from shorts_assistant.config import Settings
from shorts_assistant.security.output_policy import check_output_policy


def test_blocks_fixture_phrase(monkeypatch):
    import shorts_assistant.security.output_policy as op

    monkeypatch.setattr(op, "settings", Settings(_env_file=None, output_policy_enabled=True))
    result = check_output_policy({"hook": "x", "body": "see [UNSAFE_CONTENT_FIXTURE] here"})
    assert result.allowed is False
    assert result.reasons


def test_allows_normal_script(monkeypatch):
    import shorts_assistant.security.output_policy as op

    monkeypatch.setattr(op, "settings", Settings(_env_file=None, output_policy_enabled=True))
    result = check_output_policy({"hook": "Ship typed state", "body": "Use LangGraph"})
    assert result.allowed is True
