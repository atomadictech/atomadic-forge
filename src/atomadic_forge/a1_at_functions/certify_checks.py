"""Tier a1 — pure certification checks for a Forge-shaped repo."""

from __future__ import annotations

import time
from pathlib import Path

from ..a0_qk_constants.tier_names import TIER_NAMES
from .wire_check import scan_violations


def check_documentation(root: Path) -> tuple[bool, dict]:
    readme = (root / "README.md").exists()
    docs_md = list((root / "docs").glob("*.md")) if (root / "docs").exists() else []
    ok = readme or len(docs_md) >= 2
    return ok, {"readme": readme, "docs_md_count": len(docs_md)}


def check_tests_present(root: Path) -> tuple[bool, dict]:
    tests = []
    for d in root.rglob("tests"):
        if "__pycache__" in d.parts or not d.is_dir():
            continue
        tests.extend(d.rglob("test_*.py"))
        tests.extend(d.rglob("*_test.py"))
    return bool(tests), {"test_files_found": len(tests)}


def check_tier_layout(root: Path, package: str | None = None) -> tuple[bool, dict]:
    src = root / "src"
    base = src if src.exists() else root
    if package:
        base = base / package
    present = [t for t in TIER_NAMES if (base / t).exists()]
    ok = len(present) >= 3
    return ok, {"tiers_present": present}


def check_no_upward_imports(root: Path, package: str | None = None) -> tuple[bool, dict]:
    src = root / "src"
    base = src if src.exists() else root
    if package and (base / package).exists():
        base = base / package
    report = scan_violations(base)
    return report["verdict"] == "PASS", {
        "violation_count": report["violation_count"],
        "samples": report["violations"][:5],
    }


def certify(root: Path, *, project: str = "Atomadic project",
            package: str | None = None) -> dict:
    docs_ok, docs_d = check_documentation(root)
    tests_ok, tests_d = check_tests_present(root)
    layout_ok, layout_d = check_tier_layout(root, package)
    wire_ok, wire_d = check_no_upward_imports(root, package)

    issues: list[str] = []
    recs: list[str] = []
    if not docs_ok:
        issues.append("Documentation incomplete — add README.md or docs/*.md")
        recs.append("Run `forge auto` to scaffold a docs starter.")
    if not tests_ok:
        issues.append("No test files under tests/")
        recs.append("Add tests/test_*.py before claiming production-ready.")
    if not layout_ok:
        issues.append("Tier layout missing — Forge enforces 5-tier directories.")
        recs.append("Run `forge assimilate` to materialize the tier tree.")
    if not wire_ok:
        issues.append(f"Upward-import violations: {wire_d['violation_count']}")
        recs.append("Run `forge wire --apply` to auto-fix where unambiguous.")

    score = max(0.0, 100.0 - 25.0 * len(issues))
    return {
        "schema_version": "atomadic-forge.certify/v1",
        "project": project,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "documentation_complete": docs_ok,
        "tests_present": tests_ok,
        "tier_layout_present": layout_ok,
        "no_upward_imports": wire_ok,
        "score": score,
        "issues": issues,
        "recommendations": recs,
        "detail": {"docs": docs_d, "tests": tests_d,
                   "layout": layout_d, "wire": wire_d},
    }
