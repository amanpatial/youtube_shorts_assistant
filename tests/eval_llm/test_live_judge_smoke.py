"""Opt-in live LLM smoke (data plane). Skipped without credentials via conftest."""

from __future__ import annotations

import pytest
from tests.helpers import load_script_fixture

from shorts_assistant.judge import try_live_judge
from shorts_assistant.schemas import ScriptEvaluation


@pytest.mark.llm
def test_live_judge_returns_structured_evaluation():
    """Purpose: smoke that Gemini structured judge returns a valid ScriptEvaluation.

    Asserts schema/range only — never exact wording of summary or issues.
    """
    script = load_script_fixture("high_quality.json")
    result = try_live_judge(script, "LangGraph quality loop for Shorts")
    assert result is not None, "live judge returned None (check credentials / model)"
    assert isinstance(result, ScriptEvaluation)
    assert 0.0 <= result.overall_score <= 10.0
    assert 0.0 <= result.hook_score <= 10.0
    assert isinstance(result.summary, str) and result.summary.strip()
    assert isinstance(result.approved, bool)
