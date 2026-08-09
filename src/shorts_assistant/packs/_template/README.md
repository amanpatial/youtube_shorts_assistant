# Vertical pack template

Copy this folder to `packs/<your_pack_id>/` and fill in:

1. `schemas.py` — domain Pydantic models (draft, evaluation, deliverable)
2. `prompts/writer.txt` + `prompts/evaluator.txt`
3. Smoke dataset under `evals/packs/<id>_v1_smoke.json` (5 cases)
4. Register the pack in `shorts_assistant.packs` registry (`__init__.py`)
5. Keep `active_graph=False` until the graph is wired and tested

Checklist: [`docs/runbooks/gtm_prototype.md`](../../../../docs/runbooks/gtm_prototype.md).
