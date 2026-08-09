"""Research Agent business logic (runs inside the A2A server process)."""

from __future__ import annotations

from .contracts import ResearchRequest, ResearchResponse


def produce_research(request: ResearchRequest) -> ResearchResponse:
    """Purpose: build a ResearchResponse without calling a live LLM.

    Optionally appends MCP catalog notes when available in this process.
    """
    errors: list[str] = []
    bullets = [
        f"Concrete tip for {request.audience} on: {request.topic}",
        "Show one short demo or before/after in under 30s",
        "End with a clear CTA tied to the tip",
    ]
    sources = ["demo:local-research-agent"]

    try:
        from ..mcp_client import research_catalog_notes

        catalog = research_catalog_notes(request.topic)
        if catalog:
            # Keep catalog as one bullet; do not dump raw MCP payloads.
            bullets.append(catalog.strip()[:240])
            sources.append("mcp:shorts_catalog")
    except Exception as exc:  # noqa: BLE001 — optional enrichment
        errors.append(f"mcp_enrichment_failed:{type(exc).__name__}")

    bullets = bullets[: request.max_bullets]
    return ResearchResponse(
        topic=request.topic,
        bullets=bullets,
        sources=sources,
        confidence=0.7 if not errors else 0.55,
        errors=errors,
        status="completed",
    )
