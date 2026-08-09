"""Liveness / readiness probes (Phase 19)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Response, status
from sqlalchemy import text

from ..persistence.session import get_engine
from ..runtime_lifecycle import is_shutting_down


def ping_database() -> bool:
    """Purpose: lightweight DB connectivity check for readiness."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def liveness_payload() -> dict[str, str]:
    """Purpose: process-up signal (no dependency checks)."""
    return {"status": "ok"}


def readiness_payload() -> tuple[dict[str, Any], int]:
    """Purpose: ready for traffic only if DB ok and not shutting down."""
    if is_shutting_down():
        return {
            "status": "not_ready",
            "reason": "shutting_down",
        }, status.HTTP_503_SERVICE_UNAVAILABLE
    if not ping_database():
        return {
            "status": "not_ready",
            "reason": "database_unavailable",
        }, status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready"}, status.HTTP_200_OK


def register_health_routes(app: FastAPI) -> None:
    """Purpose: mount /healthz, /readyz, and /health alias (no auth)."""

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return liveness_payload()

    @app.get("/health")
    def health() -> dict[str, str]:
        return liveness_payload()

    @app.get("/readyz")
    def readyz(response: Response) -> dict[str, Any]:
        body, code = readiness_payload()
        response.status_code = code
        return body
