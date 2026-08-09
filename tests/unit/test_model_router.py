"""Unit tests for Phase 14 ModelRouter."""

from __future__ import annotations

from shorts_assistant.config import Settings
from shorts_assistant.models import ModelRouter, TaskType, get_router
from shorts_assistant.models.registry import task_model_map


def _settings(**fields) -> Settings:
    return Settings(_env_file=None, **fields)


def test_default_parity_all_tasks_use_model_name():
    s = _settings(model_name="gemini-2.0-flash-001")
    router = ModelRouter(s)
    for task in TaskType:
        d = router.resolve(task)
        assert d.model == "gemini-2.0-flash-001"
        assert d.fallbacks == []
        assert d.task == task.value
        assert d.reason


def test_override_write_only():
    s = _settings(
        model_name="gemini-2.0-flash-001",
        model_write="gemini-2.5-pro",
    )
    router = ModelRouter(s)
    assert router.resolve("write").model == "gemini-2.5-pro"
    assert router.resolve("evaluate").model == "gemini-2.0-flash-001"
    assert router.resolve("research").model == "gemini-2.0-flash-001"


def test_fallback_list_excludes_primary_duplicate():
    s = _settings(
        model_name="gemini-2.0-flash-001",
        model_evaluate="gemini-2.5-pro",
        model_fallback="gemini-2.0-flash-001",
    )
    d = ModelRouter(s).resolve("evaluate")
    assert d.model == "gemini-2.5-pro"
    assert d.fallbacks == ["gemini-2.0-flash-001"]
    assert d.candidates() == ["gemini-2.5-pro", "gemini-2.0-flash-001"]


def test_next_after_failure():
    s = _settings(
        model_name="flash",
        model_evaluate="pro",
        model_fallback="flash",
    )
    router = ModelRouter(s)
    d = router.resolve("evaluate")
    assert router.next_after_failure(d, failed_models=set()) == "pro"
    assert router.next_after_failure(d, failed_models={"pro"}) == "flash"
    assert router.next_after_failure(d, failed_models={"pro", "flash"}) is None


def test_task_model_map_and_get_router():
    s = _settings(model_name="gemini-2.0-flash-001", model_write="writer-x")
    assert task_model_map(s)["write"] == "writer-x"
    assert task_model_map(s)["format"] == "gemini-2.0-flash-001"
    assert get_router(s).resolve(TaskType.WRITE).model == "writer-x"
