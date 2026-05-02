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
from .preflight_change import preflight_change
from .test_selector import select_tests
from .validation_commands import detect_test_commands, release_gate_commands

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

# Machine-readable agent workflow protocol — embedded in every context pack.
# Agents must follow these phases; MCP clients can branch on specific keys.
_AGENT_WORKFLOW = {
    "protocol": "atomadic-forge.agent_workflow/v1",
    "summary": (
        "Every Forge agent session follows four phases: orient → preflight → "
        "edit → end-of-cycle. Use the tools listed in each phase. Never skip "
        "preflight_change before editing or certify at end-of-cycle."
    ),
    "phases": {
        "1_orient": {
            "description": "Run once at session start to ground the agent.",
            "required_tools": ["context_pack"],
            "recommended_tools": ["wire", "audit_list"],
            "notes": [
                "Call context_pack first — always.",
                "If wire reports violations, fix them before feature work.",
            ],
        },
        "2_preflight": {
            "description": "Run before every file edit.",
            "required_tools": ["preflight_change", "select_tests"],
            "notes": [
                "preflight_change validates tier placement and forbidden imports.",
                "select_tests returns the minimum test set to run after the edit.",
                "Do NOT edit files that preflight flags as write_scope_too_broad.",
            ],
        },
        "3_edit": {
            "description": "Apply the bounded edit, then validate immediately.",
            "required_tools": ["wire", "select_tests"],
            "recommended_tools": ["score_patch"],
            "naming_conventions": {
                "a0_qk_constants": ["*_config.py", "*_constants.py", "*_types.py", "*_enums.py"],
                "a1_at_functions": [
                    "*_utils.py", "*_helpers.py", "*_validators.py", "*_parsers.py",
                    "*_functions.py", "*_compose.py", "*_rank.py", "*_render.py",
                    "*_extract.py", "*_detect.py", "*_check.py", "*_protocol.py",
                ],
                "a2_mo_composites": ["*_client.py", "*_core.py", "*_store.py", "*_registry.py"],
                "a3_og_features": ["*_feature.py", "*_service.py", "*_pipeline.py", "*_gate.py"],
                "a4_sy_orchestration": ["*_cmd.py", "*_cli.py", "*_runner.py", "*_main.py"],
            },
            "notes": [
                "New files MUST follow the naming convention for their tier.",
                "One responsibility per file — split if it grows large.",
                "After every edit: run wire to confirm no upward imports.",
                "Run select_tests minimum set; if any fail, fix before proceeding.",
            ],
        },
        "4_end_of_cycle": {
            "description": "Run at the end of a feature dev cycle before closing the session.",
            "required_tools": ["certify"],
            "recommended_tools": ["emergent_scan", "synergy_scan", "wire"],
            "gate": "certify score must be ≥ 75 to consider the cycle complete.",
            "notes": [
                "emergent_scan finds novel a1/a2 compositions to materialise as a3 features.",
                "synergy_scan finds feature-pair gaps across CLI, a3, and a2.",
                "certify is the PASS/FAIL gate — do not close the session with score < 75.",
                "If certify < 75, run auto_plan to get ranked repair cards.",
            ],
        },
    },
    "never_do": [
        "Import upward (a0 from a1, a1 from a2, etc.) — wire will flag F004x.",
        "Put logic at a4 that belongs in a1 — CLI wrappers are thin by design.",
        "Duplicate a building block that already exists in a lower tier.",
        "Close the session without running certify.",
        "Skip preflight_change before editing more than 3 files.",
    ],
}


class ContextPack(TypedDict, total=False):
    schema_version: str
    project_root: str
    repo_purpose: str
    architecture_law: str
    agent_workflow: dict           # Machine-readable 4-phase workflow protocol
    tier_map: dict[str, int]
    primary_language: str
    blockers_summary: dict
    best_next_action: dict | None
    test_commands: list[str]
    release_gate: list[str]
    risky_files: list[dict]
    recent_lineage: list[dict]
    pinned_resources: list[str]
    focus: str
    intent: str
    target_files: list[str]
    file_context: list[dict]
    change_preflight: dict
    selected_tests: dict
    suggested_next_steps: list[dict]


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
    return detect_test_commands(project_root)


def _release_gate(project_root: Path) -> list[str]:
    """Heuristic release gate: lint + tests + wire + certify ≥ 75."""
    return release_gate_commands(project_root)


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


def _normalize_focus(focus: str | None, target_files: list[str]) -> str:
    """Return the context-pack focus mode.

    ``orientation`` preserves the original first-call behavior. File-targeted
    calls naturally become ``change`` unless the caller asks for another mode.
    """
    allowed = {"orientation", "change", "release", "debug"}
    candidate = (focus or "").strip().lower()
    if candidate in allowed:
        return candidate
    return "change" if target_files else "orientation"


def _detect_tier(path: str) -> str | None:
    for part in Path(path).parts:
        if part in {
            "a0_qk_constants",
            "a1_at_functions",
            "a2_mo_composites",
            "a3_og_features",
            "a4_sy_orchestration",
        }:
            return part
    return None


def _file_kind(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if path.startswith(("tests/", "test/")) or ".test." in path or ".spec." in path:
        return "test"
    if suffix in {".md", ".rst", ".txt", ".adoc"}:
        return "docs"
    if Path(path).name in {"pyproject.toml", "package.json", "CHANGELOG.md", "VERSION"}:
        return "release-control"
    if suffix in {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}:
        return "code"
    return "artifact"


def _sibling_samples(project_root: Path, path: str, *, limit: int = 5) -> list[str]:
    target_dir = project_root / Path(path).parent
    if not target_dir.is_dir():
        return []
    samples: list[str] = []
    for candidate in sorted(target_dir.iterdir()):
        if candidate.name == Path(path).name:
            continue
        if candidate.name.startswith(".") or candidate.name.startswith("_"):
            continue
        if not candidate.is_file():
            continue
        samples.append(str(candidate.relative_to(project_root).as_posix()))
        if len(samples) >= limit:
            break
    return samples


def _file_context(project_root: Path, files: list[str]) -> list[dict]:
    return [
        {
            "path": path,
            "exists": (project_root / path).exists(),
            "kind": _file_kind(path),
            "detected_tier": _detect_tier(path),
            "sibling_samples": _sibling_samples(project_root, path),
        }
        for path in files
    ]


def _normalize_target_files(project_root: Path, files: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw in files:
        path = Path(str(raw))
        if path.is_absolute():
            try:
                path = path.resolve().relative_to(project_root)
            except ValueError:
                normalized.append(path.as_posix())
                continue
        normalized.append(path.as_posix())
    return normalized


def _suggested_next_steps(
    *,
    focus: str,
    intent: str,
    target_files: list[str],
    blockers: dict,
    best_next: dict | None,
    release_gate: list[str],
    selected_tests: dict | None,
) -> list[dict]:
    steps: list[dict] = []
    if blockers.get("blocker_count", 0):
        steps.append({
            "action": "clear_blockers",
            "why": "Forge found blockers that should be handled before feature work.",
            "tool": "wire",
            "next_command": blockers.get("next_command", ""),
        })
    elif best_next:
        steps.append({
            "action": "run_best_next_action",
            "why": "A saved plan has a highest-ranked next action.",
            "tool": "auto_step",
            "next_command": best_next.get("next_command", ""),
        })

    if target_files:
        steps.append({
            "action": "read_target_context",
            "why": "Start with the target files and sibling samples before editing.",
            "tool": "context_pack",
            "files": target_files[:8],
        })
        if selected_tests:
            steps.append({
                "action": "run_minimum_validation",
                "why": "Focused validation for this file set.",
                "tool": "select_tests",
                "next_command": selected_tests.get("minimum_command", ""),
            })

    if focus == "release":
        steps.append({
            "action": "run_release_gate",
            "why": "Release-focused context should end with the full gate.",
            "tool": "certify",
            "next_command": " && ".join(release_gate),
        })
    elif focus == "debug":
        steps.append({
            "action": "inspect_recent_lineage",
            "why": "Debug sessions benefit from checking what changed recently.",
            "tool": "audit_list",
            "next_command": "forge audit list --json",
        })
    elif not steps:
        steps.append({
            "action": "preflight_before_edit",
            "why": (
                "No blockers found. Before editing, call context_pack with "
                "files or run preflight_change for the planned write scope."
            ),
            "tool": "preflight_change",
            "next_command": "",
        })

    if intent:
        steps.append({
            "action": "preserve_intent",
            "why": f"Keep validation tied to the stated intent: {intent[:160]}",
            "tool": "select_tests",
            "next_command": (
                selected_tests.get("full_command", "")
                if selected_tests else release_gate[0] if release_gate else ""
            ),
        })
    return steps


def emit_context_pack(
    *,
    project_root: Path,
    scout_report: dict | None = None,
    wire_report: dict | None = None,
    certify_report: dict | None = None,
    plan: dict | None = None,
    focus: str | None = None,
    intent: str = "",
    files: list[str] | None = None,
) -> ContextPack:
    """Build the first-call context bundle.

    Reports may be None — the bundle degrades gracefully and reports
    'unavailable' for missing sections.
    """
    project_root = Path(project_root).resolve()
    tier_map = (scout_report or {}).get("tier_distribution") or {}
    primary_language = (scout_report or {}).get("primary_language", "?")
    target_files = _normalize_target_files(project_root, files or [])
    focus_mode = _normalize_focus(focus, target_files)

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
    release_gate = _release_gate(project_root)
    preflight = None
    selected_tests = None
    if target_files:
        preflight = preflight_change(
            intent=intent or f"context_pack focus={focus_mode}",
            proposed_files=target_files,
            project_root=project_root,
        )
        selected_tests = select_tests(
            intent=intent,
            changed_files=target_files,
            project_root=project_root,
        )

    return ContextPack(
        schema_version=SCHEMA_VERSION_CONTEXT_PACK_V1,
        project_root=str(project_root),
        repo_purpose=_read_repo_purpose(project_root),
        architecture_law=_TIER_LAW,
        agent_workflow=_AGENT_WORKFLOW,
        tier_map=dict(tier_map),
        primary_language=primary_language,
        blockers_summary=blockers,
        best_next_action=best_next,
        test_commands=_detect_test_commands(project_root),
        release_gate=release_gate,
        risky_files=_risky_files(lineage),
        recent_lineage=lineage[-10:] if lineage else [],
        pinned_resources=[
            "forge://docs/receipt",
            "forge://docs/formalization",
            "forge://summary/blockers",
        ],
        focus=focus_mode,
        intent=intent,
        target_files=target_files,
        file_context=_file_context(project_root, target_files),
        change_preflight=preflight or {},
        selected_tests=selected_tests or {},
        suggested_next_steps=_suggested_next_steps(
            focus=focus_mode,
            intent=intent,
            target_files=target_files,
            blockers=blockers,
            best_next=best_next,
            release_gate=release_gate,
            selected_tests=selected_tests,
        ),
    )
