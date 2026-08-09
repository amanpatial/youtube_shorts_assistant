"""CLI: ``PYTHONPATH=src python -m shorts_assistant.eval_gate``."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..config import PROJECT_ROOT
from .gate import dump_gate_result, evaluate_gate_files


def _default_config() -> Path:
    return PROJECT_ROOT / "evals" / "quality_gate.yaml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AI quality gate: fail if candidate regresses beyond thresholds."
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=_default_config(),
        help="Path to quality_gate.yaml",
    )
    args = parser.parse_args(argv)

    result = evaluate_gate_files(args.baseline, args.candidate, args.config)
    print(dump_gate_result(result))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
