# Deploy runbook (Phase 19)

Simplest production shape: **API container + worker container + managed PostgreSQL**. No Kubernetes.

```text
Clients → HTTPS LB → api:8080
                      ↓
                 PostgreSQL (jobs, workflows, memory JSON)
                      ↑
                   worker
```

## Why not Kubernetes

Two long-running processes and one database do not justify a control plane. Scale by adding API/worker replicas behind a load balancer; workers claim jobs with `SKIP LOCKED`.

## Environments

| Env | `APP_ENV` | DB | HITL | Notes |
|-----|-----------|----|------|-------|
| local | `local` | SQLite or Compose Postgres | usually off | `ensure_schema` / Alembic OK |
| staging | `staging` | isolated Postgres | on | smoke `POST /shorts` |
| production | `production` | prod Postgres | on | promote same image digest |

Boot fails fast in staging/production if `DATABASE_URL` is SQLite, API keys are missing, or Gemini credentials are missing.

## Secrets (GCP Secret Manager → env)

Map secrets into the API and worker at runtime (never bake into the image):

| Secret Manager secret | Env var |
|----------------------|---------|
| `shorts-google-api-key` | `GOOGLE_API_KEY` |
| `shorts-api-key` | `API_KEY` |
| `shorts-database-url` | `DATABASE_URL` |
| `shorts-checkpoint-url` (optional) | `CHECKPOINT_POSTGRES_URL` |

Same mapping works on AWS Secrets Manager / Azure Key Vault / Doppler—only the delivery mechanism changes.

Recommended non-secret env:

```text
APP_ENV=production
CHECKPOINT_BACKEND=postgres   # or memory for early staging
HITL_REQUIRED=true
LOG_PAYLOADS=false
API_RATE_LIMIT_PER_MIN=30
JOB_TIMEOUT_SEC=300
ENABLE_OTEL=true              # optional
```

Memory embeddings remain JSON in Postgres for this phase (pgvector-ready image/DB is fine; no separate vector service).

## Local / staging Compose

```bash
# Copy env and set GOOGLE_API_KEY + API_KEY at minimum
cp .env.example .env

# Local Postgres + migrate + api + worker
docker compose --profile local-db up --build

# Or production-shaped file explicitly
docker compose -f docker-compose.prod.yml --profile local-db up --build
```

Validate Compose without starting:

```bash
docker compose -f docker-compose.prod.yml config >/dev/null
```

Probes:

- Liveness: `GET /healthz` (and `/health`)
- Readiness: `GET /readyz` (DB ping + not shutting down)

## Staging → promote

1. Build once: `docker build -t shorts-assistant:<git-sha> .`
2. Push to your registry; deploy **same digest** to staging.
3. Run migrate (Compose `migrate` service or `alembic upgrade head` against staging DB).
4. Smoke:

```bash
curl -sS -X POST "$STAGING_URL/shorts" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"topic":"How to use FastAPI lifespan hooks"}'
# poll GET /shorts/{id} then /result (or approve if HITL)
```

5. Promote the **same image digest** to production; run migrations against prod DB first.
6. Rolling restart: new API healthy on `/readyz` → drain old (SIGTERM; 60–120s grace).

## Failure / cost notes

| Failure | Expected behavior |
|---------|-------------------|
| API crash | LB fails health; jobs remain in Postgres |
| Worker crash | Current job fails/retries per `JOB_MAX_ATTEMPTS` |
| DB down | `/readyz` → 503; workers stop claiming |
| Gemini 429/5xx | Phase 6 retries; then job failed/retryable |
| SIGTERM | API marks draining (`/readyz` 503); worker finishes current job |

Cost controls already in tree: model routing, rate limits, `JOB_TIMEOUT_SEC`, `LOG_PAYLOADS=false`, nightly eval (not per-request). Scale workers on queue depth, not CPU alone.

## Out of scope here

Kubernetes manifests, Terraform, multi-region active-active, mandatory pgvector index rewrite.
