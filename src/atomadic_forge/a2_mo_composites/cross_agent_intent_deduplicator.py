"""Tier a2 - cross-agent intent deduplicator.

Holds a bounded sliding window of recent agent intents and rejects
new proposals that are too similar to any prior entry. Composes on
a1 intent_similarity for scoring. PREVENT pillar - stops multiple
agents on a shared working tree from emitting redundant work.
"""

from __future__ import annotations

from collections import deque
from itertools import count

from atomadic_forge.a1_at_functions import intent_similarity


class CrossAgentIntentDeduplicator:
    """Sliding-window deduplicator for cross-agent intents.

    On each propose() call, score the incoming intent against every
    entry currently in the window. If any prior entry meets or
    exceeds the threshold, return DUPLICATE; otherwise ACCEPT and
    append.
    """

    def __init__(self, *, max_window: int = 64,
                  threshold: float = 0.78) -> None:
        if max_window <= 0:
            raise ValueError("max_window must be positive")
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be in [0.0, 1.0]")
        self._max_window = max_window
        self._threshold = threshold
        self._window: deque[dict] = deque(maxlen=max_window)
        self._ids = count(1)

    def propose(self, agent_id: str, intent: str) -> dict:
        """Score intent against the window; ACCEPT or DUPLICATE."""
        best_score = -1.0
        best_entry = None
        for entry in self._window:
            r = intent_similarity.similarity(intent, entry["intent"])
            score = float(r.score)
            if score > best_score:
                best_score = score
                best_entry = entry
        if best_entry is not None and best_score >= self._threshold:
            return {
                "verdict":         "DUPLICATE",
                "matched_agent":   best_entry["agent_id"],
                "matched_intent":  best_entry["intent"],
                "similarity":      best_score,
            }
        intent_id = next(self._ids)
        self._window.append({
            "intent_id": intent_id,
            "agent_id":  agent_id,
            "intent":    intent,
        })
        return {"verdict": "ACCEPT", "intent_id": intent_id}

    def recent(self) -> list[dict]:
        """Window contents in insertion order; copies, not refs."""
        return [dict(entry) for entry in self._window]

    def clear(self) -> None:
        """Reset window and id counter."""
        self._window.clear()
        self._ids = count(1)
