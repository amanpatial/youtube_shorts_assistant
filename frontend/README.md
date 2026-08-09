# Shorts Assistant web UI

React 19 + Vite 6 SPA for the **backend job API** (Phase 24).  
It does not run LangGraph itself — it enqueues jobs and polls status/result.

## Architecture

```text
Browser (5173)  --proxy /shorts-->  FastAPI (8000)  -->  SQL jobs
                                         ^
                                         |
                                    Worker process  -->  LangGraph
```

| Process | Command | Why |
|---------|---------|-----|
| **API** | `python -m shorts_assistant.api --port 8000` | Auth, enqueue, status, result |
| **Worker** | `python -m shorts_assistant.worker` | Runs/resumes the graph (without it, jobs stay `queued`) |
| **UI** | `npm run dev` | Pages at http://127.0.0.1:5173 |

Vite proxies `/shorts`, `/healthz`, `/health`, `/readyz` to `127.0.0.1:8000`.  
If you set `VITE_API_BASE=http://127.0.0.1:8000`, the browser calls the API directly and backend `CORS_ORIGINS` must include the UI origin.

## Run

```bash
# Terminal 1 — API
cd /path/to/youtube_shorts_assistant
source venv/bin/activate
export PYTHONPATH=src API_KEY=dev-change-me HITL_REQUIRED=false
python -m shorts_assistant.api --port 8000

# Terminal 2 — worker
python -m shorts_assistant.worker

# Terminal 3 — UI
cd frontend
npm install
npm run dev
```

1. Open http://127.0.0.1:5173  
2. **Settings** → paste the same `API_KEY` (`dev-change-me`)  
3. **Create** a topic → you land on the run page  

Port **8000** can only have one API. If bind fails: stop the old Python on 8000 (`lsof -nP -iTCP:8000 -sTCP:LISTEN`).

## Pages

| Hash route | Backend | What you see |
|------------|---------|----------------|
| `#/` Create | `POST /shorts` | Topic, audience, HITL toggle, max iterations. Each submit sends a **new** `Idempotency-Key`. |
| `#/history` | `GET /shorts` | Owner-scoped run list (topic, status, score, created) |
| `#/runs/:id` | `GET …/status` + `GET …/result` + approve/revise | Agent pipeline, research, memory, eval scores, script beats, visual shots, final concept, HITL |
| `#/settings` | — | API key in **localStorage** only (never committed) |

## Agent pipeline (run page)

Status polling (~2s) drives a visual graph:

Research → Memory → Writer → Evaluator → Quality gate → Human review → Visualizer → Formatter

Each node: `pending` · `running` · `paused` · `done` · `failed`  
(from `GET /shorts/{id}` → `agents`, inferred from checkpoint + live LangGraph thread).

## Result payload (run page)

`GET /shorts/{id}/result` (when `succeeded` or `awaiting_human`) includes:

- `research`, `memory_context`
- `evaluation` (overall + per-dimension scores, issues, approved)
- `generated_script` (title, hook/body/cta, timed sections)
- `visual_concepts` (shots, pacing, b-roll)
- `final_short_concept` (spoken/visual table)
- HITL meta, `trace_id`, `execution_id`, script version

## Backend contract

Full HTTP docs: [`../docs/runbooks/api.md`](../docs/runbooks/api.md)  
OpenAPI: http://127.0.0.1:8000/docs  

Same `API_KEY` on API, worker, and Settings. Reuse of `Idempotency-Key` returns the **same** `workflow_id` (not a new run).

## Scripts

```bash
npm run dev      # Vite dev server (5173)
npm run build    # tsc + production bundle
npm run preview  # serve dist/
```
