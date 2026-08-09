"""Unit tests for Phase 15 A2A research contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from shorts_assistant.a2a_research.contracts import (
    ResearchRequest,
    ResearchResponse,
    response_to_research_text,
)
from shorts_assistant.a2a_research.service import produce_research


def test_research_request_requires_topic():
    with pytest.raises(ValidationError):
        ResearchRequest(topic="  ")


def test_research_response_bounds():
    with pytest.raises(ValidationError):
        ResearchResponse(topic="t", confidence=1.5)


def test_produce_and_flatten():
    req = ResearchRequest(topic="LangGraph loops", max_bullets=2)
    resp = produce_research(req)
    assert resp.status == "completed"
    assert resp.topic == "LangGraph loops"
    assert len(resp.bullets) <= 2
    text = response_to_research_text(resp)
    assert "LangGraph loops" in text
    assert "Bullets:" in text
