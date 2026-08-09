"""Agent Card for shorts_research_agent (Phase 15 A2A discovery)."""

from __future__ import annotations

from typing import Any

AGENT_NAME = "shorts_research_agent"
DEFAULT_URL = "http://127.0.0.1:9101"


def build_agent_card(*, url: str = DEFAULT_URL) -> dict[str, Any]:
    """Purpose: machine-readable identity + skills for peer discovery."""
    return {
        "name": AGENT_NAME,
        "description": (
            "Technical research for developer-focused YouTube Shorts. "
            "Produces concise bullets and sources; does not write scripts."
        ),
        "url": url.rstrip("/"),
        "version": "0.15.0",
        "protocol": "a2a-lite",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
        },
        "skills": [
            {
                "id": "research_shorts_topic",
                "name": "Research Shorts topic",
                "description": ("Gather concise, sourced notes for a developer Shorts topic"),
                "tags": ["research", "youtube-shorts", "developers"],
            }
        ],
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json"],
        "endpoints": {
            "agentCard": "/.well-known/agent-card.json",
            "researchTask": "/tasks/research",
            "health": "/health",
        },
    }
