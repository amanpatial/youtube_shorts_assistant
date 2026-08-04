# YouTube Shorts Assistant

LangGraph learning/production project that turns a developer-focused idea into a YouTube Short concept.

**Active stack:** LangGraph (`src/shorts_assistant/`)  
**ADK experiment:** archived under [`archive/adk_baseline/`](archive/adk_baseline/) — reference only, not a second runtime.

Target architecture (workflow + platform + MCP/A2A):  
[`docs/architecture/solution_architecture.md`](docs/architecture/solution_architecture.md)

Phase plans: [`docs/plans/`](docs/plans/)

## Prerequisites

- Python **3.11+** (3.12 recommended)
- A Gemini API key (or Vertex AI with ADC)

## Setup

```bash
cd /path/to/youtube_shorts_assistant

# If an old venv is broken, remove it first:
rm -rf venv

python3.12 -m venv venv   # or python3.11
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY
```

## Run (structured contracts demo)

Pipeline: Research → (Script → Evaluator → Quality Gate)↺ → Visualizer → Formatter.  
Quality gate: PASS → visuals; RETRY → rewrite script; EXHAUSTED → best script → visuals.  
Markers for offline demos: `[reject]` (always fail until exhaust), `[retry-pass]` (fail then pass).

```bash
source venv/bin/activate
PYTHONPATH=src python -m shorts_assistant "How to build AI agents with LangGraph"
# Fail-closed demo (evaluator rejects):
PYTHONPATH=src python -m shorts_assistant "Weak idea [reject]"
```

## Configuration

See [`.env.example`](.env.example).

| Variable | Purpose |
|----------|---------|
| `GOOGLE_API_KEY` | Gemini API key (required unless Vertex) |
| `GOOGLE_GENAI_USE_VERTEXAI` | `TRUE` to use Vertex ADC |
| `MODEL_NAME` | Model id (optional; has default) |
| `APP_NAME` | App identity (optional) |
| `LOG_LEVEL` | Logging level (optional) |
| `DATABASE_URL` | Domain DB (default SQLite `./data/shorts.db`) |
| `CHECKPOINT_BACKEND` | `memory` (default) or `postgres` |
| `CHECKPOINT_POSTGRES_URL` | Optional; LG checkpointer Postgres URL |

## Tests & lint

**Deterministic control-plane tests** (state, gates, loops, retries, contracts) lock
system behavior and must stay green without a model. **Probabilistic AI eval**
(`@pytest.mark.llm`) checks model quality and is opt-in — flaky by nature; never
replace one suite with the other.

```bash
source venv/bin/activate

# CI default — no live Gemini
pytest -m "not llm" -q

# Opt-in live judge smoke (needs GOOGLE_API_KEY or Vertex)
pytest -m llm -q

ruff check src tests
```

Pyramid layout under `tests/`: `unit/` · `contract/` · `workflow/` · `integration/` ·
`regression/` · `eval_harness/` · `eval_llm/` · `fixtures/`.

## Observability (Phase 9)

Every CLI/`invoke_workflow` run gets a `trace_id` (`wf_*`) and structured JSON log events
(node timings, gate decisions, final status). Secrets and full prompts are **not**
logged by default (`LOG_PAYLOADS=false`). Domain DB uses a separate UUID `workflow_id`.

Example quality-loop narrative (attempt 1 fails, attempt 2 passes):

```json
{"event":"workflow_start","trace_id":"wf_abc123"}
{"event":"gate_decision","decision":"RETRY","iteration":1,"evaluation_score":6.8,"trace_id":"wf_abc123"}
{"event":"gate_decision","decision":"PASS","iteration":2,"evaluation_score":8.2,"trace_id":"wf_abc123"}
{"event":"workflow_summary","final_status":"COMPLETED","evaluation_scores":[6.8,8.2],"trace_id":"wf_abc123"}
```

OpenTelemetry is **opt-in** (`ENABLE_OTEL=true`); install OTel packages yourself if needed.
Do not use the archived ADK `telemetry.py`.

## Persistence (Phase 10)

Two stores, one process: **LangGraph checkpointer** (resume via `thread_id=execution_id`)
and **domain tables** (workflows / executions / script_versions / evaluations / agent_executions).

```bash
# Apply migrations (prod/deploy). Local SQLite also auto-creates tables on first run.
alembic upgrade head

# Default: SQLite file + MemorySaver
PYTHONPATH=src python -m shorts_assistant "topic"

# Postgres domain + PostgresSaver
# DATABASE_URL=postgresql+psycopg://shorts:shorts@localhost:5432/shorts
# CHECKPOINT_BACKEND=postgres
```

Reload a finished run from the domain checkpoint: `load_execution_state(execution_id)`.

## Offline evaluation (Phase 8)

Establish a **baseline before** changing prompts/models. Fixed dataset + harness +
metrics let you ask “did v2 improve over v1?” via compare (same mode only).

| Mode | Command | LLM? |
|------|---------|------|
| `demo` (default) | synthetic judge, demo writers | No |
| `live_judge` | Gemini judge, demo writers | Yes |

```bash
# Offline harness / dry baseline (CI-safe)
PYTHONPATH=src python -m shorts_assistant.eval run --mode demo

# Nightly model signal (needs GOOGLE_API_KEY)
PYTHONPATH=src python -m shorts_assistant.eval run --mode live_judge \
  --save-baseline evals/results/baselines/baseline_v1.json

# Compare two runs of the same mode
PYTHONPATH=src python -m shorts_assistant.eval compare \
  --baseline evals/results/baselines/baseline_v1.json \
  --candidate evals/results/runs/<run_id>.json
```

Dataset: [`evals/shorts_v1_dataset.json`](evals/shorts_v1_dataset.json) (20 cases).  
Do **not** optimize prompts from the first baseline in this phase.

## Project layout

```
youtube_shorts_assistant/
├── src/shorts_assistant/     # LangGraph app (active; state.py = workflow contract)
│   ├── observability.py      # trace_id + structured events
│   ├── persistence/          # domain models + WorkflowRepository
│   ├── checkpointer.py       # MemorySaver / PostgresSaver factory
│   ├── telemetry.py          # opt-in OTel (not ADK)
│   ├── run.py                # traced + persisted invoke_workflow
│   └── eval/                 # dataset runner + compare
├── alembic/                  # domain DB migrations
├── evals/                    # shorts_v1 dataset + results/
├── archive/adk_baseline/     # Frozen ADK experiment
├── docs/architecture/        # Consolidated solution view
├── docs/plans/               # Phase learning roadmap
├── tests/
│   ├── unit/                 # pure helpers, state, failures, evaluator merge
│   ├── contract/             # schemas + agent invariants
│   ├── workflow/             # quality loop / termination
│   ├── integration/          # compiled graph offline smoke
│   ├── persistence/          # SQLite repo + checkpointer wiring
│   ├── regression/           # fixture structural stability
│   ├── eval_harness/         # offline eval metrics/runner tests
│   ├── eval_llm/             # @pytest.mark.llm opt-in
│   └── fixtures/
├── requirements.txt
└── requirements-dev.txt
```

## Out of scope for now

Docker Compose, deep OTEL/eval how-tos, and full agent pipeline nodes are **later phases**. Files like `Dockerfile` / CI may exist on disk but are not the Phase 1 run path.
