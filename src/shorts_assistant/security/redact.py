"""Secret redaction helpers for API/errors (Phase 17)."""

from __future__ import annotations

from ..observability import redact_text, safe_error_message


def redact_secret_text(text: str, *, limit: int | None = 500) -> str:
    """Purpose: strip key-like substrings from user-visible / logged strings."""
    return redact_text(text, limit=limit)


def safe_api_error(exc: BaseException, *, limit: int = 200) -> str:
    """Purpose: API error detail without secret material."""
    return safe_error_message(exc, limit=limit)
