"""CLI entry: ``PYTHONPATH=src python -m shorts_assistant \"your topic\"``.

Purpose: run one offline pipeline locally and print the final WorkflowState as JSON.
Exit 0 if status is COMPLETED (including Phase 5 EXHAUSTED→format path, e.g. ``[reject]``).
Exit 1 if FAILED (contract/infra/programming errors with ``error_class`` / ``error_node``).
Exit 3 if AWAITING_HUMAN (HITL_REQUIRED=true — resume via ``python -m shorts_assistant.approve``).

Phase 20: ``--stream`` prints node update names then final state.
"""

from __future__ import annotations

import argparse
import json
import sys
from uuid import uuid4

from .graph_ops import node_names_from_updates, stream_workflow
from .run import get_thread_state, run_until_human
from .state import WorkflowState


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
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Phase 20: stream node updates (then print final state JSON)",
    )
    args = parser.parse_args(argv)

    if args.stream:
        thread_id = f"cli-{uuid4().hex[:12]}"
        chunks = stream_workflow(args.topic, thread_id=thread_id)
        names = node_names_from_updates(chunks)
        print(json.dumps({"thread_id": thread_id, "nodes": names}, indent=2), file=sys.stderr)
        snap = get_thread_state(thread_id)
        values = getattr(snap, "values", None) or {}
        final = WorkflowState.from_dict(dict(values)) if values else None
        if final is None:
            print("{}", file=sys.stderr)
            return 1
        print(json.dumps(final.to_dict(), indent=2))
        status = final.status.value if hasattr(final.status, "value") else str(final.status)
        if status == "COMPLETED":
            return 0
        if status == "AWAITING_HUMAN":
            return 3
        return 1

    final = run_until_human(args.topic)
    print(json.dumps(final.to_dict(), indent=2))
    status = final.status.value
    if status == "COMPLETED":
        return 0
    if status == "AWAITING_HUMAN":
        print(
            "\nPaused for human review. Resume with:\n"
            f"  python -m shorts_assistant.approve {final.execution_id} approve\n"
            f"  python -m shorts_assistant.approve {final.execution_id} "
            'request_changes --feedback "..."',
            file=sys.stderr,
        )
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
