"""Tier a0 — canonical tier names and effect lattice."""

from __future__ import annotations

from typing import Final


TIER_NAMES: Final[tuple[str, ...]] = (
    "a0_qk_constants",
    "a1_at_functions",
    "a2_mo_composites",
    "a3_og_features",
    "a4_sy_orchestration",
)

TIER_PREFIX: Final[dict[str, str]] = {
    "a0_qk_constants": "a0",
    "a1_at_functions": "a1",
    "a2_mo_composites": "a2",
    "a3_og_features": "a3",
    "a4_sy_orchestration": "a4",
}

# Effect lattice — what each tier is *allowed* to do.
EFFECT_LATTICE: Final[dict[str, frozenset[str]]] = {
    "a0_qk_constants": frozenset(),
    "a1_at_functions": frozenset({"pure"}),
    "a2_mo_composites": frozenset({"pure", "state"}),
    "a3_og_features": frozenset({"pure", "state", "orchestrate"}),
    "a4_sy_orchestration": frozenset({"pure", "state", "orchestrate", "io"}),
}


def tier_index(tier: str) -> int:
    """Return 0..4 for the tier name; raise ValueError if unknown."""
    try:
        return TIER_NAMES.index(tier)
    except ValueError as exc:
        raise ValueError(f"unknown tier: {tier!r}") from exc


def can_import(from_tier: str, to_tier: str) -> bool:
    """Return True if ``from_tier`` is allowed to import from ``to_tier``.

    Tiers compose **upward only**: a higher tier may import from any lower
    tier, never the reverse.
    """
    return tier_index(from_tier) >= tier_index(to_tier)
