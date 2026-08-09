# ADK vs LangGraph — comparison (Phase 21)

Honest comparison for learning. **Product decision is settled** — see [ADR 0001](../adr/0001-primary-orchestration-framework.md).

For node-level translation (do not blindly map classes), see [adk_to_langgraph.md](adk_to_langgraph.md).  
For the running system shape, see [solution_architecture.md](solution_architecture.md).

## Decision (up front)

| Track | Share | Role |
|-------|------:|------|
| **LangGraph** | 100% active | Sole runtime — `src/shorts_assistant/` |
| **Google ADK** | Archive only | `archive/adk_baseline/` — read-only history |

Do **not** feature-race ADK alongside LangGraph. Do **not** delete the archive (it preserves the experiment).

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
| 10 | HITL | App-designed pause (our API) | Not as native as LG interrupt | `interrupt` / `resume` | Still need product UX |
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

## Trade-offs (summary)

- **ADK** was useful as an experiment; archive it rather than maintain it.
- **LangGraph** is the sole active orchestrator for this Shorts learning system.
- **Archive + single primary** beats dual production and beats “20% ADK forever.”
- Gemini remains a **model provider**; orchestration does not require ADK.

## When ADK is preferable

- Gemini/Vertex-first products with heavy first-class ADK MCP/A2A
- Rapid agent prototyping with `adk web`
- Teams already standardized on the Google Agent stack

## When LangGraph is preferable (this project)

- Explicit quality-loop / HITL / checkpoint-centric workflows
- Vendor-flexible model routing over time
- Deep practice with graph orchestration as a core skill
- One production surface with ADK frozen in archive

## Project-specific justification

1. Explicit orchestration (state, edges, loops, checkpoints, HITL) is the learning target.  
2. Dual active stacks split focus and create plan/code drift.  
3. The ADK experiment already taught agent/tool/session basics; the archive preserves that history.  
4. One production surface → clearer tests, deploy, and ownership.
