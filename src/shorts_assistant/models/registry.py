"""Load per-task model map from Settings (Phase 14)."""

from __future__ import annotations

from typing import Any

from .types import ALL_TASKS, TaskType


def _primary_field(task: TaskType) -> str:
    return {
        TaskType.RESEARCH: "model_research",
        TaskType.WRITE: "model_write",
        TaskType.EVALUATE: "model_evaluate",
        TaskType.VISUALIZE: "model_visualize",
        TaskType.FORMAT: "model_format",
    }[task]


def primary_for(settings: Any, task: TaskType | str) -> str:
    """Purpose: resolve primary model id; empty per-task → MODEL_NAME."""
    t = TaskType(task)
    override = str(getattr(settings, _primary_field(t), "") or "").strip()
    if override:
        return override
    return str(settings.model_name).strip()


def fallbacks_for(settings: Any, task: TaskType | str) -> list[str]:
    """Purpose: ordered availability fallbacks (excludes duplicate of primary)."""
    t = TaskType(task)
    primary = primary_for(settings, t)
    fb = str(getattr(settings, "model_fallback", "") or "").strip()
    if not fb:
        fb = str(settings.model_name).strip()
    if not fb or fb == primary:
        return []
    return [fb]


def reason_for(task: TaskType | str) -> str:
    """Purpose: short policy label for observability (quality/latency/cost)."""
    t = TaskType(task)
    return {
        TaskType.RESEARCH: "research:latency",
        TaskType.WRITE: "write:quality",
        TaskType.EVALUATE: "evaluate:quality",
        TaskType.VISUALIZE: "visualize:latency",
        TaskType.FORMAT: "format:cost",
    }[t]


def task_model_map(settings: Any) -> dict[str, str]:
    """Purpose: snapshot primary model per task (for eval artifacts)."""
    return {t.value: primary_for(settings, t) for t in ALL_TASKS}
