"""Deterministic metrics / criteria_pass tests."""

from shorts_assistant.eval.dataset import QualityCriteria
from shorts_assistant.eval.metrics import aggregate_metrics, criteria_pass


def test_criteria_pass_happy():
    criteria = QualityCriteria(
        min_overall_score=7.0,
        require_approved=True,
        max_duration_seconds=60,
        must_include_sections=["hook", "body", "cta"],
    )
    evaluation = {"overall_score": 8.0, "approved": True}
    script = {
        "estimated_duration_seconds": 45,
        "sections": [
            {"label": "hook"},
            {"label": "body"},
            {"label": "cta"},
        ],
    }
    assert criteria_pass(evaluation=evaluation, script=script, criteria=criteria)


def test_criteria_fail_low_score():
    criteria = QualityCriteria(min_overall_score=7.0, require_approved=False)
    assert not criteria_pass(
        evaluation={"overall_score": 6.0, "approved": True},
        script={
            "estimated_duration_seconds": 40,
            "sections": [{"label": "hook"}, {"label": "body"}, {"label": "cta"}],
        },
        criteria=criteria,
    )


def test_aggregate_metrics_known_fixture():
    records = [
        {
            "overall_score": 8.0,
            "hook_score": 8.0,
            "clarity_score": 8.0,
            "technical_accuracy": 8.0,
            "factual_correctness": 6.0,
            "approved": True,
            "iterations": 1,
            "revised": False,
            "failed": False,
            "criteria_pass": True,
            "exhausted": False,
        },
        {
            "overall_score": 6.0,
            "hook_score": 6.0,
            "clarity_score": 6.0,
            "technical_accuracy": 6.0,
            "factual_correctness": 6.0,
            "approved": False,
            "iterations": 3,
            "revised": True,
            "failed": False,
            "criteria_pass": False,
            "exhausted": True,
        },
        {
            "overall_score": None,
            "hook_score": None,
            "clarity_score": None,
            "approved": False,
            "iterations": 0,
            "revised": False,
            "failed": True,
            "criteria_pass": False,
            "exhausted": False,
        },
    ]
    summary = aggregate_metrics(records)
    assert summary["n_cases"] == 3
    assert summary["average_quality"] == 7.0
    assert summary["avg_hook_score"] == 7.0
    assert summary["avg_clarity"] == 7.0
    assert summary["avg_accuracy"] == 6.5
    assert summary["pass_rate"] == round(1 / 3, 4)
    assert summary["approval_rate"] == round(1 / 3, 4)
    assert summary["revision_rate"] == round(1 / 3, 4)
    assert summary["failure_rate"] == round(1 / 3, 4)
    assert summary["exhaustion_rate"] == round(1 / 3, 4)
    assert summary["average_iterations"] == round((1 + 3 + 0) / 3, 4)
