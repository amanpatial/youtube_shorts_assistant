# YouTube Shorts Assistant

LangGraph learning project that turns a developer-focused idea into a YouTube Short concept — with typed state, a quality loop, offline eval, observability, and durable persistence.

| | |
|--|--|
| **Version** | **0.10.0** (Phases **1–10** complete) |
| **Active stack** | LangGraph — [`src/shorts_assistant/`](src/shorts_assistant/) |
| **ADK experiment** | Archived — [`archive/adk_baseline/`](archive/adk_baseline/) (not a second runtime) |
| **Architecture** | [`docs/architecture/solution_architecture.md`](docs/architecture/solution_architecture.md) |
| **Phase plans** | [`docs/plans/`](docs/plans/) |

## What’s built (Phases 1–10)

| Phase | Focus | In the repo |
|------:|-------|-------------|
| 1 | Hygiene + ADK archive + LangGraph skeleton | `archive/adk_baseline/`, package under `src/` |
| 2 | Typed workflow state | `state.py` — `WorkflowState` / statuses |
| 3 | Structured contracts | `schemas.py`, `contracts.py`, prompts |
| 4 | Real evaluator | `judge.py`, `evaluation_checks.py` |
| 5 | Quality loop | `quality_gate.py` — PASS / RETRY / EXHAUSTED |
| 6 | Failure handling | `failures.py` — taxonomy + scoped LLM retries |
| 7 | Test pyramid | `tests/{unit,contract,workflow,integration,…}` |
| 8 | Offline eval dataset | `evals/`, `python -m shorts_assistant.eval` |
| 9 | Observability | `observability.py` — `trace_id`, JSON events; opt-in OTel |
| 10 | Persistent state | `persistence/`, Alembic, LG checkpointer |

**Next up:** Phase 11 — Memory / RAG ([plan](docs/plans/11_phase_memory_rag_cb33e6fb.plan.md)).

## Pipeline

```text
Research → (Scriptwriter ↔ Evaluator ↔ Quality Gate)↺ → Visualizer → Formatter
```

- **PASS** → visuals  
- **RETRY** → rewrite script (max iterations)  
- **EXHAUSTED** → keep best script → visuals  

Offline demo markers: `[reject]` (fail until exhaust), `[retry-pass]` (fail then pass).

## Prerequisites

- Python **3.11+** (3.12 recommended)
- Gemini API key **or** Vertex AI with ADC (only needed for live judge / live LLM paths)

## Setup

```bash
cd /path/to/youtube_shorts_assistant

python3.12 -m venv venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
# Edit .env — set GOOGLE_API_KEY if you will call Gemini
```

## Run

```bash
source venv/bin/activate
export PYTHONPATH=src

python -m shorts_assistant "How to build AI agents with LangGraph"
python -m shorts_assistant "Weak idea [reject]"
python -m shorts_assistant "Topic [retry-pass]"
```

Each run prints final `WorkflowState` JSON (includes `trace_id`, `execution_id` when persistence is on) and writes structured logs to stderr.

## Configuration

See [`.env.example`](.env.example).

| Variable | Purpose |
|----------|---------|
| `GOOGLE_API_KEY` | Gemini API key (required unless Vertex) |
| `GOOGLE_GENAI_USE_VERTEXAI` | `TRUE` to use Vertex ADC |
| `MODEL_NAME` | Model id (default `gemini-2.0-flash-001`) |
| `QUALITY_THRESHOLD` | Gate pass score (default `7.0`) |
| `LOG_LEVEL` / `LOG_PAYLOADS` | Logging; keep payloads off by default |
| `ENABLE_OTEL` | Opt-in OpenTelemetry |
| `DATABASE_URL` | Domain DB (default SQLite `./data/shorts.db`) |
| `CHECKPOINT_BACKEND` | `memory` (default) or `postgres` |
| `CHECKPOINT_POSTGRES_URL` | Optional Postgres URL for LG checkpointer |
| `LLM_*` / `LIVE_JUDGE_FALLBACK` | Live-call timeouts, retries, fallback |

## Tests & lint

Deterministic control-plane tests (state, gates, loops, contracts, persistence) stay green **without** a model. Live LLM tests are opt-in and flaky by nature — do not replace one suite with the other.

```bash
source venv/bin/activate
export PYTHONPATH=src

pytest -m "not llm" -q          # CI default (~81 tests)
pytest -m llm -q                # needs GOOGLE_API_KEY or Vertex
ruff check src tests
```

Layout: `tests/unit` · `contract` · `workflow` · `integration` · `persistence` · `regression` · `eval_harness` · `eval_llm` · `fixtures`.

## Offline evaluation (Phase 8)

Fixed dataset + harness + compare — establish a baseline **before** changing prompts/models.

| Mode | Command | LLM? |
|------|---------|------|
| `demo` | synthetic judge, demo writers | No |
| `live_judge` | Gemini judge, demo writers | Yes |

```bash
PYTHONPATH=src python -m shorts_assistant.eval run --mode demo

PYTHONPATH=src python -m shorts_assistant.eval run --mode live_judge \
  --save-baseline evals/results/baselines/baseline_v1.json

PYTHONPATH=src python -m shorts_assistant.eval compare \
  --baseline evals/results/baselines/baseline_v1.json \
  --candidate evals/results/runs/<run_id>.json
```

Dataset: [`evals/shorts_v1_dataset.json`](evals/shorts_v1_dataset.json) (20 cases).

## Observability (Phase 9)

Every `invoke_workflow` / CLI run gets a **`trace_id`** (`wf_*`) and JSON log events (node timings, gate decisions, summary). Domain persistence uses a separate UUID **`workflow_id`**.

```json
{"event":"workflow_start","trace_id":"wf_abc123"}
{"event":"gate_decision","decision":"RETRY","iteration":1,"evaluation_score":6.8,"trace_id":"wf_abc123"}
{"event":"gate_decision","decision":"PASS","iteration":2,"evaluation_score":8.2,"trace_id":"wf_abc123"}
{"event":"workflow_summary","final_status":"COMPLETED","evaluation_scores":[6.8,8.2],"trace_id":"wf_abc123"}
```

OpenTelemetry is opt-in (`ENABLE_OTEL=true`). Do not use archived ADK `telemetry.py`.

## Persistence (Phase 10)

Two stores, one process:

1. **LangGraph checkpointer** — step resume via `thread_id=execution_id` (`MemorySaver` default; `PostgresSaver` optional)  
2. **Domain DB** — audit/history: `workflows`, `executions`, `script_versions`, `evaluations`, `agent_executions`

```bash
# Migrations (prod/deploy). Local SQLite also auto-creates tables on first run.
alembic upgrade head

PYTHONPATH=src python -m shorts_assistant "topic"
```

Reload a finished run: `load_execution_state(execution_id)` from `shorts_assistant.run`.

Postgres example:

```bash
# DATABASE_URL=postgresql+psycopg://shorts:shorts@localhost:5432/shorts
# CHECKPOINT_BACKEND=postgres
```

## Project layout

```
youtube_shorts_assistant/
├── src/shorts_assistant/     # Active LangGraph app
│   ├── state.py              # WorkflowState contract
│   ├── schemas.py / contracts.py
│   ├── nodes.py / graph.py / quality_gate.py
│   ├── judge.py / failures.py
│   ├── observability.py / telemetry.py
│   ├── persistence/          # SQLAlchemy models + repository
│   ├── checkpointer.py
│   ├── run.py                # traced + persisted entrypoint
│   ├── memory/               # Phase 11 placeholder
│   └── eval/                 # offline dataset runner + compare
├── alembic/                  # domain migrations
├── evals/                    # shorts_v1 + results/
├── archive/adk_baseline/     # frozen ADK experiment
├── docs/architecture/        # solution architecture
├── docs/plans/               # phases 00–21 learning roadmap
├── tests/                    # pyramid (see above)
├── requirements.txt
└── requirements-dev.txt
```

## Learning process

Work follows an inspect → design → **approve** → implement → test loop per phase. Plans live in [`docs/plans/`](docs/plans/). Do not treat later-phase plans as already shipped.

## Out of scope (after Phase 10)

Not implemented yet: RAG/memory (11), MCP (12), HITL (13), model routing, A2A, production API/workers, security package, full CI-on-GitHub workflow push, and hardened deploy. `Dockerfile` / `docker-compose.yml` may exist on disk for later phases.
