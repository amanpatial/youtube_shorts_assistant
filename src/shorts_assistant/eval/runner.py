"""Run the Shorts graph over an eval dataset (demo or live_judge modes)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from ..config import PROJECT_ROOT, settings
from ..eval_flags import live_judge_mode, memory_retrieval_mode
from ..models.registry import task_model_map
from ..run import invoke_workflow
from .dataset import EvalCase, EvalDataset, load_dataset
from .metrics import aggregate_metrics, case_record_from_state

logger = logging.getLogger(__name__)

EvalMode = Literal["demo", "live_judge"]

InvokeCaseFn = Callable[[EvalCase, EvalMode], dict[str, Any]]


def prompt_version() -> str:
    """Purpose: cheap label for which prompt bundle the run used."""
    prompts = PROJECT_ROOT / "src" / "shorts_assistant" / "prompts"
    if not prompts.is_dir():
        return "unknown"
    names = sorted(p.name for p in prompts.glob("*.txt"))
    return "prompts:" + ",".join(names) if names else "prompts:none"


def default_invoke_case(case: EvalCase, mode: EvalMode) -> dict[str, Any]:
    """Purpose: run the traced graph once for a case topic.

    Forces HITL off so bulk eval never blocks on interrupt (Phase 13).
    """
    prefer_live = mode == "live_judge"
    prev_hitl = settings.hitl_required
    prev_a2a = settings.a2a_research_enabled
    settings.hitl_required = False
    settings.a2a_research_enabled = False
    try:
        with live_judge_mode(prefer_live):
            return invoke_workflow(case.input.topic).to_dict()
    finally:
        settings.hitl_required = prev_hitl
        settings.a2a_research_enabled = prev_a2a


def run_dataset(
    dataset: EvalDataset,
    *,
    mode: EvalMode = "demo",
    invoke_case: InvokeCaseFn | None = None,
    memory_retrieval: bool | None = None,
) -> dict[str, Any]:
    """Purpose: execute all cases, continue on failure, return run artifact dict.

    ``memory_retrieval`` overrides MEMORY_RETRIEVAL for Phase 11 A/B runs.
    """
    invoke = invoke_case or default_invoke_case
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    started = time.perf_counter()
    records: list[dict[str, Any]] = []

    def _run_case(case: EvalCase) -> dict[str, Any]:
        if memory_retrieval is None:
            return invoke(case, mode)
        with memory_retrieval_mode(memory_retrieval):
            return invoke(case, mode)

    for case in dataset.cases:
        case_error: str | None = None
        state: dict[str, Any] = {}
        try:
            state = _run_case(case)
            if not isinstance(state, dict):
                raise TypeError("invoke_case must return a state dict")
        except Exception as exc:  # noqa: BLE001 — continue remaining cases
            case_error = f"{type(exc).__name__}: {exc}"
            logger.exception("eval case failed case_id=%s", case.case_id)
            state = {
                "status": "FAILED",
                "error": case_error,
                "evaluation": None,
                "generated_script": None,
                "iteration": 0,
            }
        records.append(case_record_from_state(case, state, error=case_error))

    summary = aggregate_metrics(records)
    summary.update(
        {
            "mode": mode,
            "memory_retrieval": (
                settings.memory_retrieval if memory_retrieval is None else memory_retrieval
            ),
            "model_name": settings.model_name,
            "task_models": task_model_map(settings),
            "quality_threshold": settings.quality_threshold,
            "dataset_id": dataset.dataset_id,
            "dataset_version": dataset.version,
            "run_id": run_id,
            "created_at": datetime.now(UTC).isoformat(),
            "prompt_version": prompt_version(),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
    )
    return {"summary": summary, "cases": records}


def write_run_artifact(artifact: dict[str, Any], out_dir: str | Path) -> Path:
    """Purpose: persist run JSON under results/runs/{run_id}.json."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    run_id = artifact["summary"]["run_id"]
    path = out / f"{run_id}.json"
    path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return path


def save_baseline(artifact: dict[str, Any], baseline_path: str | Path) -> Path:
    """Purpose: freeze a run as a comparable baseline artifact."""
    path = Path(baseline_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return path


def run_from_path(
    dataset_path: str | Path,
    *,
    mode: EvalMode = "demo",
    out_dir: str | Path | None = None,
    save_baseline_path: str | Path | None = None,
    invoke_case: InvokeCaseFn | None = None,
    memory_retrieval: bool | None = None,
) -> dict[str, Any]:
    """Purpose: load dataset, run, optionally write run/baseline files."""
    if mode == "live_judge":
        settings.validate_for_runtime()
    dataset = load_dataset(dataset_path)
    artifact = run_dataset(
        dataset,
        mode=mode,
        invoke_case=invoke_case,
        memory_retrieval=memory_retrieval,
    )
    if out_dir is not None:
        write_run_artifact(artifact, out_dir)
    if save_baseline_path is not None:
        save_baseline(artifact, save_baseline_path)
    return artifact
