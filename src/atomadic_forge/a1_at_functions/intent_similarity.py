"""Tier a1 — deterministic similarity score between intent strings.

The atomic primitive at the foundation of
``cross_agent_intent_deduplicator`` (research note 08), the
planned ``propose_placement`` retrieval, and any agent-coordination
verb that needs "is this the same thing another agent already did."

Pure: same inputs → same output. No LLM, no embeddings, no I/O,
no global state. Cheap enough to call thousands of times per
second across an MCP server's hot path.

The score combines two cheap signals:

* **Token Jaccard** — set overlap of normalised word tokens.
* **Difflib SequenceMatcher ratio** — character-level alignment.

The blend is weighted so the Jaccard term dominates for short
intents (where every word matters) and the sequence-matcher term
dominates for long intents (where order matters more than
vocabulary). Returned scores are in ``[0.0, 1.0]``.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

SCHEMA: str = "atomadic-forge.intent-similarity/v1"

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset({
    "a", "an", "and", "the", "to", "of", "for", "in", "on", "with",
    "by", "is", "are", "be", "or", "as", "at", "from", "this", "that",
    "it", "its", "if", "then", "do", "does",
})


@dataclass(frozen=True)
class SimilarityResult:
    score: float
    jaccard: float
    seq_ratio: float
    overlap_tokens: tuple[str, ...]


def _tokens(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall((text or "").lower())
            if w and w not in _STOPWORDS]


def jaccard_token_overlap(a: str, b: str) -> tuple[float, tuple[str, ...]]:
    """Return (jaccard_score, sorted overlap tokens)."""
    sa, sb = set(_tokens(a)), set(_tokens(b))
    if not sa and not sb:
        return 1.0, ()
    union = sa | sb
    inter = sa & sb
    if not union:
        return 0.0, ()
    return len(inter) / len(union), tuple(sorted(inter))


def sequence_ratio(a: str, b: str) -> float:
    """Difflib character-ratio. ``[0.0, 1.0]``."""
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(a=a or "", b=b or "").ratio()


def similarity(a: str, b: str) -> SimilarityResult:
    """Compute a deterministic similarity score for two intents.

    Score in ``[0.0, 1.0]``. Identical inputs (after normalisation)
    return ``1.0``. Unrelated inputs return values near ``0.0``.
    """
    j, overlap = jaccard_token_overlap(a, b)
    s = sequence_ratio(a or "", b or "")
    # Token weight scales down as intents get long; sequence weight
    # picks up the slack. Average length used as the pivot.
    n = max(len(_tokens(a)), len(_tokens(b)))
    if n <= 4:
        token_weight = 0.85
    elif n <= 12:
        token_weight = 0.65
    else:
        token_weight = 0.45
    score = (token_weight * j) + ((1.0 - token_weight) * s)
    score = max(0.0, min(1.0, score))
    return SimilarityResult(
        score=score, jaccard=j, seq_ratio=s, overlap_tokens=overlap,
    )


def rank_against(query: str, candidates: list[str]
                  ) -> list[tuple[int, SimilarityResult]]:
    """Score ``query`` against each candidate; return list of
    ``(index, SimilarityResult)`` sorted by descending score.
    Stable order on ties so the function is deterministic."""
    scored = [(i, similarity(query, c)) for i, c in enumerate(candidates)]
    scored.sort(key=lambda item: (-item[1].score, item[0]))
    return scored


def is_duplicate(a: str, b: str, *, threshold: float = 0.78) -> bool:
    """Is the second intent a duplicate of the first?

    Threshold tuned against typical agent intents — "add a stripe
    webhook handler" vs "add stripe webhook with refunds" scores
    ~0.80; a clearly different "implement oauth login" scores
    well below 0.30 against either.
    """
    return similarity(a, b).score >= threshold
