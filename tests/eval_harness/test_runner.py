"""Deterministic eval runner dry-run (stub invoke, no LLM)."""

from shorts_assistant.eval.dataset import (
    CaseInput,
    EvalCase,
    EvalDataset,
    QualityCriteria,
)
from shorts_assistant.eval.runner import run_dataset


def _tiny_dataset() -> EvalDataset:
    return EvalDataset(
        dataset_id="tiny",
        version="0",
        cases=[
            EvalCase(
                case_id="ok_case",
                input=CaseInput(topic="LangGraph tips"),
                quality_criteria=QualityCriteria(
                    min_overall_score=7.0,
                    require_approved=True,
                ),
            ),
            EvalCase(
                case_id="boom_case",
                input=CaseInput(topic="explode"),
                quality_criteria=QualityCriteria(
                    min_overall_score=7.0,
                    require_approved=False,
                ),
            ),
        ],
    )


def test_runner_continues_after_case_failure():
    def stub(case, mode):
        assert mode == "demo"
        if case.case_id == "boom_case":
            raise RuntimeError("injected failure")
        return {
            "status": "COMPLETED",
            "iteration": 1,
            "error": None,
            "evaluation": {
                "overall_score": 8.0,
                "hook_score": 8.0,
                "clarity_score": 8.0,
                "technical_accuracy": 8.0,
                "factual_correctness": 8.0,
                "developer_value": 8.0,
                "pacing_score": 8.0,
                "duration_score": 8.0,
                "cta_score": 8.0,
                "approved": True,
            },
            "generated_script": {
                "estimated_duration_seconds": 45,
                "sections": [
                    {"label": "hook"},
                    {"label": "body"},
                    {"label": "cta"},
                ],
            },
        }

    artifact = run_dataset(_tiny_dataset(), mode="demo", invoke_case=stub)
    assert artifact["summary"]["n_cases"] == 2
    assert artifact["summary"]["mode"] == "demo"
    assert artifact["summary"]["failure_rate"] == 0.5
    by_id = {c["case_id"]: c for c in artifact["cases"]}
    assert by_id["ok_case"]["criteria_pass"] is True
    assert by_id["boom_case"]["failed"] is True
    assert "injected failure" in (by_id["boom_case"]["error"] or "")
