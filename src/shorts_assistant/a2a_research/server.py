"""Standalone Research Agent HTTP process (Phase 15 A2A-lite).

Run::

    PYTHONPATH=src python -m shorts_assistant.a2a_research
"""

from __future__ import annotations

import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from .agent_card import DEFAULT_URL, build_agent_card
from .contracts import ResearchRequest
from .service import produce_research

logger = logging.getLogger(__name__)


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, indent=2).encode("utf-8")


class ResearchA2AHandler(BaseHTTPRequestHandler):
    """Purpose: serve agent card + research task over HTTP."""

    server_version = "ShortsResearchA2A/0.15"

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.info("%s - " + fmt, self.address_string(), *args)

    def _send(self, code: int, payload: Any, *, content_type: str = "application/json") -> None:
        body = _json_bytes(payload)
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 — http.server API
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in {"/.well-known/agent-card.json", "/.well-known/agent.json"}:
            base = getattr(self.server, "public_url", DEFAULT_URL)
            self._send(200, build_agent_card(url=base))
            return
        if path == "/health":
            self._send(200, {"ok": True, "agent": "shorts_research_agent"})
            return
        self._send(404, {"ok": False, "error": "not_found", "path": path})

    def do_POST(self) -> None:  # noqa: N802 — http.server API
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path != "/tasks/research":
            self._send(404, {"ok": False, "error": "not_found", "path": path})
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
            request = ResearchRequest.model_validate(data)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            self._send(
                400,
                {
                    "ok": False,
                    "error": "invalid_request",
                    "detail": str(exc),
                    "status": "failed",
                },
            )
            return
        try:
            response = produce_research(request)
            self._send(200, response.model_dump(mode="json"))
        except Exception as exc:  # noqa: BLE001 — surface as failed task
            logger.exception("research task failed")
            self._send(
                500,
                {
                    "topic": request.topic,
                    "bullets": [],
                    "sources": [],
                    "confidence": 0.0,
                    "errors": [f"{type(exc).__name__}: {exc}"],
                    "status": "failed",
                },
            )


def serve(host: str = "127.0.0.1", port: int = 9101) -> None:
    """Purpose: bind ThreadingHTTPServer and serve forever."""
    public_url = f"http://{host}:{port}"
    httpd = ThreadingHTTPServer((host, port), ResearchA2AHandler)
    httpd.public_url = public_url  # type: ignore[attr-defined]
    logger.info("Research A2A agent listening on %s", public_url)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Shorts Research A2A agent (Phase 15)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9101)
    args = parser.parse_args(argv)
    serve(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
