"""Tier a1 — pure preflight check for proposed changes.

Codex's 'Copilot's Copilot' primitive #2:

  > preflight_change({intent, proposed_files}) — returns where the
  > code should live, forbidden imports, tests likely affected,
  > files the agent should read first, whether the write scope is
  > too broad. Most agent mistakes happen before code is written.

Pure: no I/O beyond optional file-read for write_scope-too-broad
size hints. The classifier reads the proposed file paths only.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict


SCHEMA_VERSION_PREFLIGHT_V1 = "atomadic-forge.preflight/v1"


_TIER_NAMES = (
    "a0_qk_constants",
    "a1_at_functions",
    "a2_mo_composites",
    "a3_og_features",
    "a4_sy_orchestration",
)

# Per tier: the tier names this tier may NOT import (forbidden).
_FORBIDDEN_BY_TIER: dict[str, tuple[str, ...]] = {
    "a0_qk_constants": (
        "a0_qk_constants",         # may not import siblings either
        "a1_at_functions", "a2_mo_composites",
        "a3_og_features", "a4_sy_orchestration",
    ),
    "a1_at_functions": (
        "a2_mo_composites", "a3_og_features", "a4_sy_orchestration",
    ),
    "a2_mo_composites": ("a3_og_features", "a4_sy_orchestration"),
    "a3_og_features":   ("a4_sy_orchestration",),
    "a4_sy_orchestration": (),
}

_DEFAULT_SCOPE_TOO_BROAD = 8


class PreflightFile(TypedDict, total=False):
    path: str
    detected_tier: str | None
    forbidden_imports: list[str]
    likely_tests: list[str]
    siblings_to_read: list[str]
    notes: list[str]


class PreflightReport(TypedDict, total=False):
    schema_version: str
    intent: str
    project_root: str
    proposed_files: list[PreflightFile]
    write_scope_too_broad: bool
    write_scope_size: int
    write_scope_threshold: int
    overall_notes: list[str]
    suggested_validation_commands: list[str]


def _detect_tier(path: str) -> str | None:
    parts = Path(path).parts
    for p in parts:
        if p in _TIER_NAMES:
            return p
    return None


def _likely_tests_for(path: str) -> list[str]:
    """Mirror-style test path heuristic.

    src/pkg/a1_at_functions/foo.py -> tests/test_foo.py,
                                       tests/a1_at_functions/test_foo.py
    """
    p = Path(path)
    stem = p.stem
    if stem.startswith("test_") or stem.endswith("_test"):
        return [path]  # the file IS a test
    candidates: list[str] = []
    candidates.append(f"tests/test_{stem}.py")
    candidates.append(f"tests/{stem}_test.py")
    parent_tier = _detect_tier(path)
    if parent_tier:
        candidates.append(f"tests/{parent_tier}/test_{stem}.py")
    return candidates


def _siblings_to_read(path: str, *, project_root: Path) -> list[str]:
    """When the agent edits a file, sibling files in the same tier
    directory are the most likely places to share patterns or to
    accidentally diverge — read them first."""
    p = Path(path)
    if not p.parent.parts:
        return []
    sib_dir = project_root / p.parent
    if not sib_dir.is_dir():
        return []
    out: list[str] = []
    for sib in sorted(sib_dir.glob("*.py")):
        if sib.name == p.name:
            continue
        if sib.name.startswith("_"):
            continue
        out.append(str(sib.relative_to(project_root).as_posix()))
        if len(out) >= 5:
            break
    return out


def _file_preflight(
    path: str,
    *,
    project_root: Path,
) -> PreflightFile:
    notes: list[str] = []
    tier = _detect_tier(path)
    forbidden = list(_FORBIDDEN_BY_TIER.get(tier, ())) if tier else []
    likely_tests = _likely_tests_for(path)
    siblings = _siblings_to_read(path, project_root=project_root)
    if tier is None:
        notes.append(
            "no tier directory in this path — file likely belongs in "
            "a tier under src/<package>/aN_*/"
        )
    if Path(path).name == "__init__.py":
        notes.append(
            "__init__.py edits affect tier re-exports; run "
            "tier_init_rebuild after a structural change"
        )
    return PreflightFile(
        path=path,
        detected_tier=tier,
        forbidden_imports=forbidden,
        likely_tests=likely_tests,
        siblings_to_read=siblings,
        notes=notes,
    )


def preflight_change(
    *,
    intent: str,
    proposed_files: list[str],
    project_root: Path,
    scope_threshold: int = _DEFAULT_SCOPE_TOO_BROAD,
) -> PreflightReport:
    """Heuristic preflight for a proposed code change.

    Pure: takes paths + intent, walks the local filesystem only to
    check sibling presence. Does NOT read the proposed_files
    themselves — they may not exist yet.

    Codex-6: when [tool.forge.agent] is declared in the project's
    pyproject.toml, ``max_files_per_patch`` overrides the default
    threshold and ``protected_files`` adds per-file warnings.
    """
    from .policy_loader import file_is_protected, load_policy
    project_root = Path(project_root).resolve()
    policy = load_policy(project_root)
    if scope_threshold == _DEFAULT_SCOPE_TOO_BROAD and \
            isinstance(policy.get("max_files_per_patch"), int):
        scope_threshold = int(policy["max_files_per_patch"])
    files: list[PreflightFile] = [
        _file_preflight(p, project_root=project_root)
        for p in proposed_files
    ]
    for f in files:
        if file_is_protected(f["path"], policy):
            notes = list(f.get("notes") or [])
            notes.append(
                "policy: this file is in [tool.forge.agent] "
                "protected_files — agent should request human review"
            )
            f["notes"] = notes
    overall: list[str] = []
    protected_in_scope = [f["path"] for f in files
                           if any("protected_files" in n
                                  for n in f.get("notes", []))]
    if protected_in_scope:
        overall.append(
            f"{len(protected_in_scope)} protected file(s) in scope "
            f"(per [tool.forge.agent]): {protected_in_scope[:5]} — "
            "request human review before applying."
        )
    too_broad = len(proposed_files) > scope_threshold
    if too_broad:
        overall.append(
            f"write_scope has {len(proposed_files)} files (> "
            f"{scope_threshold} threshold). Consider splitting the "
            "change or asking for human review."
        )
    detected_tiers = {f.get("detected_tier") for f in files}
    detected_tiers.discard(None)
    if len(detected_tiers) > 1:
        overall.append(
            f"change spans {len(detected_tiers)} tiers "
            f"({sorted(detected_tiers)}); cross-tier edits should be "
            "split into per-tier patches when possible."
        )
    if any(f.get("path", "").startswith("tests/") for f in files) and \
            not any(not f.get("path", "").startswith("tests/") for f in files):
        overall.append(
            "test-only change — verify it pins existing behaviour and "
            "is not silently masking a regression."
        )
    return PreflightReport(
        schema_version=SCHEMA_VERSION_PREFLIGHT_V1,
        intent=intent,
        project_root=str(project_root),
        proposed_files=files,
        write_scope_too_broad=too_broad,
        write_scope_size=len(proposed_files),
        write_scope_threshold=scope_threshold,
        overall_notes=overall,
        suggested_validation_commands=[
            "forge wire src --fail-on-violations",
            "python -m pytest",
            "forge certify . --fail-under 75",
        ],
    )
