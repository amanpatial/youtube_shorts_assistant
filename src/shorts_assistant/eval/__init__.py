"""Offline evaluation dataset runner and baseline compare (Phase 8).

Purpose: fixed cases → harness → metrics → baseline/compare.
Modes: ``demo`` (offline) and ``live_judge`` (Gemini judge only).
"""

from .compare import ModeMismatchError, compare_files, compare_summaries
from .dataset import EvalDataset, load_dataset
from .metrics import aggregate_metrics, criteria_pass
from .runner import run_dataset, run_from_path

__all__ = [
    "EvalDataset",
    "ModeMismatchError",
    "aggregate_metrics",
    "compare_files",
    "compare_summaries",
    "criteria_pass",
    "load_dataset",
    "run_dataset",
    "run_from_path",
]
