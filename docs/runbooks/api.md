# Shorts Assistant API

Async job API for the **YouTube Shorts** pack (Pack 0).  
`POST /shorts` returns **202** immediately; a worker claims SQL jobs and runs / resumes LangGraph.

Interactive OpenAPI UI (when API is up): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

> There is no `/briefs` HTTP surface yet. Use CLI + `PACK_ID=sales_brief` for the sales-brief pack.

---

## Run locally

You need **two processes**: API + worker. Same env vars in both.

```bash
cd /path/to/youtube_shorts_assistant
source venv/bin/activate

export PYTHONPATH=src
export API_KEY=dev-change-me
export HITL_REQUIRED=false          # true only if you want API HITL pause
# Optional: DATABASE_URL, CHECKPOINT_BACKEND=sqlite (default)

# Terminal 1 — API
python -m shorts_assistant.api --port 8000

# Terminal 2 — worker
python -m shorts_assistant.worker
```

Checks:

```bash
curl -sS http://127.0.0.1:8000/healthz
curl -sS http://127.0.0.1:8000/readyz
```

| Probe | Auth | Meaning |
|-------|------|---------|
| `GET /health` or `/healthz` | No | Process up |
| `GET /readyz` | No | DB reachable and not shutting down |

Without the worker, jobs stay `queued` forever.

---

## Auth

All `/shorts*` routes require an API key (except health probes).

| Header | Example |
|--------|---------|
| `X-API-Key` | `dev-change-me` |
| or `Authorization` | `Bearer dev-change-me` |

Set `API_KEY` (and optional comma-separated `API_KEYS`) in the environment before starting API/worker.

---

## Endpoints

Base URL: `http://127.0.0.1:8000`

| Method | Path | Status | Purpose |
|--------|------|--------|---------|
| `POST` | `/shorts` | **202** | Enqueue a Shorts pipeline job |
| `GET` | `/shorts/{workflow_id}` | 200 | Job / run status |
| `GET` | `/shorts/{workflow_id}/result` | 200 | Final concept (409 if not ready) |
| `POST` | `/shorts/{workflow_id}/approve` | **202** | Enqueue HITL approve |
| `POST` | `/shorts/{workflow_id}/revise` | **202** | Enqueue HITL reject / request_changes |

Common errors: **401** missing/invalid key · **403** wrong owner · **404** unknown workflow · **409** result/HITL not ready · **422** output policy · **429** rate limit.

---

### `POST /shorts` — create

**Headers**

```http
X-API-Key: dev-change-me
Content-Type: application/json
Idempotency-Key: unique-per-new-run   # optional; reuse returns same workflow_id
```

**Body**

```json
{
  "topic": "How to build AI agents with LangGraph",
  "audience": "developers",
  "hitl_required": false,
  "max_iterations": 3
}
```

| Field | Type | Default | Notes |
|-------|------|---------|--------|
| `topic` | string | required | User idea / article angle |
| `audience` | string | `"developers"` | Stored with the job |
| `hitl_required` | bool | `false` | When `true`, run pauses for human review |
| `max_iterations` | int | `3` | Quality-loop budget (`1`–`10`) |

**Response (202)**

```json
{
  "workflow_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "queued"
}
```

**Idempotency:** If you send the same `Idempotency-Key` again, the API returns the **original** `workflow_id` (no new run). For a new topic in Postman, change or remove the key.

---

### `GET /shorts/{workflow_id}` — status

**Headers:** `X-API-Key: dev-change-me`

**Response (200)**

```json
{
  "workflow_id": "...",
  "status": "succeeded",
  "execution_id": "...",
  "iteration": 1,
  "best_score": 8.5,
  "error": null
}
```

`status` values: `queued` · `running` · `awaiting_human` · `succeeded` · `failed` · `cancelled`

---

### `GET /shorts/{workflow_id}/result` — result

**Headers:** `X-API-Key: dev-change-me`

**Response (200)** when finished:

```json
{
  "workflow_id": "...",
  "status": "succeeded",
  "final_short_concept": { "...": "..." },
  "generated_script": { "...": "..." }
}
```

**409** if the run is not complete yet — poll status first.

---

### `POST /shorts/{workflow_id}/approve` — HITL approve

Only after status is `awaiting_human` (create with `"hitl_required": true`).

```json
{
  "reviewer": "postman",
  "feedback": null
}
```

**Response (202):** `{ "workflow_id", "job_id", "status": "queued" }`

---

### `POST /shorts/{workflow_id}/revise` — HITL revise / reject

```json
{
  "decision": "request_changes",
  "feedback": "Make the CTA sharper",
  "reviewer": "postman"
}
```

| Field | Values |
|-------|--------|
| `decision` | `"request_changes"` (default) or `"reject"` |
| `feedback` | required (non-empty string) |

---

## Curl smoke test

```bash
export API_KEY=dev-change-me

curl -s -X POST http://127.0.0.1:8000/shorts \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: demo-$(date +%s)" \
  -H "Content-Type: application/json" \
  -d '{"topic":"LangGraph async jobs","hitl_required":false,"max_iterations":3}'

# Copy workflow_id from the response, then:
curl -s http://127.0.0.1:8000/shorts/<workflow_id> \
  -H "X-API-Key: $API_KEY"

curl -s http://127.0.0.1:8000/shorts/<workflow_id>/result \
  -H "X-API-Key: $API_KEY"
```

---

## Postman

1. Collection variable: `baseUrl` = `http://127.0.0.1:8000`, `apiKey` = `dev-change-me`
2. Create request: `POST {{baseUrl}}/shorts` with headers `X-API-Key: {{apiKey}}`, body as above
3. Use a **new** `Idempotency-Key` per new topic (or omit it)
4. Tests script to save id:

```js
const data = pm.response.json();
pm.collectionVariables.set("workflow_id", data.workflow_id);
```

5. Status: `GET {{baseUrl}}/shorts/{{workflow_id}}`  
6. Result: `GET {{baseUrl}}/shorts/{{workflow_id}}/result`

---

## Related

- Deploy / Compose: [`deploy.md`](deploy.md)  
- Packs / CLI sales brief: [`gtm_prototype.md`](gtm_prototype.md)  
- Project overview: [`../../README.md`](../../README.md)
