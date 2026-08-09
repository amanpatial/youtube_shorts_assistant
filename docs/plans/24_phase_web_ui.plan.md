---
name: Phase 24 Web UI
overview: "Phase 24 adds a React + Vite UI that consumes the Shorts job API, plus CORS and GET /shorts list support."
todos:
  - id: p24-cors-list
    content: CORS middleware + GET /shorts owner-scoped list
    status: completed
  - id: p24-spa
    content: frontend/ Vite React TS — create, history, detail, HITL
    status: completed
  - id: p24-docs
    content: README + api.md + version 0.24.0
    status: completed
isProject: false
---

# Phase 24 — Web UI for the Shorts API

## Scope

- React + Vite + TypeScript SPA in `frontend/`
- Backend: `CORS_ORIGINS` + `GET /shorts` list (owner-scoped)
- Pages: create run, history, detail (poll + result + HITL)
- API key stored in browser localStorage (never committed)

## Run (after implement)

```bash
# Terminal 1 — API
API_KEY=dev-change-me PYTHONPATH=src python -m shorts_assistant.api --port 8000

# Terminal 2 — worker
API_KEY=dev-change-me PYTHONPATH=src python -m shorts_assistant.worker

# Terminal 3 — UI
cd frontend && npm install && npm run dev
# open http://127.0.0.1:5173
```

## Out of scope

- sales_brief HTTP `/briefs`
- Auth beyond API key
- Production CDN / nginx static hosting
