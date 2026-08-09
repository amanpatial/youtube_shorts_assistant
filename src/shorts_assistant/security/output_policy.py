"""Simple unsafe-content heuristics for publishable Shorts (Phase 17)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..config import settings

# Narrow blocklist — developer Shorts learning aid, not a full moderation stack.
_BLOCKED = (
    re.compile(r"(?i)\bhow\s+to\s+make\s+a\s+bomb\b"),
    re.compile(r"(?i)\bchild\s+sexual\b"),
    re.compile(r"(?i)\bcredit\s+card\s+number\s*[:=]\s*\d"),
    re.compile(r"(?i)\bkill\s+yourself\b"),
    re.compile(r"(?i)\[UNSAFE_CONTENT_FIXTURE\]"),  # deterministic tests
)


@dataclass
class OutputPolicyResult:
    allowed: bool
    reasons: list[str] = field(default_factory=list)


def _text_blob(script_or_concept: Any) -> str:
    if script_or_concept is None:
        return ""
    if isinstance(script_or_concept, str):
        return script_or_concept
    if isinstance(script_or_concept, dict):
        parts: list[str] = []
        for key in ("title", "hook", "body", "cta", "script", "summary"):
            val = script_or_concept.get(key)
            if isinstance(val, str):
                parts.append(val)
        # nested final concept
        nested = script_or_concept.get("script")
        if isinstance(nested, dict):
            parts.append(_text_blob(nested))
        return "\n".join(parts)
    dump = getattr(script_or_concept, "model_dump", None)
    if callable(dump):
        return _text_blob(dump(mode="json"))
    return str(script_or_concept)


def check_output_policy(*parts: Any) -> OutputPolicyResult:
    """Purpose: reject clearly disallowed phrases in script/concept text."""
    if not settings.output_policy_enabled:
        return OutputPolicyResult(allowed=True)
    blob = "\n".join(_text_blob(p) for p in parts)
    reasons: list[str] = []
    for pat in _BLOCKED:
        if pat.search(blob):
            reasons.append(f"blocked_pattern:{pat.pattern}")
    return OutputPolicyResult(allowed=not reasons, reasons=reasons)
