"""API key verification + stable owner key ids (Phase 17)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ..config import settings


@dataclass(frozen=True)
class AuthContext:
    """Purpose: authenticated caller identity for ownership checks."""

    key_id: str
    # Never log or return the raw key.


def key_id_for(api_key: str) -> str:
    """Purpose: short stable id from key material (not reversible)."""
    digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    return digest[:16]


def configured_api_keys() -> set[str]:
    """Purpose: accept API_KEY plus optional comma-separated API_KEYS."""
    keys: set[str] = set()
    primary = (settings.api_key or "").strip()
    if primary:
        keys.add(primary)
    extra = (getattr(settings, "api_keys", "") or "").strip()
    if extra:
        for part in extra.split(","):
            k = part.strip()
            if k:
                keys.add(k)
    return keys


def verify_api_key(presented: str | None) -> AuthContext:
    """Purpose: validate presented key; raise ValueError if missing/invalid."""
    allowed = configured_api_keys()
    if not allowed:
        raise RuntimeError("API_KEY is not configured")
    if not presented or not presented.strip():
        raise PermissionError("missing API key")
    key = presented.strip()
    if key not in allowed:
        raise PermissionError("invalid API key")
    return AuthContext(key_id=key_id_for(key))
