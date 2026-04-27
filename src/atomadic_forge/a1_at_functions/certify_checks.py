"""Tier a1 — pure certification checks for a Forge-shaped repo."""

from __future__ import annotations

import time
from pathlib import Path

from ..a0_qk_constants.tier_names import TIER_NAMES
from .import_smoke import import_smoke
from .stub_detector import detect_stubs, stub_penalty
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

    # Stub-body detection: scan the package itself (where generated code lives)
    src_for_stubs = root / "src"
    if package and (src_for_stubs / package).exists():
        src_for_stubs = src_for_stubs / package
    elif not src_for_stubs.exists():
        src_for_stubs = root
    stub_findings = detect_stubs(package_root=src_for_stubs)
    stub_pen = stub_penalty(stub_findings)
    no_stubs = stub_pen == 0

    # Runtime import smoke — does the package actually load?
    # Default to False when there's nothing to import; the import-points are
    # earned by an actual successful import, not by absence.
    smoke: dict | None = None
    importable = False
    if package and (root / "src" / package).exists():
        smoke = dict(import_smoke(output_root=root, package=package))
        importable = smoke["importable"]
    elif not package:
        # No package specified and we can't run a smoke — exempt from this
        # check so legacy callers without a package layout don't see a 40-point
        # blanket deduction.
        importable = True

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
    if not no_stubs:
        issues.append(f"Stub bodies detected: {len(stub_findings)} "
                       "function(s) with `pass`/NotImplementedError/TODO")
        for f in stub_findings[:5]:
            issues.append(f"  · {f['file']}:{f['lineno']} {f['qualname']} ({f['kind']})")
        recs.append("Replace stub bodies with real implementations before shipping.")
    if smoke is not None and not importable:
        issues.append(f"Package fails to import: {smoke['error_kind']} — "
                       f"{smoke['error_message']}")
        recs.append("Fix the import error so the package is loadable; the "
                     "wire scan can pass while the runtime fails.")

    # Score weights (sum to 100):
    #   docs/tests/layout/wire   — 15 each  (60 max)
    #   importable runtime       — 40       (heaviest — actually loads)
    #   stub-body penalty        — up to 40 deducted
    base_components = {
        "docs": (docs_ok, 15),
        "tests": (tests_ok, 15),
        "layout": (layout_ok, 15),
        "wire": (wire_ok, 15),
        "import": (importable, 40),
    }
    score = sum(weight for ok, weight in base_components.values() if ok)
    score = max(0.0, float(score) - stub_pen)
    return {
        "schema_version": "atomadic-forge.certify/v1",
        "project": project,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "documentation_complete": docs_ok,
        "tests_present": tests_ok,
        "tier_layout_present": layout_ok,
        "no_upward_imports": wire_ok,
        "no_stub_bodies": no_stubs,
        "package_importable": importable,
        "score": score,
        "issues": issues,
        "recommendations": recs,
        "detail": {"docs": docs_d, "tests": tests_d, "layout": layout_d,
                   "wire": wire_d,
                   "stubs": {"count": len(stub_findings),
                             "findings": stub_findings[:20]},
                   "import_smoke": smoke},
    }
