"""CLI: ``PYTHONPATH=src python -m shorts_assistant.eval run|compare …``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..config import PROJECT_ROOT
from .compare import ModeMismatchError, compare_files
from .runner import run_from_path


def _default_dataset() -> Path:
    return PROJECT_ROOT / "evals" / "shorts_v1_dataset.json"


def _cmd_run(args: argparse.Namespace) -> int:
    artifact = run_from_path(
        args.dataset,
        mode=args.mode,
        out_dir=args.out,
        save_baseline_path=args.save_baseline,
    )
    print(json.dumps(artifact["summary"], indent=2))
    if args.out:
        print(f"wrote run under {args.out}", file=sys.stderr)
    if args.save_baseline:
        print(f"saved baseline {args.save_baseline}", file=sys.stderr)
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    try:
        result = compare_files(args.baseline, args.candidate)
    except ModeMismatchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Purpose: argparse entry for eval run / compare."""
    parser = argparse.ArgumentParser(
        prog="python -m shorts_assistant.eval",
        description="Shorts offline eval runner (demo | live_judge)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run dataset and write metrics")
    run_p.add_argument(
        "--dataset",
        type=Path,
        default=_default_dataset(),
        help="Path to shorts_v1_dataset.json",
    )
    run_p.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "evals" / "results" / "runs",
        help="Directory for run JSON artifacts",
    )
    run_p.add_argument(
        "--mode",
        choices=("demo", "live_judge"),
        default="demo",
        help="demo = synthetic judge; live_judge = Gemini judge",
    )
    run_p.add_argument(
        "--save-baseline",
        type=Path,
        default=None,
        help="Also copy this run to a baseline path",
    )
    run_p.set_defaults(func=_cmd_run)

    cmp_p = sub.add_parser("compare", help="Compare candidate vs baseline")
    cmp_p.add_argument("--baseline", type=Path, required=True)
    cmp_p.add_argument("--candidate", type=Path, required=True)
    cmp_p.set_defaults(func=_cmd_compare)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
