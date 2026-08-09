"""Per-case criteria and aggregate metrics for eval runs."""

from __future__ import annotations

from typing import Any

from .dataset import EvalCase, QualityCriteria


def _as_dict(value: Any) -> dict[str, Any] | None:
    """Purpose: coerce Pydantic models or dicts to plain dicts."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else None
    return None


def criteria_pass(
    *,
    evaluation: dict[str, Any] | None,
    script: dict[str, Any] | None,
    criteria: QualityCriteria,
) -> bool:
    """Purpose: deterministic pass check against dataset quality_criteria.

    Soft ``expected_characteristics`` are documentation only (not string-matched).
    """
    if evaluation is None or script is None:
        return False
    overall = float(evaluation.get("overall_score", -1))
    if overall < criteria.min_overall_score:
        return False
    if criteria.require_approved and not bool(evaluation.get("approved")):
        return False
    duration = float(script.get("estimated_duration_seconds", 999))
    if duration > criteria.max_duration_seconds:
        return False
    labels = {str(s.get("label")) for s in (script.get("sections") or []) if isinstance(s, dict)}
    for required in criteria.must_include_sections:
        if required not in labels:
            return False
    return True


def case_record_from_state(
    case: EvalCase,
    state: dict[str, Any],
    *,
    error: str | None = None,
) -> dict[str, Any]:
    """Purpose: build one per-case result row from final WorkflowState dict."""
    evaluation = _as_dict(state.get("evaluation"))
    script = _as_dict(state.get("generated_script")) or _as_dict(state.get("best_script"))
    status = state.get("status")
    if hasattr(status, "value"):
        status = status.value
    iterations = int(state.get("iteration") or 0)
    failed = bool(error) or status == "FAILED" or evaluation is None
    approved = bool(evaluation.get("approved")) if evaluation else False
    passed = False
    if not failed and evaluation is not None:
        passed = criteria_pass(
            evaluation=evaluation,
            script=script,
            criteria=case.quality_criteria,
        )

    scores = evaluation or {}
    return {
        "case_id": case.case_id,
        "ok": not failed,
        "overall_score": scores.get("overall_score"),
        "hook_score": scores.get("hook_score"),
        "clarity_score": scores.get("clarity_score"),
        "technical_accuracy": scores.get("technical_accuracy"),
        "factual_correctness": scores.get("factual_correctness"),
        "developer_value": scores.get("developer_value"),
        "pacing_score": scores.get("pacing_score"),
        "duration_score": scores.get("duration_score"),
        "cta_score": scores.get("cta_score"),
        "approved": approved,
        "iterations": iterations,
        "revised": iterations > 1,
        "failed": failed,
        "error": error or state.get("error"),
        "status": status,
        "criteria_pass": passed,
        "exhausted": status == "EXHAUSTED",
    }


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def aggregate_metrics(case_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Purpose: summary metrics over per-case records."""
    n = len(case_records)
    with_eval = [
        r for r in case_records if r.get("overall_score") is not None and not r.get("failed")
    ]
    overalls = [float(r["overall_score"]) for r in with_eval]
    hooks = [float(r["hook_score"]) for r in with_eval if r.get("hook_score") is not None]
    clarity = [float(r["clarity_score"]) for r in with_eval if r.get("clarity_score") is not None]
    accuracy_parts: list[float] = []
    for r in with_eval:
        ta = r.get("technical_accuracy")
        fc = r.get("factual_correctness")
        if ta is not None and fc is not None:
            accuracy_parts.append((float(ta) + float(fc)) / 2.0)

    failures = sum(1 for r in case_records if r.get("failed"))
    passes = sum(1 for r in case_records if r.get("criteria_pass"))
    approvals = sum(1 for r in case_records if r.get("approved"))
    revisions = sum(1 for r in case_records if r.get("revised"))
    exhausted = sum(1 for r in case_records if r.get("exhausted"))
    iterations = [int(r.get("iterations") or 0) for r in case_records]

    return {
        "n_cases": n,
        "average_quality": _mean(overalls),
        "avg_hook_score": _mean(hooks),
        "avg_accuracy": _mean(accuracy_parts),
        "avg_clarity": _mean(clarity),
        "pass_rate": round(passes / n, 4) if n else 0.0,
        "approval_rate": round(approvals / n, 4) if n else 0.0,
        "revision_rate": round(revisions / n, 4) if n else 0.0,
        "average_iterations": _mean([float(i) for i in iterations]) or 0.0,
        "failure_rate": round(failures / n, 4) if n else 0.0,
        "exhaustion_rate": round(exhausted / n, 4) if n else 0.0,
    }
