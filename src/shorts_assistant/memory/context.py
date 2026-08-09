"""Format retrieved memories into a bounded context block for the scriptwriter."""

from __future__ import annotations

from .store import MemoryHit


def build_memory_context(
    hits: list[MemoryHit],
    *,
    max_chars: int = 1500,
    min_score: float | None = None,
) -> str:
    """Purpose: turn top-k hits into a short inspiration block (or empty string).

    Drops hits below ``min_score`` when set; truncates to ``max_chars``.
    """
    if not hits:
        return ""
    lines: list[str] = ["Past Shorts memory (inspire, do not copy verbatim):"]
    for hit in hits:
        if min_score is not None and hit.overall_score is not None:
            if hit.overall_score < min_score:
                continue
        score = f"{hit.overall_score:.1f}" if hit.overall_score is not None else "?"
        summary = (hit.summary or hit.text).strip().replace("\n", " ")
        lines.append(
            f"- [{hit.kind}] topic={hit.topic[:80]!r} score={score} "
            f"sim={hit.similarity:.2f}: {summary}"
        )
    if len(lines) == 1:
        return ""
    text = "\n".join(lines)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."
