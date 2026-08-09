"""Persist useful hooks/scripts into long-term memory after a good run."""

from __future__ import annotations

import logging
import re

from ..config import settings
from ..observability import redact_text
from ..state import WorkflowState, WorkflowStatus
from .store import MemoryRecord, MemoryStore, get_memory_store

logger = logging.getLogger(__name__)

_SECRET_RE = re.compile(r"(?i)(api[_-]?key|token|secret|password|GOOGLE_API_KEY)\s*[:=]\s*\S+")


def maybe_persist_memory(
    state: WorkflowState,
    *,
    store: MemoryStore | None = None,
) -> list[str]:
    """Purpose: insert memory rows for PASS/EXHAUSTED best scripts above threshold.

    Fail-open: logs and returns [] on errors. Skips when score too low or no script.
    """
    if state.status not in (
        WorkflowStatus.PASSED,
        WorkflowStatus.EXHAUSTED,
        WorkflowStatus.COMPLETED,
    ):
        return []
    script = state.best_script or state.generated_script
    score = state.best_score
    if script is None:
        return []
    if score is None and state.evaluation is not None:
        score = float(state.evaluation.overall_score)
    min_score = settings.memory_write_min_score
    if score is None or score < min_score:
        return []

    topic = state.request
    if _looks_like_secret(topic) or _looks_like_secret(script.hook):
        logger.info("memory writer skipped: secret-like content")
        return []

    backend = store or get_memory_store()
    ids: list[str] = []
    try:
        summary = redact_text(f"{script.hook} | {script.cta} | {script.body[:200]}", limit=400)
        ids.append(
            backend.upsert(
                MemoryRecord(
                    kind="successful_hook",
                    topic=topic,
                    text=script.hook,
                    summary=summary,
                    overall_score=float(score),
                    execution_id=state.execution_id,
                    metadata={"status": state.status.value},
                )
            )
        )
        ids.append(
            backend.upsert(
                MemoryRecord(
                    kind="script_success",
                    topic=topic,
                    text=summary,
                    summary=f"CTA: {script.cta}",
                    overall_score=float(score),
                    execution_id=state.execution_id,
                    metadata={"status": state.status.value},
                )
            )
        )
        # Exhaust / weak approve path: keep "what to avoid" signal when issues exist.
        exhausted_like = (
            state.iteration >= state.max_iterations
            and state.evaluation is not None
            and not state.evaluation.approved
        )
        if exhausted_like and state.evaluation.issues:
            issues = "; ".join(state.evaluation.issues[:5])
            ids.append(
                backend.upsert(
                    MemoryRecord(
                        kind="unsuccessful_hook",
                        topic=topic,
                        text=script.hook,
                        summary=f"Avoid: {issues}",
                        overall_score=float(score),
                        execution_id=state.execution_id,
                        metadata={"issues": state.evaluation.issues[:5]},
                    )
                )
            )
    except Exception:  # noqa: BLE001 — fail-open
        logger.warning("maybe_persist_memory failed", exc_info=True)
        return []
    return ids


def _looks_like_secret(text: str) -> bool:
    return bool(_SECRET_RE.search(text or ""))
