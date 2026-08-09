"""LangGraph assembly for sales_brief (no visualizer)."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from ...checkpointer import get_checkpointer
from ...observability import observe_node
from .hitl import human_review_node, route_after_human
from .nodes import (
    evaluator_node,
    formatter_node,
    memory_retrieve_node,
    research_node,
    writer_node,
)
from .quality_gate import quality_gate_node, route_after_gate
from .state import BriefWorkflowState


def build_sales_brief_graph() -> StateGraph:
    """Purpose: research → memory → write↔eval↔gate → human → format."""
    graph = StateGraph(BriefWorkflowState)
    graph.add_node("research", observe_node("research", research_node))
    graph.add_node("memory_retrieve", observe_node("memory_retrieve", memory_retrieve_node))
    graph.add_node("writer", observe_node("writer", writer_node))
    graph.add_node("evaluator", observe_node("evaluator", evaluator_node))
    graph.add_node("quality_gate", observe_node("quality_gate", quality_gate_node))
    graph.add_node("human_review", observe_node("human_review", human_review_node))
    graph.add_node("formatter", observe_node("formatter", formatter_node))

    graph.add_edge(START, "research")
    graph.add_edge("research", "memory_retrieve")
    graph.add_edge("memory_retrieve", "writer")
    graph.add_edge("writer", "evaluator")
    graph.add_edge("evaluator", "quality_gate")
    graph.add_conditional_edges(
        "quality_gate",
        route_after_gate,
        {
            "retry": "writer",
            "continue": "human_review",
            "fail": END,
        },
    )
    graph.add_conditional_edges(
        "human_review",
        route_after_human,
        {
            "continue": "formatter",
            "revise": "writer",
            "fail": END,
        },
    )
    graph.add_edge("formatter", END)
    return graph


def get_compiled_sales_brief_graph(*, with_checkpointer: bool = True, checkpointer=None):
    """Purpose: compiled sales_brief graph for invoke / HITL resume."""
    if not with_checkpointer:
        return build_sales_brief_graph().compile()
    saver = get_checkpointer() if checkpointer is None else checkpointer
    return build_sales_brief_graph().compile(checkpointer=saver)
