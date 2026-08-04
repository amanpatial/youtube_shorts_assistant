# ADK baseline archive (historical)

This directory preserves the original **Google ADK** experiment for the YouTube Shorts Assistant.

## Status

- **Not** an active runtime
- **Not** mixed into the LangGraph app under `src/shorts_assistant/`
- Kept for learning/reference only

## Narrative

The project started as a Google ADK multi-agent pipeline (`SequentialAgent`: scriptwriter → critic → visualizer → formatter). It is being rebuilt **fresh on LangGraph** for stateful orchestration, evaluation loops, MCP, A2A, observability, persistence, and production AI engineering.

See:

- [docs/architecture/solution_architecture.md](../../docs/architecture/solution_architecture.md)
- [docs/plans/00_master_learning_roadmap_24e99839.plan.md](../../docs/plans/00_master_learning_roadmap_24e99839.plan.md)

## Contents

| Path | Notes |
|------|--------|
| `agent.py` | ADK `LlmAgent` / `SequentialAgent` graph |
| `runner.py` | ADK CLI / session runner |
| `telemetry.py` | Optional OTel bootstrap |
| `*_instruction.txt` | Prompts (reuse ideas later; rewrite for LG) |
| `evals/` | ADK evalset format |
| `schemas.py` / `config.py` / `util.py` | Snapshots; active copies live under `src/shorts_assistant/` |

Do not `pip install google-adk` into the active project for day-to-day work.
