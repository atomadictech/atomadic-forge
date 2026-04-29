"""Tier a0 — types for the Emergent Behaviors Scan.

Emergent Scan reads the existing tier-organized catalog and synthesizes
*new* features by composing components that nobody wired together yet.

Pipeline:

  symbols → signatures (a1) → composition graph (a1) → candidates (a1)
                                                         ↓
                                       optional synthesis (a1) → a3 feature

These TypedDicts are the wire format between those steps.  No logic here.
"""

from __future__ import annotations

from typing import Literal, TypedDict

Tier = Literal[
    "a0_qk_constants",
    "a1_at_functions",
    "a2_mo_composites",
    "a3_og_features",
    "a4_sy_orchestration",
]


class SymbolSignatureCard(TypedDict):
    """One callable's typed surface, tier, and domain tag."""

    name: str                     # bare function/class name (e.g. ``infer_tier``)
    qualname: str                 # module-qualified (e.g. ``atomadic_forge.a1_at_functions.foo.bar``)
    module: str                   # importable module path
    tier: str                     # one of Tier
    domain: str                   # heuristic group (``kg``, ``swarm``, ``cherry`` …)
    inputs: list[tuple[str, str]] # [(param_name, type_annotation_text), …]
    output: str                   # return annotation text (or "Any")
    is_pure: bool                 # heuristic: no obvious I/O / mutable state
    docstring: str                # one-line


class CompositionChain(TypedDict):
    """An ordered chain of symbols where each output feeds the next."""

    chain: list[str]              # qualnames in execution order
    bridges: list[str]            # type-text describing each consumed-output edge
    tiers: list[str]              # tier of each step
    domains: list[str]            # domain tag of each step
    crosses_domains: int          # number of distinct domains involved
    crosses_tiers: int            # number of distinct tiers involved
    final_output_type: str
    pure: bool                    # all steps inferred pure


class EmergentCandidateCard(TypedDict):
    """A scored synthesis candidate ready for review or materialisation."""

    candidate_id: str             # short hash identifier
    name: str                     # heuristic kebab-case name
    summary: str                  # 1-line description
    chain: CompositionChain
    score: float                  # 0..100
    score_breakdown: dict[str, float]
    suggested_tier: str
    novelty_signals: list[str]    # why this is "emergent"


class EmergentScanReport(TypedDict):
    """Top-level wire format produced by ``atomadic-forge emergent scan --json``."""

    schema_version: str           # "atomadic-forge.emergent.scan/v1"
    generated_at_utc: str
    catalog_size: int
    chain_count_considered: int
    candidates: list[EmergentCandidateCard]
    domain_inventory: dict[str, int]
    tier_inventory: dict[str, int]
