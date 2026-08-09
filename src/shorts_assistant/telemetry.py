"""Opt-in OpenTelemetry bootstrap for LangGraph Shorts runs (not ADK).

Purpose: create root/child spans when ENABLE_OTEL or OTLP endpoint is set.
Soft dependency — missing OTel packages → warn once and no-op.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from typing import Any

from .config import settings

logger = logging.getLogger(__name__)

_warned_missing = False
_tracer: Any = None
_root_span: Any = None
_root_token: Any = None


def _otel_requested() -> bool:
    otlp = bool(
        os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    )
    return bool(settings.enable_otel or otlp)


def setup_telemetry() -> None:
    """Purpose: configure TracerProvider when opted in; otherwise no-op."""
    global _tracer, _warned_missing
    if not _otel_requested():
        logger.debug("OpenTelemetry disabled (ENABLE_OTEL=false, no OTLP endpoint).")
        return
    if _tracer is not None:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        if not _warned_missing:
            logger.warning(
                "ENABLE_OTEL set but OpenTelemetry packages missing; "
                "pip install opentelemetry-api opentelemetry-sdk "
                "opentelemetry-exporter-otlp"
            )
            _warned_missing = True
        return

    try:
        resource = Resource.create({"service.name": settings.app_name})
        provider = TracerProvider(resource=resource)
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv(
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"
        )
        if endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )

                provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
            except Exception as exc:  # noqa: BLE001 — fail-open
                logger.warning("OTLP exporter setup failed: %s", exc)
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("shorts_assistant")
        logger.info("OpenTelemetry tracer configured.")
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("Failed to configure OpenTelemetry: %s", exc)


def start_workflow_span(trace_id: str) -> None:
    """Purpose: open root span shorts.workflow for one invoke."""
    global _root_span, _root_token
    setup_telemetry()
    if _tracer is None:
        return
    try:
        from opentelemetry import context as otel_context
        from opentelemetry import trace

        _root_span = _tracer.start_span(
            "shorts.workflow",
            attributes={"trace_id": trace_id},
        )
        ctx = trace.set_span_in_context(_root_span)
        _root_token = otel_context.attach(ctx)
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("start_workflow_span failed: %s", exc)


def end_workflow_span(*, error: str | None = None) -> None:
    """Purpose: close root workflow span."""
    global _root_span, _root_token
    try:
        from opentelemetry import context as otel_context
        from opentelemetry import trace

        if _root_span is not None:
            if error:
                _root_span.set_status(trace.Status(trace.StatusCode.ERROR, error))
            _root_span.end()
        if _root_token is not None:
            otel_context.detach(_root_token)
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("end_workflow_span failed: %s", exc)
    finally:
        _root_span = None
        _root_token = None


@contextmanager
def node_span(name: str) -> Iterator[None]:
    """Purpose: child span around one LangGraph node (no-op when OTel off)."""
    setup_telemetry()
    if _tracer is None:
        yield
        return
    try:
        cm = _tracer.start_as_current_span(f"shorts.node.{name}")
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("node_span start failed: %s", exc)
        cm = nullcontext()
    with cm:
        yield
