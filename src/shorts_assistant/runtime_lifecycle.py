"""Process lifecycle flags (Phase 19) — graceful shutdown for API / worker."""

from __future__ import annotations

_shutting_down = False


def request_shutdown() -> None:
    """Purpose: mark the process as draining (SIGTERM / lifespan end)."""
    global _shutting_down
    _shutting_down = True


def is_shutting_down() -> bool:
    """Purpose: true after shutdown was requested (LB should stop sending traffic)."""
    return _shutting_down


def reset_for_tests() -> None:
    """Purpose: clear shutdown flag between unit tests."""
    global _shutting_down
    _shutting_down = False
