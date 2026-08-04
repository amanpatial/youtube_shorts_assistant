---
name: Phase 1 Repo Hygiene
overview: "Phase 1: repo hygiene + archive ADK to archive/adk_baseline/ + LangGraph-only project skeleton/deps (langgraph, langchain-google-genai). Remove google-adk from active requirements. No dual-stack. Archive waits for explicit implement approval."
todos:
  - id: p1-gitignore
    content: Tighten .gitignore for logs/temp/coverage; keep secrets/venv/pycache/adk/db ignores
    status: completed
  - id: p1-env-example
    content: Restructure .env.example into required vs optional/advanced sections (no secrets)
    status: completed
  - id: p1-deps
    content: "Split runtime vs dev deps: langgraph + langchain-google-genai (or similar); remove google-adk from active requirements"
    status: completed
  - id: p1-archive
    content: "On implement approval: move ADK-era code to archive/adk_baseline/ + ARCHIVE_README.md"
    status: completed
  - id: p1-skeleton
    content: Establish LangGraph-only project skeleton package (empty/minimal graph stub)
    status: completed
  - id: p1-readme
    content: "Update README: LangGraph-only run path; ADK archive note; de-emphasize Docker/deploy/adk web"
    status: completed
  - id: p1-verify
    content: Recreate venv, install LangGraph deps, verify import/tests/smoke
    status: completed
isProject: false
---

# Phase 1 — Production Repository Hygiene


## Master alignment
- Active stack: LangGraph only
- ADK: archive only (not a second runtime)
- If this plan still describes ADK APIs below, treat them as historical; redesign for LangGraph in Steps 2–3 of the phase loop
- Consolidated end-state view: [../architecture/solution_architecture.md](../architecture/solution_architecture.md) — Phase 1 only lights up stub + archive, not the full diagram

## Working rules for this phase

- Teach-then-implement (this plan is the teaching + change list)
- One concept: **repo engineering hygiene**
- Archive ADK experiment code under `archive/adk_baseline/` when implement is approved (do not keep as live baseline)
- Do **not** introduce or expand Docker/Kubernetes
- Do **not** rewrite schemas/prompts beyond what archive + skeleton require
- Keep a runnable LangGraph skeleton after the step (ADK becomes archive, not a second runtime)

**Framework decision (locked in master):** LangGraph-only active stack; ADK will be **archived** (not mixed).

**This phase (when implement is approved):** hygiene + move ADK-era code to `archive/adk_baseline/`; establish LangGraph project skeleton/deps; do not run dual frameworks.

**Until implement approval:** inspect/design only — do not move/delete ADK files yet (archive happens on implement approval).

---

## 1. What is wrong? (inspection findings)

**Inspected:** 2026-08-01 (Phase 1 Step 1). Live facts below supersede earlier notes where they differ.

| Area | Current finding |
|------|-----------------|
| Secrets | [`.env`](.env) exists (real key present). Ignored by [`.gitignore`](.gitignore). **Not a git repo yet** — leak risk is latent until `git init`. |
| `.env` handling | [`.env.example`](.env.example) exists; mixes required (`GOOGLE_API_KEY`) with later knobs (`SESSION_DB_URL`, OTEL). |
| Virtualenv | [`venv/`](venv/) **broken**: created from old path `Documents/projects/...`; `home` points at missing `/opt/homebrew/.../python3.11`. `venv/bin/python` does not run. |
| System Python | `/usr/bin/python3` → **3.9.6** only. `python3.11` not on PATH. Brew *prefixes* for 3.11/3.12/3.13 exist but **binaries missing** — need reinstall Python ≥3.11 before verify. |
| Generated / local | [`__pycache__/`](__pycache__/), [`.adk/session.db`](.adk/session.db) (~524KB ADK session DB). |
| Logs / temp | [`.gitignore`](.gitignore) lacks `*.log`, `logs/`, `tmp/`, coverage artifacts. |
| Dependencies | [`requirements.txt`](requirements.txt) = `google-adk==1.20.0` + dotenv/settings/aiosqlite **plus** pytest/ruff. [`pyproject.toml`](pyproject.toml) still describes ADK package; optional `dev` already split there but unused as source of truth. |
| Active code (ADK) | Flat package: `agent.py` (`SequentialAgent` + critic), `runner.py`, `telemetry.py`, four `*_instruction.txt`, `schemas.py` (`ShortConcept`), `config.py`, `util.py`, `__init__.py` exports `root_agent`. |
| Tests | ADK-coupled: `tests/test_agent_structure.py` imports `google.adk` / `SequentialAgent`. Config/util/schema tests may survive after port. |
| README | Fully ADK-oriented: `adk web`, `adk eval`, `adk deploy`, Docker compose as primary paths. |
| Out-of-scope on disk | `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `evals/` — leave dormant; do not expand in Phase 1. |
| Archive | `archive/` does **not** exist yet (correct until implement approval). |
| Plans | [`docs/plans/`](docs/plans/) present and aligned to LangGraph-only master. |

---

## 2. Why does it matter?

- **Secrets hygiene** is non-negotiable before any commit history exists.
- **Ignore rules** prevent committing caches, local DBs, and venvs that pollute reviews and CI.
- **Split dependencies** keep production installs lean and make “what the app needs” explicit.
- **Honest README** is how a senior engineer re-enters the project without reverse-engineering accidental scaffolding.
- **Broken venv** means “production hygiene” is theoretical until import/run works.

---

## 3. What should be changed? (smallest useful set)

### 3.1 Update [`.gitignore`](.gitignore)

Keep existing rules; add only missing hygiene patterns:

- `*.log`, `logs/`
- `tmp/`, `temp/`, `.tmp/`
- coverage artifacts (`.coverage`, `htmlcov/`)
- keep ignoring `.env`, `venv/`, `__pycache__/`, `.adk/`, `*.db`, `data/*` + `!data/.gitkeep`

### 3.2 Tighten [`.env.example`](.env.example)

Restructure into two clear sections:

1. **Required to run** — `GOOGLE_API_KEY`, `GOOGLE_GENAI_USE_VERTEXAI`
2. **Optional (already supported by config; safe defaults)** — `MODEL_NAME`, `APP_NAME`, `LOG_LEVEL`

Move session-DB / OTEL / max-input notes to a short “Advanced (existing config)” comment block so Phase 1 docs do not pretend observability/persistence are the lesson.

No real secrets in the example file.

### 3.3 Split dependencies + LangGraph runtime

- [`requirements.txt`](requirements.txt) — **runtime only**: `langgraph`, `langchain-google-genai` (or `langchain-core` + Google GenAI binding), `python-dotenv`, `pydantic-settings`, `aiosqlite` (as needed)
- **Remove** `google-adk` from active requirements (ADK lives under archive after move)
- New [`requirements-dev.txt`](requirements-dev.txt) — `-r requirements.txt` plus `pytest`, `pytest-asyncio`, `ruff`

No dual orchestrators. Do not add ADK back “for baseline.”

### 3.4 Archive ADK experiment (on implement approval)

**Move into** `archive/adk_baseline/` (preserve history; not runnable product path):

| Item | Why |
|------|-----|
| `agent.py`, `runner.py`, `telemetry.py`, `__main__.py` | ADK orchestration / CLI / OTel bootstrap |
| `*_instruction.txt` | ADK-era prompts (reference for later LG prompt rewrite) |
| `evals/` | ADK evalset format |
| Copy of root `__init__.py` that exports `root_agent` | Package entry for ADK |
| Short `ARCHIVE_README.md` | Narrative: experiment → LangGraph rebuild |

**Reuse into new package (copy, then leave originals in archive or delete from root after copy):**

| Item | Why |
|------|-----|
| `schemas.py` | Pydantic contracts still useful (Phase 3 will deepen) |
| `config.py` | Settings pattern — slim for LG; no redesign of settings model |
| `util.py` | `load_instruction_from_file` still useful |

**Leave on disk untouched (dormant):** `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `docs/plans/`.

### 3.5 LangGraph skeleton layout (concrete choice)

**Package root:** `src/shorts_assistant/` (not a second top-level ADK package name).

```
src/shorts_assistant/
  __init__.py          # exports graph factory / version
  config.py            # from ADK-era settings (slim)
  schemas.py           # ShortConcept (+ rows)
  util.py
  graph.py             # minimal StateGraph stub (passthrough / hello node)
tests/
  test_graph_imports.py  # no live LLM; replaces ADK structure tests
requirements.txt       # langgraph + langchain-google-genai + dotenv + pydantic-settings
requirements-dev.txt   # -r requirements.txt + pytest + pytest-asyncio + ruff
pyproject.toml         # point name/deps/pythonpath at src layout; drop google-adk
```

Stub graph: compile a trivial graph that accepts `{topic: str}` and returns a placeholder — proves import + invoke without claiming pipeline parity.

**Target end-state graph** (Research → Writer → Evaluator → Quality Gate → Visualizer → Formatter → Human Approval → Done) is recorded in the master roadmap. Phase 1 only creates the empty shell; do **not** implement Research/Writer/Evaluator/gate/HITL here.

Do **not** line-by-line translate `LlmAgent` / `SequentialAgent`.

### 3.6 Update [`README.md`](README.md) for Phase 1 truthfulness

Keep: purpose, setup, `.env`, LangGraph-oriented run/smoke path, config table for required vars, how to run tests with `requirements-dev.txt`.

Document: **Active stack = LangGraph**; **ADK = archive only** under `archive/adk_baseline/`.

Remove or clearly mark as **out of scope for now** (do not delete Docker files from disk in this phase):

- Docker / compose as a recommended run path
- `adk web` / `adk deploy` as primary run instructions
- Deep OTEL/eval how-to (one-line “later phase” pointer is enough)

Add: recreate-venv instructions when the existing `venv` is broken.

### 3.7 Local environment repair + verify (implementation step, not a code feature)

**Blocker found in Inspect:** no working Python ≥3.11 binary on this machine (brew Cellar prefixes empty). Before verify:

1. Reinstall/provide Python 3.11+ (e.g. `brew reinstall python@3.11` and ensure it is on PATH, or another install the user prefers)
2. Remove broken `venv/`; recreate with that interpreter
3. `pip install -r requirements.txt` and `pip install -r requirements-dev.txt`
4. Smoke verify (in order):
   - `from shorts_assistant.graph import ...` (or package import) succeeds
   - pytest for skeleton + config/util/schema (no live LLM)
   - optional live Gemini smoke later (not required for Phase 1 exit if key/network flaky)

---

## 4. What should NOT be changed yet?

- Full quality loop / evaluator redesign (Phases 4–5) — skeleton only in Phase 1
- Typed workflow state model deep design (Phase 2) beyond package layout
- Structured contracts (Phase 3), real evaluator (Phase 4), quality loop (Phase 5)
- Failure handling, tests pyramid, eval dataset, observability (Phases 6–9)
- Persistence, memory/RAG, MCP, HITL, routing, A2A (Phases 10–15)
- API / security / CI/CD / deploy expansion (Phases 16–19)
- Docker/K8s introduction or Dockerfile edits — leave files on disk; do not teach/expand in Phase 1
- Do not expand beyond hygiene + ADK archive + LangGraph skeleton in this phase
- Do not `git init` unless you explicitly ask later (hygiene files prepare for it)
- Do **not** keep ADK as a second live runtime or “20% baseline”

---

## Teaching framing (before any edit)

**Problem:** The repo already has agent features, but the engineering envelope (secrets, ignores, deps, docs, runnable env) is inconsistent with a serious learning/production path.

**Why current is insufficient:** A broken venv + mixed deps + README that advertises Docker/deploy makes “does it still work?” hard to answer and invites committing the wrong artifacts later.

**Design decision:** Treat Phase 1 as **repository contract + stack pivot** — ignore rules, env template, LangGraph deps, ADK archive, accurate runbook, verified local skeleton.

**Alternatives considered:**

- Keep ADK runnable as 20% baseline alongside LangGraph — **rejected** (master: LangGraph-only; ADK archive)
- Full feature port in Phase 1 — rejected (violates one-phase / approval loop)
- Poetry/uv lockfile migration — rejected for Phase 1 (new toolchain without need)
- Deleting Docker/CI files now — rejected (unrelated cleanup; leave them dormant; LangGraph-only active path)

**Trade-off:** We leave some “future phase” files on disk, so README discipline matters more than filesystem purity.

---

## Implementation checklist (after you approve Phase 1 design)

1. Ensure Python ≥3.11 available on PATH (machine fix; may need brew reinstall)
2. Update `.gitignore` (logs/temp/coverage gaps only)
3. Tighten `.env.example` sections
4. Split deps: LangGraph runtime; **remove** `google-adk` from active requirements + update `pyproject.toml`
5. Archive ADK → `archive/adk_baseline/` + `ARCHIVE_README.md` (inventory in §3.4)
6. Add `src/shorts_assistant/` LangGraph stub (`graph.py`) + port schemas/config/util
7. Replace ADK structure tests with skeleton import/invoke tests
8. Trim README: LangGraph-only; ADK archive note; no `adk web` as primary
9. Recreate venv; install deps; run import + pytest
10. Explain what changed and why after implementation

## Phase 1 exit criteria

- `.env` remains local-only (ignored)
- `.env.example` documents required vars without secrets
- Runtime vs dev dependencies are separated; **no `google-adk` in active runtime deps**
- ADK code lives under `archive/adk_baseline/` (reference only)
- LangGraph skeleton package exists and imports
- README tells a correct, minimal LangGraph run path (no Docker / `adk web` as primary)
- Fresh venv installs cleanly
- Project imports/runs on LangGraph path after hygiene changes
