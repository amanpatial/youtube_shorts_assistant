---
name: Phase 20 LangGraph Rebuild
overview: "Phase 20 hardens the existing LangGraph shorts_assistant (not a rebuild). Ship ADK→LG learning map, streaming + time-travel helpers/tests, doc topology alignment; keep custom memory (no dual Store rewrite). Target 0.20.0."
todos:
  - id: p20-map
    content: Publish ADK→LangGraph concept map under docs/architecture (learning only; ADK stays archive)
    status: completed
  - id: p20-stream-timetravel
    content: Add stream + get_state/get_state_history helpers + unit/workflow tests (no SSE API required)
    status: completed
  - id: p20-docs-align
    content: Align solution_architecture HITL order with graph.py; sync pyproject version; README Phase 20 notes
    status: completed
  - id: p20-optional-store
    content: Document Store API vs custom memory decision (keep SQL memory; no forced PostgresStore migration)
    status: completed
  - id: p20-tests
    content: Tests for stream events / state history / loop still terminates; version 0.20.0
    status: completed
isProject: false
---

# Phase 20 — LangGraph Parity / Hardening


## Master alignment
- Active stack: LangGraph only
- ADK: archive only (not a second runtime)
- If this plan still describes ADK APIs below, treat them as historical; redesign for LangGraph in Steps 2–3 of the phase loop

## Scope lock

- **Purpose:** harden the **existing** `shorts_assistant` LangGraph app + document ADK→LG concept map for learning  
- **ADK:** already in `archive/adk_baseline/` — do not revive; do **not** create a second package (`langgraph_shorts/`)  
- **Not a rebuild:** nodes, quality loop, HITL, checkpointer, MCP/A2A, API/worker already shipped (Phases 2–19)  
- Do not introduce K8s; do not force LangGraph Store API migration this phase  

**Status:** Implemented locally as **0.20.0** (2026-08-05). Uncommitted until batch check (Phases 11–21).  
**Commit policy:** batch code-check/commit for Phases 11–21 later (no commit until you ask).

## Inspect findings (2026-08-05)

| Area | Finding |
|------|---------|
| Plan body / todos | Still a **rebuild checklist** (`langgraph_shorts/`, implement nodes from scratch) — **outdated** vs code |
| Graph | **Done** in `graph.py`: research → memory → script ↔ eval ↔ gate → human_review → visual → format |
| HITL + checkpointer | **Done** (`interrupt` / `Command(resume=…)`, Memory/Postgres saver) |
| Streaming | **Missing** — only `graph.invoke`; no `astream` / `stream_mode` helpers |
| Time-travel | **Missing** — no `get_state` / `get_state_history` usage or tests |
| Subgraphs | **Missing** — flat graph; A2A/MCP are in-node (acceptable; optional later) |
| Store API | **Not used** — Phase 11 custom SQLAlchemy memory (JSON embeddings); keep for this phase |
| Architecture docs | **Stale**: `solution_architecture.md` shows HITL *after* formatter; code has HITL *before* visualizer |
| ADK in `src/` | Comments / deprecated `SESSION_DB_URL` only — no ADK runtime |
| Version skew | App `__version__` = **0.19.0**; `pyproject.toml` still `0.1.0` |
| Functional checklist in old plan | Already met by Phases 2–13+ |

### What already exists (do not rebuild)

- Typed `WorkflowState`, quality loop, structured schemas, retries, obs  
- Checkpointer + HITL interrupt/resume + approve CLI/API  
- Memory/RAG, MCP, A2A, model router, async API/worker, security, CI, deploy  

### Gaps this phase must close

1. **Teaching doc:** `docs/architecture/adk_to_langgraph.md` — ADK→LG map + “do not blindly translate” (keep tables below; trim rebuild package layout)  
2. **Streaming helper:** e.g. `run.stream_workflow` / `graph_ops.stream_events` wrapping `graph.stream` (updates or values) for CLI/learning  
3. **Time-travel helper:** `get_thread_state` / `list_state_history` over checkpointer + small CLI or module API  
4. **Tests:** stream yields node transitions; history non-empty after invoke; loop termination still green  
5. **Docs align:** fix architecture HITL order; README Phase 20; sync `pyproject.toml` version to **0.20.0**  
6. **Decision note:** LangGraph Store vs custom memory — **keep custom memory**; document why (CI SQLite, already shipped)  
7. **Out of scope:** SSE job API, AsyncPostgresSaver rewrite, subgraphs for A2A, reviving ADK, new package  

### Concrete design (for Approve)

```text
docs/architecture/adk_to_langgraph.md   # learning map (from this plan’s tables)
src/shorts_assistant/graph_ops.py       # stream_workflow, get_thread_state, list_state_history
src/shorts_assistant/run.py             # thin wrappers / CLI flags optional
tests/workflow/test_stream_and_history.py
docs/architecture/solution_architecture.md  # HITL before visualizer
```

| API | Behavior |
|-----|----------|
| `stream_workflow(topic, …)` | `graph.stream(..., stream_mode="updates")` → list/iterator of `{node: delta}` |
| `get_thread_state(thread_id)` | `graph.get_state(config)` |
| `list_state_history(thread_id, limit=N)` | `graph.get_state_history(config)` |

No new HTTP streaming endpoint required (Phase 16 jobs remain request/response). Optional: `python -m shorts_assistant … --stream` if CLI already exists and is cheap.

---

## Teaching: do not blindly translate

| Bad translation | Better thinking |
|-----------------|-----------------|
| `LlmAgent` → “LangGraph Agent class” | A **node** that calls a model with a typed update |
| `LoopAgent` → while True wrapper | **Conditional edges** + reducers on state |
| `output_key` → mystery | Explicit **state channels** / reducers |
| `SessionService` → ignore | LangGraph **checkpointer** (Memory/SQLite/Postgres) |

ADK is **agent-graph + session dict**. LangGraph is **state machine + reducers + checkpoints**.

---

## Mapping: Google ADK → LangGraph

| Google ADK | LangGraph |
|------------|-----------|
| `WorkflowState` / session dict | `TypedDict` / Pydantic state with reducers |
| `LlmAgent` | Node function (`def scriptwriter(state) -> delta`) |
| `SequentialAgent` | Linear edges `A → B → C` |
| `LoopAgent` + escalate | Cycle + `conditional_edges` to exit |
| `output_key` | Return partial state update |
| `output_schema` | Structured output / Zod-like via Pydantic parse in node |
| Tools / `google_search` | Bind tools to model or tool node |
| MCP `McpToolset` | MCP client called inside a node (or langchain-mcp adapters) |
| `RemoteA2aAgent` | HTTP/A2A call inside a node (custom); not first-class same as ADK |
| QualityGate `BaseAgent` | Pure node + conditional edge |
| `Runner` + session | `graph.invoke` / `ainvoke` + thread_id |
| `DatabaseSessionService` | `PostgresSaver` / `SqliteSaver` checkpointer |
| HITL pause/resume | `interrupt()` / `Command(resume=...)` (LG HITL) |
| Observability callbacks | LangChain callbacks / OTel / custom node logging |
| Eval runner | Same dataset; invoke LG graph instead of ADK root |

---

## Comparison deep dive

| Topic | ADK | LangGraph |
|-------|-----|-----------|
| **State** | Opaque/mutable session dict + our Pydantic lens | First-class graph state; reducers merge updates |
| **Agents** | First-class `LlmAgent` objects | Often “just nodes”; agent is a pattern |
| **Tools** | On `LlmAgent.tools` | Tool nodes or bind_tools; ReAct subgraphs |
| **Nodes** | Sub-agents in a parent | Explicit unit of compute |
| **Edges** | Implicit in Sequential/Loop | Explicit control flow |
| **Conditional edges** | Gate escalate / callbacks | Core loop mechanism |
| **Loops** | `LoopAgent(max_iterations)` | Conditional cycle + counters in state |
| **Checkpoints** | Session persistence / our PG | Built-in checkpointer per step |
| **Persistence** | DIY + SessionService | Checkpointer + optional store |
| **HITL** | App-level pause (our design) | Native interrupt/resume primitives |
| **MCP** | `McpToolset` integrated | Manual/adapter integration |
| **A2A** | `RemoteA2aAgent` | Custom node; less “batteries included” |
| **Observability** | Events + our logs | LangSmith optional; callbacks |
| **Testing** | Fake agents / gate pure fn | Test nodes + `graph.invoke` fixtures |

---

## Target LangGraph topology

```mermaid
flowchart TD
    [START] --> research[research_node]
    research --> script[scriptwriter_node]
    script --> evaluate[evaluator_node]
    evaluate --> gate[quality_gate_node]
    gate -->|retry| script
    gate -->|pass_or_exhausted| hitl{hitl_interrupt}
    hitl -->|approve| visual[visualizer_node]
    hitl -->|revise| script
    visual --> format[formatter_node]
    format --> END[END]
```

State (shared functional fields): `request`, `research`, `generated_script`, `evaluation`, `iteration`, `max_iterations`, `best_script`, `best_score`, `visual_concepts`, `final_short_concept`, `human_*`, `status`, `error`, `retry_count`.

Structured outputs: parse to existing `ShortScript` / `ScriptEvaluation` / `VisualPlan` / `ShortConcept` in each node (reuse [`schemas.py`](schemas.py) via import without depending on ADK agent module).

---

## Package layout (current — do not fork)

Active app is already [`src/shorts_assistant/`](../../src/shorts_assistant/). ADK lives only under `archive/adk_baseline/`.

Phase 20 **adds** `graph_ops.py` + teaching doc; it does **not** create `langgraph_shorts/`.

---

## Functional parity checklist (status after Inspect)

| Requirement | Status |
|-------------|--------|
| Explicit state | Done — `WorkflowState` |
| Scriptwriter / Evaluator | Done — nodes + schemas |
| Quality gate / loop / best / terminate | Done — Phase 5 |
| Visualizer / Formatter | Done — after HITL approve |
| Retry / observability / eval | Done — Phases 6–9 / 8 |
| HITL + checkpointer | Done — Phases 10 / 13 |
| Streaming + time-travel helpers | **Phase 20** |
| ADK→LG learning map | **Phase 20** |
| Architecture doc topology match | **Phase 20** |

---

## Implementation order (after approval)

1. Publish `docs/architecture/adk_to_langgraph.md` from the teaching tables above  
2. Add `graph_ops.py` (stream + get_state + history) wired to compiled graph/checkpointer  
3. Tests for stream updates + non-empty history after a demo invoke  
4. Align `solution_architecture.md` HITL order with `graph.py`  
5. Document Store-vs-custom-memory decision (keep custom)  
6. Bump to **0.20.0** (`__init__`, API, smoke test, `pyproject.toml`)  
7. Confirm ADK remains archive-only  

---

## What NOT to do

- Rebuild nodes into a second package  
- Revive ADK as an active runtime  
- Force LangGraph Store / PostgresStore migration  
- Require SSE/WebSocket job streaming in the API  
- Rewrite async checkpointer stack unless trivial  
- Claim “LG is always better”—document trade-offs honestly  

---

## Exit criteria

- ADK→LG mapping documented under `docs/architecture/`  
- Stream + state-history helpers exist with tests  
- Architecture docs match real topology (HITL before visualizer)  
- Custom memory retained with explicit Store decision note  
- Version **0.20.0**; ADK still archive-only  
