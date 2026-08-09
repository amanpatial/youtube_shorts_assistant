# ADR 0001 — Primary orchestration framework

- **Status:** Accepted  
- **Date:** 2026-08-05  
- **Deciders:** Project owner (learning roadmap Phases 00–21)  
- **Tags:** orchestration, langgraph, adk, archive  

## Context

This project started as a **Google ADK** experiment and was rebuilt on **LangGraph** to explore stateful agent orchestration, evaluation loops, MCP, A2A, observability, persistence, and production AI engineering.

By Phase 20 the active product path was already a single LangGraph package (`src/shorts_assistant/`) with ADK code under `archive/adk_baseline/`. Phase 21 records that fact as an architecture decision so future contributors do not revive a dual runtime.

Related reading:

- [ADK vs LangGraph comparison](../architecture/adk_vs_langgraph.md)  
- [ADK → LangGraph concept map](../architecture/adk_to_langgraph.md)  
- [Solution architecture](../architecture/solution_architecture.md)  

## Decision

**LangGraph is the sole active orchestration runtime.**

**Google ADK is archived** under `archive/adk_baseline/` as historical reference only — not mixed into the app, not a maintained “20% baseline,” and not a second production path.

Gemini (and Vertex when configured) may still be used as the **model provider** without ADK as the orchestrator.

Effort allocation:

| Track | Role |
|-------|------|
| LangGraph | 100% of active development and production |
| ADK | Archive only — readable history |

## Consequences

### Positive

- One control-flow model (StateGraph, checkpoints, interrupt/resume) for tests and deploy  
- Clear ownership: quality loop, HITL, API/worker all sit on one stack  
- Learning goals (edges, loops, persistence) stay explicit  
- Plans and code cannot drift across two frameworks  

### Negative / costs

- More glue for MCP/A2A than ADK’s batteries-included adapters  
- LangChain/LangGraph version churn and dependency surface  
- Losing `adk web` as the interactive prototyping UI (CLI/API/eval instead)  

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| **ADK as primary** | Learning target is explicit graph orchestration; would discard Phases 2–20 LangGraph investment |
| **Dual production (ADK + LangGraph)** | Splits focus, doubles tests/deploy, violates master “do not mix” rule |
| **Delete ADK archive** | Loses a useful historical experiment; archive is cheap and non-runnable |
| **20% ADK forever** | Soft dual-stack; still causes drift and ambiguous “source of truth” |

## Compliance

- Do not import ADK from active `src/shorts_assistant/`  
- Do not add `google-adk` to active `requirements.txt`  
- Do not feature-race archive ADK against LangGraph  
- Keep `archive/adk_baseline/` read-only reference  

## Notes

This ADR does **not** claim LangGraph is universally better than ADK. It records the **project-specific** choice after an honest comparison (see the 20-dimension matrix).
