"""YouTube Shorts multi-agent pipeline (SequentialAgent)."""

from __future__ import annotations

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search

from .config import settings
from .schemas import ShortConcept
from .util import load_instruction_from_file

# --- Sub Agent 1: Scriptwriter ---
scriptwriter_agent = LlmAgent(
    name="ShortsScriptwriter",
    model=settings.model_name,
    instruction=load_instruction_from_file("scriptwriter_instruction.txt"),
    description="Researches (if needed) and writes a developer-focused Shorts script.",
    tools=[google_search],
    output_key="generated_script",
)

# --- Sub Agent 2: Critic / quality gate ---
critic_agent = LlmAgent(
    name="ShortsCritic",
    model=settings.model_name,
    instruction=load_instruction_from_file("critic_instruction.txt"),
    description="Reviews script length, tone, structure, and developer value; rewrites if needed.",
    output_key="generated_script",
)

# --- Sub Agent 3: Visualizer ---
visualizer_agent = LlmAgent(
    name="ShortsVisualizer",
    model=settings.model_name,
    instruction=load_instruction_from_file("visualizer_instruction.txt"),
    description="Generates visual concepts based on a provided script.",
    output_key="visual_concepts",
)

# --- Sub Agent 4: Formatter (structured output) ---
formatter_agent = LlmAgent(
    name="ConceptFormatter",
    model=settings.model_name,
    instruction=load_instruction_from_file("formatter_instruction.txt"),
    description="Formats the final Short concept into a structured schema.",
    output_schema=ShortConcept,
    output_key="final_short_concept",
)

# --- Sequential pipeline: script → critic → visuals → format ---
youtube_shorts_agent = SequentialAgent(
    name="youtube_shorts_agent",
    sub_agents=[
        scriptwriter_agent,
        critic_agent,
        visualizer_agent,
        formatter_agent,
    ],
)

# Root agent discovered by ADK (`adk web`, AgentLoader)
root_agent = youtube_shorts_agent
