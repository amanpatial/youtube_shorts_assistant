"""In-process per-key rate limiter (Phase 17)."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class _Bucket:
    events: deque[float] = field(default_factory=deque)


class RateLimiter:
    """Purpose: allow at most ``limit`` events per ``window_sec`` per key_id."""

    def __init__(self, *, limit: int = 30, window_sec: float = 60.0) -> None:
        self.limit = max(1, int(limit))
        self.window_sec = float(window_sec)
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def allow(self, key_id: str) -> tuple[bool, float]:
        """Purpose: return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.setdefault(key_id, _Bucket())
            cutoff = now - self.window_sec
            while bucket.events and bucket.events[0] < cutoff:
                bucket.events.popleft()
            if len(bucket.events) >= self.limit:
                retry = self.window_sec - (now - bucket.events[0])
                return False, max(0.1, round(retry, 2))
            bucket.events.append(now)
            return True, 0.0

    def reset(self) -> None:
        """Purpose: clear state (tests)."""
        with self._lock:
            self._buckets.clear()


_default_limiter: RateLimiter | None = None
_limiter_lock = threading.Lock()


def get_rate_limiter(*, limit: int | None = None, window_sec: float = 60.0) -> RateLimiter:
    """Purpose: process-wide limiter (reconfigured when limit changes in tests)."""
    global _default_limiter
    from ..config import settings

    lim = int(limit if limit is not None else settings.api_rate_limit_per_min)
    with _limiter_lock:
        if _default_limiter is None or _default_limiter.limit != lim:
            _default_limiter = RateLimiter(limit=lim, window_sec=window_sec)
        return _default_limiter


def reset_rate_limiter_for_tests() -> None:
    global _default_limiter
    with _limiter_lock:
        if _default_limiter is not None:
            _default_limiter.reset()
        _default_limiter = None
