"""Phase 17 redact + auth helpers."""

from __future__ import annotations

import pytest

from shorts_assistant.config import Settings
from shorts_assistant.security.auth import key_id_for, verify_api_key
from shorts_assistant.security.redact import redact_secret_text


def test_redact_strips_google_style_key():
    text = "err GOOGLE_API_KEY=AIzaSyDummyKeyMaterial123456789012345 and sk-abcdef1234567890"
    cleaned = redact_secret_text(text)
    assert "AIza" not in cleaned
    assert "sk-abcdef" not in cleaned
    assert "REDACTED" in cleaned


def test_verify_api_key(monkeypatch):
    import shorts_assistant.security.auth as auth

    monkeypatch.setattr(
        auth,
        "settings",
        Settings(_env_file=None, api_key="alpha", api_keys="beta"),
    )
    ctx = verify_api_key("beta")
    assert ctx.key_id == key_id_for("beta")
    with pytest.raises(PermissionError):
        verify_api_key("gamma")
