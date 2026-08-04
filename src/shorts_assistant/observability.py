"""Structured workflow observability: correlation IDs, events, cost, redaction.

Purpose: make agent runs debuggable (iteration, scores, timing, status) without
logging secrets or full prompts. Fail-open — never break the graph.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, TypeVar

from .config import settings

logger = logging.getLogger("shorts_assistant.obs")

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_logging_configured = False

T = TypeVar("T")
NodeFn = Callable[[Any], dict[str, Any]]

_KEY_ASSIGN_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|GOOGLE_API_KEY)\s*[:=]\s*\S+"
)
_SK_RE = re.compile(r"sk-[A-Za-z0-9]{10,}")
_AIZA_RE = re.compile(r"AIza[0-9A-Za-z_-]{20,}")


def get_trace_id() -> str | None:
    """Purpose: read the active observability trace id (if any)."""
    return _trace_id.get()


def estimate_cost_usd(
    input_tokens: int | None,
    output_tokens: int | None,
    *,
    input_rate: float | None = None,
    output_rate: float | None = None,
) -> float | None:
    """Purpose: rough USD estimate from token counts (not a billing API)."""
    if input_tokens is None and output_tokens is None:
        return None
    in_rate = (
        settings.cost_per_1m_input_usd if input_rate is None else input_rate
    )
    out_rate = (
        settings.cost_per_1m_output_usd if output_rate is None else output_rate
    )
    inp = float(input_tokens or 0)
    out = float(output_tokens or 0)
    return round((inp * in_rate + out * out_rate) / 1_000_000.0, 8)


def safe_error_message(exc: BaseException, *, limit: int = 200) -> str:
    """Purpose: truncate and redact secret-like substrings from errors."""
    return redact_text(f"{type(exc).__name__}: {exc}", limit=limit)


def redact_text(text: str, *, limit: int | None = None) -> str:
    """Purpose: redact secrets; optionally truncate for LOG_PAYLOADS."""
    cleaned = _KEY_ASSIGN_RE.sub(r"\1=[REDACTED]", text)
    cleaned = _SK_RE.sub("[REDACTED]", cleaned)
    cleaned = _AIZA_RE.sub("[REDACTED]", cleaned)
    if limit is not None and len(cleaned) > limit:
        return cleaned[: limit - 3] + "..."
    return cleaned

class _TraceIdFilter(logging.Filter):
    """Purpose: inject trace_id onto every LogRecord in this process."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id() or "-"  # type: ignore[attr-defined]
        return True


class JsonLineFormatter(logging.Formatter):
    """Purpose: one JSON object per log line for structured drains."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", get_trace_id()),
        }
        event = getattr(record, "obs_event", None)
        if isinstance(event, dict):
            payload.update(event)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str | None = None) -> None:
    """Purpose: attach JSON formatter + trace_id filter once per process.

    Configures the ``shorts_assistant`` logger tree only (does not wipe root
    handlers, so pytest capture and host apps keep working).
    """
    global _logging_configured
    if _logging_configured:
        return
    lvl = getattr(logging, (level or settings.log_level).upper(), logging.INFO)
    pkg = logging.getLogger("shorts_assistant")
    pkg.setLevel(lvl)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLineFormatter())
    handler.addFilter(_TraceIdFilter())
    pkg.addHandler(handler)
    pkg.propagate = False
    _logging_configured = True


def reset_logging_for_tests() -> None:
    """Purpose: allow unit tests to reconfigure logging."""
    global _logging_configured
    _logging_configured = False
    for name in ("shorts_assistant", "shorts_assistant.obs"):
        log = logging.getLogger(name)
        log.handlers.clear()
        log.filters.clear()
        log.setLevel(logging.NOTSET)
        log.disabled = False
        log.propagate = True


def log_event(event: str, *, agent: str | None = None, **fields: Any) -> None:
    """Purpose: emit one structured observability event (fail-open)."""
    try:
        payload: dict[str, Any] = {
            "event": event,
            "agent": agent,
            "trace_id": get_trace_id(),
            "model": settings.model_name,
        }
        for key, value in fields.items():
            if value is not None:
                payload[key] = value
        if settings.log_payloads and "payload" in payload:
            payload["payload"] = redact_text(str(payload["payload"]), limit=200)
        elif "payload" in payload and not settings.log_payloads:
            payload.pop("payload", None)
        logger.info("%s", event, extra={"obs_event": payload})
    except Exception:  # noqa: BLE001 — fail-open
        logger.warning("observability log_event failed", exc_info=True)


def _score_from_update(update: dict[str, Any], state: Any) -> float | None:
    evaluation = update.get("evaluation")
    if evaluation is None and hasattr(state, "evaluation"):
        evaluation = state.evaluation
    if evaluation is None:
        return None
    if isinstance(evaluation, dict):
        score = evaluation.get("overall_score")
    else:
        score = getattr(evaluation, "overall_score", None)
    return float(score) if score is not None else None


def _iteration_from(update: dict[str, Any], state: Any) -> int | None:
    if "iteration" in update:
        return int(update["iteration"])
    if hasattr(state, "iteration"):
        return int(state.iteration)
    return None


def observe_node(name: str, fn: NodeFn) -> NodeFn:
    """Purpose: wrap a LangGraph node with timing + structured end event."""

    def wrapped(state: Any) -> dict[str, Any]:
        started = time.perf_counter()
        error: str | None = None
        update: dict[str, Any] = {}
        with _node_span(name):
            try:
                update = fn(state) or {}
                return update
            except Exception as exc:  # noqa: BLE001 — record then re-raise
                error = safe_error_message(exc)
                raise
            finally:
                duration_ms = int((time.perf_counter() - started) * 1000)
                try:
                    status = update.get("status")
                    if status is not None and hasattr(status, "value"):
                        status = status.value
                    log_event(
                        "agent_end",
                        agent=name,
                        duration_ms=duration_ms,
                        iteration=_iteration_from(update, state),
                        evaluation_score=_score_from_update(update, state),
                        status=status,
                        error=error,
                        retry_count=0,
                    )
                except Exception:  # noqa: BLE001 — fail-open
                    logger.warning("observe_node end log failed", exc_info=True)

    wrapped.__name__ = getattr(fn, "__name__", name)
    wrapped.__qualname__ = getattr(fn, "__qualname__", name)
    return wrapped


@contextmanager
def _node_span(name: str) -> Iterator[None]:
    try:
        from .telemetry import node_span

        with node_span(name):
            yield
    except Exception:  # noqa: BLE001 — fail-open
        yield


@dataclass
class WorkflowTrace:
    """Purpose: bound one graph invoke with start/end summary events."""

    trace_id: str = field(default_factory=lambda: f"wf_{uuid.uuid4().hex[:12]}")
    started: float = field(default_factory=time.perf_counter)
    _token: Any = field(default=None, init=False, repr=False)
    scores_seen: list[float] = field(default_factory=list)

    def __enter__(self) -> WorkflowTrace:
        self._token = _trace_id.set(self.trace_id)
        self.started = time.perf_counter()
        try:
            from .telemetry import start_workflow_span

            start_workflow_span(self.trace_id)
        except Exception:  # noqa: BLE001 — fail-open
            pass
        log_event("workflow_start", agent="runner")
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        duration_ms = int((time.perf_counter() - self.started) * 1000)
        err = safe_error_message(exc) if exc else None
        log_event(
            "workflow_end",
            agent="runner",
            duration_ms=duration_ms,
            error=err,
            evaluation_scores=self.scores_seen or None,
        )
        try:
            from .telemetry import end_workflow_span

            end_workflow_span(error=err)
        except Exception:  # noqa: BLE001 — fail-open
            pass
        if self._token is not None:
            _trace_id.reset(self._token)

    def note_score(self, score: float | None) -> None:
        """Purpose: record scores seen across quality-loop attempts."""
        if score is not None:
            self.scores_seen.append(float(score))


def finalize_trace(
    trace: WorkflowTrace,
    final: Any,
    *,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> None:
    """Purpose: emit workflow summary with final_status after invoke."""
    try:
        status = getattr(final, "status", None)
        status_val = status.value if hasattr(status, "value") else status
        score = None
        if getattr(final, "evaluation", None) is not None:
            score = float(final.evaluation.overall_score)
            trace.note_score(score)
        cost = estimate_cost_usd(input_tokens, output_tokens)
        log_event(
            "workflow_summary",
            agent="runner",
            final_status=status_val,
            iteration=getattr(final, "iteration", None),
            evaluation_score=score,
            best_score=getattr(final, "best_score", None),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost,
            evaluation_scores=trace.scores_seen or None,
        )
    except Exception:  # noqa: BLE001 — fail-open
        logger.warning("finalize_trace failed", exc_info=True)
