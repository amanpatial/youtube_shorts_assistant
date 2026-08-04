---
name: Phase 21 ADK vs LangGraph ADR
overview: "Phase 21 ADR documents the confirmed decision: LangGraph-only active stack; ADK archived (not mixed, not 20% maintained). Comparison matrix for learning; does not revive dual-runtime."
todos:
  - id: p21-compare-doc
    content: Write docs/architecture/adk_vs_langgraph.md with full 20-dimension comparison (learning), strengths, weaknesses, trade-offs, scenarios
    status: pending
  - id: p21-adr
    content: "Write docs/adr/0001-primary-orchestration-framework.md: LangGraph-only; ADK archived under archive/adk_baseline/"
    status: pending
  - id: p21-readme
    content: Point README at ADR — LangGraph-only; ADK archive reference
    status: pending
isProject: false
---

# Phase 21 — ADK vs LangGraph Architecture Review


## Master alignment
- Active stack: LangGraph only
- ADK: archive only (not a second runtime)
- If this plan still describes ADK APIs below, treat them as historical; redesign for LangGraph in Steps 2–3 of the phase loop

## Project narrative (canonical)

> This project started as a Google ADK experiment and is being rebuilt fresh on LangGraph to explore stateful agent orchestration, evaluation loops, MCP, A2A, observability, persistence, and production AI engineering.

**Confirmed product decision:** LangGraph-only active runtime; ADK in `archive/adk_baseline/` only.

## Scope lock

- Deliverable: comparison write-up + **ADR** (`docs/adr/0001-primary-orchestration-framework.md`)
- Honest comparison (no fake universal winner)
- **Decision already made:** LangGraph-only; ADK archived — ADR records it  
- Do not propose reviving dual-stack maintenance  

---

## Recommendation (decision up front)

**Active implementation: LangGraph only.**  
**Google ADK: archived reference — not a maintained 20% baseline, not mixed into the app.**

### Justification (project-specific)

1. Explicit orchestration skills (state, edges, loops, checkpoints, HITL) are the learning target.  
2. Dual active stacks split focus and create plan/code drift.  
3. ADK experiment already taught agent/tool/session basics; archive preserves that history.  
4. Gemini can remain a **model provider** without ADK as the orchestrator.  
5. One production surface → clearer tests, deploy, and ownership.

---

## Effort allocation

| Track | Share | Role |
|-------|------:|------|
| LangGraph | 100% active | Sole runtime and production path |
| ADK | Archive only | `archive/adk_baseline/` — read-only history |

**Do not** run or feature-race ADK alongside LangGraph.

---

## Comparison matrix (20 dimensions)

| # | Dimension | ADK — strengths | ADK — weaknesses | LangGraph — strengths | LangGraph — weaknesses |
|---|-----------|-----------------|------------------|-----------------------|------------------------|
| 1 | Developer experience | Agent-centric; `adk web`; fast Gemini path | Younger mental model; docs evolving | Explicit graphs; huge LC tutorials | More concepts (reducers, compile, LC versions) |
| 2 | State management | Session dict + our Pydantic lens | State not first-class in framework | Typed state + reducers | Easy to over-engineer channels |
| 3 | Orchestration | Sequential/Loop/Parallel agents | Less “draw the graph” | StateGraph is the product | Boilerplate for simple pipelines |
| 4 | Conditional routing | Callbacks / escalate / custom agents | Less declarative | `conditional_edges` native | Must design well or spaghetti |
| 5 | Loops | `LoopAgent` + max_iterations | Escalate patterns to learn | Cycles + state counters | Infinite loops if mis-edged |
| 6 | Multi-agent | Sub-agents, transfer, AgentTool | Patterns opinionated | Subgraphs, supervisor patterns | Many competing patterns |
| 7 | MCP | First-class `McpToolset` | Tied to ADK lifecycle | Via adapters / manual | More glue |
| 8 | A2A | `RemoteA2aAgent` | Ecosystem still early | DIY node | Not batteries-included |
| 9 | Persistence | SessionService + our PG | Split brain if not careful | Checkpointers per step | Ops of saver backends |
| 10 | HITL | App-designed pause (our API) | Not as native as LG interrupt | `interrupt`/`resume` | Still need product UX |
| 11 | Observability | Events + OTel hooks | Prompt tooling less than LangSmith | LangSmith optional | Vendor gravity to LangSmith |
| 12 | Testing | Pure gate fn + fakes | Agent objects heavier | Node unit tests natural | Graph integration verbosity |
| 13 | Debugging | `adk web`, event stream | Harder graph visualization | Graph diagrams, studio | LC stack traces deep |
| 14 | Extensibility | Custom `BaseAgent` | Framework boundaries | Any node function | Dependency sprawl |
| 15 | Vendor neutrality | Google-leaning | Portability cost | Provider-flexible | LC coupling |
| 16 | Ecosystem | Google ADK/Gemini/Vertex | Smaller than LC | Massive LC/LG ecosystem | Breaking changes / versioning |
| 17 | Production deploy | `adk deploy` + our Docker API/worker | Google gravity | Containerize graph service | You build more platform |
| 18 | Failure handling | Our resilience layer | Fewer built-in job semantics | Retry in nodes; checkpoints help resume | Easy inconsistent policies |
| 19 | Performance | Direct Gemini path | Loop agent overhead TBD | Efficient if nodes lean | LC abstractions overhead |
| 20 | Maintainability | Clear as historical archive | Drift if revived beside LG | Clear control flow as sole primary | Must not dual-feature |

---

## Trade-offs (summary)

- **ADK** was useful as an experiment; archive it rather than maintain it.  
- **LangGraph** is the sole active orchestrator.  
- **Archive + single primary** beats dual production and beats “20% ADK forever.”

---

## When ADK is preferable

- Gemini/Vertex-first products with heavy ADK MCP/A2A  
- Rapid agent prototyping with `adk web`  
- Teams standardized on Google Agent stack  

## When LangGraph is preferable (this project’s primary bet)

- Explicit quality-loop / HITL / checkpoint-centric workflows  
- Desire for vendor-flexible model routing long-term  
- Deep practice with graph orchestration as a core skill  
- Single primary production surface with ADK frozen in archive  

---

## ADR to write on implementation

**File:** [`docs/adr/0001-primary-orchestration-framework.md`](docs/adr/0001-primary-orchestration-framework.md)

Structure:

1. Title / Status: **Accepted**  
2. Context: quote project narrative (ADK experiment → LangGraph rebuild for orchestration, eval loops, MCP, A2A, obs, persistence, prod AI engineering)  
3. Decision: **LangGraph-only; ADK archived (not mixed)**  
4. Consequences (positive/negative)  
5. Alternatives considered (ADK primary, dual-prod, delete ADK)  
6. Appendix: comparison matrix  

README: “Primary: LangGraph; ADK: archive reference only.”

---

## Implementation order (after approval of this phase’s design)

1. Write `docs/architecture/adk_vs_langgraph.md`  
2. Write ADR 0001 with **LangGraph-only; ADK archived** decision  
3. Update README pointers: LangGraph-only; ADK archive reference  
4. Do **not** delete archived ADK under `archive/adk_baseline/` (reference only); do **not** revive as runtime  

## Exit criteria

- Full 20-dimension comparison documented  
- Trade-offs and scenarios clear  
- ADR records LangGraph-only + ADK archived  
- Effort: LangGraph 100% active; ADK archive only
