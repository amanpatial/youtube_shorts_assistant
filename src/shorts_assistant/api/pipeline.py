"""Infer Shorts agent pipeline steps for the web UI."""

from __future__ import annotations

from typing import Any, Literal

AgentState = Literal["pending", "running", "paused", "done", "failed"]

SHORTS_AGENTS: tuple[tuple[str, str], ...] = (
    ("research", "Research"),
    ("memory_retrieve", "Memory"),
    ("scriptwriter", "Writer"),
    ("evaluator", "Evaluator"),
    ("quality_gate", "Quality gate"),
    ("human_review", "Human review"),
    ("visualizer", "Visualizer"),
    ("formatter", "Formatter"),
)


def _status_value(raw: Any) -> str:
    if raw is None:
        return ""
    if hasattr(raw, "value"):
        return str(raw.value)
    return str(raw)


def _done_flags(cp: dict[str, Any]) -> dict[str, bool]:
    research = bool(cp.get("research"))
    mem_ids = cp.get("retrieved_memory_ids")
    memory = research or isinstance(mem_ids, list) or cp.get("memory_context") is not None
    script = cp.get("generated_script") is not None or cp.get("best_script") is not None
    evaluation = cp.get("evaluation") is not None
    iteration = int(cp.get("iteration") or 0)
    gate = evaluation and iteration >= 1
    human = bool(cp.get("human_decision")) or _status_value(cp.get("status")).upper() in {
        "APPROVED",
        "VISUALIZING",
        "FORMATTING",
        "COMPLETED",
    }
    visuals = cp.get("visual_concepts") is not None
    formatter = cp.get("final_short_concept") is not None or _status_value(cp.get("status")).upper() in {
        "COMPLETED",
        "FORMATTING",
    }
    if visuals:
        human = True
        gate = True
    if formatter:
        visuals = True
        human = True
        gate = True
    if gate:
        evaluation = True
        script = True
    if evaluation:
        script = True
        memory = True
        research = True
    if script:
        memory = True
        research = True
    if memory:
        research = True
    return {
        "research": research,
        "memory_retrieve": memory,
        "scriptwriter": script,
        "evaluator": evaluation,
        "quality_gate": gate,
        "human_review": human,
        "visualizer": visuals,
        "formatter": formatter,
    }


def live_checkpoint(execution_id: str | None, domain_cp: dict[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
    """Purpose: prefer LangGraph thread state when the worker is mid-run."""
    domain = dict(domain_cp or {})
    if not execution_id:
        return domain, []
    try:
        from ..graph_ops import get_thread_state

        snap = get_thread_state(execution_id)
        values = dict(getattr(snap, "values", {}) or {})
        nxt = [str(n) for n in (getattr(snap, "next", None) or [])]
        if values:
            return values, nxt
        return domain, nxt
    except Exception:  # noqa: BLE001 — fail open to domain checkpoint
        return domain, []


def infer_agent_pipeline(
    *,
    checkpoint: dict[str, Any] | None,
    api_status: str,
    next_nodes: list[str] | None = None,
    error_node: str | None = None,
) -> list[dict[str, str]]:
    """Purpose: one row per Shorts graph node with UI state."""
    cp = dict(checkpoint or {})
    done = _done_flags(cp)
    nxt = set(next_nodes or [])
    err = (error_node or _status_value(cp.get("error_node")) or "").strip()
    api = (api_status or "").lower()

    steps: list[dict[str, str]] = []
    first_incomplete: str | None = None
    for agent_id, label in SHORTS_AGENTS:
        if not done.get(agent_id):
            first_incomplete = agent_id
            break

    for agent_id, label in SHORTS_AGENTS:
        state: AgentState = "pending"
        if err and err == agent_id:
            state = "failed"
        elif api == "failed" and done.get(agent_id) and agent_id == (err or ""):
            state = "failed"
        elif agent_id in nxt and api == "awaiting_human" and agent_id == "human_review":
            state = "paused"
        elif agent_id in nxt:
            state = "running"
        elif api == "awaiting_human" and agent_id == "human_review" and not done["human_review"]:
            state = "paused"
        elif done.get(agent_id):
            state = "done"
        elif api == "succeeded":
            state = "done"
        elif api == "failed" and first_incomplete == agent_id:
            state = "failed"
        elif api == "running" and not nxt and first_incomplete == agent_id:
            state = "running"
        elif api == "queued":
            state = "pending"
        steps.append({"id": agent_id, "label": label, "state": state})

    if api == "succeeded":
        for step in steps:
            if step["state"] in {"pending", "running", "paused"}:
                step["state"] = "done"
    return steps
