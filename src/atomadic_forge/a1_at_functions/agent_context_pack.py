"""Tier a1 — pure agent context pack.

Codex's 'Copilot's Copilot' primitive #1:

  > Add one MCP tool that every agent calls first: forge_context_pack.
  > Returns: repo purpose, architecture law, tier map, current
  > blockers, best next action, test commands, release gate, risky
  > files, recent lineage. Agents waste a lot of time rediscovering
  > this.

Pure: takes already-computed reports + a project root, returns a
single bundle. The orchestration that runs the scans lives in a3.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import TypedDict

from .agent_summary import summarize_blockers
from .lineage_reader import read_lineage

SCHEMA_VERSION_CONTEXT_PACK_V1 = "atomadic-forge.context_pack/v1"


# The architecture law — pinned text, the same on every pack.
_TIER_LAW = (
    "Tier composition is upward-only. Files in a0_qk_constants/ "
    "import nothing. a1_at_functions/ may import a0. a2_mo_composites/ "
    "may import a0 + a1. a3_og_features/ may import a0..a2. "
    "a4_sy_orchestration/ may import a0..a3. Never import upward; "
    "never import sideways. Wire violations carry F-codes "
    "F0040–F0049."
)


class ContextPack(TypedDict, total=False):
    schema_version: str
    project_root: str
    repo_purpose: str
    architecture_law: str
    tier_map: dict[str, int]
    primary_language: str
    blockers_summary: dict
    best_next_action: dict | None
    test_commands: list[str]
    release_gate: list[str]
    risky_files: list[dict]
    recent_lineage: list[dict]
    pinned_resources: list[str]


def _read_repo_purpose(project_root: Path) -> str:
    """Best-effort: pull the first paragraph from the README, or the
    pyproject description. Falls back to the directory name."""
    for name in ("README.md", "README.rst", "README"):
        readme = project_root / name
        if not readme.exists():
            continue
        try:
            text = readme.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # First non-heading paragraph.
        for para in text.split("\n\n"):
            stripped = para.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # Strip leading badges and HTML <p> wrappers.
            cleaned = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", stripped)
            cleaned = re.sub(r"\[[^\]]*\]\([^)]+\)", "", cleaned)
            cleaned = re.sub(r"<[^>]+>", "", cleaned).strip()
            if len(cleaned) >= 20:
                return cleaned[:400]
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        m = re.search(r'description\s*=\s*"([^"]+)"', text)
        if m:
            return m.group(1)[:400]
    return f"Repo at {project_root.name} (no README description found)"


def _detect_test_commands(project_root: Path) -> list[str]:
    cmds: list[str] = []
    if (project_root / "pyproject.toml").exists():
        cmds.append("python -m pytest")
    if (project_root / "tox.ini").exists():
        cmds.append("tox")
    if (project_root / "package.json").exists():
        cmds.append("npm test")
    if (project_root / "Cargo.toml").exists():
        cmds.append("cargo test")
    if (project_root / "Makefile").exists():
        # Look for a 'test' target.
        try:
            mk = (project_root / "Makefile").read_text(
                encoding="utf-8", errors="replace")
            if re.search(r"^test:", mk, re.MULTILINE):
                cmds.append("make test")
        except OSError:
            pass
    if not cmds:
        cmds.append("# no test runner detected — add tests/ + pytest")
    return cmds


def _release_gate(project_root: Path) -> list[str]:
    """Heuristic release gate: lint + tests + wire + certify ≥ 75."""
    gate: list[str] = []
    if (project_root / "pyproject.toml").exists():
        gate.append("python -m ruff check .")
    gate.extend([
        "python -m pytest",
        "forge wire src --fail-on-violations",
        "forge certify . --fail-under 75",
    ])
    return gate


def _risky_files(lineage: list[dict], top_n: int = 10) -> list[dict]:
    """Files written most often in the recent lineage are 'risky' —
    they're the ones the agent has been touching repeatedly. Useful
    proxy for hot spots without a real edit-frequency analysis."""
    counter: Counter[str] = Counter()
    for entry in lineage:
        path = entry.get("path") or entry.get("artifact")
        if path:
            counter[path] += 1
    return [
        {"path": p, "edit_count": n}
        for p, n in counter.most_common(top_n)
    ]


def emit_context_pack(
    *,
    project_root: Path,
    scout_report: dict | None = None,
    wire_report: dict | None = None,
    certify_report: dict | None = None,
    plan: dict | None = None,
) -> ContextPack:
    """Build the first-call context bundle.

    Reports may be None — the bundle degrades gracefully and reports
    'unavailable' for missing sections.
    """
    project_root = Path(project_root).resolve()
    tier_map = (scout_report or {}).get("tier_distribution") or {}
    primary_language = (scout_report or {}).get("primary_language", "?")

    blockers = summarize_blockers(
        wire_report=wire_report, certify_report=certify_report,
        package_root=project_root.name,
    )
    best_next: dict | None = None
    if plan and plan.get("top_actions"):
        best_next = plan["top_actions"][0]
    elif blockers["blockers"]:
        b = blockers["blockers"][0]
        best_next = {
            "id": "blocker." + (b.get("f_code") or "?"),
            "title": b.get("title", ""),
            "next_command": b.get("next_command", ""),
            "kind": "blocker",
        }

    lineage = read_lineage(project_root, last=20)

    return ContextPack(
        schema_version=SCHEMA_VERSION_CONTEXT_PACK_V1,
        project_root=str(project_root),
        repo_purpose=_read_repo_purpose(project_root),
        architecture_law=_TIER_LAW,
        tier_map=dict(tier_map),
        primary_language=primary_language,
        blockers_summary=blockers,
        best_next_action=best_next,
        test_commands=_detect_test_commands(project_root),
        release_gate=_release_gate(project_root),
        risky_files=_risky_files(lineage),
        recent_lineage=lineage[-10:] if lineage else [],
        pinned_resources=[
            "forge://docs/receipt",
            "forge://docs/formalization",
            "forge://summary/blockers",
        ],
    )
