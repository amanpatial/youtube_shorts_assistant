"""Text → embedding vectors for memory retrieval (Phase 11).

CI/default: deterministic bag-of-hashes (no API). Optional live Gemini later.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence

_DIM = 64
_TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)


def embedding_dim() -> int:
    """Purpose: vector width used by the offline embedder."""
    return _DIM


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Purpose: embed one or more strings into unit L2 vectors.

    Offline path is deterministic so tests can assert top-k order without Gemini.
    """
    return [_embed_one(t) for t in texts]


def embed_query(text: str) -> list[float]:
    """Purpose: embed a single query/topic string."""
    return _embed_one(text)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Purpose: cosine similarity; 0.0 if either vector is empty/zero."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _embed_one(text: str) -> list[float]:
    vec = [0.0] * _DIM
    tokens = _TOKEN_RE.findall((text or "").lower())
    if not tokens:
        tokens = ["empty"]
    for tok in tokens:
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        # Mix several bytes into buckets for a denser signature.
        for i in range(0, 16, 2):
            idx = digest[i] % _DIM
            sign = 1.0 if digest[i + 1] % 2 == 0 else -1.0
            vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]
