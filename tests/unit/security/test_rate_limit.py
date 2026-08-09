"""Phase 17 rate limiter unit tests."""

from __future__ import annotations

from shorts_assistant.security.rate_limit import RateLimiter


def test_rate_limit_blocks_after_n():
    lim = RateLimiter(limit=3, window_sec=60.0)
    assert lim.allow("k")[0] is True
    assert lim.allow("k")[0] is True
    assert lim.allow("k")[0] is True
    ok, retry = lim.allow("k")
    assert ok is False
    assert retry > 0


def test_rate_limit_per_key_isolated():
    lim = RateLimiter(limit=1, window_sec=60.0)
    assert lim.allow("a")[0] is True
    assert lim.allow("b")[0] is True
    assert lim.allow("a")[0] is False
