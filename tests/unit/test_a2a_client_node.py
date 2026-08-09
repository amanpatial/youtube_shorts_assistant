"""A2A client wiring: mocked peer + in-process parity."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from shorts_assistant.a2a_research.client import A2AResearchError, call_research
from shorts_assistant.a2a_research.contracts import ResearchResponse
from shorts_assistant.config import get_settings
from shorts_assistant.nodes import research_node
from shorts_assistant.state import WorkflowState, WorkflowStatus


def test_a2a_disabled_uses_demo(monkeypatch):
    monkeypatch.setenv("A2A_RESEARCH_ENABLED", "false")
    get_settings.cache_clear()
    import shorts_assistant.config as cfg
    import shorts_assistant.nodes as nodes

    monkeypatch.setattr(cfg, "settings", get_settings())
    monkeypatch.setattr(nodes, "settings", get_settings())

    update = research_node(WorkflowState.initial("in-process topic"))
    assert update["status"] == WorkflowStatus.RESEARCHING
    assert "in-process topic" in (update["research"] or "")
    get_settings.cache_clear()


def test_a2a_enabled_mocked_success(monkeypatch):
    monkeypatch.setenv("A2A_RESEARCH_ENABLED", "true")
    get_settings.cache_clear()
    import shorts_assistant.a2a_research.client as client_mod
    import shorts_assistant.config as cfg
    import shorts_assistant.nodes as nodes

    monkeypatch.setattr(cfg, "settings", get_settings())
    monkeypatch.setattr(nodes, "settings", get_settings())

    def fake_fetch(topic: str, **_kwargs: object) -> str:
        return f"A2A research for: {topic}\nBullets:\n- tip"

    monkeypatch.setattr(client_mod, "fetch_research_text", fake_fetch)

    update = research_node(WorkflowState.initial("remote topic"))
    assert "A2A research for: remote topic" in (update["research"] or "")
    get_settings.cache_clear()


def test_a2a_degraded_empty_when_not_required(monkeypatch):
    monkeypatch.setenv("A2A_RESEARCH_ENABLED", "true")
    monkeypatch.setenv("A2A_RESEARCH_REQUIRED", "false")
    get_settings.cache_clear()
    import shorts_assistant.a2a_research.client as client_mod
    import shorts_assistant.config as cfg
    import shorts_assistant.nodes as nodes

    monkeypatch.setattr(cfg, "settings", get_settings())
    monkeypatch.setattr(nodes, "settings", get_settings())

    def boom(topic: str, **_kwargs: object) -> str:
        raise A2AResearchError("connection refused")

    monkeypatch.setattr(client_mod, "fetch_research_text", boom)
    update = research_node(WorkflowState.initial("down peer"))
    assert update["research"] == ""
    assert update["status"] == WorkflowStatus.RESEARCHING
    get_settings.cache_clear()


def test_a2a_required_fails_node(monkeypatch):
    monkeypatch.setenv("A2A_RESEARCH_ENABLED", "true")
    monkeypatch.setenv("A2A_RESEARCH_REQUIRED", "true")
    get_settings.cache_clear()
    import shorts_assistant.a2a_research.client as client_mod
    import shorts_assistant.config as cfg
    import shorts_assistant.nodes as nodes

    monkeypatch.setattr(cfg, "settings", get_settings())
    monkeypatch.setattr(nodes, "settings", get_settings())

    def boom(topic: str, **_kwargs: object) -> str:
        raise A2AResearchError("connection refused")

    monkeypatch.setattr(client_mod, "fetch_research_text", boom)
    update = research_node(WorkflowState.initial("must have peer"))
    assert update["status"] == WorkflowStatus.FAILED
    assert update.get("error_node") == "research"
    get_settings.cache_clear()


def test_malformed_response_rejected(monkeypatch):
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):  # noqa: ANN002
            return

        def do_POST(self):  # noqa: N802
            body = json.dumps({"not": "a research response"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = httpd.server_address[1]
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(A2AResearchError):
            call_research("topic", base_url=f"http://127.0.0.1:{port}", timeout=2.0)
    finally:
        httpd.shutdown()


@pytest.mark.a2a
def test_live_local_a2a_server_smoke():
    """Opt-in: real local research server process in-thread."""
    from shorts_assistant.a2a_research.server import ResearchA2AHandler

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), ResearchA2AHandler)
    httpd.public_url = f"http://127.0.0.1:{httpd.server_address[1]}"  # type: ignore[attr-defined]
    port = httpd.server_address[1]
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{port}"
        from shorts_assistant.a2a_research.client import fetch_agent_card

        card = fetch_agent_card(base_url=base, timeout=2.0)
        assert card["name"] == "shorts_research_agent"
        resp = call_research("A2A smoke", base_url=base, timeout=2.0)
        assert isinstance(resp, ResearchResponse)
        assert resp.status == "completed"
        assert resp.bullets
    finally:
        httpd.shutdown()
