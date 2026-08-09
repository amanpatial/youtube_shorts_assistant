"""LangGraph nodes for the sales_brief pack."""

from __future__ import annotations

from pydantic import ValidationError

from ...config import settings
from ...contracts import parse_contract
from ...failures import clear_error_fields, failure_update
from ...memory.context import build_memory_context
from ...memory.retriever import retrieve_memories
from ...state import WorkflowStatus
from .contracts import ContractValidationError, guard_draft
from .demo_producers import demo_brief, demo_format_brief, demo_research
from .judge import judge_brief
from .schemas import BriefDraft
from .state import BriefWorkflowState


def research_node(state: BriefWorkflowState) -> dict:
    if state.status == WorkflowStatus.FAILED:
        return {}
    try:
        notes = demo_research(state.request)
        return {
            "research": notes,
            "status": WorkflowStatus.RESEARCHING,
            **clear_error_fields(),
        }
    except Exception as exc:  # noqa: BLE001
        return failure_update("research", exc)


def memory_retrieve_node(state: BriefWorkflowState) -> dict:
    if state.status == WorkflowStatus.FAILED:
        return {}
    try:
        hits = retrieve_memories(state.request)
        context = build_memory_context(
            hits,
            max_chars=settings.memory_max_context_chars,
        )
        return {
            "memory_context": context or None,
            "retrieved_memory_ids": [h.id for h in hits],
            **clear_error_fields(),
        }
    except Exception:  # noqa: BLE001 — fail-open
        return {
            "memory_context": None,
            "retrieved_memory_ids": [],
        }


def writer_node(state: BriefWorkflowState) -> dict:
    if state.status == WorkflowStatus.FAILED:
        return {}
    try:
        draft = parse_contract(
            BriefDraft,
            demo_brief(
                state.request,
                state.research,
                evaluation=state.evaluation,
                memory_context=state.memory_context,
                human_feedback=state.human_feedback,
            ),
            agent="writer",
        )
        return {
            "generated_draft": draft,
            "draft_version": state.draft_version + 1,
            "status": WorkflowStatus.SCRIPTING,
            **clear_error_fields(),
        }
    except (ContractValidationError, ValidationError) as exc:
        return failure_update("writer", exc)
    except Exception as exc:  # noqa: BLE001
        return failure_update("writer", exc)


def evaluator_node(state: BriefWorkflowState) -> dict:
    if state.status == WorkflowStatus.FAILED:
        return {}
    try:
        draft = guard_draft(state.generated_draft, agent="evaluator")
        before = draft.model_dump()
        evaluation = judge_brief(
            draft,
            state.request,
            research=state.research,
            prefer_live=False,
        )
        if draft.model_dump() != before:
            return failure_update(
                "evaluator",
                RuntimeError("invariant violated: draft was mutated"),
            )
        return {
            "evaluation": evaluation,
            "status": WorkflowStatus.EVALUATING,
            **clear_error_fields(),
        }
    except ContractValidationError as exc:
        return {
            **failure_update("evaluator", exc),
            "evaluation": None,
        }
    except Exception as exc:  # noqa: BLE001
        return failure_update("evaluator", exc)


def formatter_node(state: BriefWorkflowState) -> dict:
    if state.status == WorkflowStatus.FAILED:
        return {}
    if state.status not in (
        WorkflowStatus.APPROVED,
        WorkflowStatus.PASSED,
        WorkflowStatus.EXHAUSTED,
    ):
        return failure_update(
            "formatter",
            RuntimeError("expected APPROVED (or PASS/EXHAUST without HITL)"),
        )
    try:
        draft = guard_draft(state.generated_draft, agent="formatter")
        concept = demo_format_brief(draft, state.evaluation)
        return {
            "final_brief_concept": concept,
            "status": WorkflowStatus.COMPLETED,
            **clear_error_fields(),
        }
    except ContractValidationError as exc:
        return failure_update("formatter", exc)
    except Exception as exc:  # noqa: BLE001
        return failure_update("formatter", exc)
