"""Phase 15: Research Agent A2A-lite (agent↔agent, not MCP)."""

from .client import A2AResearchError, call_research, fetch_agent_card, fetch_research_text
from .contracts import ResearchRequest, ResearchResponse, response_to_research_text

__all__ = [
    "A2AResearchError",
    "ResearchRequest",
    "ResearchResponse",
    "call_research",
    "fetch_agent_card",
    "fetch_research_text",
    "response_to_research_text",
]
