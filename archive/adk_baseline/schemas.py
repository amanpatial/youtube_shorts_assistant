"""Structured output models for the Shorts concept pipeline."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ScriptVisualRow(BaseModel):
    """One beat of spoken script paired with a visual direction."""

    timestamp_or_beat: str = Field(
        description="Time range or beat label, e.g. '0-3s' or 'Hook'."
    )
    spoken_line: str = Field(description="Narration or spoken line for this beat.")
    visual: str = Field(description="Visual direction that supports this beat.")


class ShortConcept(BaseModel):
    """Final YouTube Short concept produced by the formatter agent."""

    hook: str = Field(description="Opening 1-3 second hook line.")
    script_and_visuals: list[ScriptVisualRow] = Field(
        description="Ordered script beats paired with visuals."
    )
    visual_notes: str = Field(
        description="Pacing, on-screen text/graphics, and B-roll guidance."
    )
    cta: str = Field(description="Call to action for the viewer.")
    quality_notes: Optional[str] = Field(
        default=None,
        description="Optional reviewer notes if present in state.",
    )

    def to_markdown(self) -> str:
        """Render a human-readable Markdown view of the concept."""
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
            lines.append(
                f"| {row.timestamp_or_beat} | {row.spoken_line} | {row.visual} |"
            )
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
