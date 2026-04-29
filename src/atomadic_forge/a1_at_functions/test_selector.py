"""Tier a1 — select_tests: per-intent test selection (Codex #7).

Codex's prescription:

  > Agents over-run tests or under-run them. Add select_tests({
  >   changed_files, intent }). Returns minimum test set, full-
  >   confidence test set, commands, why those tests matter.

Pure: takes paths + intent, walks tests/ to match by name + path
heuristics. The 'minimum' set is the mirror-style direct match
(tests/test_<stem>.py); the 'full' set adds tier-mate tests + any
tests under the proposed file's tier.
"""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict


SCHEMA_VERSION_TEST_SELECT_V1 = "atomadic-forge.test_select/v1"

_TIER_NAMES = (
    "a0_qk_constants", "a1_at_functions", "a2_mo_composites",
    "a3_og_features", "a4_sy_orchestration",
)


class TestSelection(TypedDict, total=False):
    schema_version: str
    intent: str
    changed_files: list[str]
    minimum_tests: list[str]
    full_tests: list[str]
    minimum_command: str
    full_command: str
    rationale: list[str]


def _detect_tier(path: str) -> str | None:
    for part in path.split("/"):
        if part in _TIER_NAMES:
            return part
    return None


def _list_tests(project_root: Path) -> list[str]:
    candidates: list[str] = []
    for sub in ("tests", "test"):
        d = project_root / sub
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("test_*.py")):
            candidates.append(str(f.relative_to(project_root).as_posix()))
        for f in sorted(d.rglob("*_test.py")):
            candidates.append(str(f.relative_to(project_root).as_posix()))
    return sorted(set(candidates))


def select_tests(
    *,
    intent: str,
    changed_files: list[str],
    project_root: Path,
) -> TestSelection:
    """Compute minimum + full test sets for a proposed change."""
    project_root = Path(project_root).resolve()
    all_tests = _list_tests(project_root)
    minimum: set[str] = set()
    full: set[str] = set()
    rationale: list[str] = []

    for path in changed_files:
        stem = Path(path).stem
        tier = _detect_tier(path)
        # Direct mirror match
        for t in all_tests:
            tname = Path(t).stem
            if tname in (f"test_{stem}", f"{stem}_test"):
                minimum.add(t)
                full.add(t)
        # Tier-mate matches
        if tier:
            for t in all_tests:
                if f"/{tier}/" in t or t.endswith(f"/{tier}"):
                    full.add(t)
        # Any test mentioning the stem in its filename gets full.
        for t in all_tests:
            if stem and stem in Path(t).stem and stem != Path(t).stem:
                full.add(t)
    if not minimum and all_tests:
        # No mirror match — the safe minimum is full + a clear note.
        rationale.append(
            "no mirror-name test match for any changed file; "
            "minimum_tests promoted to the full set so coverage is "
            "preserved."
        )
        minimum = set(full or all_tests)
    if not full:
        full = set(all_tests)
        rationale.append(
            "no tier-mate matches found; full_tests defaulted to the "
            "complete tests/ tree."
        )
    rationale.append(
        f"intent: {intent[:200]}" if intent
        else "no intent provided — selection is path-based only."
    )

    minimum_list = sorted(minimum)
    full_list = sorted(full)
    return TestSelection(
        schema_version=SCHEMA_VERSION_TEST_SELECT_V1,
        intent=intent,
        changed_files=list(changed_files),
        minimum_tests=minimum_list,
        full_tests=full_list,
        minimum_command=(
            "python -m pytest " + " ".join(minimum_list)
            if minimum_list else "python -m pytest"
        ),
        full_command="python -m pytest",
        rationale=rationale,
    )
