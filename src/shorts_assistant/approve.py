"""CLI: resume a HITL-paused execution.

Usage::

    PYTHONPATH=src python -m shorts_assistant.approve <execution_id> approve
    PYTHONPATH=src python -m shorts_assistant.approve <execution_id> reject --feedback "..."
    PYTHONPATH=src python -m shorts_assistant.approve <execution_id> \\
        request_changes --feedback "..."
"""

from __future__ import annotations

import argparse
import json
import sys

from .run import resume_with_decision


def main(argv: list[str] | None = None) -> int:
    """Purpose: parse decision, resume graph, print final/paused WorkflowState JSON."""
    parser = argparse.ArgumentParser(
        description="Approve / reject / request_changes for a paused Shorts run"
    )
    parser.add_argument("execution_id", help="execution_id from run_until_human pause")
    parser.add_argument(
        "decision",
        choices=("approve", "reject", "request_changes"),
        help="Human decision",
    )
    parser.add_argument(
        "--feedback",
        default=None,
        help="Required for request_changes; optional notes for reject/approve",
    )
    parser.add_argument(
        "--reviewer",
        default="local",
        help="Reviewer id for audit logs (default: local)",
    )
    args = parser.parse_args(argv)

    if args.decision == "request_changes" and not (args.feedback or "").strip():
        print("error: --feedback is required for request_changes", file=sys.stderr)
        return 2

    try:
        final = resume_with_decision(
            args.execution_id,
            decision=args.decision,
            feedback=args.feedback,
            reviewer=args.reviewer,
        )
    except Exception as exc:  # noqa: BLE001 — CLI surface
        msg = str(exc)
        print(f"error: {exc}", file=sys.stderr)
        if "Field required" in msg or "input_value={}" in msg:
            print(
                "\nHint: LangGraph checkpoint was empty. Cross-process HITL needs a durable "
                "checkpointer (CHECKPOINT_BACKEND=sqlite|postgres). "
                "memory does not survive a new approve process. "
                "Re-run the pause step, then approve again.",
                file=sys.stderr,
            )
        return 1

    print(json.dumps(final.to_dict(), indent=2))
    status = final.status.value if hasattr(final.status, "value") else str(final.status)
    if status == "COMPLETED":
        return 0
    if status == "AWAITING_HUMAN":
        return 3  # paused again (another human round)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
