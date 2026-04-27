"""Tier a0 — types for the Synergy Scan.

Synergy Scan operates at the *feature / CLI verb* level (one level above
Emergent Scan, which operates on symbols).  It finds pairs of features
where one produces an artifact the other could consume — but no code path
wires them together yet.  Optionally it generates an adapter that does.

Wire format:

* :class:`FeatureSurfaceCard` — one feature/CLI verb's I/O surface.
* :class:`SynergyCandidateCard` — one (producer, consumer) pair with score.
* :class:`SynergyScanReport` — top-level scan output.
"""

from __future__ import annotations

from typing import Literal, TypedDict


SynergyKind = Literal[
    "json_artifact",        # producer emits --json-out, consumer takes file arg
    "in_memory_pipe",       # producer's return type matches consumer's first arg
    "shared_schema",        # both reference the same JSON schema name
    "shared_vocabulary",    # high lexical overlap in help/docstrings
    "phase_omission",       # natural phase chain skips a step
]


class FeatureSurfaceCard(TypedDict):
    """One feature/CLI verb's input + output surface."""

    name: str                   # CLI verb (e.g. "scout", "assimilate")
    module: str                 # importable module path
    help_text: str
    inputs: list[str]           # canonical arg names (e.g. ["repo", "policy"])
    input_files: list[str]      # filename patterns it accepts
    outputs: list[str]          # canonical product names (e.g. ["scout-report"])
    output_files: list[str]     # filename patterns it emits (e.g. ["*.json"])
    schemas: list[str]          # schema names mentioned in help/docstring
    vocabulary: list[str]       # unique tokens harvested from help+args
    phase_hint: str             # heuristic phase tag (recon/ingest/.../emit)


class SynergyCandidateCard(TypedDict):
    """One detected synergy between two features."""

    candidate_id: str
    producer: str               # feature name
    consumer: str               # feature name
    kind: SynergyKind
    why: list[str]              # human-readable signals supporting this synergy
    score: float                # 0..100
    score_breakdown: dict[str, float]
    proposed_adapter_name: str  # kebab-case CLI verb for the auto-wired pair
    proposed_summary: str


class SynergyScanReport(TypedDict):
    schema_version: str         # "atomadic-forge.synergy.scan/v1"
    generated_at_utc: str
    feature_count: int
    candidate_count: int
    candidates: list[SynergyCandidateCard]
