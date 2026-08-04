"""Compare two eval run/baseline artifacts (same mode only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DELTA_KEYS = (
    "pass_rate",
    "average_quality",
    "failure_rate",
    "average_iterations",
    "approval_rate",
)


class ModeMismatchError(ValueError):
    """Purpose: refuse comparing demo vs live_judge baselines."""


def load_artifact(path: str | Path) -> dict[str, Any]:
    """Purpose: load a run or baseline JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare_summaries(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Purpose: compute candidate − baseline deltas on key metrics.

    Why it exists: answers “did v2 improve over v1?” on a fixed harness/mode.
    """
    base_summary = baseline.get("summary") or baseline
    cand_summary = candidate.get("summary") or candidate
    base_mode = base_summary.get("mode")
    cand_mode = cand_summary.get("mode")
    if base_mode != cand_mode:
        raise ModeMismatchError(
            f"mode mismatch: baseline={base_mode!r} candidate={cand_mode!r}"
        )

    deltas: dict[str, Any] = {}
    for key in DELTA_KEYS:
        b = base_summary.get(key)
        c = cand_summary.get(key)
        if b is None or c is None:
            deltas[key] = None
        else:
            deltas[key] = round(float(c) - float(b), 4)

    return {
        "baseline_run_id": base_summary.get("run_id"),
        "candidate_run_id": cand_summary.get("run_id"),
        "mode": base_mode,
        "deltas": deltas,
        "baseline": {k: base_summary.get(k) for k in DELTA_KEYS},
        "candidate": {k: cand_summary.get(k) for k in DELTA_KEYS},
    }


def compare_files(baseline_path: str | Path, candidate_path: str | Path) -> dict[str, Any]:
    """Purpose: load two artifacts and return compare payload."""
    return compare_summaries(load_artifact(baseline_path), load_artifact(candidate_path))
