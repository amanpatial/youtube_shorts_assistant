"""Tests for structured contracts and fail-closed gates (no live LLM)."""

import pytest
from pydantic import ValidationError

from shorts_assistant.contracts import (
    ContractValidationError,
    guard_script,
    parse_contract,
    ready_for_visuals,
)
from shorts_assistant.demo_producers import demo_script
from shorts_assistant.schemas import (
    ScriptEvaluation,
    ScriptSection,
    ShortScript,
    VisualPlan,
    VisualShot,
)


def _valid_script() -> ShortScript:
    return demo_script("How to use LangGraph state")


def test_valid_short_script_parse():
    script = _valid_script()
    parsed = parse_contract(ShortScript, script.model_dump(), agent="test")
    assert parsed.title
    assert len(parsed.sections) >= 3


def test_valid_visual_plan_and_evaluation():
    plan = VisualPlan(
        shots=[
            VisualShot(
                beat="hook",
                description="Title",
                shot_type="title_card",
            ),
            VisualShot(
                beat="body",
                description="Demo",
                shot_type="screen_recording",
            ),
            VisualShot(
                beat="cta",
                description="Overlay",
                shot_type="code_overlay",
            ),
        ],
        pacing="fast",
    )
    assert len(plan.shots) == 3
    evaluation = ScriptEvaluation(
        overall_score=8.0,
        hook_score=8.0,
        clarity_score=8.0,
        pacing_score=8.0,
        technical_accuracy=8.0,
        factual_correctness=8.0,
        developer_value=8.0,
        duration_score=8.0,
        cta_score=8.0,
        tone_score=8.0,
        approved=True,
    )
    assert ready_for_visuals(evaluation)


def test_malformed_script_missing_sections():
    with pytest.raises(ContractValidationError):
        parse_contract(
            ShortScript,
            {
                "title": "x",
                "hook": "h",
                "body": "b",
                "cta": "c",
                "estimated_duration_seconds": 30,
                "sections": [],
            },
            agent="scriptwriter",
        )


def test_score_eleven_rejected():
    with pytest.raises(ValidationError):
        ScriptEvaluation(
            overall_score=11,
            hook_score=8,
            clarity_score=8,
            pacing_score=8,
            technical_accuracy=8,
            factual_correctness=8,
            developer_value=8,
            duration_score=8,
            cta_score=8,
            tone_score=8,
            approved=True,
        )


def test_duration_too_long_rejected():
    with pytest.raises(ValidationError):
        ShortScript(
            title="x",
            hook="h",
            body="b",
            cta="c",
            estimated_duration_seconds=120,
            sections=[
                ScriptSection(label="hook", text="h", estimated_seconds=3),
                ScriptSection(label="body", text="b", estimated_seconds=30),
                ScriptSection(label="cta", text="c", estimated_seconds=5),
            ],
        )


def test_guard_script_requires_value():
    with pytest.raises(ContractValidationError, match="required"):
        guard_script(None)


def test_approved_false_not_ready_for_visuals():
    evaluation = ScriptEvaluation(
        overall_score=4.0,
        hook_score=4.0,
        clarity_score=4.0,
        pacing_score=4.0,
        technical_accuracy=4.0,
        factual_correctness=4.0,
        developer_value=4.0,
        duration_score=4.0,
        cta_score=4.0,
        tone_score=4.0,
        approved=False,
        issues=["weak hook"],
    )
    assert ready_for_visuals(evaluation) is False
    assert ready_for_visuals(None) is False
