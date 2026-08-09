"""Sales brief domain schemas (wired into pack graph in Phase 23)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BriefSection(BaseModel):
    """Purpose: one labeled section of an account / opportunity brief."""

    label: str = Field(min_length=1)
    text: str = Field(min_length=1)


class BriefDraft(BaseModel):
    """Purpose: structured sales brief draft for a GTM prototype pack."""

    account_name: str = Field(min_length=1, max_length=200)
    opportunity: str = Field(min_length=1)
    executive_summary: str = Field(min_length=1)
    pain_points: list[str] = Field(default_factory=list)
    value_props: list[str] = Field(default_factory=list)
    recommended_next_step: str = Field(min_length=1)
    sections: list[BriefSection] = Field(default_factory=list)


class BriefEvaluation(BaseModel):
    """Purpose: quality judgment for a BriefDraft (mirrors Shorts eval shape)."""

    overall_score: float = Field(ge=0, le=10)
    clarity_score: float = Field(ge=0, le=10)
    relevance_score: float = Field(ge=0, le=10)
    actionability_score: float = Field(ge=0, le=10)
    issues: list[str] = Field(default_factory=list)
    approved: bool = False
    summary: str = ""


class BriefConcept(BaseModel):
    """Purpose: deliverable brief package after HITL approve (formatter analogue)."""

    title: str
    draft: BriefDraft
    evaluation: BriefEvaluation | None = None
    owner_notes: str = ""
