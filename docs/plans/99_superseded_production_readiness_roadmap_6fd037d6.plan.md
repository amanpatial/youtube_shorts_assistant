---
name: Production Readiness Roadmap
overview: "SUPERSEDED. Early 3-phase ADK-only production plan. Do not execute. Canonical roadmap is 00_master + Phases 1–21 (LangGraph-only; ADK archived)."
todos:
  - id: phase1-consolidate
    content: "SUPERSEDED — see 00_master and 01_phase_repo_hygiene onward"
    status: cancelled
  - id: phase2-reliability
    content: "SUPERSEDED — split across Phases 1, 6, 7, 9, 10, 18"
    status: cancelled
  - id: phase3-production
    content: "SUPERSEDED — split across Phases 3–5, 8–9, 17, 19 + LangGraph 20–21"
    status: cancelled
isProject: false
---

# SUPERSEDED — Do Not Execute This Plan

**Status:** Obsolete relative to the later learning roadmap.

**Canonical process:** [00_master_learning_roadmap_24e99839.plan.md](00_master_learning_roadmap_24e99839.plan.md)  
**Canonical phases:** `01_phase_*.plan.md` … `21_phase_*.plan.md` (sorted top-to-bottom in plans folder)  
**Narrative (current master):** ADK experiment → LangGraph-only rebuild; ADK archived (not 20% maintained)

This file is kept only as historical context (maturity snapshot + early stack notes).

---

## Verification: why it does not align

| Topic | This old plan (3 phases) | Later phased plans (1–21) |
|-------|--------------------------|---------------------------|
| Phase numbering | Phase 1 = correctness (SequentialAgent, runner, consolidate) | Phase 1 = **repo hygiene only** |
| Phase 2 | config + logging + SQLite + tests + CI | Phase 2 = **typed workflow state** |
| Phase 3 | structured output + critic + eval + OTel + Docker + security | Phase 3 = **structured LLM contracts** only |
| Granularity | 3 fat phases | 21 teach-then-implement phases |
| Quality loop | Critic as optional one-shot; earlier said LoopAgent→Sequential | Phase 4 evaluator + Phase 5 LangGraph conditional-edge quality loop |
| Failure handling | Light try/except in old Phase 2 | Phase 6 (plan file **missing** — gap) |
| Tests / CI | Bundled early | Phases 7 and 18 |
| Eval dataset | Thin ADK eval in old Phase 3 | Phase 8 (20 cases + baseline) |
| Observability | Old Phase 3.4 | Phase 9 |
| Persistence | SQLite sessions in old Phase 2 | Phase 10 PostgreSQL domain model |
| Memory/RAG, MCP, A2A, HITL, routing, async API | Absent | Phases 11–16 |
| Security | Light, end of old Phase 3 | Phase 17 |
| Deploy | Docker + `adk deploy` in old Phase 3 | Phase 19; **no K8s by default** |
| Primary framework | **ADK forever** | **LangGraph primary**, ADK baseline |
| Process | Implement incrementally | Inspect → understand → approve → implement → test → learn |
| Maturity scorecard | Still useful as a **snapshot** | Keep for reference only |

### Dangerous collisions if someone follows both

1. **Old Phase 1 “fix LoopAgent → SequentialAgent”** vs **new Phase 5 “bring back LoopAgent for quality loop”** — different intents; old doc looks contradictory later.  
2. **Old Phase 1 includes runner + agent correctness**; **new Phase 1 forbids unrelated agent redesign** (hygiene only).  
3. **Old plan pushes Docker/CI/eval early**; **new plan delays Docker** and splits CI vs AI eval.  
4. **Old plan never mentions LangGraph**; executing it fights the 80/20 decision.

### Also missing from the later set

- **No `phase_6_*.plan.md`** for Production Failure Handling (user pasted Phase 6, then Phase 7; Phase 6 plan was never created).

---

## What is still reusable from this file

- Maturity Level 2 scorecard (as of first inspection)  
- Early stack inventory (ADK 1.20, Gemini, `.env` keys)  
- List of original bugs (`raw_idea`, duplicate files, broken runner) — triage under the **new** phase that owns each concern  

## What to follow instead

1. Working agreement (no autonomous multi-phase implementation)  
2. Start at **Phase 1 hygiene** plan when ready (Step 1 Inspect)  
3. Proceed phase-by-phase through 21  
4. Create Phase 6 plan when you reach failure-handling  
5. Treat LangGraph as primary after Phases 20–21 are done under the approval loop  

---

## Historical content below (archived)

The original maturity tables, stack notes, and 3-phase checklist remain in git history of this plan file’s prior versions if needed. **Do not implement from the old Phase 1–3 sections.**
