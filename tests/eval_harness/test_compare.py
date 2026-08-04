"""Deterministic baseline vs candidate compare tests."""

import pytest

from shorts_assistant.eval.compare import ModeMismatchError, compare_summaries


def _artifact(mode: str, **metrics):
    summary = {
        "mode": mode,
        "run_id": "r1",
        "pass_rate": 0.5,
        "average_quality": 7.0,
        "failure_rate": 0.1,
        "average_iterations": 1.5,
        "approval_rate": 0.4,
    }
    summary.update(metrics)
    return {"summary": summary, "cases": []}


def test_compare_deltas():
    baseline = _artifact("demo")
    candidate = _artifact(
        "demo",
        run_id="r2",
        pass_rate=0.8,
        average_quality=7.5,
        failure_rate=0.0,
        average_iterations=1.2,
        approval_rate=0.6,
    )
    result = compare_summaries(baseline, candidate)
    assert result["deltas"]["pass_rate"] == 0.3
    assert result["deltas"]["average_quality"] == 0.5
    assert result["deltas"]["failure_rate"] == -0.1
    assert result["deltas"]["average_iterations"] == -0.3
    assert result["deltas"]["approval_rate"] == 0.2


def test_compare_mode_mismatch():
    with pytest.raises(ModeMismatchError):
        compare_summaries(_artifact("demo"), _artifact("live_judge"))
