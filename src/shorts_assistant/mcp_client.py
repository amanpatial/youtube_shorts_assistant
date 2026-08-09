"""MCP client helper for shorts_catalog (allowlist, timeout, obs, degraded).

Research uses the in-process CatalogService path by default so CI stays offline.
Stdio MCP remains available via ``python -m shorts_assistant.mcp_servers.shorts_catalog``.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Any

from pydantic import ValidationError

from .config import settings
from .mcp_servers.shorts_catalog.catalog import CatalogService
from .mcp_servers.shorts_catalog.schemas import (
    GetShortArgs,
    ListRecentShortsArgs,
    SearchShortsArgs,
)
from .observability import get_trace_id, log_event

logger = logging.getLogger(__name__)

DEFAULT_ALLOWED_TOOLS = frozenset({"list_recent_shorts", "search_shorts", "get_short"})


def allowed_tools() -> set[str]:
    """Purpose: parse MCP_ALLOWED_TOOLS (comma-separated) or default three."""
    raw = (settings.mcp_allowed_tools or "").strip()
    if not raw:
        return set(DEFAULT_ALLOWED_TOOLS)
    return {part.strip() for part in raw.split(",") if part.strip()}


def list_discovered_tools() -> list[str]:
    """Purpose: tool discovery surface for wiring/tests (allowlisted names)."""
    return sorted(allowed_tools() & DEFAULT_ALLOWED_TOOLS)


def call_catalog_tool(
    tool: str,
    arguments: dict[str, Any] | None = None,
    *,
    catalog: CatalogService | None = None,
) -> dict[str, Any]:
    """Purpose: invoke one allowlisted catalog tool with timeout + obs.

    Returns a result dict. On failure returns ``{"ok": False, "error_type": ...}``
    so Research can degrade without crashing the graph.
    """
    args = arguments or {}
    started = time.perf_counter()
    if not settings.mcp_shorts_catalog_enabled:
        return {"ok": False, "error_type": "disabled", "tool": tool}

    if tool not in allowed_tools():
        _log_tool(tool, ok=False, duration_ms=0, error_type="allowlist")
        return {"ok": False, "error_type": "allowlist", "tool": tool}

    if tool not in DEFAULT_ALLOWED_TOOLS:
        _log_tool(tool, ok=False, duration_ms=0, error_type="unknown_tool")
        return {"ok": False, "error_type": "unknown_tool", "tool": tool}

    service = catalog or CatalogService()
    timeout = float(settings.mcp_tool_timeout_sec)

    def _invoke() -> dict[str, Any]:
        if tool == "list_recent_shorts":
            parsed = ListRecentShortsArgs.model_validate(args)
            return service.list_recent_shorts(limit=parsed.limit)
        if tool == "search_shorts":
            parsed = SearchShortsArgs.model_validate(args)
            return service.search_shorts(query=parsed.query, limit=parsed.limit)
        if tool == "get_short":
            parsed = GetShortArgs.model_validate(args)
            return service.get_short(execution_id=str(parsed.execution_id))
        raise ValueError(f"unknown tool {tool}")

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_invoke)
            payload = future.result(timeout=timeout)
        duration_ms = int((time.perf_counter() - started) * 1000)
        _log_tool(tool, ok=True, duration_ms=duration_ms, error_type=None)
        return {"ok": True, "tool": tool, "result": payload}
    except ValidationError as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        _log_tool(tool, ok=False, duration_ms=duration_ms, error_type="validation")
        return {
            "ok": False,
            "error_type": "validation",
            "tool": tool,
            "error": exc.errors(),
        }
    except FuturesTimeout:
        duration_ms = int((time.perf_counter() - started) * 1000)
        _log_tool(tool, ok=False, duration_ms=duration_ms, error_type="timeout")
        return {"ok": False, "error_type": "timeout", "tool": tool}
    except Exception as exc:  # noqa: BLE001 — degrade
        duration_ms = int((time.perf_counter() - started) * 1000)
        _log_tool(
            tool,
            ok=False,
            duration_ms=duration_ms,
            error_type=type(exc).__name__,
        )
        logger.warning("catalog tool failed tool=%s", tool, exc_info=True)
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "tool": tool,
            "error": str(exc)[:200],
        }


def research_catalog_notes(topic: str) -> str | None:
    """Purpose: fetch a short catalog blurb for Research (fail-open → None)."""
    if not settings.mcp_shorts_catalog_enabled:
        return None
    discovered = list_discovered_tools()
    log_event(
        "mcp_discovery",
        agent="research",
        mcp_server="shorts_catalog",
        tools=discovered,
        trace_id=get_trace_id(),
    )
    search = call_catalog_tool("search_shorts", {"query": topic[:200], "limit": 3})
    recent = call_catalog_tool("list_recent_shorts", {"limit": 3})
    parts: list[str] = []
    if search.get("ok") and search.get("result", {}).get("items"):
        items = search["result"]["items"]
        topics = "; ".join(
            f"{it.get('topic', '?')[:60]} (score={it.get('best_score')})" for it in items[:3]
        )
        parts.append(f"Catalog search hits: {topics}")
    if recent.get("ok") and recent.get("result", {}).get("items"):
        items = recent["result"]["items"]
        topics = "; ".join(f"{it.get('topic', '?')[:60]}" for it in items[:3])
        parts.append(f"Recent shorts: {topics}")
    if not parts:
        return None
    return "MCP shorts_catalog (read-only): " + " | ".join(parts)


def _log_tool(
    tool: str,
    *,
    ok: bool,
    duration_ms: int,
    error_type: str | None,
) -> None:
    log_event(
        "mcp_tool",
        agent="research",
        mcp_server="shorts_catalog",
        tool=tool,
        duration_ms=duration_ms,
        ok=ok,
        error_type=error_type,
        trace_id=get_trace_id(),
    )
