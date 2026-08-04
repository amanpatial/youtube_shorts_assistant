"""CLI entry: ``PYTHONPATH=src python -m shorts_assistant \"your topic\"``.

Purpose: run one offline pipeline locally and print the final WorkflowState as JSON.
Exit 0 if status is COMPLETED (including Phase 5 EXHAUSTED→format path, e.g. ``[reject]``).
Exit 1 if FAILED (contract/infra/programming errors with ``error_class`` / ``error_node``).
"""

from __future__ import annotations

import argparse
import json

from .run import invoke_workflow


def main(argv: list[str] | None = None) -> int:
    """Purpose: parse topic, invoke traced graph, print JSON, return exit code."""
    parser = argparse.ArgumentParser(
        description="YouTube Shorts Assistant — LangGraph (structured contracts)"
    )
    parser.add_argument(
        "topic",
        nargs="?",
        default="Phase 3 structured contracts smoke",
        help="Topic / request seeded into WorkflowState.initial(...)",
    )
    args = parser.parse_args(argv)

    final = invoke_workflow(args.topic)
    print(json.dumps(final.to_dict(), indent=2))
    return 0 if final.status.value == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
