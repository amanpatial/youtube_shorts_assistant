"""Scoped failure taxonomy and retry policy for external I/O.

Purpose: classify errors and retry only transient LLM/tool failures — never
quality-gate misses (Phase 5) and never spray retries on every node.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Any, TypeVar

from .contracts import ContractValidationError
from .state import FailureClass, WorkflowStatus

logger = logging.getLogger(__name__)

T = TypeVar("T")

__all__ = [
    "FailureClass",
    "FailureInfo",
    "RetriesExhaustedError",
    "RetryPolicy",
    "call_with_policy",
    "classify_exception",
    "clear_error_fields",
    "failure_update",
    "llm_retry_policy_from_settings",
]


class RetriesExhaustedError(Exception):
    """Purpose: signal that TRANSIENT retries hit the attempt limit.

    Why it exists: callers decide fallback vs fail-closed after exhaustion.
    """

    def __init__(self, message: str, *, last_error: BaseException | None = None) -> None:
        super().__init__(message)
        self.last_error = last_error


@dataclass(frozen=True)
class RetryPolicy:
    """Purpose: hard limits for one external call site (not the quality loop)."""

    max_attempts: int = 3
    timeout_seconds: float = 30.0
    backoff_base_seconds: float = 0.5
    backoff_max_seconds: float = 8.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")


@dataclass(frozen=True)
class FailureInfo:
    """Purpose: structured error surface for WorkflowState / CLI / later API."""

    message: str
    failure_class: FailureClass
    node: str
    cause_type: str | None = None

    def format(self) -> str:
        """Purpose: single-line user-visible error string."""
        return f"[{self.node}] {self.failure_class.value}: {self.message}"


def _status_code(exc: BaseException) -> int | None:
    for attr in ("status_code", "code", "http_status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    if response is not None:
        code = getattr(response, "status_code", None)
        if isinstance(code, int):
            return code
    return None


def _message(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}".lower()


def classify_exception(exc: BaseException) -> FailureClass:
    """Purpose: map an exception to a failure class for retry / state.

    Why it exists: ``call_with_policy`` retries only TRANSIENT; nodes write
    the class onto state. QUALITY never comes from exceptions.
    """
    if isinstance(exc, ContractValidationError):
        return FailureClass.PERMANENT
    if isinstance(exc, RetriesExhaustedError):
        return FailureClass.TRANSIENT

    if isinstance(
        exc,
        (
            TimeoutError,
            FuturesTimeoutError,
            ConnectionError,
            ConnectionResetError,
            BrokenPipeError,
        ),
    ):
        return FailureClass.TRANSIENT

    # Optional dependency error types (httpx / requests) without hard imports.
    name = type(exc).__name__
    if name in {"ReadTimeout", "ConnectTimeout", "PoolTimeout", "TimeoutException"}:
        return FailureClass.TRANSIENT
    if name in {"RemoteProtocolError", "NetworkError", "ConnectError"}:
        return FailureClass.TRANSIENT

    code = _status_code(exc)
    if code == 429 or (code is not None and 500 <= code <= 599):
        return FailureClass.TRANSIENT
    if code in {401, 403, 400, 404}:
        return FailureClass.PERMANENT

    text = _message(exc)
    if re.search(r"\b(429|rate.?limit|timeout|temporarily unavailable|econnreset)\b", text):
        return FailureClass.TRANSIENT
    if re.search(r"\b(401|403|unauthorized|forbidden|invalid api key|api key)\b", text):
        return FailureClass.PERMANENT

    # Unknown at a node boundary = programming/invariant, not worth retrying.
    return FailureClass.PROGRAMMING


def failure_update(node: str, exc: BaseException) -> dict[str, Any]:
    """Purpose: build a WorkflowState partial update for a terminal node failure."""
    failure_class = classify_exception(exc)
    info = FailureInfo(
        message=str(exc),
        failure_class=failure_class,
        node=node,
        cause_type=type(exc).__name__,
    )
    logger.info(
        "node_failure node=%s class=%s cause=%s",
        node,
        failure_class.value,
        info.cause_type,
    )
    return {
        "status": WorkflowStatus.FAILED,
        "error": info.format(),
        "error_class": failure_class,
        "error_node": node,
    }


def clear_error_fields() -> dict[str, None]:
    """Purpose: wipe error channels on a successful node update."""
    return {"error": None, "error_class": None, "error_node": None}


def _run_with_timeout(fn: Callable[[], T], timeout_seconds: float) -> T:
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError as exc:
            future.cancel()
            raise TimeoutError(f"call exceeded timeout of {timeout_seconds}s") from exc


def call_with_policy(
    fn: Callable[[], T],
    *,
    policy: RetryPolicy,
    sleep: Callable[[float], None] = time.sleep,
    classify: Callable[[BaseException], FailureClass] = classify_exception,
) -> T:
    """Purpose: invoke ``fn`` with per-attempt timeout and TRANSIENT-only retries.

    Why it exists: keep backoff/limits out of business nodes; unit-test without Gemini.
    """
    last_error: BaseException | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return _run_with_timeout(fn, policy.timeout_seconds)
        except Exception as exc:  # noqa: BLE001 — classify then decide retry
            last_error = exc
            failure_class = classify(exc)
            logger.info(
                "call_with_policy attempt=%s/%s class=%s error=%s",
                attempt,
                policy.max_attempts,
                failure_class.value,
                exc,
            )
            if failure_class != FailureClass.TRANSIENT:
                raise
            if attempt >= policy.max_attempts:
                break
            delay = min(
                policy.backoff_base_seconds * (2 ** (attempt - 1)),
                policy.backoff_max_seconds,
            )
            sleep(delay)

    raise RetriesExhaustedError(
        f"exhausted {policy.max_attempts} attempts",
        last_error=last_error,
    )


def llm_retry_policy_from_settings(settings: Any) -> RetryPolicy:
    """Purpose: build RetryPolicy from application Settings fields."""
    return RetryPolicy(
        max_attempts=int(settings.llm_max_attempts),
        timeout_seconds=float(settings.llm_timeout_seconds),
        backoff_base_seconds=float(settings.llm_backoff_base_seconds),
        backoff_max_seconds=float(settings.llm_backoff_max_seconds),
    )
