---
name: Phase 20 LangGraph Rebuild
overview: "Phase 20: LangGraph parity/hardening (ADK already archived). Concept map ADK→LG for learning only; deepen LG state/loop/HITL/obs. Not a second live stack; no 20/80 dual maintenance."
todos:
  - id: p20-map
    content: Write ADK→LangGraph concept map and comparison (state, agents, tools, edges, loops, HITL, MCP, A2A, obs, tests)
    status: pending
  - id: p20-state-graph
    content: "Create langgraph_shorts package: ShortsState, quality_gate conditional loop, best-version tracking"
    status: pending
  - id: p20-nodes
    content: Implement research/script/eval/visual/format nodes with structured outputs + retries + obs
    status: pending
  - id: p20-hitl-checkpoint
    content: Add checkpointer + HITL interrupt/resume path
    status: pending
  - id: p20-tests-docs
    content: LangGraph loop/termination tests; README notes LangGraph-only; ADK already archived
    status: pending
isProject: false
---

# Phase 20 — LangGraph Parity / Hardening


## Master alignment
- Active stack: LangGraph only
- ADK: archive only (not a second runtime)
- If this plan still describes ADK APIs below, treat them as historical; redesign for LangGraph in Steps 2–3 of the phase loop

## Scope lock

- **Purpose:** deepen LangGraph implementation + document ADK→LG concept map for learning  
- **ADK:** already in `archive/adk_baseline/` per master decision — do not revive as active runtime  
- **Active stack:** LangGraph only  
- Package: primary app is LangGraph (name TBD in Phase 1 skeleton)  
- Same **functional** requirements listed by you  
- Shared contracts where practical (`schemas`, eval dataset)—not shared orchestrators  
- Do not introduce K8s; local runnable graph + API/worker migrate to LG in later phases  

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

## Package layout (primary LangGraph app)

```text
langgraph_shorts/
  state.py
  graph.py          # StateGraph compile
  nodes/
    research.py
    scriptwriter.py
    evaluator.py
    quality_gate.py
    visualizer.py
    formatter.py
  routing.py        # model choice (mirror Phase 14 ideas)
  resilience.py     # retry wrappers
  observability.py
  cli.py
tests_langgraph/
  test_gate_graph.py
  test_loop_termination.py
```

Active package is the LangGraph app (name from Phase 1 skeleton); ADK lives only under `archive/adk_baseline/`.

---

## Functional parity checklist

| Requirement | LG approach |
|-------------|-------------|
| Explicit state | `ShortsState` TypedDict/Pydantic |
| Scriptwriter / Evaluator | nodes + structured parse |
| Quality gate / loop / best / terminate | gate node + conditional edges |
| Visualizer / Formatter | nodes after pass |
| Retry | tenacity around model calls in nodes |
| Observability | workflow_id + node logs |
| Evaluation | eval_runner invokes LangGraph graph (sole backend) |

---

## Implementation order (after approval)

1. Publish ADK↔LG mapping table (teach)  
2. Define `ShortsState` + compile empty graph with gate logic ported from pure `apply_quality_gate`  
3. Implement nodes with structured outputs (Gemini via `langchain-google-genai` or google-genai SDK)  
4. Add checkpointer (SQLite) + HITL interrupt  
5. CLI invoke parity smoke  
6. Port/adapt loop tests to `graph.invoke`  
7. Document architectural differences essay in `langgraph_shorts/README.md`  
8. Confirm ADK remains archive-only (not revived)  
9. Document LangGraph as the sole production path  

---

## What NOT to do

- Revive ADK as an active runtime  
- Force every historical ADK class to a LangGraph class of the same name  
- Feature-race archive ADK and LangGraph (violates LangGraph-only)  
- Rewrite MCP/A2A fully before core loop works—stub research node first, add MCP later  
- Claim “LG is always better”—document trade-offs honestly  

---

## Exit criteria

- Mapping + comparison documented  
- LangGraph app meets functional checklist as the sole primary  
- ADK remains archive-only (not a live baseline)  
- Tests for gate/loop/termination on LG graph  
- Clear write-up of architectural differences + LangGraph-only allocation
