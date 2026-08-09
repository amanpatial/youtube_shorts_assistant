# YouTube Shorts Assistant

LangGraph learning project that turns a developer-focused idea into a YouTube Short concept — with typed state, a quality loop, offline eval, observability, and durable persistence.

| | |
|--|--|
| **Version** | **0.23.0** (Phases **1–23** — live `sales_brief` pack) |
| **Active stack** | LangGraph — [`src/shorts_assistant/`](src/shorts_assistant/) |
| **ADK experiment** | Archived — [`archive/adk_baseline/`](archive/adk_baseline/) (not a second runtime) |
| **ADR** | [0001 — LangGraph-only](docs/adr/0001-primary-orchestration-framework.md) |
| **Architecture** | [`docs/architecture/solution_architecture.md`](docs/architecture/solution_architecture.md) |
| **Phase plans** | [`docs/plans/`](docs/plans/) |

## What’s built (Phases 1–23)

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
| 11 | Memory / RAG | `memory/` — retrieve → context → store after good runs |
| 12 | MCP tools | `mcp_servers/shorts_catalog` + `mcp_client.py` (read-only) |
| 13 | Human-in-the-loop | `hitl.py`, `approve` CLI — `interrupt` / resume |
| 14 | Model routing | `models/` — per-task `ModelRouter` (no LiteLLM) |
| 15 | A2A peer research | `a2a_research/` — agent card + HTTP task API |
| 16 | Async job API | `api/` + `worker/` — FastAPI 202 + SQL jobs |
| 17 | Security / guardrails | `security/` — authz, rate limit, input/output guards |
| 18 | AI CI/CD | `.github/workflows/` + `eval_gate` + smoke baseline |
| 19 | Production deploy | `Dockerfile`, `docker-compose.prod.yml`, `/healthz` `/readyz` |
| 20 | LG parity / hardening | `graph_ops.py`, ADK→LG map, stream + state history |
| 21 | ADR LangGraph-only | [`docs/adr/0001-…`](docs/adr/0001-primary-orchestration-framework.md) + [comparison](docs/architecture/adk_vs_langgraph.md) |
| 22 | GTM vertical packs | `packs/` registry — Pack 0 Shorts + `sales_brief` stub |
| 23 | Live `sales_brief` pack | Pack graph + `PACK_ID` dispatch; Shorts remains default |

**Learning roadmap 1–21 complete; Phases 22–23 add accelerator packs.** Default `PACK_ID=youtube_shorts`.

## Pipeline

```text
Research → Memory → (Scriptwriter ↔ Evaluator ↔ Quality Gate)↺ → Human review → Visualizer → Formatter
```

- **PASS / EXHAUSTED** → human review (auto-approve when `HITL_REQUIRED=false`)  
- **RETRY** → rewrite script (max iterations)  
- Human **approve** → visuals; **reject / request_changes** → rewrite (max `MAX_HUMAN_ROUNDS`)  

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

### Human approval (Phase 13)

Default `HITL_REQUIRED=false` so CI/eval never hang. For interactive pause/resume:

```bash
export HITL_REQUIRED=true
python -m shorts_assistant "Topic for review"   # exit 3 when AWAITING_HUMAN

python -m shorts_assistant.approve <execution_id> approve
python -m shorts_assistant.approve <execution_id> request_changes --feedback "Sharper CTA"
python -m shorts_assistant.approve <execution_id> reject --feedback "Off brand"
```

Offline eval forces HITL off even if `.env` has it enabled.

## Configuration

See [`.env.example`](.env.example).

| Variable | Purpose |
|----------|---------|
| `GOOGLE_API_KEY` | Gemini API key (required unless Vertex) |
| `GOOGLE_GENAI_USE_VERTEXAI` | `TRUE` to use Vertex ADC |
| `MODEL_NAME` | Default model id (default `gemini-2.0-flash-001`) |
| `MODEL_RESEARCH` / `WRITE` / `EVALUATE` / `VISUALIZE` / `FORMAT` | Per-task override (empty → `MODEL_NAME`) |
| `MODEL_FALLBACK` | Availability fallback model (empty → `MODEL_NAME`) |
| `QUALITY_THRESHOLD` | Gate pass score (default `7.0`) |
| `LOG_LEVEL` / `LOG_PAYLOADS` | Logging; keep payloads off by default |
| `ENABLE_OTEL` | Opt-in OpenTelemetry |
| `DATABASE_URL` | Domain DB (default SQLite `./data/shorts.db`) |
| `CHECKPOINT_BACKEND` | `memory` (default) or `postgres` |
| `CHECKPOINT_POSTGRES_URL` | Optional Postgres URL for LG checkpointer |
| `LLM_*` / `LIVE_JUDGE_FALLBACK` | Live-call timeouts, retries, fallback |
| `MEMORY_RETRIEVAL` | Inject past Shorts context (default `true`) |
| `MEMORY_TOP_K` / `MEMORY_MAX_CONTEXT_CHARS` | Retrieval size bounds |
| `MEMORY_WRITE_MIN_SCORE` | Min score before writing memory |
| `MEMORY_RETENTION_DAYS` | Retention policy (doc + stub; default 180) |
| `MCP_SHORTS_CATALOG_ENABLED` | Attach read-only catalog tools to Research |
| `MCP_TOOL_TIMEOUT_SEC` | Per-tool timeout (default 5s) |
| `MCP_ALLOWED_TOOLS` | Comma-separated allowlist |
| `HITL_REQUIRED` | Pause for human after AI gate (default `false`) |
| `MAX_HUMAN_ROUNDS` | Max reject/request_changes loops (default `2`) |
| `A2A_RESEARCH_ENABLED` | Use peer Research Agent (default `false`) |
| `A2A_RESEARCH_URL` | Peer base URL (default `http://127.0.0.1:9101`) |
| `A2A_TIMEOUT_SEC` | Client timeout (default `30`) |
| `A2A_RESEARCH_REQUIRED` | Fail graph if A2A down (default `false` → degrade) |
| `API_KEY` / `API_KEYS` | FastAPI keys (`Bearer` or `X-API-Key`) |
| `WORKER_POLL_SEC` | Worker idle poll interval (default `1`) |
| `JOB_MAX_ATTEMPTS` | Transient job retries (default `3`) |
| `API_RATE_LIMIT_PER_MIN` | Per-key `POST /shorts` limit (default `30`) |
| `JOB_TIMEOUT_SEC` | Worker wall-clock timeout (default `300`) |
| `FORCE_HITL_ON_INJECTION` | Force HITL on injection heuristics (default `true`) |
| `OUTPUT_POLICY_ENABLED` | Block disallowed output phrases (default `true`) |

## Tests & lint

Deterministic control-plane tests (state, gates, loops, contracts, persistence) stay green **without** a model. Live LLM tests are opt-in and flaky by nature — do not replace one suite with the other.

```bash
source venv/bin/activate
export PYTHONPATH=src

pytest -m "not llm and not a2a" -q   # CI default
pytest -m llm -q                     # needs GOOGLE_API_KEY or Vertex
pytest -m a2a -q                     # local Research A2A server smoke
ruff format --check src tests
ruff check src tests
pyright
```

Layout: `tests/unit` · `contract` · `workflow` · `integration` · `persistence` · `regression` · `eval_harness` · `eval_llm` · `fixtures`.

## CI / AI quality gate (Phase 18)

Traditional CI catches syntax, types, and deterministic bugs — not prompt regressions or score drift. Phase 18 adds:

| Workflow | When | What |
|----------|------|------|
| [`ci.yml`](.github/workflows/ci.yml) | every PR / push | format → lint → pyright → `pytest -m "not llm and not a2a"` → pip-audit → gitleaks |
| [`ai-eval.yml`](.github/workflows/ai-eval.yml) | AI paths change **or** label `run-ai-eval` | demo smoke (5 cases) + quality gate vs committed baseline |
| [`nightly-eval.yml`](.github/workflows/nightly-eval.yml) | schedule / manual | full 20-case demo (+ live_judge if `GOOGLE_API_KEY` secret) |

**PR AI gate (free, deterministic):**

```bash
PYTHONPATH=src python -m shorts_assistant.eval run --mode demo \
  --dataset evals/shorts_v1_smoke.json \
  --save-baseline /tmp/candidate_demo.json

PYTHONPATH=src python -m shorts_assistant.eval_gate \
  --baseline evals/results/baselines/baseline_demo_v1.json \
  --candidate /tmp/candidate_demo.json \
  --config evals/quality_gate.yaml
```

Thresholds live in [`evals/quality_gate.yaml`](evals/quality_gate.yaml). Gate **fails closed** if the baseline file is missing.

### Updating the demo baseline

1. Run smoke demo and write a new baseline path.
2. Open an **explicit PR** that only (or mainly) updates `evals/results/baselines/baseline_demo_v1.json`.
3. Reviewers check metric deltas — CI must not silently overwrite the baseline.

### Secrets & forks

- Set repo secret `GOOGLE_API_KEY` for optional `live_judge` jobs.
- Fork PRs never receive that secret; live_judge is skipped (demo gate still runs on path/label triggers).
- Pushing workflow files may need a GitHub token with `workflow` scope (see [`.github/README.md`](.github/README.md)).

## Offline evaluation (Phase 8)

Fixed dataset + harness + compare — establish a baseline **before** changing prompts/models.

| Mode | Command | LLM? |
|------|---------|------|
| `demo` | synthetic judge, demo writers | No |
| `live_judge` | Gemini judge, demo writers | Yes |

| Dataset | Cases | Use |
|---------|------:|-----|
| [`evals/shorts_v1_smoke.json`](evals/shorts_v1_smoke.json) | 5 | PR AI gate |
| [`evals/shorts_v1_dataset.json`](evals/shorts_v1_dataset.json) | 20 | nightly / full local |

```bash
PYTHONPATH=src python -m shorts_assistant.eval run --mode demo

PYTHONPATH=src python -m shorts_assistant.eval run --mode live_judge \
  --save-baseline evals/results/baselines/baseline_v1.json

PYTHONPATH=src python -m shorts_assistant.eval compare \
  --baseline evals/results/baselines/baseline_demo_v1.json \
  --candidate evals/results/runs/<run_id>.json
```

### Memory A/B (Phase 11)

```bash
# Baseline without retrieval
PYTHONPATH=src python -m shorts_assistant.eval run --mode demo --memory off \
  --out evals/results/runs

# With retrieval (seed memory by running the app on a few topics first)
PYTHONPATH=src python -m shorts_assistant.eval run --mode demo --memory on \
  --out evals/results/runs

# Compare summaries (same mode)
PYTHONPATH=src python -m shorts_assistant.eval compare \
  --baseline evals/results/runs/<no_memory_run>.json \
  --candidate evals/results/runs/<with_memory_run>.json
```

Do **not** store secrets, full system prompts, or raw API keys in memory.  
`CHECKPOINT_BACKEND=memory` is the LangGraph checkpointer — unrelated to RAG.

## Model routing (Phase 14)

Custom `ModelRouter` (not LiteLLM): each task resolves a primary + optional availability fallback. Defaults equal `MODEL_NAME` so behavior is unchanged until you override.

```bash
# A/B write model (measure only — no auto-optimize)
MODEL_WRITE=gemini-2.0-flash-001 PYTHONPATH=src python -m shorts_assistant.eval run --mode demo --out evals/results/runs
MODEL_WRITE=gemini-2.5-pro PYTHONPATH=src python -m shorts_assistant.eval run --mode demo --out evals/results/runs

PYTHONPATH=src python -m shorts_assistant.eval model-compare \
  --baseline evals/results/runs/<flash_run>.json \
  --candidate evals/results/runs/<pro_run>.json \
  --out evals/results/model_compare.json
```

## MCP catalog (Phase 12)

**MCP ≠ A2A.** MCP = agent ↔ tools/resources. A2A = agent ↔ agent.

One in-repo read-only server: `shorts_catalog` (list / search / get). Research appends catalog notes when enabled; failures degrade (graph continues). Writes stay in app persistence/memory — no MCP write tools.

```bash
# Stdio MCP server (for MCP-compatible clients)
PYTHONPATH=src python -m shorts_assistant.mcp_servers.shorts_catalog

# Disable catalog tools
# MCP_SHORTS_CATALOG_ENABLED=false
```

## A2A Research Agent (Phase 15)

Peer agent `shorts_research_agent` (separate process). Default path stays in-process; enable A2A for the interop experiment.

| Boundary | Code |
|----------|------|
| In-process research | `research_node` + `demo_research` |
| MCP tools | `mcp_client` / `shorts_catalog` |
| A2A peer | `a2a_research/` server + client |

```bash
# Terminal 1 — Research Agent
PYTHONPATH=src python -m shorts_assistant.a2a_research --port 9101

# Terminal 2 — Shorts graph via A2A research
export A2A_RESEARCH_ENABLED=true
export A2A_RESEARCH_URL=http://127.0.0.1:9101
PYTHONPATH=src python -m shorts_assistant "LangGraph A2A research"
```

If the peer is down: degrade to empty research (log `a2a_research_degraded`) unless `A2A_RESEARCH_REQUIRED=true`. Offline eval forces A2A off.

## Async API + worker (Phase 16)

Non-blocking job API (no Kubernetes). `POST /shorts` returns **202** immediately; a same-repo worker claims SQL jobs and runs/resumes LangGraph.

```bash
export API_KEY=dev-change-me
export PYTHONPATH=src

# Terminal 1 — API
python -m shorts_assistant.api --port 8000

# Terminal 2 — worker
python -m shorts_assistant.worker

# Client
curl -s -X POST http://127.0.0.1:8000/shorts \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: demo-1" \
  -H "Content-Type: application/json" \
  -d '{"topic":"LangGraph async jobs","hitl_required":false}'

curl -s http://127.0.0.1:8000/shorts/<workflow_id> -H "X-API-Key: $API_KEY"
curl -s http://127.0.0.1:8000/shorts/<workflow_id>/result -H "X-API-Key: $API_KEY"
```

HITL: `POST …/approve` and `POST …/revise` enqueue resume jobs (worker calls `resume_with_decision`).

## GTM accelerator / vertical packs (Phases 22–23)

Shared **core** (checkpointer, HITL pattern, API, worker, security, eval, CI) + swappable **packs**.

| `PACK_ID` | Role |
|-----------|------|
| `youtube_shorts` | Pack 0 — **live** Shorts pipeline (**default**) |
| `sales_brief` | **Live** brief pack — `PACK_ID=sales_brief` |

```bash
# List packs
PYTHONPATH=src python -c "from shorts_assistant.packs import list_packs; \
print([(p.pack_id, p.active_graph) for p in list_packs()])"

# Run sales brief offline demo
PACK_ID=sales_brief HITL_REQUIRED=false \
  PYTHONPATH=src python -m shorts_assistant "Acme Corp — expand analytics seat"
```

Checklist for a new customer vertical: [`docs/runbooks/gtm_prototype.md`](docs/runbooks/gtm_prototype.md).  
Template: `src/shorts_assistant/packs/_template/`.

## Stack decision (Phase 21 ADR)

**Primary: LangGraph. ADK: archive reference only.**

- ADR: [`docs/adr/0001-primary-orchestration-framework.md`](docs/adr/0001-primary-orchestration-framework.md)  
- Comparison (20 dimensions): [`docs/architecture/adk_vs_langgraph.md`](docs/architecture/adk_vs_langgraph.md)  
- Concept map: [`docs/architecture/adk_to_langgraph.md`](docs/architecture/adk_to_langgraph.md)  

Do not revive ADK as a second runtime. Do not delete `archive/adk_baseline/`.

## LangGraph hardening (Phase 20)

Not a rebuild — the app already *is* LangGraph. Phase 20 adds learning + ops surface:

| Piece | Role |
|-------|------|
| [`docs/architecture/adk_to_langgraph.md`](docs/architecture/adk_to_langgraph.md) | ADK→LG concept map (archive stays read-only) |
| `graph_ops.py` | `stream_workflow`, `get_thread_state`, `list_state_history` |
| CLI `--stream` | Print node update names, then final state JSON |

```bash
PYTHONPATH=src python -m shorts_assistant "How LangGraph checkpoints work" --stream
```

Custom SQL memory is kept (not LangGraph Store) — see the decision note in the concept map.

## Production deploy (Phase 19)

Two containers + managed Postgres — **no Kubernetes**. Full runbook: [`docs/runbooks/deploy.md`](docs/runbooks/deploy.md).

```bash
# Local staging-shaped stack (Postgres profile)
docker compose --profile local-db up --build

# Probes (no auth)
curl -sS http://127.0.0.1:8080/healthz
curl -sS http://127.0.0.1:8080/readyz
```

| Piece | Role |
|-------|------|
| `Dockerfile` | Multi-stage, non-root, default CMD = uvicorn API |
| `docker-compose.prod.yml` | `migrate` → `api` + `worker` (+ optional `postgres` profile) |
| `APP_ENV=staging\|production` | Fail-fast: Postgres URL, API key(s), Gemini/Vertex |
| `/healthz` | Liveness (process up) |
| `/readyz` | Readiness (DB ping + not shutting down) |

Promote **image digests** local → staging → production. Secrets via Secret Manager → env (never image layers).

## Security & guardrails (Phase 17)

Threat → control (highest value only):

| Threat | Control |
|--------|---------|
| Open API | `Bearer` / `X-API-Key` required (except `/health`, `/healthz`, `/readyz`) |
| IDOR | `workflows.owner_key_id` — mismatch → **403** |
| Job spam | Per-key rate limit → **429** + `Retry-After` |
| Secret leakage | Redaction in logs + API error details |
| Prompt injection | `USER_TOPIC` fence + heuristics → optional force HITL |
| PII in topics | Light email/phone detect; strip for stored request |
| Unsafe output | Output policy scan before result / job succeed |
| Runaway jobs | `JOB_TIMEOUT_SEC` in worker |
| Tool abuse | MCP allowlist (Phase 12) |

Package: `src/shorts_assistant/security/`.

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
│   ├── run.py                # traced + persisted entrypoint (+ HITL resume)
│   ├── hitl.py / approve.py  # interrupt + approve CLI
│   ├── models/               # ModelRouter + per-task IDs
│   ├── a2a_research/         # peer Research Agent (A2A-lite)
│   ├── api/                  # FastAPI job API (202 + healthz/readyz)
│   ├── worker/               # job poller → LangGraph run/resume
│   ├── security/             # authz, rate limit, input/output guards
│   ├── memory/               # RAG retrieve / context / writer
│   ├── packs/                # vertical packs (youtube_shorts, sales_brief, _template)
│   ├── graph_ops.py          # stream + get_state / history
│   ├── runtime_lifecycle.py  # graceful shutdown flag
│   ├── mcp_client.py         # allowlist / timeout / degraded calls
│   ├── mcp_servers/          # shorts_catalog MCP stdio server
│   ├── eval/                 # offline dataset runner + compare
│   └── eval_gate/            # AI quality gate vs baseline
├── alembic/                  # domain migrations
├── evals/                    # smoke + full datasets + packs/
├── .github/workflows/        # ci / ai-eval / nightly-eval
├── docker-compose.prod.yml   # migrate + api + worker (+ optional postgres)
├── docs/runbooks/            # deploy + gtm_prototype
├── docs/adr/                 # ADR 0001 LangGraph-only
├── archive/adk_baseline/     # frozen ADK experiment
├── docs/architecture/        # solution architecture + ADK vs LG
├── docs/plans/               # phases 00–23
├── tests/                    # pyramid (see above)
├── requirements.txt
└── requirements-dev.txt
```

## Learning process

Work follows an inspect → design → **approve** → implement → test loop per phase. Plans live in [`docs/plans/`](docs/plans/). Current local version: **0.23.0**.

## Out of scope (post-roadmap)

Not implemented: Kubernetes, Terraform, multi-region, SSE streaming, LangGraph Store, CRM MCP for sales_brief. Not dual-stack ADK work.
