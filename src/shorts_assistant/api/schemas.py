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


class StatusResponse(BaseModel):
    workflow_id: str
    status: ApiStatus
    execution_id: str | None = None
    iteration: int | None = None
    best_score: float | None = None
    error: str | None = None


class ResultResponse(BaseModel):
    workflow_id: str
    status: ApiStatus
    final_short_concept: dict[str, Any] | None = None
    generated_script: dict[str, Any] | None = None


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
