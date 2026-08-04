"""Optional OpenTelemetry setup for ADK runs."""

from __future__ import annotations

import logging

from .config import settings

logger = logging.getLogger(__name__)


def setup_telemetry() -> None:
    """Enable ADK OTel providers when ENABLE_OTEL is true or OTLP env is set.

    Set one of:
      - ENABLE_OTEL=true
      - OTEL_EXPORTER_OTLP_ENDPOINT / OTEL_EXPORTER_OTLP_TRACES_ENDPOINT
    """
    import os

    otlp_configured = bool(
        os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    )
    if not (settings.enable_otel or otlp_configured):
        logger.debug("OpenTelemetry disabled (ENABLE_OTEL=false and no OTLP endpoint).")
        return

    try:
        from google.adk.telemetry.setup import maybe_set_otel_providers

        maybe_set_otel_providers()
        logger.info("OpenTelemetry providers configured.")
    except Exception as exc:  # pragma: no cover - best-effort bootstrapping
        logger.warning("Failed to configure OpenTelemetry: %s", exc)
