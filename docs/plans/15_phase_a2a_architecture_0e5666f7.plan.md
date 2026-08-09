---
name: Phase 15 A2A Architecture
overview: "Phase 15 introduces A2A as agent-to-agent interoperability (distinct from MCP), defines an independently responsible Research Agent with identity/capabilities/contracts, and implements the smallest custom LangGraph node/experiment—not RemoteA2aAgent as primary."
todos:
  - id: p15-teach
    content: Explain MCP vs A2A and function/tool/MCP/sub-agent/A2A-remote differences
    status: completed
  - id: p15-contract
    content: Define Research Agent identity, capabilities, ResearchRequest/Response, lifecycle, failures
    status: completed
  - id: p15-server
    content: Implement smallest research A2A server process (standalone; not ADK RemoteA2aAgent as primary)
    status: completed
  - id: p15-client
    content: Wire custom LG A2A client node behind A2A_RESEARCH_ENABLED; map response to WorkflowState.research
    status: completed
  - id: p15-tests
    content: Contract tests + mocked A2A + optional live a2a marker
    status: completed
  - id: p15-docs
    content: Document two-process local run and degraded fallback
    status: completed
isProject: false
---

# Phase 15 — Agent-to-Agent Architecture


## Master alignment
- Active stack: LangGraph only
- ADK: archive only (not a second runtime)
- If this plan still describes ADK APIs below, treat them as historical; redesign for LangGraph in Steps 2–3 of the phase loop

## Prerequisite

Phase 12 MCP working (agent↔tool). This phase adds **agent↔agent** only after that distinction is clear in the project.

## Scope lock

- One concept: **A2A interoperability** (learning exercise)
- **One** second independently responsible agent: **Research Agent**
- Do **not** split Scriptwriter/Evaluator/Visualizer/Formatter into services
- Prefer a custom LangGraph research node (HTTP/A2A client) + local A2A server process experiment
- Feature flag: default path can remain in-process; A2A opt-in for the experiment
- Not microservices for their own sake

**Status:** Implemented locally as **0.15.0** (2026-08-05). Uncommitted until batch check (Phases 11–21).  
**Commit policy:** batch code-check/commit for Phases 11–21 later (no commit until you ask).

## Inspect findings (2026-08-05)

| Area | Finding |
|------|---------|
| A2A code | **Missing** — no `a2a_*` package, no agent card, no remote client |
| Research today | In-process `research_node` → `demo_research` + optional MCP catalog notes |
| MCP (Phase 12) | `shorts_catalog` tools — agent↔tool (correctly separate from A2A) |
| Config | No `A2A_RESEARCH_*` flags |
| Deps | No `a2a-sdk`; HTTP client not required yet for research |
| ADK | Archive only — do **not** use `RemoteA2aAgent` as primary |
| CI | Must keep `A2A_RESEARCH_ENABLED=false` (default) so offline tests never need a peer process |

### What already exists (reuse)

- `WorkflowState.research: str | None` — map A2A response into a string brief  
- MCP fail-open pattern (`research_catalog_notes`) — mirror for A2A degraded  
- Obs `log_event` + timeouts pattern from `mcp_client`  
- Two-process local run pattern (like MCP stdio server docs)  

### Gaps this phase must close

1. `ResearchRequest` / `ResearchResponse` Pydantic contracts  
2. Standalone research agent process + agent card + task endpoint  
3. Custom LG client behind `A2A_RESEARCH_ENABLED` (default **false**)  
4. Timeout / malformed / down → degraded (or fail if `A2A_RESEARCH_REQUIRED`)  
5. Docs: MCP vs A2A vs in-process; two-terminal local run  
6. Tests: contracts + mocked client; optional `@pytest.mark.a2a` live smoke  

### Concrete design (for Approve)

**Smallest useful stack (learning):** thin HTTP + Agent Card JSON + JSON task API that carries our contracts — optionally wrap with `a2a-sdk` if it stays small; prefer **stdlib/httpx + FastAPI/Starlette** over pulling ADK. Full JSON-RPC A2A surface is welcome but not required if card + `POST /tasks/research` + lifecycle statuses meet the learning goal.

```text
src/shorts_assistant/
  a2a_research/
    contracts.py      # ResearchRequest / ResearchResponse
    agent_card.py     # shorts_research_agent card JSON
    server.py         # standalone process (demo research + optional MCP)
    client.py         # HTTP client used by research_node
  nodes.py            # if A2A enabled → client; else demo+MCP (today)
```

| Flag | Default | Behavior |
|------|---------|----------|
| `A2A_RESEARCH_ENABLED` | `false` | in-process research (CI parity) |
| `A2A_RESEARCH_URL` | `http://127.0.0.1:9101` | peer base URL |
| `A2A_TIMEOUT_SEC` | `30` | client timeout |
| `A2A_RESEARCH_REQUIRED` | `false` | if true, A2A failure → FAILED; else degrade |

- Map `ResearchResponse` → `state.research` (bullets + sources joined as text)  
- Target package version **0.15.0**  
- Marker: `@pytest.mark.a2a` (exclude from default CI like `llm`)  

---

## Teaching

### MCP vs A2A

| | MCP | A2A |
|--|-----|-----|
| Relationship | **Agent ↔ Tool/Resource** | **Agent ↔ Agent** |
| Counterpart | catalog DB, APIs, files | another agent with goals/contracts |
| Example here | `shorts_catalog` tools | Research Agent produces research brief |

### Function call vs tool call vs MCP vs sub-agent vs A2A remote

| Mechanism | What it is | Boundary |
|-----------|------------|----------|
| **Function call** | Model emits a typed call; runtime executes a local Python function | In-process function |
| **Tool call** | Same idea in agent frameworks; tool may wrap APIs | Usually in-process or HTTP behind a tool |
| **MCP** | Standard protocol for discovering/calling **tools/resources** | Agent ↔ tool server |
| **Sub-agent / subgraph** | Another node or subgraph in the **same** LangGraph | Same process, shared state often |
| **A2A remote agent** | Protocol to message a **separate agent identity** (card, tasks, lifecycle) | Process/network boundary; own responsibility |

Sub-agent ≠ A2A: same graph composition vs **interop across agent boundaries**.

---

## Second agent: Research Agent (independent)

### Agent identity

- **Name:** `shorts_research_agent`  
- **URL (local):** `http://127.0.0.1:9101` (dev only)  
- **Agent card:** skills = technical research for developer Shorts  

### Capabilities

- Gather concise, sourced notes for a topic  
- Optionally use MCP `shorts_catalog` and/or google_search **inside the research agent**  
- Does **not** write final scripts or evaluate quality  

### Task contract

```text
ResearchRequest:
  topic: str
  audience: str = "developers"
  max_bullets: int = 8

ResearchResponse:
  topic: str
  bullets: list[str]          # facts / angles
  sources: list[str]          # urls or labels
  confidence: float           # 0-1
  errors: list[str] = []
```

Pydantic models in shared `contracts/research_a2a.py` (or under `a2a_research/`).

### Lifecycle

```mermaid
sequenceDiagram
    participant Shorts as ShortsLangGraph
    participant A2A as A2A client node
    participant Res as ResearchAgent Server

    Shorts->>A2A: ResearchRequest task
    A2A->>Res: A2A message/task
    Res->>Res: tools MCP/search
    Res-->>A2A: ResearchResponse
    A2A-->>Shorts: state research filled
    Shorts->>Shorts: scriptwriter_node ...
```

States: `submitted → working → completed | failed | timeout`.

### Failure handling

| Failure | Behavior |
|---------|----------|
| Research agent down | Timeout; Shorts continues with empty research + log (degraded) or fail if `A2A_RESEARCH_REQUIRED=true` |
| Malformed response | Validate; treat as failure; do not poison script state |
| Slow | `A2A_TIMEOUT_SEC` (e.g. 30s) |
| Partial | Return bullets with `errors[]` |

---

## Smallest A2A experiment (chosen technology)

**Stack:** LangGraph custom research client node + lightweight A2A/HTTP server process (official A2A Python pieces welcome). **Not** ADK `RemoteA2aAgent` as the primary design.

1. **`a2a_research/`** package: standalone research agent process + A2A/HTTP serve entry  
2. **Main Shorts LangGraph:** replace in-process research node with custom A2A client node when `A2A_RESEARCH_ENABLED=true`  
3. Map `ResearchResponse` → `WorkflowState.research` (string or structured dump)  
4. Local docker-compose **optional later**; Phase 15 docs: run two terminals (research server + shorts runner)

**Not in scope:** Kubernetes, service mesh, splitting the whole pipeline, reviving ADK as the A2A host.

```mermaid
flowchart LR
    subgraph shorts [Shorts process]
      Root[LangGraph Shorts]
      Remote[custom A2A client node]
      Root --> Remote
    end
    subgraph research [Research process]
      Card[Agent Card]
      RA[Research agent]
      Card --> RA
    end
    Remote -->|A2A/HTTP| Card
```

---

## Definition of done for the learning exercise

- You can point to code and say: this boundary is **A2A**, that one is **MCP**, that one is **sub-agent**  
- Research has its own contract and can run as its own process  
- Shorts still owns script/eval/visual loop  
- Degraded path documented when research A2A is down  

---

## Tests

| Test | Type |
|------|------|
| `ResearchRequest`/`ResearchResponse` validation | unit |
| Mock A2A client returns brief → state.research set | unit/integration |
| Malformed A2A payload rejected | unit |
| `A2A_RESEARCH_ENABLED=false` uses in-process research (parity) | wiring |
| Optional: live local server smoke marked `@pytest.mark.a2a` | opt-in |

---

## What NOT to do

- Turn every existing agent into a remote service  
- Confuse MCP catalog tools with Research Agent  
- Require A2A for CI default  
- Design Netflix-scale agent mesh  

---

## Implementation order (after approval)

1. Teach MCP vs A2A and the five-way comparison table  
2. Freeze Research identity + request/response contracts  
3. Implement research agent app + local A2A serve  
4. Wire custom LG A2A client node behind feature flag  
5. Failure/timeout/degraded behavior + tests  
6. Wrap-up: when to use sub-agent vs A2A vs MCP  

## Exit criteria

- Clear conceptual distinctions documented  
- Independent Research Agent with contract  
- Smallest custom LangGraph A2A experiment runs locally  
- Pipeline not microservice-splattered  
- Learning goal (interop) met without unnecessary infra
