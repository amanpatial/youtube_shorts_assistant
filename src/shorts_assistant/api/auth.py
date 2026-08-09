"""API auth dependency — Bearer or X-API-Key (Phase 16/17)."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from ..security.auth import AuthContext, verify_api_key
from ..security.redact import safe_api_error


def require_api_key(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> AuthContext:
    """Purpose: authenticate via ``Authorization: Bearer`` or ``X-API-Key``."""
    presented: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        presented = authorization[7:].strip()
    elif x_api_key:
        presented = x_api_key
    try:
        return verify_api_key(presented)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=safe_api_error(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=safe_api_error(exc),
        ) from exc
