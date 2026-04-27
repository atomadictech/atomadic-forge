"""Tier a1 — pure cherry-picker.

Given a scout report and a selection (names or 'all'), produce a manifest
that downstream assimilate consumes.  Conflict resolution is deferred to
the assimilate phase; this layer just records intent.
"""

from __future__ import annotations

from typing import Iterable


def select_items(scout_report: dict, *, names: Iterable[str] | None = None,
                 pick_all: bool = False, min_confidence: float = 0.0,
                 only_tier: str | None = None) -> dict:
    """Build a cherry_pick manifest from a scout report.

    Filters:
      * ``names`` — explicit qualnames.  None ⇒ apply other filters.
      * ``pick_all`` — take every symbol that passes the other filters.
      * ``min_confidence`` — drop symbols with low classification confidence.
        (Forge currently emits 0.0 for hard hits and 0.5 for fallbacks; future
        versions will produce richer signals.)
      * ``only_tier`` — restrict to symbols already classified to this tier.
    """
    syms = scout_report.get("symbols", [])
    wanted = set(names) if names else None
    items: list[dict] = []
    for s in syms:
        if wanted is not None and s["qualname"] not in wanted and s["name"] not in wanted:
            continue
        if not pick_all and wanted is None:
            continue
        if only_tier and s["tier_guess"] != only_tier:
            continue
        items.append({
            "qualname": s["qualname"],
            "target_tier": s["tier_guess"],
            "confidence": _confidence_of(s),
            "reasons": _reasons_for(s),
        })
    return {
        "schema_version": "atomadic-forge.cherry/v1",
        "source_repo": scout_report.get("repo", ""),
        "items": items,
    }


def _confidence_of(symbol: dict) -> float:
    # High confidence when name tokens drove the decision; lower when we fell
    # back to the kind-default (function→a1, class→a2).  Cheap proxy: complexity
    # below 800 ⇒ small hand-shaped helper, easy to reason about.
    base = 0.7 if symbol["complexity"] < 800 else 0.6
    if symbol["has_self_assign"]:
        base += 0.1
    if symbol["effects"] == ["pure"]:
        base += 0.05
    return min(0.95, round(base, 2))


def _reasons_for(symbol: dict) -> list[str]:
    out: list[str] = []
    if symbol["has_self_assign"]:
        out.append("class with mutable instance state ⇒ a2 promotion")
    if symbol["effects"] == ["pure"]:
        out.append("no detected I/O or state — clean composition target")
    if "io" in symbol["effects"]:
        out.append("I/O-heavy — needs sandboxing on absorb")
    if not out:
        out.append("standard tier-classification fit")
    return out
