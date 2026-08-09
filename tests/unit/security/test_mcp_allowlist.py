"""Confirm MCP allowlist fail-closed (Phase 12/17)."""

from __future__ import annotations

from shorts_assistant.config import Settings
from shorts_assistant.mcp_client import call_catalog_tool


def test_non_allowlisted_tool_rejected(monkeypatch):
    import shorts_assistant.mcp_client as mcp

    monkeypatch.setattr(
        mcp,
        "settings",
        Settings(
            _env_file=None,
            mcp_shorts_catalog_enabled=True,
            mcp_allowed_tools="list_recent_shorts",
        ),
    )
    result = call_catalog_tool("search_shorts", {"query": "x"})
    assert result.get("ok") is False
