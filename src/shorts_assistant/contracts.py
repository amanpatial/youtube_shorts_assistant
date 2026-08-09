"""Contract validation and fail-closed gates between pipeline steps.

Purpose: turn raw/partial data into validated schema objects, or refuse to
continue. Downstream nodes must not consume invalid or unapproved work.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .schemas import ScriptEvaluation, ShortScript, VisualPlan

T = TypeVar("T", bound=BaseModel)


class ContractValidationError(ValueError):
    """Purpose: signal that a structured contract failed validation or a gate.

    Why it exists: callers need a single exception type with which node failed
    (``agent``) and optional Pydantic error details — not a bare ValidationError.

    Raised by: ``parse_contract`` and the ``guard_*`` helpers.
    Handled by: nodes (set ``status=FAILED`` + ``error``) and tests.
    """

    def __init__(self, agent: str, message: str, *, errors: Any = None) -> None:
        self.agent = agent
        self.errors = errors
        super().__init__(f"[{agent}] {message}")


def parse_contract(model_type: type[T], raw: Any, *, agent: str = "unknown") -> T:
    """Purpose: validate ``raw`` into ``model_type`` or raise ContractValidationError.

    Why it exists: demo/LLM output must become a real Pydantic object before it
    is written into WorkflowState. Partial or malformed data must not pass through.

    Accepts: an instance of ``model_type``, another BaseModel, or a dict.
    """
    try:
        if isinstance(raw, model_type):
            return raw
        if isinstance(raw, BaseModel):
            return model_type.model_validate(raw.model_dump())
        return model_type.model_validate(raw)
    except ValidationError as exc:
        raise ContractValidationError(
            agent,
            "malformed or invalid contract",
            errors=exc.errors(),
        ) from exc


def guard_script(script: ShortScript | None, *, agent: str = "script") -> ShortScript:
    """Purpose: require a valid ShortScript before a node that depends on it.

    Called by: evaluator, visualizer, formatter.
    Fails if: missing or not parseable as ShortScript.
    """
    if script is None:
        raise ContractValidationError(agent, "generated_script is required")
    return parse_contract(ShortScript, script, agent=agent)


def guard_evaluation(
    evaluation: ScriptEvaluation | None, *, agent: str = "evaluator"
) -> ScriptEvaluation:
    """Purpose: require a valid ScriptEvaluation before treating the run as judged.

    Called by: visualizer (and helpers like ``ready_for_visuals``).
    Fails if: missing or not parseable as ScriptEvaluation.
    """
    if evaluation is None:
        raise ContractValidationError(agent, "evaluation is required")
    return parse_contract(ScriptEvaluation, evaluation, agent=agent)


def guard_visuals(visuals: VisualPlan | None, *, agent: str = "visualizer") -> VisualPlan:
    """Purpose: require a valid VisualPlan before formatting the final concept.

    Called by: formatter.
    Fails if: missing or not parseable as VisualPlan.
    """
    if visuals is None:
        raise ContractValidationError(agent, "visual_concepts is required")
    return parse_contract(VisualPlan, visuals, agent=agent)


def ready_for_visuals(evaluation: ScriptEvaluation | None) -> bool:
    """Purpose: decide whether the visualizer is allowed to run.

    Why it exists: fail closed — no visuals unless there is a valid evaluation
    with ``approved=True``. Prevents formatting garbage or weak scripts.

    Called by: visualizer_node.
    Returns: True only when evaluation parses and ``approved`` is True.
    """
    if evaluation is None:
        return False
    try:
        parsed = guard_evaluation(evaluation)
    except ContractValidationError:
        return False
    return parsed.approved is True
