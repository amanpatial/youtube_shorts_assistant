"""Offline stand-ins for sales_brief (no LLM)."""

from __future__ import annotations

from ...demo_producers import REJECT_MARKER, RETRY_PASS_MARKER
from .schemas import BriefConcept, BriefDraft, BriefEvaluation, BriefSection

__all__ = [
    "REJECT_MARKER",
    "RETRY_PASS_MARKER",
    "demo_brief",
    "demo_format_brief",
    "demo_research",
    "parse_account_opportunity",
]


def parse_account_opportunity(request: str) -> tuple[str, str]:
    """Purpose: split ``Account — opportunity`` topics used in smoke cases."""
    text = request.strip()
    for sep in (" — ", " - ", " – ", ": "):
        if sep in text:
            left, right = text.split(sep, 1)
            account = left.strip() or "Unknown account"
            opportunity = right.strip() or text
            return account[:200], opportunity
    return "Prospect", text


def demo_research(request: str) -> str:
    """Purpose: fake account notes for the brief topic."""
    account, opportunity = parse_account_opportunity(request)
    return (
        f"Research notes for account={account}. Opportunity focus: {opportunity}. "
        "Use only public/context clues; do not invent pricing or confidential metrics."
    )


def demo_brief(
    request: str,
    research: str | None = None,
    *,
    evaluation: BriefEvaluation | None = None,
    memory_context: str | None = None,
    human_feedback: str | None = None,
) -> BriefDraft:
    """Purpose: build a schema-valid BriefDraft (optionally revised from issues)."""
    account, opportunity = parse_account_opportunity(request)
    summary = (
        f"{account} is evaluating {opportunity}. "
        f"{(research or '')[:160]}".strip()
    )
    pain_points = [
        "Fragmented tooling slows decisions",
        "Stakeholders need a crisp next step before committing time",
    ]
    value_props = [
        "Unified narrative for AE + SE alignment",
        "Concrete discovery agenda tied to the opportunity",
    ]
    next_step = f"Schedule a 30-minute discovery with the champion for {account}."

    if memory_context:
        summary = f"{summary} Inspired by past winning patterns (not copied)."

    if human_feedback:
        summary = (
            f"{summary} Human revision guidance: {human_feedback[:200]}. "
            "Tightened summary and next step for the reviewer."
        )
        next_step = f"Revised next step for {account}: confirm stakeholders and agenda."

    if evaluation and evaluation.issues:
        feedback = "; ".join(evaluation.issues[:3])
        summary = (
            f"{summary} Addressed feedback: {feedback}. "
            "Clarified pains, value props, and recommended next step."
        )
        next_step = f"Book a focused discovery call for {account} with an agenda."

    return BriefDraft(
        account_name=account,
        opportunity=opportunity,
        executive_summary=summary,
        pain_points=pain_points,
        value_props=value_props,
        recommended_next_step=next_step,
        sections=[
            BriefSection(label="summary", text=summary),
            BriefSection(label="next_step", text=next_step),
        ],
    )


def demo_format_brief(
    draft: BriefDraft,
    evaluation: BriefEvaluation | None = None,
) -> BriefConcept:
    """Purpose: package approved draft into BriefConcept deliverable."""
    return BriefConcept(
        title=f"{draft.account_name}: {draft.opportunity}"[:200],
        draft=draft,
        evaluation=evaluation,
        owner_notes="Demo offline brief package",
    )
