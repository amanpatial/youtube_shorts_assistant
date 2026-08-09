"""Workflow state for the sales_brief pack (Phase 23).

Separate from Shorts ``WorkflowState`` so BriefDraft never masquerades as ShortScript.
Reuses shared status / failure enums from the core package.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator

from ...state import FailureClass, HumanDecision, WorkflowStatus
from .schemas import BriefConcept, BriefDraft, BriefEvaluation

__all__ = [
    "BriefWorkflowState",
    "FailureClass",
    "HumanDecision",
    "WorkflowStatus",
]


class BriefWorkflowState(BaseModel):
    """Purpose: hold inputs/outputs for one sales-brief generation run."""

    request: str = Field(min_length=1)
    raw_idea: str = Field(min_length=1)
    trace_id: str | None = None
    execution_id: str | None = None
    research: str | None = None
    memory_context: str | None = None
    retrieved_memory_ids: list[str] = Field(default_factory=list)
    generated_draft: BriefDraft | None = None
    draft_version: int = Field(default=0, ge=0)
    evaluation: BriefEvaluation | None = None
    final_brief_concept: BriefConcept | None = None
    iteration: int = Field(default=0, ge=0)
    max_iterations: int = Field(default=3, ge=1)
    best_draft: BriefDraft | None = None
    best_score: float | None = None
    human_decision: HumanDecision | None = None
    human_feedback: str | None = None
    human_reviewer: str | None = None
    human_reviewed_at: datetime | None = None
    human_revision_count: int = Field(default=0, ge=0)
    status: WorkflowStatus = WorkflowStatus.INITIALIZED
    error: str | None = None
    error_class: FailureClass | None = None
    error_node: str | None = None

    @field_validator("best_score")
    @classmethod
    def best_score_in_range(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value < 0.0 or value > 10.0:
            raise ValueError("best_score must be between 0 and 10 inclusive")
        return value

    @classmethod
    def initial(cls, request: str, *, max_iterations: int = 3) -> Self:
        cleaned = request.strip()
        if not cleaned:
            raise ValueError("request must be a non-empty string")
        return cls(
            request=cleaned,
            raw_idea=cleaned,
            max_iterations=max_iterations,
            status=WorkflowStatus.INITIALIZED,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls.model_validate(data)

    def apply_update(self, **fields: Any) -> Self:
        payload = self.model_dump()
        payload.update(fields)
        return self.__class__.model_validate(payload)
