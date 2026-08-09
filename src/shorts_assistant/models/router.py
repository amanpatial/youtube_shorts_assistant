"""Config-driven ModelRouter (Phase 14)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import registry
from .types import TaskType


@dataclass(frozen=True)
class RouteDecision:
    """Purpose: resolved model choice for one task invocation."""

    task: str
    model: str
    fallbacks: list[str] = field(default_factory=list)
    reason: str = ""

    def candidates(self) -> list[str]:
        """Purpose: primary then fallbacks (deduped, order preserved)."""
        seen: set[str] = set()
        out: list[str] = []
        for mid in (self.model, *self.fallbacks):
            if mid and mid not in seen:
                seen.add(mid)
                out.append(mid)
        return out


class ModelRouter:
    """Purpose: map task → model id + fallbacks from Settings."""

    def __init__(self, settings: Any) -> None:
        self._settings = settings

    def resolve(self, task: TaskType | str) -> RouteDecision:
        """Purpose: return RouteDecision for ``task`` (no network I/O)."""
        t = TaskType(task)
        return RouteDecision(
            task=t.value,
            model=registry.primary_for(self._settings, t),
            fallbacks=registry.fallbacks_for(self._settings, t),
            reason=registry.reason_for(t),
        )

    def next_after_failure(
        self,
        decision: RouteDecision,
        *,
        failed_models: set[str],
    ) -> str | None:
        """Purpose: pick next availability candidate not in ``failed_models``."""
        for mid in decision.candidates():
            if mid not in failed_models:
                return mid
        return None


def get_router(settings: Any | None = None) -> ModelRouter:
    """Purpose: build a router bound to process settings (or override)."""
    if settings is None:
        from ..config import settings as default_settings

        settings = default_settings
    return ModelRouter(settings)
