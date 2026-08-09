"""HTTP request/response models for the Shorts job API (Phase 16)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ApiStatus = Literal[
    "queued",
    "running",
    "awaiting_human",
    "succeeded",
    "failed",
    "cancelled",
]


class CreateShortRequest(BaseModel):
    topic: str = Field(min_length=1)
    audience: str = "developers"
    hitl_required: bool = False
    max_iterations: int = Field(default=3, ge=1, le=10)


class CreateShortResponse(BaseModel):
    workflow_id: str
    status: ApiStatus = "queued"


class AgentStep(BaseModel):
    id: str
    label: str
    state: Literal["pending", "running", "paused", "done", "failed"]


class StatusResponse(BaseModel):
    workflow_id: str
    status: ApiStatus
    execution_id: str | None = None
    iteration: int | None = None
    best_score: float | None = None
    error: str | None = None
    topic: str | None = None
    created_at: str | None = None
    agents: list[AgentStep] = Field(default_factory=list)


class WorkflowListItem(BaseModel):
    workflow_id: str
    topic: str
    status: ApiStatus
    execution_id: str | None = None
    iteration: int | None = None
    best_score: float | None = None
    created_at: str | None = None


class WorkflowListResponse(BaseModel):
    items: list[WorkflowListItem]
    limit: int
    offset: int


class ResultResponse(BaseModel):
    workflow_id: str
    status: ApiStatus
    final_short_concept: dict[str, Any] | None = None
    generated_script: dict[str, Any] | None = None
    research: str | None = None
    evaluation: dict[str, Any] | None = None
    visual_concepts: dict[str, Any] | None = None
    memory_context: str | None = None
    retrieved_memory_ids: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    execution_id: str | None = None
    script_version: int | None = None
    max_iterations: int | None = None
    human_decision: str | None = None
    human_feedback: str | None = None
    human_reviewer: str | None = None
    human_revision_count: int | None = None
    error_class: str | None = None
    error_node: str | None = None
    agents: list[AgentStep] = Field(default_factory=list)


class ApproveRequest(BaseModel):
    reviewer: str = "api"
    feedback: str | None = None


class ReviseRequest(BaseModel):
    feedback: str = Field(min_length=1)
    reviewer: str = "api"
    decision: Literal["reject", "request_changes"] = "request_changes"


class EnqueueResponse(BaseModel):
    workflow_id: str
    job_id: str
    status: ApiStatus = "queued"
