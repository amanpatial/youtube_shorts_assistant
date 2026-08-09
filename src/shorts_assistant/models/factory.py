"""Build LangChain Gemini chat models from RouteDecision (Phase 14)."""

from __future__ import annotations

from typing import Any

from .router import RouteDecision, get_router
from .types import TaskType


def chat_model_for_task(
    task: TaskType | str,
    *,
    settings: Any | None = None,
    model_id: str | None = None,
) -> Any:
    """Purpose: construct ``ChatGoogleGenerativeAI`` for a routed task.

    ``model_id`` overrides the router primary (used for availability fallback).
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    if settings is None:
        from ..config import settings as default_settings

        settings = default_settings

    decision = get_router(settings).resolve(task)
    mid = model_id or decision.model
    return ChatGoogleGenerativeAI(
        model=mid,
        google_api_key=settings.google_api_key or None,
    )


def decision_for(
    task: TaskType | str,
    *,
    settings: Any | None = None,
) -> RouteDecision:
    """Purpose: resolve without constructing a client (tests / logging)."""
    return get_router(settings).resolve(task)
