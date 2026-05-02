"""Tier a1 — rollback_plan: reversible-move guidance (Codex #11).

Codex's prescription:

  > Agents need reversible moves. rollback_plan({changed_files})
  > returns: generated files to remove, caches to clean, docs to
  > restore, tests to rerun, risk of rollback.

Pure heuristic: classifies each changed file by extension + path
shape and returns a structured undo plan. The agent decides whether
to apply the moves; this is advisory.
"""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict

SCHEMA_VERSION_ROLLBACK_V1 = "atomadic-forge.rollback/v1"


_GENERATED_DIRS = (
    "build", "dist", ".pytest_cache", "__pycache__",
    "node_modules", ".turbo", ".next", ".nuxt",
    ".atomadic-forge",
)
_CACHE_DIRS = (
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", ".coverage",
)
_DOCS_DIRS = ("docs", "doc", "documentation")
_RELEASE_FILES = (
    "pyproject.toml", "setup.py", "setup.cfg", "package.json",
    "Cargo.toml", "CHANGELOG.md", "VERSION",
)


class RollbackPlan(TypedDict, total=False):
    schema_version: str
    changed_files: list[str]
    files_to_remove: list[str]
    caches_to_clean: list[str]
    docs_to_restore: list[str]
    tests_to_rerun: list[str]
    risk_level: str
    notes: list[str]
    suggested_commands: list[str]


def _is_generated(path: str) -> bool:
    return any(seg in _GENERATED_DIRS for seg in path.split("/"))


def _is_cache(path: str) -> bool:
    return any(seg in _CACHE_DIRS for seg in path.split("/"))


def _is_docs(path: str) -> bool:
    return any(seg in _DOCS_DIRS for seg in path.split("/"))


def _is_release(path: str) -> bool:
    return Path(path).name in _RELEASE_FILES


def rollback_plan(
    *,
    changed_files: list[str],
    project_root: Path,
) -> RollbackPlan:
    """Build a structured rollback plan for ``changed_files``.

    Pure: walks paths only. Returns the categories the agent should
    consider when undoing the change, with shell sketches.
    """
    files_to_remove: list[str] = []
    caches: list[str] = []
    docs: list[str] = []
    tests: list[str] = []
    notes: list[str] = []
    has_release_change = False

    for f in changed_files:
        if _is_generated(f):
            files_to_remove.append(f)
        if _is_cache(f):
            caches.append(f)
        if _is_docs(f):
            docs.append(f)
        if "tests/" in f or "test/" in f or f.endswith("_test.py"):
            tests.append(f)
        if _is_release(f):
            has_release_change = True
            notes.append(
                f"{f} is a release-control file — reverting it must "
                "include a corresponding CHANGELOG note + version "
                "decrement decision."
            )

    # If there are non-generated, non-test, non-doc src changes, those
    # are the riskiest part of a rollback because they may have
    # downstream consumers.
    src_changes = [f for f in changed_files
                   if not _is_generated(f) and not _is_cache(f)
                   and not _is_docs(f)
                   and "tests/" not in f and "test/" not in f]
    if has_release_change:
        risk = "high"
    elif len(src_changes) > 5:
        risk = "high"
        notes.append(
            f"{len(src_changes)} src files in scope — bulk rollback is "
            "high-risk; prefer per-card reverts via plan-step rollbacks."
        )
    elif len(src_changes) > 0:
        risk = "medium"
    else:
        risk = "low"

    if not tests and src_changes:
        tests = ["python -m pytest"]
        notes.append(
            "no test files in scope but src changed — re-run the full "
            "suite to confirm the rollback didn't break a covered path."
        )

    suggested: list[str] = []
    if files_to_remove:
        suggested.append("rm -rf " + " ".join(sorted(set(files_to_remove))))
    if caches:
        suggested.append(
            "find . -type d -name __pycache__ -exec rm -rf {} +")
    suggested.append("git restore " + " ".join(src_changes)
                      if src_changes else "git status")
    if tests:
        suggested.append("python -m pytest")

    return RollbackPlan(
        schema_version=SCHEMA_VERSION_ROLLBACK_V1,
        changed_files=list(changed_files),
        files_to_remove=sorted(set(files_to_remove)),
        caches_to_clean=sorted(set(caches)),
        docs_to_restore=sorted(set(docs)),
        tests_to_rerun=sorted(set(tests)),
        risk_level=risk,
        notes=notes,
        suggested_commands=suggested,
    )
