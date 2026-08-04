"""AI-as-judge: produce a ScriptEvaluation without mutating the script.

Purpose: score a ShortScript (synthetic rubric for CI; optional live Gemini).
Always pair with ``evaluation_checks.merge_evaluation`` before writing state.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .config import settings
from .demo_producers import REJECT_MARKER, RETRY_PASS_MARKER
from .evaluation_checks import deterministic_checks, merge_evaluation
from .schemas import ScriptEvaluation, ShortScript
from .util import load_instruction_from_file

logger = logging.getLogger(__name__)
_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def synthetic_judge(
    script: ShortScript,
    request: str,
    *,
    research: str | None = None,
) -> ScriptEvaluation:
    """Purpose: offline rubric-ish scores from script heuristics (no API).

    Honors ``REJECT_MARKER`` in ``request`` for fail-closed smoke tests.
    """
    if REJECT_MARKER in request:
        return ScriptEvaluation(
            overall_score=3.5,
            hook_score=3.0,
            clarity_score=4.0,
            pacing_score=4.0,
            technical_accuracy=4.0,
            factual_correctness=4.0,
            developer_value=3.0,
            duration_score=5.0,
            cta_score=3.0,
            tone_score=4.0,
            issues=["Reject marker present in request"],
            approved=False,
            summary="Synthetic judge rejected request for fail-closed testing.",
        )

    if RETRY_PASS_MARKER in request:
        revised = "Addressed feedback" in script.body
        if revised:
            return ScriptEvaluation(
                overall_score=8.5,
                hook_score=8.5,
                clarity_score=8.5,
                pacing_score=8.0,
                technical_accuracy=8.0,
                factual_correctness=8.0,
                developer_value=8.5,
                duration_score=9.0,
                cta_score=8.5,
                tone_score=8.5,
                issues=[],
                approved=True,
                summary="Synthetic judge approved revised script after retry.",
            )
        return ScriptEvaluation(
            overall_score=5.0,
            hook_score=5.0,
            clarity_score=5.0,
            pacing_score=5.0,
            technical_accuracy=5.0,
            factual_correctness=5.0,
            developer_value=5.0,
            duration_score=6.0,
            cta_score=5.0,
            tone_score=5.0,
            issues=["Needs a revision pass addressing prior feedback"],
            approved=False,
            summary="Synthetic judge requires retry before approval.",
        )

    hook_len = len(script.hook.strip())
    cta_len = len(script.cta.strip())
    body_len = len(script.body.strip())

    hook_score = 9.0 if hook_len >= 24 else 7.0 if hook_len >= 12 else 4.0
    cta_score = 9.0 if cta_len >= 24 else 7.0 if cta_len >= 12 else 4.0
    clarity_score = 9.0 if body_len >= 80 else 7.0 if body_len >= 40 else 4.0
    duration_score = (
        9.0
        if 20 <= script.estimated_duration_seconds <= 55
        else 6.0
    )
    developer_value = 8.5 if research else 7.5
    technical_accuracy = 8.0
    factual_correctness = 7.5
    pacing_score = 8.0
    tone_score = 8.5

    scores = [
        hook_score,
        clarity_score,
        pacing_score,
        technical_accuracy,
        factual_correctness,
        developer_value,
        duration_score,
        cta_score,
        tone_score,
    ]
    overall = round(sum(scores) / len(scores), 1)
    approved = overall >= 7.0 and hook_score >= 6.0 and cta_score >= 6.0

    return ScriptEvaluation(
        overall_score=overall,
        hook_score=hook_score,
        clarity_score=clarity_score,
        pacing_score=pacing_score,
        technical_accuracy=technical_accuracy,
        factual_correctness=factual_correctness,
        developer_value=developer_value,
        duration_score=duration_score,
        cta_score=cta_score,
        tone_score=tone_score,
        issues=[] if approved else ["Synthetic judge: scores below approval bar"],
        approved=approved,
        summary=f"Synthetic rubric judgment for: {script.title}",
    )


def try_live_judge(
    script: ShortScript,
    request: str,
    *,
    research: str | None = None,
    sleep=None,
) -> ScriptEvaluation | None:
    """Purpose: optional Gemini structured-output judge; None if unavailable.

    Uses Phase 6 ``call_with_policy`` (timeout + TRANSIENT retries). On exhaustion
    or permanent failure: return ``None`` when ``LIVE_JUDGE_FALLBACK`` is true so
    ``judge_script`` can use ``synthetic_judge``; otherwise re-raise.
    """
    from .failures import (
        RetriesExhaustedError,
        call_with_policy,
        classify_exception,
        llm_retry_policy_from_settings,
    )
    from .state import FailureClass

    try:
        settings.validate_for_runtime()
    except ValueError:
        return None

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        logger.warning("langchain_google_genai not available; using synthetic judge")
        return None

    instruction = load_instruction_from_file(
        "evaluator.txt",
        default_instruction="Judge the ShortScript only. Do not rewrite it.",
        base_dir=_PROMPTS_DIR,
    )
    research_block = research or "(none)"
    user_payload = (
        f"{instruction}\n\n"
        f"## User idea\n{request}\n\n"
        f"## Research\n{research_block}\n\n"
        f"## Script JSON\n{script.model_dump_json(indent=2)}\n"
    )

    def _invoke() -> ScriptEvaluation:
        llm = ChatGoogleGenerativeAI(
            model=settings.model_name,
            google_api_key=settings.google_api_key or None,
        )
        structured = llm.with_structured_output(ScriptEvaluation)
        result = structured.invoke(user_payload)
        if isinstance(result, ScriptEvaluation):
            return result
        return ScriptEvaluation.model_validate(result)

    policy = llm_retry_policy_from_settings(settings)
    kwargs: dict = {"policy": policy}
    if sleep is not None:
        kwargs["sleep"] = sleep

    try:
        return call_with_policy(_invoke, **kwargs)
    except RetriesExhaustedError as exc:
        if settings.live_judge_fallback:
            logger.warning(
                "Live judge retries exhausted (%s); using synthetic judge", exc
            )
            return None
        raise
    except Exception as exc:  # noqa: BLE001 — classify then fallback or propagate
        failure_class = classify_exception(exc)
        if settings.live_judge_fallback and failure_class != FailureClass.QUALITY:
            logger.warning(
                "Live judge failed class=%s (%s); using synthetic judge",
                failure_class.value,
                exc,
            )
            return None
        raise


def judge_script(
    script: ShortScript,
    request: str,
    *,
    research: str | None = None,
    prefer_live: bool = False,
) -> ScriptEvaluation:
    """Purpose: produce a merged ScriptEvaluation (judgment + deterministic checks).

    Never mutates ``script``. Live Gemini only when ``prefer_live`` and credentials ok.
    """
    judgment: ScriptEvaluation | None = None
    if prefer_live:
        judgment = try_live_judge(script, request, research=research)
    if judgment is None:
        judgment = synthetic_judge(script, request, research=research)
    return merge_evaluation(judgment, deterministic_checks(script))
