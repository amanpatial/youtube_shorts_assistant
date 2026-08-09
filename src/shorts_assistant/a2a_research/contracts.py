"""A2A Research Agent request/response contracts (Phase 15)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ResearchRequest(BaseModel):
    """Purpose: task payload sent from Shorts graph → Research Agent."""

    topic: str = Field(min_length=1)
    audience: str = "developers"
    max_bullets: int = Field(default=8, ge=1, le=20)

    @field_validator("topic")
    @classmethod
    def strip_topic(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("topic must not be empty")
        return cleaned


class ResearchResponse(BaseModel):
    """Purpose: structured research brief returned by the Research Agent."""

    topic: str = Field(min_length=1)
    bullets: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    errors: list[str] = Field(default_factory=list)
    status: str = Field(
        default="completed",
        description="submitted | working | completed | failed | timeout",
    )


def response_to_research_text(response: ResearchResponse) -> str:
    """Purpose: flatten ResearchResponse into WorkflowState.research string."""
    lines: list[str] = [f"A2A research for: {response.topic}"]
    if response.bullets:
        lines.append("Bullets:")
        for b in response.bullets:
            lines.append(f"- {b}")
    if response.sources:
        lines.append("Sources: " + "; ".join(response.sources))
    if response.errors:
        lines.append("Errors: " + "; ".join(response.errors))
    lines.append(f"Confidence: {response.confidence:.2f}")
    return "\n".join(lines)
