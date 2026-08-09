"""Pydantic data contracts for the Shorts pipeline.

Each class is a fixed JSON shape that nodes write into ``WorkflowState``.
Purpose: stop passing free-text blobs between steps — every field is typed and
validated so bad model output fails early instead of poisoning the next node.

Pipeline ownership (who writes what):
  scriptwriter  → ShortScript (+ ScriptSection)
  evaluator     → ScriptEvaluation
  visualizer    → VisualPlan (+ VisualShot)
  formatter     → ShortConcept (+ ScriptVisualRow)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ScriptSection(BaseModel):
    """Purpose: one timed piece of the spoken script (hook, body, or CTA).

    Why it exists: a Short is a sequence of beats with time budgets; the
    evaluator and visualizer need labeled chunks, not one undifferentiated blob.

    Written as part of: ``ShortScript.sections`` (by the scriptwriter).
    """

    label: Literal["hook", "body", "cta"]
    text: str = Field(min_length=1)
    estimated_seconds: float = Field(ge=0.5, le=30)


class ShortScript(BaseModel):
    """Purpose: the full draft YouTube Shorts script as structured data.

    Why it exists: later nodes must score, visualize, and format specific fields
    (hook, body, CTA, duration). A plain string cannot be validated or gated.

    Written by: scriptwriter node → ``WorkflowState.generated_script``.
    Read by: evaluator (judge only), visualizer, formatter.
    Must not be rewritten by: evaluator (judge never mutates the script).
    """

    title: str = Field(min_length=1, max_length=120)
    hook: str = Field(min_length=1)
    body: str = Field(min_length=1)
    cta: str = Field(min_length=1)
    target_audience: str = "developers"
    estimated_duration_seconds: float = Field(ge=15, le=60)
    sections: list[ScriptSection] = Field(min_length=3, max_length=8)


class VisualShot(BaseModel):
    """Purpose: one camera/on-screen direction for a single script beat.

    Why it exists: visuals are planned beat-by-beat (what to show, what text
    appears, what kind of shot). The formatter pairs each shot with spoken lines.

    Written as part of: ``VisualPlan.shots`` (by the visualizer).
    """

    beat: str
    description: str = Field(min_length=1)
    on_screen_text: str = ""
    shot_type: Literal[
        "screen_recording",
        "diagram",
        "code_overlay",
        "ui",
        "b_roll",
        "title_card",
    ]


class VisualPlan(BaseModel):
    """Purpose: the complete visual direction pack for the Short.

    Why it exists: filming/editing guidance must be a list of shots plus pacing
    notes, not free-form prose the formatter cannot reliably parse.

    Written by: visualizer node → ``WorkflowState.visual_concepts``.
    Read by: formatter (only after evaluation approved the script).
    """

    shots: list[VisualShot] = Field(min_length=3, max_length=8)
    pacing: str = Field(min_length=1)
    graphics_notes: str = ""
    b_roll: list[str] = Field(default_factory=list)


class ScriptEvaluation(BaseModel):
    """Purpose: a structured quality judgment of a ``ShortScript``.

    Why it exists: the pipeline needs machine-readable scores and a boolean
    gate (``approved``) so visuals do not run on weak or invalid scripts.
    This is the AI-as-judge output — scores and issues only, never a new script.

    Written by: evaluator node → ``WorkflowState.evaluation``.
    Read by: ``ready_for_visuals()`` / visualizer (``approved`` must be true).
    Score scale: each ``*_score`` and ``overall_score`` is 0.0–10.0.
    """

    overall_score: float = Field(ge=0, le=10)
    hook_score: float = Field(ge=0, le=10)
    clarity_score: float = Field(ge=0, le=10)
    pacing_score: float = Field(ge=0, le=10)
    technical_accuracy: float = Field(ge=0, le=10)
    factual_correctness: float = Field(ge=0, le=10)
    developer_value: float = Field(ge=0, le=10)
    duration_score: float = Field(ge=0, le=10)
    cta_score: float = Field(ge=0, le=10)
    tone_score: float = Field(ge=0, le=10)
    issues: list[str] = Field(default_factory=list)
    approved: bool
    summary: str = ""


class ScriptVisualRow(BaseModel):
    """Purpose: one row in the final concept table — spoken line + matching visual.

    Why it exists: the deliverable is a beat-aligned script/visual grid creators
    can shoot from. Built by the formatter from ``ShortScript`` + ``VisualPlan``.

    Written as part of: ``ShortConcept.script_and_visuals``.
    """

    timestamp_or_beat: str = Field(description="Time range or beat label, e.g. '0-3s' or 'Hook'.")
    spoken_line: str = Field(description="Narration or spoken line for this beat.")
    visual: str = Field(description="Visual direction that supports this beat.")


class ShortConcept(BaseModel):
    """Purpose: the final user-facing Shorts concept package.

    Why it exists: this is the product output — hook, beat table, visual notes,
    and CTA — ready to hand to a creator (or later an API/HITL UI).

    Written by: formatter node → ``WorkflowState.final_short_concept``.
    Built from: approved ``ShortScript`` + ``VisualPlan``.
    """

    hook: str = Field(description="Opening 1-3 second hook line.")
    script_and_visuals: list[ScriptVisualRow] = Field(
        description="Ordered script beats paired with visuals."
    )
    visual_notes: str = Field(description="Pacing, on-screen text/graphics, and B-roll guidance.")
    cta: str = Field(description="Call to action for the viewer.")
    quality_notes: str | None = Field(
        default=None,
        description="Optional reviewer notes if present in state.",
    )

    def to_markdown(self) -> str:
        """Turn this concept into readable Markdown for CLI or docs preview."""
        lines = [
            "# YouTube Short Concept",
            "",
            "## Hook",
            self.hook,
            "",
            "## Script & Visuals",
            "",
            "| Beat | Spoken | Visual |",
            "| --- | --- | --- |",
        ]
        for row in self.script_and_visuals:
            lines.append(f"| {row.timestamp_or_beat} | {row.spoken_line} | {row.visual} |")
        lines.extend(
            [
                "",
                "## Visual Notes",
                self.visual_notes,
                "",
                "## CTA",
                self.cta,
            ]
        )
        if self.quality_notes:
            lines.extend(["", "## Quality Notes", self.quality_notes])
        return "\n".join(lines)
