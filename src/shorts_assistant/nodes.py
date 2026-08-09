"""LangGraph node functions — one step of the Shorts pipeline each.

Purpose: read ``WorkflowState``, do one job, return a partial state update.
Quality loop: scriptwriter ↔ evaluator ↔ quality_gate; then visualizer → formatter.
Phase 6: unexpected exceptions map to FAILED via ``failure_update``.
"""

from __future__ import annotations

from pydantic import ValidationError

from .config import settings
from .contracts import (
    ContractValidationError,
    guard_script,
    guard_visuals,
    parse_contract,
)
from .demo_producers import demo_format, demo_research, demo_script, demo_visuals
from .eval_flags import prefer_live_judge
from .failures import clear_error_fields, failure_update
from .judge import judge_script
from .memory.context import build_memory_context
from .memory.retriever import retrieve_memories
from .schemas import ShortScript, VisualPlan
from .state import WorkflowState, WorkflowStatus


def research_node(state: WorkflowState) -> dict:
    """Purpose: gather context notes for the user's topic (runs once before loop).

    Phase 15: when ``A2A_RESEARCH_ENABLED``, call peer Research Agent (A2A-lite).
    Phase 12: in-process path optionally appends MCP shorts_catalog notes.
    """
    if state.status == WorkflowStatus.FAILED:
        return {}
    try:
        if settings.a2a_research_enabled:
            notes = _research_via_a2a(state.request)
        else:
            notes = demo_research(state.request)
            try:
                from .mcp_client import research_catalog_notes

                catalog_blurb = research_catalog_notes(state.request)
                if catalog_blurb:
                    notes = f"{notes}\n{catalog_blurb}"
            except Exception:  # noqa: BLE001 — MCP must not break research
                pass
        return {
            "research": notes,
            "status": WorkflowStatus.RESEARCHING,
            **clear_error_fields(),
        }
    except Exception as exc:  # noqa: BLE001 — map to FAILED for invoke safety
        return failure_update("research", exc)


def _research_via_a2a(topic: str) -> str:
    """Purpose: A2A peer research; degrade to empty or raise when required."""
    from .a2a_research.client import A2AResearchError, fetch_research_text
    from .observability import log_event

    try:
        return fetch_research_text(topic)
    except (A2AResearchError, Exception) as exc:  # noqa: BLE001 — degrade path
        log_event(
            "a2a_research_degraded",
            agent="research",
            error=f"{type(exc).__name__}: {exc}",
            required=settings.a2a_research_required,
        )
        if settings.a2a_research_required:
            raise
        return ""


def memory_retrieve_node(state: WorkflowState) -> dict:
    """Purpose: RAG retrieve past Shorts into ``memory_context`` (Phase 11)."""
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
    except Exception:  # noqa: BLE001 — fail-open empty memory
        return {
            "memory_context": None,
            "retrieved_memory_ids": [],
        }


def scriptwriter_node(state: WorkflowState) -> dict:
    """Purpose: create or revise the draft Shorts script as a ``ShortScript``.

    On quality-gate RETRY, uses ``evaluation.issues`` to produce a revised demo script.
    Uses ``memory_context`` as optional inspiration (do not copy verbatim).
    """
    if state.status == WorkflowStatus.FAILED:
        return {}
    try:
        script = parse_contract(
            ShortScript,
            demo_script(
                state.request,
                state.research,
                evaluation=state.evaluation,
                memory_context=state.memory_context,
                human_feedback=state.human_feedback,
            ),
            agent="scriptwriter",
        )
        return {
            "generated_script": script,
            "script_version": state.script_version + 1,
            "status": WorkflowStatus.SCRIPTING,
            **clear_error_fields(),
        }
    except (ContractValidationError, ValidationError) as exc:
        return failure_update("scriptwriter", exc)
    except Exception as exc:  # noqa: BLE001 — map to FAILED for invoke safety
        return failure_update("scriptwriter", exc)


def evaluator_node(state: WorkflowState) -> dict:
    """Purpose: judge the script and write ``evaluation`` only (never mutates script).

    Does not own ``best_score`` / ``best_script`` — the quality gate tracks those.
    """
    if state.status == WorkflowStatus.FAILED:
        return {}
    try:
        script = guard_script(state.generated_script, agent="evaluator")
        script_before = script.model_dump()
        evaluation = judge_script(
            script,
            state.request,
            research=state.research,
            prefer_live=prefer_live_judge(),
        )
        if script.model_dump() != script_before:
            return failure_update(
                "evaluator",
                RuntimeError("invariant violated: script was mutated"),
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
    except Exception as exc:  # noqa: BLE001 — map to FAILED for invoke safety
        return failure_update("evaluator", exc)


def visualizer_node(state: WorkflowState) -> dict:
    """Purpose: plan shots/visuals after AI gate + human approval.

    Runs when status is APPROVED (Phase 13), or PASSED/EXHAUSTED if HITL skipped.
    """
    if state.status == WorkflowStatus.FAILED:
        return {}
    if state.status not in (
        WorkflowStatus.APPROVED,
        WorkflowStatus.PASSED,
        WorkflowStatus.EXHAUSTED,
    ):
        return failure_update(
            "visualizer",
            RuntimeError("expected APPROVED (or PASS/EXHAUST without HITL)"),
        )
    try:
        script = guard_script(state.generated_script, agent="visualizer")
        plan = parse_contract(VisualPlan, demo_visuals(script), agent="visualizer")
        return {
            "visual_concepts": plan,
            "status": WorkflowStatus.VISUALIZING,
            **clear_error_fields(),
        }
    except ContractValidationError as exc:
        return failure_update("visualizer", exc)
    except Exception as exc:  # noqa: BLE001 — map to FAILED for invoke safety
        return failure_update("visualizer", exc)


def formatter_node(state: WorkflowState) -> dict:
    """Purpose: merge script + visuals into the final ``ShortConcept`` package."""
    if state.status == WorkflowStatus.FAILED:
        return {}
    try:
        script = guard_script(state.generated_script, agent="formatter")
        visuals = guard_visuals(state.visual_concepts, agent="formatter")
        concept = demo_format(script, visuals)
        return {
            "final_short_concept": concept,
            "status": WorkflowStatus.COMPLETED,
            **clear_error_fields(),
        }
    except ContractValidationError as exc:
        return failure_update("formatter", exc)
    except Exception as exc:  # noqa: BLE001 — map to FAILED for invoke safety
        return failure_update("formatter", exc)
