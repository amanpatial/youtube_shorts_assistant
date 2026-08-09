"""Phase 6: failure classification, retry policy, fallback, node boundary."""

from __future__ import annotations

import pytest

from shorts_assistant.contracts import ContractValidationError
from shorts_assistant.demo_producers import demo_script
from shorts_assistant.failures import (
    RetriesExhaustedError,
    RetryPolicy,
    call_with_policy,
    classify_exception,
)
from shorts_assistant.graph import get_compiled_graph
from shorts_assistant.judge import try_live_judge
from shorts_assistant.schemas import ScriptEvaluation
from shorts_assistant.state import FailureClass, WorkflowState, WorkflowStatus


class _HttpError(Exception):
    def __init__(self, status_code: int, message: str = "http") -> None:
        super().__init__(message)
        self.status_code = status_code


def test_classify_timeout_transient():
    assert classify_exception(TimeoutError("slow")) == FailureClass.TRANSIENT


def test_classify_429_transient():
    assert classify_exception(_HttpError(429)) == FailureClass.TRANSIENT


def test_classify_5xx_transient():
    assert classify_exception(_HttpError(503)) == FailureClass.TRANSIENT


def test_classify_auth_permanent():
    assert classify_exception(_HttpError(401, "unauthorized")) == FailureClass.PERMANENT
    assert classify_exception(_HttpError(403)) == FailureClass.PERMANENT


def test_classify_contract_permanent():
    exc = ContractValidationError("evaluator", "generated_script is required")
    assert classify_exception(exc) == FailureClass.PERMANENT


def test_classify_unknown_programming():
    assert classify_exception(RuntimeError("boom")) == FailureClass.PROGRAMMING


def test_call_with_policy_succeeds_on_second_attempt():
    attempts = {"n": 0}

    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise TimeoutError("blip")
        return "ok"

    sleeps: list[float] = []
    result = call_with_policy(
        flaky,
        policy=RetryPolicy(max_attempts=3, timeout_seconds=5.0, backoff_base_seconds=0.1),
        sleep=sleeps.append,
    )
    assert result == "ok"
    assert attempts["n"] == 2
    assert sleeps == [0.1]


def test_call_with_policy_exhausts_transient():
    def always_timeout() -> str:
        raise TimeoutError("nope")

    sleeps: list[float] = []
    with pytest.raises(RetriesExhaustedError):
        call_with_policy(
            always_timeout,
            policy=RetryPolicy(
                max_attempts=3,
                timeout_seconds=5.0,
                backoff_base_seconds=0.5,
                backoff_max_seconds=8.0,
            ),
            sleep=sleeps.append,
        )
    assert sleeps == [0.5, 1.0]


def test_call_with_policy_permanent_single_attempt():
    attempts = {"n": 0}

    def auth_fail() -> str:
        attempts["n"] += 1
        raise _HttpError(401, "invalid api key")

    with pytest.raises(_HttpError):
        call_with_policy(
            auth_fail,
            policy=RetryPolicy(max_attempts=5, timeout_seconds=5.0),
            sleep=lambda _d: None,
        )
    assert attempts["n"] == 1


def _patch_live_settings(monkeypatch, judge_mod, *, max_attempts: int = 3) -> None:
    monkeypatch.setattr(judge_mod.settings, "google_api_key", "fake-key")
    monkeypatch.setattr(judge_mod.settings, "google_genai_use_vertexai", "FALSE")
    monkeypatch.setattr(judge_mod.settings, "live_judge_fallback", True)
    monkeypatch.setattr(judge_mod.settings, "llm_max_attempts", max_attempts)
    monkeypatch.setattr(judge_mod.settings, "llm_timeout_seconds", 5.0)
    monkeypatch.setattr(judge_mod.settings, "llm_backoff_base_seconds", 0.01)
    monkeypatch.setattr(judge_mod.settings, "llm_backoff_max_seconds", 1.0)


def test_live_judge_retries_then_success(monkeypatch):
    from shorts_assistant import judge as judge_mod

    _patch_live_settings(monkeypatch, judge_mod)
    attempts = {"n": 0}
    good = ScriptEvaluation(
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
        summary="live ok",
    )

    class _Structured:
        def invoke(self, _payload: str) -> ScriptEvaluation:
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise TimeoutError("blip")
            return good

    class _LLM:
        def with_structured_output(self, _model):
            return _Structured()

    monkeypatch.setattr(
        "langchain_google_genai.ChatGoogleGenerativeAI",
        lambda **_kwargs: _LLM(),
    )

    result = try_live_judge(demo_script("topic"), "topic", sleep=lambda _d: None)
    assert result is not None
    assert result.summary == "live ok"
    assert attempts["n"] == 2


def test_live_judge_exhausted_falls_back(monkeypatch):
    from shorts_assistant import judge as judge_mod

    _patch_live_settings(monkeypatch, judge_mod, max_attempts=2)

    class _Structured:
        def invoke(self, _payload: str) -> ScriptEvaluation:
            raise TimeoutError("always")

    class _LLM:
        def with_structured_output(self, _model):
            return _Structured()

    monkeypatch.setattr(
        "langchain_google_genai.ChatGoogleGenerativeAI",
        lambda **_kwargs: _LLM(),
    )

    assert try_live_judge(demo_script("topic"), "topic", sleep=lambda _d: None) is None


def test_live_judge_availability_fallback_model(monkeypatch):
    """Primary model permanently fails → try MODEL_FALLBACK once."""
    from shorts_assistant import judge as judge_mod

    _patch_live_settings(monkeypatch, judge_mod, max_attempts=1)
    monkeypatch.setattr(judge_mod.settings, "model_evaluate", "primary-model")
    monkeypatch.setattr(judge_mod.settings, "model_fallback", "fallback-model")
    monkeypatch.setattr(judge_mod.settings, "model_name", "fallback-model")

    seen: list[str] = []
    good = ScriptEvaluation(
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
        summary="fallback ok",
    )

    class _Structured:
        def __init__(self, model: str) -> None:
            self.model = model

        def invoke(self, _payload: str) -> ScriptEvaluation:
            seen.append(self.model)
            if self.model == "primary-model":
                raise _HttpError(401, "primary dead")
            return good

    class _LLM:
        def __init__(self, **kwargs) -> None:
            self.model = kwargs.get("model", "")

        def with_structured_output(self, _model):
            return _Structured(self.model)

    monkeypatch.setattr(
        "langchain_google_genai.ChatGoogleGenerativeAI",
        _LLM,
    )

    result = try_live_judge(demo_script("topic"), "topic", sleep=lambda _d: None)
    assert result is not None
    assert result.summary == "fallback ok"
    assert seen == ["primary-model", "fallback-model"]


def test_node_boundary_uncaught_maps_to_failed(monkeypatch):
    def boom(_request: str) -> str:
        raise RuntimeError("research exploded")

    monkeypatch.setattr("shorts_assistant.nodes.demo_research", boom)
    result = get_compiled_graph(with_checkpointer=False).invoke(
        WorkflowState.initial("boundary").to_dict()
    )
    final = WorkflowState.from_dict(result)
    assert final.status == WorkflowStatus.FAILED
    assert final.error_class == FailureClass.PROGRAMMING
    assert final.error_node == "research"
    assert "research" in (final.error or "")
