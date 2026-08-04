---
name: Phase 10 Persistent State
overview: "Phase 10 adds PostgreSQL persistence for workflows/executions/steps/versions/evaluations plus LangGraph checkpointer—clarifying session vs workflow vs durable/checkpoint/history/audit—single deployable LangGraph service. ADK SessionService notes below are historical."
todos:
  - id: p10-teach
    content: Explain session vs workflow state, durable execution, checkpoint, history, audit trail
    status: completed
  - id: p10-schema
    content: Add SQLAlchemy models + Alembic migration for workflows/executions/agent_executions/script_versions/evaluations
    status: completed
  - id: p10-repo
    content: Implement WorkflowRepository + DATABASE_URL session factory
    status: completed
  - id: p10-wire
    content: Wire runner/quality gate to checkpoint and append script/eval/agent rows
    status: completed
  - id: p10-tests
    content: "SQLite sync tests: migrate, checkpoint round-trip, versions, evaluations, finish"
    status: completed
  - id: p10-docs
    content: Document alembic upgrade + Postgres URL; keep single-service deploy story
    status: completed
isProject: false
---

# Phase 10 — Persistent Workflow State


## Master alignment
- Active stack: LangGraph only
- ADK: archive only (not a second runtime)
- If this plan still describes ADK APIs below, treat them as historical; redesign for LangGraph in Steps 2–3 of the phase loop

## Scope lock

- One concept: **durable workflow persistence** (PostgreSQL) + LangGraph checkpointer
- Single deployable service (modular package layout, **no microservices**)
- Stay on LangGraph; persistence sits beside the graph runner/checkpointer
- Do **not** introduce Kafka/Redis/K8s
- LangGraph **checkpointer** handles step resume; **business workflow durability** (audit/history/versions) uses our schema
- Depends on: `WorkflowState`, quality loop fields, evaluations, script contracts

**Note:** Historical ADK `DatabaseSessionService` / session blobs are archive-era patterns. Phase 10 targets LG checkpointer + explicit application persistence for audit/history/versions.

**Status:** Implemented (package **0.10.0**). Sync SQLAlchemy + MemorySaver default; Postgres optional.

## Inspect findings (2026-08-02, post Phase 9)

| Area | Finding |
|------|---------|
| LangGraph compile | `get_compiled_graph()` → `.compile()` with **no** checkpointer |
| Resume / `thread_id` | **Missing** — each `invoke` is ephemeral in-memory |
| Domain persistence | **No** `persistence/` package, models, repository, Alembic |
| `SESSION_DB_URL` | Present in config (default SQLite path) — **unused** by LangGraph app; ADK-era leftover naming |
| Deps | `aiosqlite` present; **no** SQLAlchemy, Alembic, asyncpg, `langgraph-checkpoint-postgres` |
| Docker Compose | Exists on disk (Postgres-shaped later deploy); not wired to active app |
| Observability `workflow_id` | Phase 9 `wf_*` trace id on `WorkflowState` — **name collision risk** with domain `workflows.id` UUID; design must rename/clarify (e.g. `trace_id` vs `workflow_id`) |
| Eval / CLI | Persist JSON files / stdout only — not durable DB |
| Plan drift | Mentions ADK session patterns as historical — keep LG checkpointer + domain schema |

### What already exists (keep)

- Typed `WorkflowState` serializable via `to_dict` / `from_dict` (good checkpoint payload)
- `run.invoke_workflow` as single wire point for persistence hooks
- Quality loop fields (`iteration`, `best_script`, `evaluation`) ready for version rows
- Phase 9 agent timing events (can map → `agent_executions`)

### Gaps this phase must close

1. Clarify **LG checkpointer** (thread resume) vs **domain Postgres tables** (audit/history)  
2. `DATABASE_URL` (+ deprecate/alias `SESSION_DB_URL`), SQLAlchemy async + Alembic  
3. Wire `compile(checkpointer=...)` + `thread_id` / configurable MemorySaver for tests  
4. Repository write path from `invoke_workflow` / gate (checkpoint + script/eval versions)  
5. CI tests on SQLite async; document Postgres for local/prod  

---

## Teaching (before coding)

### Session / thread state

LangGraph thread/checkpoint state for one run (`thread_id`). Optimized for graph resume. Can be memory or DB-backed via checkpointer.

### Workflow state

Our domain object (`WorkflowState`): `raw_idea`, `generated_script`, `evaluation`, `iteration`, `best_script`, …  
This is what **product logic** reasons about. It should be serializable and versioned independently of framework internals.

### Durable execution

The ability to **survive process restart** and still know: which workflow, which iteration, last scores, best script, final status. Not merely “logs exist”—**state can be reloaded**.

### Checkpoint

A **saved snapshot** of workflow state at a safe point (e.g. after evaluator, after quality gate). Enables resume/debug. Phase 10 minimum: persist checkpoint after each gate decision and at terminal status (not a full Temporal-style worker).

### Execution history

Ordered record of **what ran**: agent name, attempt/iteration, timestamps, status, token/cost if known. Answers “what happened in this run?”

### Audit trail

Append-only (or insert-only) history suitable for **post-hoc review**: who/what changed script versions and evaluations, with timestamps. Do not update-in-place over prior script versions—insert new version rows.

---

## Design principles

| Principle | Choice |
|-----------|--------|
| Deployable unit | One service / one process entrypoint |
| Modularity | `persistence/` package: models, repository, migrations |
| DB | PostgreSQL (prod); SQLite allowed for local tests via SQLAlchemy URL |
| LG checkpointer | Persist graph steps for resume; **also** write domain rows |
| ORM | SQLAlchemy 2.x async |
| Migrations | Alembic |

---

## Minimum PostgreSQL schema

```mermaid
erDiagram
    workflows ||--o{ executions : has
    executions ||--o{ agent_executions : has
    executions ||--o{ script_versions : has
    executions ||--o{ evaluations : has

    workflows {
        uuid id PK
        text request
        text status
        timestamptz created_at
        timestamptz updated_at
    }

    executions {
        uuid id PK
        uuid workflow_id FK
        text workflow_trace_id
        text final_status
        int iteration
        int max_iterations
        float best_score
        jsonb state_checkpoint
        text error
        timestamptz started_at
        timestamptz finished_at
    }

    agent_executions {
        uuid id PK
        uuid execution_id FK
        text agent_name
        int iteration
        text status
        int duration_ms
        int input_tokens
        int output_tokens
        float estimated_cost_usd
        int retry_count
        text error
        timestamptz started_at
        timestamptz finished_at
    }

    script_versions {
        uuid id PK
        uuid execution_id FK
        int iteration
        int version
        jsonb script
        boolean is_best
        timestamptz created_at
    }

    evaluations {
        uuid id PK
        uuid execution_id FK
        uuid script_version_id FK
        int iteration
        jsonb evaluation
        float overall_score
        boolean approved
        timestamptz created_at
    }
```

### Table roles

| Table | Purpose |
|-------|---------|
| `workflows` | Logical user request / job identity |
| `executions` | One pipeline run; holds latest checkpoint JSON + counters |
| `agent_executions` | Per-agent history (observability join) |
| `script_versions` | Immutable script snapshots per iteration |
| `evaluations` | Immutable eval snapshots linked to script version |

Indexes: `executions(workflow_id)`, `script_versions(execution_id, iteration)`, `evaluations(execution_id)`, `workflows(created_at)`.

---

## Persistence API (modular, in-process)

```text
persistence/
  models.py          # SQLAlchemy models
  repository.py      # WorkflowRepository
  session.py         # engine / session factory from DATABASE_URL
alembic/             # migrations
```

`WorkflowRepository` methods (minimum):

- `create_workflow(request) -> workflow_id`
- `start_execution(workflow_id, max_iterations, trace_id)`
- `checkpoint(execution_id, WorkflowState)`
- `record_agent_execution(...)`
- `add_script_version(execution_id, iteration, script, is_best)`
- `add_evaluation(execution_id, script_version_id, evaluation)`
- `finish_execution(execution_id, final_status, error=None)`

Wire from [`runner.py`](runner.py) / quality gate hooks—**same process**, no new service.

### Config

`DATABASE_URL=postgresql+asyncpg://...`  
Local default for tests: `sqlite+aiosqlite:///:memory:` or file under `data/`.

---

## Migration strategy

1. Add Alembic with initial revision creating the five tables  
2. Document: `alembic upgrade head` on deploy  
3. No destructive data migrations in v1  
4. Expand-only future revisions  

---

## Relationship to LangGraph checkpointer + domain DB

```mermaid
flowchart LR
    Runner --> CP["LangGraph checkpointer"]
    Runner --> Repo["WorkflowRepository PostgreSQL"]
    Nodes["Graph nodes"] --> CP
    Gate["quality_gate_node"] --> CP
    Gate --> Repo
    Runner --> Repo
```

LangGraph checkpointer is the live coordination/resume bus during a run.  
PostgreSQL domain tables are the **system of record** after each meaningful step (audit/history/versions).

---

## Tests

| Test | Assert |
|------|--------|
| Migration upgrade on SQLite/Postgres test URL | tables exist |
| Repository create workflow + execution | rows persisted |
| Checkpoint round-trip | `WorkflowState` reloadable from `state_checkpoint` |
| Script version immutability | two iterations → two rows; best flag updates correctly |
| Evaluation linked to script_version | FK integrity |
| Finish execution | `final_status` + `finished_at` set |

Use pytest-asyncio + in-memory/async SQLite for CI (no required external Postgres in default CI). Optional mark `postgres` for real PG.

---

## What NOT to do

- Split into workflow-service / eval-service microservices  
- Replace ADK with a durable-execution engine (Temporal) in this phase  
- Store API keys in checkpoint JSON  
- Full HITL approval tables (later phase)  

---

## Concrete design (for Approve)

### Teaching map → implementation

| Concept | Implementation |
|---------|----------------|
| Session / thread state | LangGraph `thread_id` + checkpointer |
| Workflow state | `WorkflowState` (domain) |
| Durable execution | Reload domain `executions.state_checkpoint` + optional LG resume by `thread_id` |
| Checkpoint | LG auto-checkpoint per step **and** domain JSON snapshot after gate / terminal |
| Execution history | `agent_executions` rows (from obs hooks / gate) |
| Audit trail | Insert-only `script_versions` + `evaluations` |

### Decision: two stores, one service

| Store | Role | Default (CI/local) | Prod |
|-------|------|--------------------|------|
| LangGraph checkpointer | Graph resume / step snapshots | `MemorySaver` | `PostgresSaver` (`langgraph-checkpoint-postgres`) |
| Domain DB | Audit, versions, reloadable business checkpoint | SQLite file/memory via SQLAlchemy | PostgreSQL |

Do **not** treat LG checkpoint tables as the product audit trail.

### Naming fix (required)

Phase 9 put obs id on `WorkflowState.workflow_id` (`wf_*`). Phase 10 domain table is also `workflows.id`.

**Chosen:** rename state field to `trace_id` (observability). Domain UUID stays `workflow_id` in DB / repository APIs. Update CLI JSON, obs events, tests accordingly (small breaking rename inside this learning repo).

### Config

| Knob | Purpose |
|------|---------|
| `DATABASE_URL` | Domain SQLAlchemy URL (primary) |
| `SESSION_DB_URL` | Deprecated alias → same as `DATABASE_URL` if unset |
| `CHECKPOINT_BACKEND` | `memory` (default) \| `postgres` |
| `CHECKPOINT_POSTGRES_URL` | Optional; defaults to `DATABASE_URL` when backend=postgres (psycopg form) |

Examples:

```bash
# CI / local domain + memory checkpointer
DATABASE_URL=sqlite+pysqlite:///:memory:
CHECKPOINT_BACKEND=memory

# Local durable
DATABASE_URL=sqlite+pysqlite:///./data/shorts.db

# Postgres (domain + LG checkpointer)
DATABASE_URL=postgresql+psycopg://shorts:shorts@localhost:5432/shorts
CHECKPOINT_BACKEND=postgres
```

### Sync path (match current CLI)

Keep `invoke` synchronous for Phase 10:

- SQLAlchemy **sync** engine/session (2.x style)  
- LangGraph **`PostgresSaver`** (sync) when backend=postgres; **`MemorySaver`** otherwise  
- Async API/`ainvoke` deferred to Phase 16  

Deps to add: `sqlalchemy`, `alembic`, `psycopg[binary]` (or `psycopg`), `langgraph-checkpoint-postgres`. Keep `aiosqlite` unused or drop later — prefer `sqlite+pysqlite` for sync tests.

### Package layout

```text
src/shorts_assistant/
  persistence/
    models.py
    session.py          # engine + SessionLocal from DATABASE_URL
    repository.py       # WorkflowRepository
  graph.py              # compile(checkpointer=...)
  run.py                # create workflow/execution, thread_id, persist hooks
alembic/ + alembic.ini
```

### LangGraph wiring

```python
graph = build_graph().compile(checkpointer=get_checkpointer())
config = {"configurable": {"thread_id": str(execution_id)}}
graph.invoke(state, config)
```

- `get_checkpointer()`: MemorySaver or PostgresSaver (+ `setup()` once)  
- `thread_id` = domain `execution.id` (UUID string)  
- Resume helper (minimum): `load_execution_state(execution_id)` from domain checkpoint JSON; optional `graph.get_state(config)` demo in tests/docs  

### Domain write path (from `invoke_workflow`)

1. `create_workflow(request)` → `start_execution(..., trace_id)`  
2. Invoke graph with checkpointer + `thread_id=execution_id`  
3. After invoke (and ideally after each gate via thin hook):  
   - `checkpoint(execution_id, WorkflowState.to_dict())`  
   - `add_script_version` / `add_evaluation` when script/eval present (per iteration)  
4. `finish_execution(final_status, error)`  
5. Best-effort `record_agent_execution` from gate/obs (can start minimal: one row per gate decision + terminal)

Fail-open vs fail-closed for DB: **fail-closed on start** (cannot create execution → raise); **fail-open on mid-run agent_execution inserts** (log warning) so a flaky history write does not kill a good short — but checkpoint/finish should surface errors in logs and set execution.error when finish fails.

### Schema

Keep the five-table ERD in this plan (workflows / executions / agent_executions / script_versions / evaluations).  
`executions.workflow_trace_id` stores Phase 9 `trace_id`.  
Never store API keys in `state_checkpoint` JSON (strip if present).

### Tests (`tests/persistence/` or `tests/unit` + `tests/integration`)

| Test | Backend |
|------|---------|
| Alembic upgrade → tables exist | SQLite file/memory |
| Repository CRUD + checkpoint round-trip | SQLite |
| Script versions immutable across iterations | SQLite |
| `compile(MemorySaver)` + invoke with `thread_id` | Memory |
| Optional `@pytest.mark.postgres` PostgresSaver smoke | Real PG only |

Default CI: **no external Postgres**.

### Docs / version

- README: `alembic upgrade head`, `DATABASE_URL`, `CHECKPOINT_BACKEND`, naming `trace_id` vs domain workflow  
- Docker Compose: add Postgres service later-friendly; Phase 10 can document URL without forcing Compose rewrite  
- Package **0.10.0**

### Out of scope

- Temporal / Kafka / Redis  
- Microservices  
- HITL interrupt tables (Phase 13)  
- Full async rewrite  
- Migrating eval JSON results into Postgres  

---

## Implementation order (after Approve)

1. Rename `workflow_id` → `trace_id` on state/obs/CLI  
2. `persistence/` models + session + Alembic initial migration  
3. `WorkflowRepository`  
4. Checkpointer factory + `compile(checkpointer=...)` + `thread_id` in `run.py`  
5. Wire checkpoint/versions/evals/finish  
6. Tests (SQLite + MemorySaver) + README  
7. Verify: migrate, invoke, reload checkpoint from DB  

## Exit criteria

- Concepts mapped to LG checkpointer + domain tables  
- Migrations create minimum schema  
- Execution survives process restart via domain checkpoint reload  
- Script versions + evaluations auditable  
- CI green without external Postgres  
- `trace_id` vs domain `workflow_id` unambiguous  

## Approval gate

Implement only after explicit:

- “Approve Phase 10 design — implement”  
- or “Approved, proceed with implementation”
