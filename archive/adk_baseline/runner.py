"""Programmatic / CLI runner for the YouTube Shorts Assistant."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from .agent import root_agent
from .config import PROJECT_ROOT, settings
from .schemas import ShortConcept
from .telemetry import setup_telemetry

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    """Structured result from a pipeline run."""

    ok: bool
    session_id: str
    final_text: Optional[str] = None
    final_concept: Optional[dict[str, Any]] = None
    error: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "session_id": self.session_id,
            "final_text": self.final_text,
            "final_concept": self.final_concept,
            "error": self.error,
        }


def configure_logging(level: Optional[str] = None) -> None:
    logging.basicConfig(
        level=getattr(logging, (level or settings.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def sanitize_input(query: str) -> str:
    """Validate and truncate user input for safer / cheaper runs."""
    text = (query or "").strip()
    if not text:
        raise ValueError("Input query must be a non-empty string.")
    if len(text) > settings.max_input_length:
        raise ValueError(
            f"Input exceeds MAX_INPUT_LENGTH ({settings.max_input_length} characters)."
        )
    return text


def _ensure_data_dir() -> None:
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)


def _concept_from_state(value: Any) -> Optional[ShortConcept]:
    if value is None:
        return None
    if isinstance(value, ShortConcept):
        return value
    if isinstance(value, dict):
        return ShortConcept.model_validate(value)
    if isinstance(value, str):
        try:
            return ShortConcept.model_validate_json(value)
        except Exception:
            return None
    return None


def _extract_text_from_event(event: Any) -> Optional[str]:
    content = getattr(event, "content", None)
    if not content or not getattr(content, "parts", None):
        return None
    chunks = [part.text for part in content.parts if getattr(part, "text", None)]
    text = "".join(chunks).strip()
    return text or None


async def call_agent_async(
    query: str,
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> RunResult:
    """Run the Shorts pipeline once and return a structured result."""
    load_dotenv(PROJECT_ROOT / ".env")
    settings.validate_for_runtime()
    setup_telemetry()

    try:
        cleaned = sanitize_input(query)
    except ValueError as exc:
        return RunResult(ok=False, session_id=session_id or "", error=str(exc))

    user_id = user_id or f"user-{uuid.uuid4().hex[:8]}"
    session_id = session_id or f"session-{uuid.uuid4().hex}"

    _ensure_data_dir()
    session_service = DatabaseSessionService(db_url=settings.session_db_url)

    try:
        await session_service.create_session(
            app_name=settings.app_name,
            user_id=user_id,
            session_id=session_id,
            state={"raw_idea": cleaned},
        )
        runner = Runner(
            agent=root_agent,
            app_name=settings.app_name,
            session_service=session_service,
        )

        content = types.Content(role="user", parts=[types.Part(text=cleaned)])
        logger.info(
            "Starting run app=%s user=%s session=%s",
            settings.app_name,
            user_id,
            session_id,
        )

        final_text: Optional[str] = None
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            author = getattr(event, "author", None)
            if author:
                logger.info("Event from agent=%s", author)
            if event.is_final_response():
                final_text = _extract_text_from_event(event)

        session = await session_service.get_session(
            app_name=settings.app_name,
            user_id=user_id,
            session_id=session_id,
        )
        concept_raw = (session.state if session else {}).get("final_short_concept")
        concept = _concept_from_state(concept_raw)

        if concept is not None:
            return RunResult(
                ok=True,
                session_id=session_id,
                final_text=concept.to_markdown(),
                final_concept=concept.model_dump(exclude_none=True),
            )

        if final_text:
            return RunResult(
                ok=True,
                session_id=session_id,
                final_text=final_text,
                final_concept=concept_raw if isinstance(concept_raw, dict) else None,
            )

        return RunResult(
            ok=False,
            session_id=session_id,
            error="No final response produced by the agent pipeline.",
        )
    except Exception as exc:
        logger.exception("Agent run failed for session=%s", session_id)
        return RunResult(ok=False, session_id=session_id, error=str(exc))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a developer-focused YouTube Short concept."
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Topic or product idea for the Short.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the structured RunResult as JSON.",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help="Optional user id for the session.",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Optional session id (default: generated UUID).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    configure_logging()
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not args.query:
        parser.print_help()
        return 2

    result = asyncio.run(
        call_agent_async(
            args.query,
            user_id=args.user_id,
            session_id=args.session_id,
        )
    )

    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    elif result.ok and result.final_text:
        print(result.final_text)
    else:
        print(f"Error: {result.error}", file=sys.stderr)

    return 0 if result.ok else 1


if __name__ == "__main__":
    # Allow `python runner.py "..."` from the package directory.
    if __package__ is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        __package__ = "youtube_shorts_assistant"
    raise SystemExit(main())
