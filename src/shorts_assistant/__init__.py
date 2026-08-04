"""YouTube Shorts Assistant — active LangGraph application package.

Purpose: public entry for the Shorts pipeline (state, contracts, graph).
ADK experiment code lives under ``archive/adk_baseline/`` and is not imported here.

Pipeline today: research → scriptwriter ↔ evaluator ↔ quality_gate → visualizer → formatter.
See ``docs/architecture/solution_architecture.md`` for the full target system.
"""

from .contracts import ContractValidationError, ready_for_visuals
from .graph import build_graph, get_compiled_graph
from .schemas import ScriptEvaluation, ShortConcept, ShortScript, VisualPlan
from .state import FailureClass, WorkflowState, WorkflowStatus

__all__ = [
    "ContractValidationError",
    "FailureClass",
    "ScriptEvaluation",
    "ShortConcept",
    "ShortScript",
    "VisualPlan",
    "WorkflowState",
    "WorkflowStatus",
    "build_graph",
    "get_compiled_graph",
    "ready_for_visuals",
    "__version__",
]

__version__ = "0.10.0"
