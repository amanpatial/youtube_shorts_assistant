"""Offline stand-ins that build valid contracts without calling an LLM.

Purpose: keep CI and local ``python -m shorts_assistant`` runnable with no API key.
These are not product-quality generations — they only prove wiring and schemas.
"""

from __future__ import annotations

from .schemas import (
    ScriptEvaluation,
    ScriptSection,
    ScriptVisualRow,
    ShortConcept,
    ShortScript,
    VisualPlan,
    VisualShot,
)

# Request markers for offline control of the quality loop / judge.
REJECT_MARKER = "[reject]"
RETRY_PASS_MARKER = "[retry-pass]"


def demo_research(request: str) -> str:
    """Purpose: fake research notes for the topic (stand-in for tools/RAG)."""
    return (
        f"Research notes for developers about: {request}. "
        "Focus on a concrete tip, one demo, and a clear CTA."
    )


def demo_script(
    request: str,
    research: str | None = None,
    *,
    evaluation: ScriptEvaluation | None = None,
) -> ShortScript:
    """Purpose: build a schema-valid ShortScript (optionally revised from issues).

    On retry, when ``evaluation.issues`` is present, appends an "Addressed feedback"
    clause so ``[retry-pass]`` judge can approve the second attempt.
    """
    hook = f"Stop overcomplicating {request[:40]}."
    body = (
        f"Here is a practical take on {request}. "
        f"{(research or '')[:120]}".strip()
    )
    cta = "Try this pattern in your next short."
    title = request[:120]

    if evaluation and evaluation.issues:
        feedback = "; ".join(evaluation.issues[:3])
        body = (
            f"{body} Addressed feedback: {feedback}. "
            "Tightened hook, clarified the tip, and strengthened the CTA."
        )
        hook = f"Here's the fix: ship typed state for {request[:28]}."
        cta = "Apply this revision pattern in your next agent graph."
        title = f"Revised: {request[:100]}"

    return ShortScript(
        title=title,
        hook=hook,
        body=body,
        cta=cta,
        target_audience="developers",
        estimated_duration_seconds=45.0,
        sections=[
            ScriptSection(label="hook", text=hook, estimated_seconds=3.0),
            ScriptSection(label="body", text=body, estimated_seconds=30.0),
            ScriptSection(label="cta", text=cta, estimated_seconds=7.0),
        ],
    )


def demo_visuals(script: ShortScript) -> VisualPlan:
    """Purpose: build a schema-valid VisualPlan from an approved script (no LLM)."""
    return VisualPlan(
        shots=[
            VisualShot(
                beat="hook",
                description="Title card over IDE",
                on_screen_text=script.hook[:60],
                shot_type="title_card",
            ),
            VisualShot(
                beat="body",
                description="Screen recording of the tip",
                on_screen_text="",
                shot_type="screen_recording",
            ),
            VisualShot(
                beat="cta",
                description="Code overlay with next step",
                on_screen_text=script.cta[:60],
                shot_type="code_overlay",
            ),
        ],
        pacing="Brisk; cut every 3–5s; stay under 60s",
        graphics_notes="Large readable fonts; dark IDE theme",
        b_roll=["keyboard close-up", "terminal scroll"],
    )


def demo_format(script: ShortScript, visuals: VisualPlan) -> ShortConcept:
    """Purpose: merge script + visuals into the final ShortConcept deliverable."""
    rows: list[ScriptVisualRow] = []
    for shot, section in zip(visuals.shots, script.sections, strict=False):
        rows.append(
            ScriptVisualRow(
                timestamp_or_beat=shot.beat,
                spoken_line=section.text,
                visual=shot.description,
            )
        )
    while len(rows) < len(visuals.shots):
        shot = visuals.shots[len(rows)]
        rows.append(
            ScriptVisualRow(
                timestamp_or_beat=shot.beat,
                spoken_line=script.body,
                visual=shot.description,
            )
        )
    return ShortConcept(
        hook=script.hook,
        script_and_visuals=rows,
        visual_notes=f"{visuals.pacing}. {visuals.graphics_notes}",
        cta=script.cta,
        quality_notes=None,
    )
