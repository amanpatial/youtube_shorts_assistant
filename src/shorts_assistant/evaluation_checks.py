"""Deterministic script checks that complement the AI-as-judge.

Purpose: enforce invariants the LLM must not "opinion away" (duration sanity,
empty hook/CTA, required section labels). Merge hard-fails into ScriptEvaluation
so ``approved`` can be forced false before visuals run.
"""

from __future__ import annotations

from dataclasses import dataclass

from .schemas import ScriptEvaluation, ShortScript

MIN_HOOK_CHARS = 12
MIN_CTA_CHARS = 12
MIN_BODY_CHARS = 40


@dataclass(frozen=True)
class DeterministicIssue:
    """Purpose: one code-level problem found on a ShortScript (not LLM opinion)."""

    message: str
    hard_fail: bool = True


def deterministic_checks(script: ShortScript) -> list[DeterministicIssue]:
    """Purpose: run pure-Python invariant checks on a validated ShortScript.

    Returns issues (hard_fail=True means merge must set approved=False).
    """
    issues: list[DeterministicIssue] = []

    duration = script.estimated_duration_seconds
    if duration < 15 or duration > 60:
        issues.append(
            DeterministicIssue(
                f"estimated_duration_seconds={duration} outside 15–60",
                hard_fail=True,
            )
        )

    hook = script.hook.strip()
    body = script.body.strip()
    cta = script.cta.strip()
    if len(hook) < MIN_HOOK_CHARS:
        issues.append(
            DeterministicIssue(
                f"hook too short ({len(hook)} chars; need ≥{MIN_HOOK_CHARS})",
                hard_fail=True,
            )
        )
    if len(cta) < MIN_CTA_CHARS:
        issues.append(
            DeterministicIssue(
                f"cta too short ({len(cta)} chars; need ≥{MIN_CTA_CHARS})",
                hard_fail=True,
            )
        )
    if len(body) < MIN_BODY_CHARS:
        issues.append(
            DeterministicIssue(
                f"body too short ({len(body)} chars; need ≥{MIN_BODY_CHARS})",
                hard_fail=True,
            )
        )

    labels = {section.label for section in script.sections}
    for required in ("hook", "body", "cta"):
        if required not in labels:
            issues.append(
                DeterministicIssue(
                    f"sections missing required label '{required}'",
                    hard_fail=True,
                )
            )

    section_total = sum(s.estimated_seconds for s in script.sections)
    if section_total > 60:
        issues.append(
            DeterministicIssue(
                f"section estimated_seconds sum {section_total} exceeds 60s",
                hard_fail=True,
            )
        )

    return issues


def merge_evaluation(
    judgment: ScriptEvaluation,
    det_issues: list[DeterministicIssue],
) -> ScriptEvaluation:
    """Purpose: combine LLM/synthetic judgment with deterministic issues.

    Why it exists: hard-fail invariants always win — they append to ``issues``
    and force ``approved=False`` (and cap duration_score when duration failed).
    """
    data = judgment.model_dump()
    messages = list(data.get("issues") or [])
    hard = False
    duration_failed = False
    for issue in det_issues:
        if issue.message not in messages:
            messages.append(issue.message)
        if issue.hard_fail:
            hard = True
        if "duration" in issue.message.lower() or "15–60" in issue.message:
            duration_failed = True
    data["issues"] = messages
    if hard:
        data["approved"] = False
    if duration_failed:
        data["duration_score"] = min(float(data["duration_score"]), 3.0)
    return ScriptEvaluation.model_validate(data)
