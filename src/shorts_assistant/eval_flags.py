"""Process-local flags for eval runs (not product CLI defaults).

Purpose: let ``eval.runner`` enable live judging without changing normal CLI
behavior. Uses a contextvar so nested calls stay scoped to one case/run.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_prefer_live_judge: ContextVar[bool] = ContextVar("prefer_live_judge", default=False)
_memory_retrieval_override: ContextVar[bool | None] = ContextVar(
    "memory_retrieval_override", default=None
)


def prefer_live_judge() -> bool:
    """Purpose: whether evaluator_node should call Gemini for this invoke."""
    return _prefer_live_judge.get()


def memory_retrieval_enabled() -> bool | None:
    """Purpose: eval override for MEMORY_RETRIEVAL; None → use settings."""
    return _memory_retrieval_override.get()


@contextmanager
def live_judge_mode(enabled: bool = True) -> Iterator[None]:
    """Purpose: temporarily set live-judge preference for an eval case."""
    token = _prefer_live_judge.set(enabled)
    try:
        yield
    finally:
        _prefer_live_judge.reset(token)


@contextmanager
def memory_retrieval_mode(enabled: bool) -> Iterator[None]:
    """Purpose: force memory retrieval on/off for an eval A/B run."""
    token = _memory_retrieval_override.set(enabled)
    try:
        yield
    finally:
        _memory_retrieval_override.reset(token)
