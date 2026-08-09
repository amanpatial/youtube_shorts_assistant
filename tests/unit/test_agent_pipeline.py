"""Infer Shorts agent pipeline states for the web UI."""

from shorts_assistant.api.pipeline import infer_agent_pipeline


def _by_id(steps: list[dict]) -> dict[str, str]:
    return {s["id"]: s["state"] for s in steps}


def test_queued_all_pending() -> None:
    states = _by_id(infer_agent_pipeline(checkpoint={}, api_status="queued"))
    assert states["research"] == "pending"
    assert states["formatter"] == "pending"


def test_succeeded_all_done() -> None:
    cp = {
        "research": "notes",
        "retrieved_memory_ids": [],
        "generated_script": {"hook": "h", "body": "b", "cta": "c"},
        "evaluation": {"overall_score": 8.5, "approved": True},
        "iteration": 1,
        "human_decision": "approve",
        "visual_concepts": {"shots": []},
        "final_short_concept": {"hook": "h"},
        "status": "COMPLETED",
    }
    states = _by_id(infer_agent_pipeline(checkpoint=cp, api_status="succeeded"))
    assert all(v == "done" for v in states.values())
    assert len(states) == 8


def test_awaiting_human_pauses_review() -> None:
    cp = {
        "research": "notes",
        "retrieved_memory_ids": ["m1"],
        "generated_script": {"hook": "h"},
        "evaluation": {"overall_score": 8.0, "approved": True},
        "iteration": 1,
        "status": "PASSED",
    }
    states = _by_id(
        infer_agent_pipeline(
            checkpoint=cp,
            api_status="awaiting_human",
            next_nodes=["human_review"],
        )
    )
    assert states["quality_gate"] == "done"
    assert states["human_review"] == "paused"
    assert states["visualizer"] == "pending"
    assert states["formatter"] == "pending"


def test_error_node_failed() -> None:
    cp = {"research": "notes", "error_node": "evaluator"}
    states = _by_id(
        infer_agent_pipeline(checkpoint=cp, api_status="failed", error_node="evaluator")
    )
    assert states["research"] == "done"
    assert states["evaluator"] == "failed"
