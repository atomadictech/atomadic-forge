"""Tier a0 — Forge-specific report shapes.

Wire formats for scout / cherry-pick / wire / certify / assimilate output.
"""

from __future__ import annotations

from typing import Literal, TypedDict


SymbolKind = Literal["function", "class", "method"]


class SymbolRecord(TypedDict):
    """One callable discovered in a target repo."""

    name: str
    qualname: str            # e.g. "Counter.incr"
    kind: SymbolKind
    file: str                # repo-relative path
    lineno: int
    tier_guess: str          # one of TIER_NAMES
    effects: list[str]       # ["pure"], ["io"], etc.
    complexity: int          # ast.dump length (cheap proxy)
    has_self_assign: bool


class ScoutReport(TypedDict):
    schema_version: str       # "atomadic-forge.scout/v1"
    repo: str
    file_count: int
    python_file_count: int
    symbol_count: int
    tier_distribution: dict[str, int]
    effect_distribution: dict[str, int]
    symbols: list[SymbolRecord]
    recommendations: list[str]


class CherryPickItem(TypedDict):
    qualname: str
    target_tier: str
    confidence: float
    reasons: list[str]


class CherryPickManifest(TypedDict):
    schema_version: str       # "atomadic-forge.cherry/v1"
    source_repo: str
    items: list[CherryPickItem]


class WireViolation(TypedDict):
    file: str
    from_tier: str
    to_tier: str
    imported: str
    proposed_fix: str         # rewritten import line, or "" if no fix found


class WireReport(TypedDict):
    schema_version: str       # "atomadic-forge.wire/v1"
    source_dir: str
    violation_count: int
    auto_fixable: int
    violations: list[WireViolation]
    verdict: Literal["PASS", "FAIL"]


class CertifyResult(TypedDict):
    schema_version: str       # "atomadic-forge.certify/v1"
    project: str
    timestamp: str
    documentation_complete: bool
    tests_present: bool
    tier_layout_present: bool
    no_upward_imports: bool
    score: float              # 0..100
    issues: list[str]
    recommendations: list[str]


class AssimilateReport(TypedDict):
    schema_version: str       # "atomadic-forge.assimilate/v1"
    target_root: str
    source_repos: list[str]
    components_emitted: int
    tier_distribution: dict[str, int]
    files_repaired: int
    digest: str
