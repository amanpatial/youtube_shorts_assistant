"""Load quality_gate.yaml and decide pass/fail from compare deltas."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..eval.compare import ModeMismatchError, compare_summaries, load_artifact


@dataclass(frozen=True)
class GateConfig:
    """Thresholds for candidate vs baseline regression."""

    min_pass_rate_delta: float = -0.05
    min_average_quality_delta: float = -0.3
    max_failure_rate: float = 0.15
    max_failure_rate_delta: float = 0.05


@dataclass
class GateResult:
    """Outcome of a quality-gate evaluation."""

    passed: bool
    reasons: list[str] = field(default_factory=list)
    compare: dict[str, Any] = field(default_factory=dict)
    candidate_failure_rate: float | None = None


def load_gate_config(path: str | Path) -> GateConfig:
    """Purpose: load gate thresholds from YAML (fail closed on missing file)."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"quality gate config not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return GateConfig(
        min_pass_rate_delta=float(raw.get("min_pass_rate_delta", -0.05)),
        min_average_quality_delta=float(raw.get("min_average_quality_delta", -0.3)),
        max_failure_rate=float(raw.get("max_failure_rate", 0.15)),
        max_failure_rate_delta=float(raw.get("max_failure_rate_delta", 0.05)),
    )


def evaluate_gate(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    config: GateConfig,
) -> GateResult:
    """Purpose: apply regression rules on compare deltas + absolute failure cap."""
    try:
        compare = compare_summaries(baseline, candidate)
    except ModeMismatchError as exc:
        return GateResult(passed=False, reasons=[str(exc)])

    deltas = compare.get("deltas") or {}
    cand = compare.get("candidate") or {}
    reasons: list[str] = []

    pr_delta = deltas.get("pass_rate")
    if pr_delta is None:
        reasons.append("pass_rate delta unavailable")
    elif float(pr_delta) < config.min_pass_rate_delta:
        reasons.append(
            f"pass_rate delta {pr_delta} < min_pass_rate_delta {config.min_pass_rate_delta}"
        )

    aq_delta = deltas.get("average_quality")
    if aq_delta is None:
        reasons.append("average_quality delta unavailable")
    elif float(aq_delta) < config.min_average_quality_delta:
        reasons.append(
            "average_quality delta "
            f"{aq_delta} < min_average_quality_delta {config.min_average_quality_delta}"
        )

    fr_cand = cand.get("failure_rate")
    if fr_cand is None:
        reasons.append("candidate failure_rate unavailable")
    else:
        fr_val = float(fr_cand)
        if fr_val > config.max_failure_rate:
            reasons.append(f"failure_rate {fr_val} > max_failure_rate {config.max_failure_rate}")
        fr_delta = deltas.get("failure_rate")
        if fr_delta is None:
            reasons.append("failure_rate delta unavailable")
        elif float(fr_delta) > config.max_failure_rate_delta:
            reasons.append(
                "failure_rate delta "
                f"{fr_delta} > max_failure_rate_delta {config.max_failure_rate_delta}"
            )

    return GateResult(
        passed=not reasons,
        reasons=reasons,
        compare=compare,
        candidate_failure_rate=float(fr_cand) if fr_cand is not None else None,
    )


def evaluate_gate_files(
    baseline_path: str | Path,
    candidate_path: str | Path,
    config_path: str | Path,
) -> GateResult:
    """Purpose: load artifacts + config and evaluate (fail closed if baseline missing)."""
    bp = Path(baseline_path)
    if not bp.is_file():
        return GateResult(
            passed=False,
            reasons=[f"baseline missing (fail closed): {bp}"],
        )
    cp = Path(candidate_path)
    if not cp.is_file():
        return GateResult(
            passed=False,
            reasons=[f"candidate missing (fail closed): {cp}"],
        )
    config = load_gate_config(config_path)
    return evaluate_gate(load_artifact(bp), load_artifact(cp), config)


def gate_result_to_dict(result: GateResult) -> dict[str, Any]:
    """Purpose: JSON-serializable gate payload for CI logs."""
    return {
        "passed": result.passed,
        "reasons": result.reasons,
        "candidate_failure_rate": result.candidate_failure_rate,
        "compare": result.compare,
    }


def dump_gate_result(result: GateResult) -> str:
    """Purpose: pretty JSON for stdout."""
    return json.dumps(gate_result_to_dict(result), indent=2)
