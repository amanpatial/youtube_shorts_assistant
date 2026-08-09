# GTM vertical prototype checklist

Use this repo as a **LangGraph accelerator**: shared core + swappable packs.

| Layer | Lives in | Swappable per customer? |
|-------|----------|-------------------------|
| Core | checkpointer, HITL pattern, API/worker, security, eval_gate, CI, Docker | No |
| Pack | schemas, prompts, smoke eval, pack graph/nodes, MCP allowlist | Yes |

Formal decision: LangGraph-only — [ADR 0001](../adr/0001-primary-orchestration-framework.md).

## Packs today

| `PACK_ID` | Status | Live graph? |
|-----------|--------|-------------|
| `youtube_shorts` | Pack 0 (reference product, **default**) | **Yes** |
| `sales_brief` | Account / opportunity brief | **Yes** (Phase 23) |

```bash
# Default pack
echo $PACK_ID   # youtube_shorts (or unset)

PACK_ID=sales_brief HITL_REQUIRED=false \
  PYTHONPATH=src python -m shorts_assistant "Acme Corp — expand analytics"

PYTHONPATH=src python - <<'PY'
from shorts_assistant.packs import list_packs, get_pack, active_graph_pack
for p in list_packs():
    print(p.pack_id, "active=" + str(p.active_graph))
print("selected:", active_graph_pack().pack_id)
print(get_pack("sales_brief").smoke_dataset)
PY
```

## New vertical in ~1 week

1. **Copy template**  
   `cp -R src/shorts_assistant/packs/_template src/shorts_assistant/packs/<pack_id>`
2. **Define schemas** — draft + evaluation + deliverable (see `sales_brief/schemas.py`)
3. **Write prompts** — `prompts/writer.txt`, `prompts/evaluator.txt`
4. **Add smoke dataset** — `evals/packs/<pack_id>_v1_smoke.json` (5 stratified cases)
5. **Register** in `packs/__init__.py` `_REGISTRY`
6. **Keep `active_graph=False`** until pack graph/nodes + tests pass
7. **Wire pack graph** (mirror `sales_brief/`) and dispatch from `run.py` on `PACK_ID`
8. **Demo** with `HITL_REQUIRED=true`; CI stays offline-demo for both packs
9. **Optional** read-only MCP tools for CRM/KB

## Do not

- Rewrite the tree into multi-orchestrator kits (CrewAI, etc.)
- Turn on a second live graph without smoke + gate tests
- Invent multi-tenant billing before 2–3 successful packs
- Force new pack schemas into Shorts `ShortScript` fields

## Related

- Deploy: [`deploy.md`](deploy.md)  
- Live brief pack: `src/shorts_assistant/packs/sales_brief/`  
- Template: `src/shorts_assistant/packs/_template/`
