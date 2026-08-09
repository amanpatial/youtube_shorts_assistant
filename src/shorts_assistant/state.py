"""Workflow state: the shared data bag for one Shorts generation run.

Purpose: define every field the graph can read/write, with types and validation.
LangGraph passes this object between nodes; each node returns a partial update.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, field_validator

from .schemas import ScriptEvaluation, ShortConcept, ShortScript, VisualPlan

HumanDecision = Literal["approve", "reject", "request_changes"]


class FailureClass(StrEnum):
    """Purpose: classify why a run failed (infra vs quality vs bug).

    Written by: failure helpers / nodes on error paths.
    Read by: CLI, logs, later API — not by the Phase 5 quality gate.
    """

    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    QUALITY = "QUALITY"
    PROGRAMMING = "PROGRAMMING"


class WorkflowStatus(StrEnum):
    """Purpose: name the current step (or terminal outcome) of one run.

    Why it exists: nodes and the CLI need a single field to answer
    "where did this request stop?" without scanning every other field.

    Written by: each node when it finishes its step (or fails).
    Read by: later nodes (skip work if already FAILED), CLI exit code,
    and ``route_after_gate`` (PASSED / EXHAUSTED / SCRIPTING / FAILED).
    """

    INITIALIZED = "INITIALIZED"
    RESEARCHING = "RESEARCHING"
    SCRIPTING = "SCRIPTING"
    EVALUATING = "EVALUATING"
    PASSED = "PASSED"
    EXHAUSTED = "EXHAUSTED"
    AWAITING_HUMAN = "AWAITING_HUMAN"
    APPROVED = "APPROVED"
    VISUALIZING = "VISUALIZING"
    FORMATTING = "FORMATTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkflowState(BaseModel):
    """Purpose: hold all inputs, intermediates, and outputs for one Shorts run.

    Why it exists: without a typed shared state, nodes invent ad-hoc keys,
    typos go unnoticed, and you cannot test transitions. This is the
    LangGraph ``StateGraph`` schema (domain data, not framework internals).

    Field ownership (who primarily writes):
      request / raw_idea     → entrypoint (``initial``)
      research               → research_node
      generated_script       → scriptwriter_node (gate may restore best)
      evaluation             → evaluator_node
      visual_concepts        → visualizer_node
      final_short_concept    → formatter_node
      iteration / best_*     → quality_gate_node
      status / error*        → whichever node last updated (Phase 6 adds class/node)
      trace_id               → invoke_workflow / observability (Phase 9/10)
      execution_id           → persistence execution UUID (Phase 10)
      memory_context         → memory_retrieve_node (Phase 11)
      retrieved_memory_ids   → memory_retrieve_node (Phase 11)
      human_*                → human_review_node / approve CLI (Phase 13)
    """

    request: str = Field(min_length=1)
    raw_idea: str = Field(min_length=1)
    trace_id: str | None = None
    execution_id: str | None = None
    research: str | None = None
    memory_context: str | None = None
    retrieved_memory_ids: list[str] = Field(default_factory=list)
    generated_script: ShortScript | None = None
    script_version: int = Field(default=0, ge=0)
    evaluation: ScriptEvaluation | None = None
    visual_concepts: VisualPlan | None = None
    final_short_concept: ShortConcept | None = None
    iteration: int = Field(default=0, ge=0)
    max_iterations: int = Field(default=3, ge=1)
    best_script: ShortScript | None = None
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
        """Purpose: keep ``best_score`` on the same 0–10 scale as evaluation scores."""
        if value is None:
            return value
        if value < 0.0 or value > 10.0:
            raise ValueError("best_score must be between 0 and 10 inclusive")
        return value

    @classmethod
    def initial(cls, request: str, *, max_iterations: int = 3) -> Self:
        """Purpose: build a clean starting state from the user's topic string."""
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
        """Purpose: serialize state to JSON-friendly dict for invoke / CLI / storage."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Purpose: re-validate a dict (e.g. graph result) back into WorkflowState."""
        return cls.model_validate(data)

    def apply_update(self, **fields: Any) -> Self:
        """Purpose: return a new validated copy with selected fields changed."""
        payload = self.model_dump()
        payload.update(fields)
        return self.__class__.model_validate(payload)
