"""LangGraph node functions — one step of the Shorts pipeline each.

Purpose: read ``WorkflowState``, do one job, return a partial state update.
Quality loop: scriptwriter ↔ evaluator ↔ quality_gate; then visualizer → formatter.
Phase 6: unexpected exceptions map to FAILED via ``failure_update``.
"""

from __future__ import annotations

from pydantic import ValidationError

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
from .schemas import ShortScript, VisualPlan
from .state import WorkflowState, WorkflowStatus


def research_node(state: WorkflowState) -> dict:
    """Purpose: gather context notes for the user's topic (runs once before loop)."""
    if state.status == WorkflowStatus.FAILED:
        return {}
    try:
        notes = demo_research(state.request)
        return {
            "research": notes,
            "status": WorkflowStatus.RESEARCHING,
            **clear_error_fields(),
        }
    except Exception as exc:  # noqa: BLE001 — map to FAILED for invoke safety
        return failure_update("research", exc)


def scriptwriter_node(state: WorkflowState) -> dict:
    """Purpose: create or revise the draft Shorts script as a ``ShortScript``.

    On quality-gate RETRY, uses ``evaluation.issues`` to produce a revised demo script.
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
    """Purpose: plan shots/visuals after the quality loop exits.

    Runs when status is PASSED or EXHAUSTED (best script restored).
    """
    if state.status == WorkflowStatus.FAILED:
        return {}
    if state.status not in (WorkflowStatus.PASSED, WorkflowStatus.EXHAUSTED):
        return failure_update(
            "visualizer",
            RuntimeError("quality gate did not PASS or EXHAUST"),
        )
    try:
        script = guard_script(state.generated_script, agent="visualizer")
        plan = parse_contract(
            VisualPlan, demo_visuals(script), agent="visualizer"
        )
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
