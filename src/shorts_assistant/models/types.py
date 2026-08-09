"""Task types for per-node model routing (Phase 14)."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

TaskName = Literal["research", "write", "evaluate", "visualize", "format"]


class TaskType(StrEnum):
    """Purpose: name the LLM task a model id is chosen for."""

    RESEARCH = "research"
    WRITE = "write"
    EVALUATE = "evaluate"
    VISUALIZE = "visualize"
    FORMAT = "format"


ALL_TASKS: tuple[TaskType, ...] = tuple(TaskType)
