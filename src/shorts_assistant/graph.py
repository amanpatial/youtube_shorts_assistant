"""LangGraph graph assembly for the Shorts pipeline.

Purpose: wire nodes and edges into one runnable ``StateGraph`` over WorkflowState.
Includes the Phase 5 quality loop (writer → evaluator → gate → retry/continue).
Phase 9: each node is wrapped with ``observe_node`` for timing/events.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .checkpointer import get_checkpointer
from .hitl import human_review_node, route_after_human
from .nodes import (
    evaluator_node,
    formatter_node,
    memory_retrieve_node,
    research_node,
    scriptwriter_node,
    visualizer_node,
)
from .observability import observe_node
from .quality_gate import quality_gate_node, route_after_gate
from .state import WorkflowState


def build_graph() -> StateGraph:
    """Purpose: research → memory → script↔eval↔gate → human → visual→format.

    Returns: an uncompiled ``StateGraph`` ready for ``.compile()``.
    """
    graph = StateGraph(WorkflowState)
    graph.add_node("research", observe_node("research", research_node))
    graph.add_node("memory_retrieve", observe_node("memory_retrieve", memory_retrieve_node))
    graph.add_node("scriptwriter", observe_node("scriptwriter", scriptwriter_node))
    graph.add_node("evaluator", observe_node("evaluator", evaluator_node))
    graph.add_node("quality_gate", observe_node("quality_gate", quality_gate_node))
    graph.add_node("human_review", observe_node("human_review", human_review_node))
    graph.add_node("visualizer", observe_node("visualizer", visualizer_node))
    graph.add_node("formatter", observe_node("formatter", formatter_node))

    graph.add_edge(START, "research")
    graph.add_edge("research", "memory_retrieve")
    graph.add_edge("memory_retrieve", "scriptwriter")
    graph.add_edge("scriptwriter", "evaluator")
    graph.add_edge("evaluator", "quality_gate")
    graph.add_conditional_edges(
        "quality_gate",
        route_after_gate,
        {
            "retry": "scriptwriter",
            "continue": "human_review",
            "fail": END,
        },
    )
    graph.add_conditional_edges(
        "human_review",
        route_after_human,
        {
            "continue": "visualizer",
            "revise": "scriptwriter",
            "fail": END,
        },
    )
    graph.add_edge("visualizer", "formatter")
    graph.add_edge("formatter", END)
    return graph


def get_compiled_graph(*, with_checkpointer: bool = True, checkpointer=None):
    """Purpose: return a compiled graph ready for ``invoke`` / CLI smoke.

    With checkpointer (default), callers must pass
    ``config={"configurable": {"thread_id": ...}}``. Pass
    ``with_checkpointer=False`` for ephemeral unit/workflow tests.
    """
    if not with_checkpointer:
        return build_graph().compile()
    saver = get_checkpointer() if checkpointer is None else checkpointer
    return build_graph().compile(checkpointer=saver)
