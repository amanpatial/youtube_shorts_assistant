"""HTTP client for the Research A2A agent (Phase 15)."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from ..config import settings
from ..observability import log_event
from .contracts import ResearchRequest, ResearchResponse, response_to_research_text

logger = logging.getLogger(__name__)


class A2AResearchError(Exception):
    """Purpose: client-side failure talking to the Research Agent."""


def fetch_agent_card(
    *, base_url: str | None = None, timeout: float | None = None
) -> dict[str, Any]:
    """Purpose: GET /.well-known/agent-card.json for discovery/smoke tests."""
    root = (base_url or settings.a2a_research_url).rstrip("/")
    url = f"{root}/.well-known/agent-card.json"
    return _get_json(url, timeout=timeout or settings.a2a_timeout_sec)


def call_research(
    topic: str,
    *,
    audience: str = "developers",
    max_bullets: int = 8,
    base_url: str | None = None,
    timeout: float | None = None,
) -> ResearchResponse:
    """Purpose: POST ResearchRequest and validate ResearchResponse."""
    root = (base_url or settings.a2a_research_url).rstrip("/")
    url = f"{root}/tasks/research"
    request = ResearchRequest(topic=topic, audience=audience, max_bullets=max_bullets)
    started = time.perf_counter()
    try:
        raw = _post_json(
            url,
            request.model_dump(mode="json"),
            timeout=timeout or settings.a2a_timeout_sec,
        )
        response = ResearchResponse.model_validate(raw)
        log_event(
            "a2a_research",
            agent="research",
            ok=True,
            duration_ms=int((time.perf_counter() - started) * 1000),
            a2a_url=root,
            status=response.status,
            confidence=response.confidence,
        )
        return response
    except Exception as exc:  # noqa: BLE001 — obs then re-raise typed
        log_event(
            "a2a_research",
            agent="research",
            ok=False,
            duration_ms=int((time.perf_counter() - started) * 1000),
            a2a_url=root,
            error=f"{type(exc).__name__}: {exc}",
        )
        if isinstance(exc, A2AResearchError):
            raise
        raise A2AResearchError(str(exc)) from exc


def fetch_research_text(topic: str, **kwargs: Any) -> str:
    """Purpose: call A2A and flatten to WorkflowState.research string."""
    return response_to_research_text(call_research(topic, **kwargs))


def _get_json(url: str, *, timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — local A2A
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise A2AResearchError(f"HTTP {exc.code} for GET {url}") from exc
    except Exception as exc:  # noqa: BLE001
        raise A2AResearchError(f"GET failed: {exc}") from exc
    if not isinstance(data, dict):
        raise A2AResearchError("agent card must be a JSON object")
    return data


def _post_json(url: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — local A2A
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise A2AResearchError(f"HTTP {exc.code} for POST {url}: {detail}") from exc
    except Exception as exc:  # noqa: BLE001
        raise A2AResearchError(f"POST failed: {exc}") from exc

    if not isinstance(raw, dict):
        raise A2AResearchError("response must be a JSON object")
    return raw
