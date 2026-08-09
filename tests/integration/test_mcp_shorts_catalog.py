"""Phase 12: shorts_catalog MCP tools — discovery, validation, allowlist, wiring."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from shorts_assistant.config import get_settings
from shorts_assistant.demo_producers import demo_script
from shorts_assistant.graph import build_graph
from shorts_assistant.mcp_client import (
    call_catalog_tool,
    list_discovered_tools,
    research_catalog_notes,
)
from shorts_assistant.mcp_servers.shorts_catalog.catalog import CatalogService
from shorts_assistant.mcp_servers.shorts_catalog.schemas import ListRecentShortsArgs
from shorts_assistant.nodes import research_node
from shorts_assistant.persistence.repository import WorkflowRepository
from shorts_assistant.persistence.session import ensure_schema, reset_engine_cache, session_scope
from shorts_assistant.state import WorkflowState


@pytest.fixture()
def catalog_db(tmp_path, monkeypatch):
    db = tmp_path / "mcp.db"
    url = f"sqlite+pysqlite:///{db}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("MCP_SHORTS_CATALOG_ENABLED", "true")
    get_settings.cache_clear()
    reset_engine_cache()
    import shorts_assistant.config as cfg
    import shorts_assistant.mcp_client as client
    import shorts_assistant.persistence.session as sess

    monkeypatch.setattr(cfg, "settings", get_settings())
    monkeypatch.setattr(sess, "settings", get_settings())
    monkeypatch.setattr(client, "settings", get_settings())
    ensure_schema(url)
    with session_scope(url) as session:
        repo = WorkflowRepository(session)
        wf = repo.create_workflow("LangGraph MCP catalog tip")
        ex = repo.start_execution(wf, trace_id="wf_mcp")
        script = demo_script("LangGraph MCP catalog tip")
        repo.add_script_version(ex, iteration=1, script=script, is_best=True)
        repo.finish_execution(ex, final_status="COMPLETED")
        execution_id = ex
    yield {"url": url, "execution_id": execution_id}
    reset_engine_cache()
    get_settings.cache_clear()


def test_discovered_tools_include_three():
    names = list_discovered_tools()
    assert set(names) == {
        "list_recent_shorts",
        "search_shorts",
        "get_short",
    }


def test_list_recent_shorts_seeded(catalog_db):
    svc = CatalogService()
    out = svc.list_recent_shorts(limit=5)
    assert out["count"] >= 1
    assert any("LangGraph" in it["topic"] for it in out["items"])


def test_invalid_limit_validation():
    with pytest.raises(ValidationError):
        ListRecentShortsArgs(limit=999)
    bad = call_catalog_tool("list_recent_shorts", {"limit": 999})
    assert bad["ok"] is False
    assert bad["error_type"] == "validation"


def test_allowlist_blocks_unknown(monkeypatch, catalog_db):
    monkeypatch.setattr(
        "shorts_assistant.mcp_client.settings.mcp_allowed_tools",
        "list_recent_shorts",
    )
    blocked = call_catalog_tool("search_shorts", {"query": "x", "limit": 1})
    assert blocked["ok"] is False
    assert blocked["error_type"] == "allowlist"


def test_timeout_path(monkeypatch, catalog_db):
    monkeypatch.setattr("shorts_assistant.mcp_client.settings.mcp_tool_timeout_sec", 0.01)

    class Slow(CatalogService):
        def list_recent_shorts(self, *, limit: int = 5):
            import time

            time.sleep(0.2)
            return super().list_recent_shorts(limit=limit)

    out = call_catalog_tool("list_recent_shorts", {"limit": 1}, catalog=Slow())
    assert out["ok"] is False
    assert out["error_type"] == "timeout"


def test_research_node_includes_catalog_when_enabled(catalog_db, monkeypatch):
    monkeypatch.setattr("shorts_assistant.mcp_client.settings.mcp_shorts_catalog_enabled", True)
    state = WorkflowState.initial("LangGraph agents")
    update = research_node(state)
    assert "research" in update
    assert "MCP shorts_catalog" in update["research"]


def test_graph_still_has_research_not_replaced():
    g = build_graph()
    assert "research" in g.nodes
    assert "scriptwriter" in g.nodes
    assert "evaluator" in g.nodes


def test_get_short_and_search(catalog_db):
    ex = catalog_db["execution_id"]
    got = call_catalog_tool("get_short", {"execution_id": ex})
    assert got["ok"] is True
    assert got["result"]["found"] is True
    search = call_catalog_tool("search_shorts", {"query": "LangGraph", "limit": 5})
    assert search["ok"] is True
    assert search["result"]["count"] >= 1


def test_research_catalog_notes_disabled(monkeypatch):
    monkeypatch.setattr("shorts_assistant.mcp_client.settings.mcp_shorts_catalog_enabled", False)
    assert research_catalog_notes("topic") is None


def test_fastmcp_server_registers_tools():
    from shorts_assistant.mcp_servers.shorts_catalog import server as srv

    tools = srv.mcp._tool_manager.list_tools()
    names = {t.name for t in tools}
    assert names >= {"list_recent_shorts", "search_shorts", "get_short"}
