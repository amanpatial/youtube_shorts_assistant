# ADK → LangGraph concept map (Phase 20)

Learning reference only. **Active runtime is LangGraph** (`src/shorts_assistant/`).  
Google ADK lives under [`archive/adk_baseline/`](../../archive/adk_baseline/) and is not maintained as a second stack.

Formal decision: [ADR 0001](../adr/0001-primary-orchestration-framework.md).  
Full comparison matrix: [adk_vs_langgraph.md](adk_vs_langgraph.md).

## Do not blindly translate

| Bad translation | Better thinking |
|-----------------|-----------------|
| `LlmAgent` → “LangGraph Agent class” | A **node** that calls a model with a typed update |
| `LoopAgent` → `while True` wrapper | **Conditional edges** + counters on state |
| `output_key` → mystery | Explicit **state channels** / reducers |
| `SessionService` → ignore | LangGraph **checkpointer** (Memory / Postgres) |

ADK is **agent-graph + session dict**. LangGraph is **state machine + reducers + checkpoints**.

## Mapping

| Google ADK | LangGraph (this project) |
|------------|---------------------------|
| Session / `WorkflowState` dict | `WorkflowState` (Pydantic) on `StateGraph` |
| `LlmAgent` | Node fn → partial state update (`nodes.py`) |
| `SequentialAgent` | Linear edges `A → B → C` |
| `LoopAgent` + escalate | Cycle + `conditional_edges` (`quality_gate`, HITL) |
| `output_schema` | Pydantic parse in node (`schemas.py` / `contracts.py`) |
| MCP `McpToolset` | MCP client inside research node |
| `RemoteA2aAgent` | HTTP A2A client inside research (custom) |
| Quality gate agent | Pure node + `route_after_gate` |
| `Runner` + session | `graph.invoke` / `graph.stream` + `thread_id` |
| Session DB | Domain SQL + LangGraph checkpointer |
| HITL pause | `interrupt()` / `Command(resume=…)` |

## Comparison (honest)

| Topic | ADK | LangGraph |
|-------|-----|-----------|
| State | Session dict + our Pydantic lens | First-class graph state |
| Agents | First-class `LlmAgent` | Often “just nodes” |
| Loops | `LoopAgent(max_iterations)` | Conditional cycle + counters |
| Checkpoints | SessionService / DIY | Built-in checkpointer per step |
| HITL | App-level pause | Native interrupt/resume |
| MCP / A2A | Batteries-included adapters | Manual / custom nodes (more glue) |
| Obs | Events | Custom JSON + optional OTel; LangSmith optional |

LangGraph is not “always better”—it matches this project’s learning goals (explicit edges, checkpoints, HITL). ADK taught agent/tool/session basics; the archive preserves that history.

## Actual topology (code)

```text
research → memory_retrieve → scriptwriter ↔ evaluator ↔ quality_gate
                              ↓ (pass/exhausted)
                         human_review → visualizer → formatter → END
```

Helpers (Phase 20): [`graph_ops.py`](../../src/shorts_assistant/graph_ops.py) — `stream_workflow`, `get_thread_state`, `list_state_history`.

## LangGraph Store vs custom memory (decision)

| Option | Pros | Cons |
|--------|------|------|
| LangGraph `Store` / `PostgresStore` | First-class LG API, cross-thread memory patterns | Extra migration; CI still needs SQLite story |
| **Custom SQLAlchemy memory (current)** | Already shipped (Phase 11); works on SQLite + Postgres; eval A/B hooks | Not the LG Store API |

**Decision for Phase 20:** keep **custom** `memory/` (JSON embeddings in domain DB). Revisit Store only if cross-thread LG-native memory becomes a product requirement. Deploy shape stays “one Postgres”; embeddings need not move to pgvector indexes yet.
