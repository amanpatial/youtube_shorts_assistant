"""Fail-closed guards for sales_brief contracts."""

from __future__ import annotations

from ...contracts import ContractValidationError, parse_contract
from .schemas import BriefDraft, BriefEvaluation

__all__ = [
    "ContractValidationError",
    "guard_draft",
    "guard_evaluation",
    "parse_contract",
]


def guard_draft(draft: BriefDraft | None, *, agent: str = "writer") -> BriefDraft:
    if draft is None:
        raise ContractValidationError(agent, "generated_draft is required")
    return parse_contract(BriefDraft, draft, agent=agent)


def guard_evaluation(
    evaluation: BriefEvaluation | None,
    *,
    agent: str = "evaluator",
) -> BriefEvaluation:
    if evaluation is None:
        raise ContractValidationError(agent, "evaluation is required")
    return parse_contract(BriefEvaluation, evaluation, agent=agent)
