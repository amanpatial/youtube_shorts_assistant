"""LangGraph stream + time-travel helpers (Phase 20 hardening).

Purpose: thin wrappers over ``graph.stream``, ``get_state``, and
``get_state_history`` so learning/CLI/tests do not re-implement config glue.
Does not add HTTP SSE — the Phase 16 job API stays request/response.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import uuid4

from .graph import get_compiled_graph
from .state import WorkflowState


def thread_config(thread_id: str) -> dict[str, Any]:
    """Purpose: standard LangGraph configurable for a checkpoint thread."""
    return {"configurable": {"thread_id": thread_id}}


def stream_workflow(
    request: str,
    *,
    thread_id: str | None = None,
    max_iterations: int = 3,
    stream_mode: str = "updates",
    graph: Any | None = None,
) -> list[dict[str, Any]]:
    """Purpose: run the graph with ``stream`` and collect chunks (list form).

    Default ``stream_mode="updates"`` yields ``{node_name: state_delta}`` per step.
    """
    return list(
        iter_stream_workflow(
            request,
            thread_id=thread_id,
            max_iterations=max_iterations,
            stream_mode=stream_mode,
            graph=graph,
        )
    )


def iter_stream_workflow(
    request: str,
    *,
    thread_id: str | None = None,
    max_iterations: int = 3,
    stream_mode: str = "updates",
    graph: Any | None = None,
) -> Iterator[dict[str, Any]]:
    """Purpose: lazy iterator over stream chunks (same args as ``stream_workflow``)."""
    compiled = graph if graph is not None else get_compiled_graph()
    tid = thread_id or f"stream-{uuid4().hex[:12]}"
    initial = WorkflowState.initial(request, max_iterations=max_iterations)
    yield from compiled.stream(
        initial.to_dict(),
        thread_config(tid),
        stream_mode=stream_mode,
    )


def get_thread_state(thread_id: str, *, graph: Any | None = None) -> Any:
    """Purpose: return the latest checkpoint ``StateSnapshot`` for ``thread_id``."""
    compiled = graph if graph is not None else get_compiled_graph()
    return compiled.get_state(thread_config(thread_id))


def list_state_history(
    thread_id: str,
    *,
    limit: int = 20,
    graph: Any | None = None,
) -> list[Any]:
    """Purpose: newest-first checkpoint history (capped) for time-travel demos."""
    compiled = graph if graph is not None else get_compiled_graph()
    out: list[Any] = []
    for i, snap in enumerate(compiled.get_state_history(thread_config(thread_id))):
        if i >= limit:
            break
        out.append(snap)
    return out


def node_names_from_updates(chunks: list[dict[str, Any]]) -> list[str]:
    """Purpose: extract node names from ``stream_mode='updates'`` chunks."""
    names: list[str] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        for key in chunk:
            if key != "__interrupt__":
                names.append(str(key))
    return names
