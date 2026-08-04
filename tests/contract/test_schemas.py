"""Tests for structured schemas."""

from shorts_assistant.schemas import ScriptVisualRow, ShortConcept


def test_short_concept_to_markdown():
    concept = ShortConcept(
        hook="Stop writing agents the hard way.",
        script_and_visuals=[
            ScriptVisualRow(
                timestamp_or_beat="0-3s",
                spoken_line="Stop writing agents the hard way.",
                visual="Title card over IDE screenshot",
            )
        ],
        visual_notes="Steady pacing; large readable code overlays.",
        cta="Try LangGraph today.",
    )
    md = concept.to_markdown()
    assert "## Hook" in md
    assert "Stop writing agents" in md
    assert "## CTA" in md
