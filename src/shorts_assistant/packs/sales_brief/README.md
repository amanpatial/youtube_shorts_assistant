# Pack: `sales_brief`

GTM vertical for **account / opportunity brief** drafts.

| Status | Meaning |
|--------|---------|
| Schemas / prompts / smoke | Ready |
| Live graph | **Yes** — select with `PACK_ID=sales_brief` |
| API `/shorts` | Still Pack 0 only (CLI / `run_until_human` for briefs) |

## Topology

```text
research → memory_retrieve → writer ↔ evaluator ↔ quality_gate
                                    ↓
                               human_review → formatter → END
```

(No visualizer.)

## Demo

```bash
PACK_ID=sales_brief HITL_REQUIRED=false \
  PYTHONPATH=src python -m shorts_assistant "Acme Corp — expand analytics seat"

PACK_ID=sales_brief HITL_REQUIRED=true \
  PYTHONPATH=src python -m shorts_assistant "Northwind Bank — fraud POC"
# resume with PACK_ID still set:
PACK_ID=sales_brief PYTHONPATH=src python -m shorts_assistant.approve <execution_id> approve
```

See [`docs/runbooks/gtm_prototype.md`](../../../../docs/runbooks/gtm_prototype.md).
