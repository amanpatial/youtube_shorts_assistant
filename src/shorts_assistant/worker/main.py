"""Worker poll loop: ``python -m shorts_assistant.worker``."""

from __future__ import annotations

import argparse
import logging
import signal
import time

from ..config import settings
from ..observability import configure_logging
from ..runtime_lifecycle import is_shutting_down, request_shutdown
from .bridge import process_one_job

logger = logging.getLogger(__name__)


def _handle_signal(signum: int, _frame: object) -> None:
    logger.info("received signal %s; stopping after current job", signum)
    request_shutdown()


def run_forever(*, poll_sec: float | None = None, once: bool = False) -> int:
    """Purpose: poll/claim jobs until SIGINT/SIGTERM (or one shot if once)."""
    configure_logging()
    settings.validate_for_production()
    interval = float(poll_sec if poll_sec is not None else settings.worker_poll_sec)
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    logger.info("worker started poll_sec=%s app_env=%s", interval, settings.app_env)

    while not is_shutting_down():
        worked = process_one_job()
        if once:
            return 0 if worked else 0
        if not worked:
            time.sleep(interval)
    logger.info("worker stopped")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Shorts async job worker (Phase 16)")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process at most one job then exit (tests / smoke)",
    )
    parser.add_argument(
        "--poll-sec",
        type=float,
        default=None,
        help="Override WORKER_POLL_SEC",
    )
    args = parser.parse_args(argv)
    return run_forever(poll_sec=args.poll_sec, once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
