---
name: Master Learning Roadmap
overview: "Master index: LangGraph-only active stack; ADK archived (not mixed). Per-phase approval loop; phases 01–21; plans live in docs/plans for later git push. Do not implement autonomously."
todos:
  - id: current-phase
    content: "Phase 10 implement complete (0.10.0). Next: Start Phase 11 — Inspect (RAG/memory) when ready."
    status: completed
  - id: archive-adk
    content: "ADK archived under archive/adk_baseline/; google-adk removed from active deps; LangGraph sole active runtime"
    status: completed
  - id: gap-phase-6
    content: "Expand 06_phase_failure_handling_stub.plan.md into full Phase 6 design when that phase is reached"
    status: completed
isProject: false
---

# Master Learning Roadmap — YouTube Shorts Assistant

**Canonical location (in repo — commit with the project):**  
`docs/plans/`  
Absolute: `/Users/amanpatial/Projects/personal/youtube_shorts_assistant/docs/plans/`

These plans are **source artifacts** for later git remote push. Do not gitignore this folder.

Cursor `~/.cursor/plans/NN_…` files are **symlinks** here.

If anything conflicts with this file, **this file wins** (except detailed design inside a phase plan you have explicitly approved).

---

## Decision (confirmed)

**LangGraph-only for all active development.**  
**Google ADK is archived — not maintained as a second live stack, not mixed into the running app.**

| Track | Role |
|-------|------|
| **LangGraph** | **100% of active implementation** (orchestration, API, workers, deploy) |
| **ADK** | **Archive only** — historical experiment under `archive/adk_baseline/` (after approved Phase 1 implement). Readable reference; not a runnable product path. |

### Why

- Avoid dual-framework tax and mixed mental models  
- Align learning with explicit state machines, loops, checkpoints, HITL  
- Preserve ADK history without operating two productions  

### Archive policy (when implement is approved — not before)

1. Move ADK-era modules/prompts worth keeping → `archive/adk_baseline/` + short `ARCHIVE_README.md`  
2. Remove `google-adk` from active `requirements.txt` / runtime  
3. New package root for the app (e.g. `src/shorts_assistant/` or `langgraph_shorts/`) — LangGraph only  
4. Do **not** line-by-line translate ADK classes; rebuild from functional requirements  

---

## Project narrative

This project started as a Google ADK experiment and is being rebuilt **fresh on LangGraph** to explore stateful agent orchestration, evaluation loops, MCP, A2A, observability, persistence, and production AI engineering.

ADK remains in **archive** for context. It is not an active baseline you maintain at 20% effort.

---

## Hard rule — no autonomous implementation

Cursor must **not** implement the roadmap autonomously.

- No multi-phase coding in one go  
- No “while we’re here” later-phase work  
- Draft / mixed ADK code on disk is **untrusted** until Phase 1 archive + LangGraph greenfield are approved  
- `99_superseded_production_readiness_roadmap_*.plan.md` — do not execute  

---

## Per-phase loop (mandatory)

| Step | Owner | Activity |
|------|--------|----------|
| 1. Inspect | Cursor | Read current code/files; report findings |
| 2. Understand | You + Cursor | Teach/discuss the concept (**no code**) |
| 3. Review architecture | You + Cursor | Design, alternatives, trade-offs |
| 4. Approve design | **You only** | Explicit approval required |
| 5. Implement | Cursor | Smallest useful change for **this phase only** |
| 6. Test | Cursor + You | Verify tests; keep system runnable |
| 7. Review learning | You + Cursor | What changed, why, what you learned — then **stop** |

### Approval language (required before Step 5)

- “Approve Phase N design — implement”  
- “Approved, proceed with implementation”  

**Not** enough: pasting the next PHASE spec, “continue”, or silence.

---

## Current position

| Item | Value |
|------|--------|
| **Framework strategy** | LangGraph-only; ADK → archive |
| **Active phase** | Phase 10 complete (0.10.0) — persistent state |
| **Next step** | **Start Phase 11 — Inspect** (RAG/memory) when ready |
| **ADK code archived on disk?** | Yes — `archive/adk_baseline/` |
| **Solution architecture** | [docs/architecture/solution_architecture.md](../architecture/solution_architecture.md) |
| **Phase 6** | Complete (0.6.0) — taxonomy + scoped LLM retries |

---

## Canonical phase index (sorted 00 → 21)

All phases below target **LangGraph** unless noted. ADK appears only as archive/reference.

| # | Title | Plan file | Notes |
|--:|-------|-----------|-------|
| 00 | **Master roadmap (this file)** | [00_master_learning_roadmap_24e99839.plan.md](00_master_learning_roadmap_24e99839.plan.md) | |
| 01 | Repo hygiene + ADK archive | [01_phase_repo_hygiene_dce91540.plan.md](01_phase_repo_hygiene_dce91540.plan.md) | Archive ADK; LangGraph project skeleton |
| 02 | Explicit typed workflow state | [02_phase_workflow_state_6cfb4cd5.plan.md](02_phase_workflow_state_6cfb4cd5.plan.md) | LangGraph state |
| 03 | Structured LLM contracts | [03_phase_structured_contracts_82d939d7.plan.md](03_phase_structured_contracts_82d939d7.plan.md) | |
| 04 | Real AI evaluator | [04_phase_real_evaluator_99ae754e.plan.md](04_phase_real_evaluator_99ae754e.plan.md) | |
| 05 | Quality-controlled agent loop | [05_phase_quality_loop_ad5c8440.plan.md](05_phase_quality_loop_ad5c8440.plan.md) | Conditional edges, not ADK LoopAgent |
| 06 | Production failure handling | [06_phase_failure_handling_stub.plan.md](06_phase_failure_handling_stub.plan.md) | Complete — taxonomy + scoped retries |
| 07 | Test strategy | [07_phase_test_strategy_021d23b6.plan.md](07_phase_test_strategy_021d23b6.plan.md) | |
| 08 | AI evaluation dataset | [08_phase_eval_dataset_a8617ded.plan.md](08_phase_eval_dataset_a8617ded.plan.md) | |
| 09 | AI observability | [09_phase_ai_observability_f00e7c78.plan.md](09_phase_ai_observability_f00e7c78.plan.md) | |
| 10 | Persistent workflow state | [10_phase_persistent_state_019178ab.plan.md](10_phase_persistent_state_019178ab.plan.md) | + LG checkpointer |
| 11 | Memory / RAG | [11_phase_memory_rag_cb33e6fb.plan.md](11_phase_memory_rag_cb33e6fb.plan.md) | |
| 12 | MCP integration | [12_phase_mcp_integration_940c4e9c.plan.md](12_phase_mcp_integration_940c4e9c.plan.md) | LG/langchain MCP adapters |
| 13 | Human-in-the-loop | [13_phase_human_in_loop_d6d12396.plan.md](13_phase_human_in_loop_d6d12396.plan.md) | `interrupt` / resume |
| 14 | Model routing | [14_phase_model_routing_ff380361.plan.md](14_phase_model_routing_ff380361.plan.md) | |
| 15 | A2A architecture | [15_phase_a2a_architecture_0e5666f7.plan.md](15_phase_a2a_architecture_0e5666f7.plan.md) | Custom node / experiment |
| 16 | Production API + async jobs | [16_phase_async_api_dad62339.plan.md](16_phase_async_api_dad62339.plan.md) | |
| 17 | Security and guardrails | [17_phase_security_guardrails_d1e7b8a8.plan.md](17_phase_security_guardrails_d1e7b8a8.plan.md) | |
| 18 | AI CI/CD | [18_phase_ai_cicd_de26bb4e.plan.md](18_phase_ai_cicd_de26bb4e.plan.md) | |
| 19 | Production deployment | [19_phase_production_deploy_2f80e8d4.plan.md](19_phase_production_deploy_2f80e8d4.plan.md) | |
| 20 | LangGraph parity / hardening | [20_phase_langgraph_rebuild_75bfc0c3.plan.md](20_phase_langgraph_rebuild_75bfc0c3.plan.md) | Not “second stack” — deepen LG |
| 21 | ADR: LangGraph-only decision | [21_phase_adk_vs_langgraph_adr_26a2def9.plan.md](21_phase_adk_vs_langgraph_adr_26a2def9.plan.md) | Record archive vs dual-stack |
| 99 | SUPERSEDED old 3-phase plan | [99_superseded_production_readiness_roadmap_6fd037d6.plan.md](99_superseded_production_readiness_roadmap_6fd037d6.plan.md) | Historical |

Detail plans written earlier may still mention ADK APIs; **treat those as outdated** where they conflict with this master file. When a phase starts, redesign for LangGraph in Steps 2–3.

---

## Target architecture (end state)

**Canonical consolidated solution view (use while implementing every phase):**  
[docs/architecture/solution_architecture.md](../architecture/solution_architecture.md)

That document is the single source for:

1. Workflow graph (Research → Writer → Evaluator → Quality Gate → Visualizer → Formatter → HITL → Done)  
2. Platform stack (Postgres/checkpointing, Evaluation, Observability, RAG, MCP, A2A, Model Router, HITL, API, Async workers)  
3. MCP/A2A integration spokes (tools + peer agents)  
4. Target repo shape  
5. **Phase build-up matrix** (what exists after each phase)

Master keeps process + phase index; architecture detail lives in the solution doc. If they conflict, update the solution doc and point here.

**Phase 1** still only: hygiene + ADK archive + stub graph — not the full consolidated diagram.

---

## Cursor behavior constraints

- One phase at a time  
- Teach/design before code  
- Wait for approval before Step 5  
- After Step 7, **stop**  
- **Do not** keep ADK and LangGraph both as active runtimes  
- **Do not** delete ADK until archive step is explicitly approved in Phase 1 implement  
- Do not execute `99_superseded_*`  

---

## How to proceed

Say: **“Start Phase 1 — Inspect”**

Cursor will inspect the repo (including what would move to `archive/adk_baseline/`) and propose a LangGraph-only hygiene + archive design. No code until you approve.
