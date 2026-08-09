"""Synthetic judge for BriefDraft (offline CI / demo)."""

from __future__ import annotations

from .demo_producers import REJECT_MARKER, RETRY_PASS_MARKER
from .schemas import BriefDraft, BriefEvaluation


def synthetic_judge(
    draft: BriefDraft,
    request: str,
    *,
    research: str | None = None,
) -> BriefEvaluation:
    """Purpose: offline rubric-ish scores from brief heuristics (no API)."""
    if REJECT_MARKER in request:
        return BriefEvaluation(
            overall_score=3.5,
            clarity_score=3.0,
            relevance_score=4.0,
            actionability_score=3.0,
            issues=["Reject marker present in request"],
            approved=False,
            summary="Synthetic judge rejected request for fail-closed testing.",
        )

    if RETRY_PASS_MARKER in request:
        revised = "Addressed feedback" in draft.executive_summary
        if revised:
            return BriefEvaluation(
                overall_score=8.5,
                clarity_score=8.5,
                relevance_score=8.5,
                actionability_score=8.5,
                issues=[],
                approved=True,
                summary="Synthetic judge approved revised brief after retry.",
            )
        return BriefEvaluation(
            overall_score=5.0,
            clarity_score=5.0,
            relevance_score=5.0,
            actionability_score=5.0,
            issues=["Needs a revision pass addressing prior feedback"],
            approved=False,
            summary="Synthetic judge requires retry before approval.",
        )

    summary_len = len(draft.executive_summary.strip())
    next_len = len(draft.recommended_next_step.strip())
    clarity = 9.0 if summary_len >= 80 else 7.0 if summary_len >= 40 else 4.0
    relevance = 8.5 if research else 7.5
    actionability = 9.0 if next_len >= 24 else 7.0 if next_len >= 12 else 4.0
    if draft.pain_points and draft.value_props:
        relevance = min(10.0, relevance + 0.5)
    overall = round((clarity + relevance + actionability) / 3.0, 1)
    approved = overall >= 7.0 and actionability >= 6.0 and clarity >= 6.0

    return BriefEvaluation(
        overall_score=overall,
        clarity_score=clarity,
        relevance_score=relevance,
        actionability_score=actionability,
        issues=[] if approved else ["Synthetic judge: scores below approval bar"],
        approved=approved,
        summary=f"Synthetic rubric judgment for: {draft.account_name}",
    )


def judge_brief(
    draft: BriefDraft,
    request: str,
    *,
    research: str | None = None,
    prefer_live: bool = False,
) -> BriefEvaluation:
    """Purpose: produce BriefEvaluation (demo synthetic only in Phase 23)."""
    _ = prefer_live  # live Gemini judge deferred; offline path is the product for CI
    return synthetic_judge(draft, request, research=research)
