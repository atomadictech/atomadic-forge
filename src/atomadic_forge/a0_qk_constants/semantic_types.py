"""Tier a0 — types for semantic conflict resolution.

When Forge absorbs from multiple repos and two symbols collide on name,
we extract an *intent signature* from each and compute a similarity score
to decide whether they're the same concept (merge), distinct flavours of
the same concept (rename with semantic suffix), or genuinely different
concepts (keep both, namespace by source module).

This is the structured wire format for that pipeline.
"""

from __future__ import annotations

from typing import Literal, TypedDict


MergeDecision = Literal["merge", "rename_semantic", "rename_module"]


class IntentSignature(TypedDict):
    """Cheap, deterministic proxies for a class's intent.

    None of these are "real" semantics — they're surface signals correlated
    with intent.  The decisive design choice: combine many weak signals,
    weighted, rather than rely on a single strong one.
    """

    name: str
    fields: list[str]              # ``self.<x> = …`` left-hand sides
    method_names: list[str]        # public methods only
    field_types: dict[str, str]    # field → annotation text (when present)
    doc_tokens: list[str]          # significant tokens from docstring
    verb_signature: list[str]      # method-name verb prefixes (get/set/save/post/…)
    sibling_imports: list[str]     # other names imported in the same file
    base_classes: list[str]        # superclasses
    file_path: str
    source_root: str               # which repo it came from


class SimilarityScore(TypedDict):
    """Weighted-Jaccard breakdown for an intent-signature comparison."""

    overall: float                 # 0.0 … 1.0
    fields: float
    method_names: float
    field_types: float
    doc_tokens: float
    verb_signature: float
    sibling_imports: float
    discriminating_tokens: list[str]  # doc tokens unique to one side


class ConflictResolution(TypedDict):
    """The outcome of resolving one (A, B) conflict."""

    name: str
    decision: MergeDecision
    score: float
    rationale: list[str]
    merged_signature: IntentSignature | None  # filled when decision == "merge"
    proposed_names: list[str]                  # 1 for merge, 2 for rename
    review_marker: str                         # "# REVIEW: …" line for the output
