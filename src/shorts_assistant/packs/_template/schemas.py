"""Template domain schemas — replace with your vertical models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DraftDocument(BaseModel):
    """Purpose: primary artifact produced by the writer node."""

    title: str = Field(min_length=1)
    body: str = Field(min_length=1)


class DraftEvaluation(BaseModel):
    """Purpose: evaluator judgment (do not mutate the draft)."""

    overall_score: float = Field(ge=0, le=10)
    issues: list[str] = Field(default_factory=list)
    approved: bool = False
    summary: str = ""
