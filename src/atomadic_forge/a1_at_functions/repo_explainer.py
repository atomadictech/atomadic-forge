"""Tier a1 — explain_repo: humane operational orientation (Codex #6).

Codex distinguished this from context_pack:

  > 'This is different from docs. It is operational orientation.
  >  Output: This is a Python package for…  Core flow is…  Do not
  >  break…  Most important tests are…  Release state is…'

Pure: takes already-computed reports (or None) and emits a short
operational paragraph + a few bullets the agent should treat as
hard constraints.
"""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict

SCHEMA_VERSION_EXPLAIN_V1 = "atomadic-forge.explain_repo/v1"


class RepoExplanation(TypedDict, total=False):
    schema_version: str
    project_root: str
    one_liner: str
    core_flow: str
    do_not_break: list[str]
    important_tests: list[str]
    release_state: str
    depth: str


def _detect_core_flow(scout_report: dict | None) -> str:
    if not scout_report:
        return "(scout report unavailable; run forge recon)"
    tiers = scout_report.get("tier_distribution") or {}
    if not tiers:
        return "(repo has no tier-organized symbols)"
    primary_tier = max(tiers.items(), key=lambda kv: kv[1])[0]
    return (
        f"primary symbol density is in {primary_tier} "
        f"({tiers[primary_tier]} symbols). "
        f"a4_sy_orchestration calls into a3 features which compose "
        f"a2 stateful classes from a1 pure functions over a0 "
        f"constants — the upward-only law applies."
    )


def _detect_release_state(certify_report: dict | None,
                           wire_report: dict | None) -> str:
    if certify_report is None and wire_report is None:
        return "(no certify / wire scans available)"
    score = (certify_report or {}).get("score")
    wire_verdict = (wire_report or {}).get("verdict", "?")
    # Wire FAIL is blocking regardless of whether certify ran.
    if wire_verdict == "FAIL":
        return f"BLOCKED — wire verdict={wire_verdict}; fix violations first."
    if score is None:
        return f"wire={wire_verdict}; no certify score available."
    if score >= 100 and wire_verdict == "PASS":
        return "PASS — every gate green; ready to ship."
    if score >= 75 and wire_verdict == "PASS":
        return f"GREEN-ISH — score {score:.0f}/100; ship-ready by team-grade gate."
    return f"REFINE — score {score:.0f}/100 below shipping bar."


def _important_tests(project_root: Path) -> list[str]:
    """Heuristic: tests at the top of tests/ are usually the smoke +
    contract tests; tests with 'smoke' or 'contract' in the name
    explicitly. Cap at 5."""
    out: list[str] = []
    for sub in ("tests", "test"):
        d = project_root / sub
        if not d.is_dir():
            continue
        # Smoke / contract first.
        for f in sorted(d.glob("test_*.py")):
            n = f.name.lower()
            if "smoke" in n or "contract" in n or "import" in n:
                out.append(str(f.relative_to(project_root).as_posix()))
        # Then any other top-level tests/.
        for f in sorted(d.glob("test_*.py")):
            rel = str(f.relative_to(project_root).as_posix())
            if rel not in out:
                out.append(rel)
            if len(out) >= 5:
                break
        break
    return out[:5]


def explain_repo(
    *,
    project_root: Path,
    repo_purpose: str,
    scout_report: dict | None = None,
    wire_report: dict | None = None,
    certify_report: dict | None = None,
    depth: str = "agent",
) -> RepoExplanation:
    """Build the humane orientation paragraph + bullets.

    ``depth`` is reserved for future variants ('agent' | 'reviewer' |
    'newcomer'); v1 emits the agent-tuned version regardless.
    """
    project_root = Path(project_root).resolve()
    one_liner = (repo_purpose or f"Repo at {project_root.name}")[:200]
    do_not_break = [
        "the upward-only tier law (a0 → a1 → a2 → a3 → a4); "
        "any wire violation blocks merge",
        "public re-exports in __init__.py — touching them is a "
        "public_api_risk in score_patch",
        "release-control files (pyproject.toml, CHANGELOG.md, "
        "VERSION) — version bumps require a CHANGELOG entry",
    ]
    return RepoExplanation(
        schema_version=SCHEMA_VERSION_EXPLAIN_V1,
        project_root=str(project_root),
        one_liner=one_liner,
        core_flow=_detect_core_flow(scout_report),
        do_not_break=do_not_break,
        important_tests=_important_tests(project_root),
        release_state=_detect_release_state(certify_report, wire_report),
        depth=depth,
    )
