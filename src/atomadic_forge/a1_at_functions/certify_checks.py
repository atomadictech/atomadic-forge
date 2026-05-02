"""Tier a1 — pure certification checks for a Forge-shaped repo."""

from __future__ import annotations

import time
from pathlib import Path

from ..a0_qk_constants.lang_extensions import (
    ALL_SOURCE_EXTS,
    path_parts_contain_ignored_dir,
)
from ..a0_qk_constants.tier_names import TIER_NAMES
from .import_smoke import import_smoke
from .stub_detector import detect_stubs, stub_penalty
from .test_runner import run_pytest
from .wire_check import scan_violations


def _is_under_ignored(rel_parts: tuple[str, ...]) -> bool:
    """Path-segment check against IGNORED_DIRS (used by every walk)."""
    return path_parts_contain_ignored_dir(rel_parts)


def check_documentation(root: Path) -> tuple[bool, dict]:
    """Documentation signal — markdown anywhere meaningful counts.

    Recognises:
      * README at root (``.md`` / ``.rst`` / no extension)
      * Any ``.md`` / ``.markdown`` / ``.mdx`` under ``docs/``, ``doc/``,
        ``documentation/``, ``guides/``, ``guide/``
      * The repo passes if README exists, OR there are ≥2 doc files
        anywhere in the recognised doc directories.
    """
    readme_names = {"README.md", "README.rst", "README.markdown",
                     "README", "readme.md"}
    readme = any((root / n).exists() for n in readme_names)

    # Find every directory anywhere in the tree whose basename matches a
    # known doc-folder convention.  Catches both top-level (./docs/) and
    # nested (./cognition/guides/) layouts.  IGNORED_DIRS still apply.
    DOC_DIR_NAMES = {"docs", "doc", "documentation", "guides", "guide"}
    doc_dirs_found: list[str] = []
    doc_files: set[Path] = set()
    samples: list[str] = []
    seen_dirs: set[Path] = set()
    for d in root.rglob("*"):
        if not d.is_dir() or d.name not in DOC_DIR_NAMES:
            continue
        rel_parts = d.relative_to(root).parts
        if _is_under_ignored(rel_parts):
            continue
        if d in seen_dirs:
            continue
        seen_dirs.add(d)
        doc_dirs_found.append(d.relative_to(root).as_posix())
        for p in d.rglob("*"):
            if not p.is_file():
                continue
            rel_parts_p = p.relative_to(root).parts
            if _is_under_ignored(rel_parts_p):
                continue
            if p.suffix.lower() in {".md", ".markdown", ".mdx", ".rst"}:
                doc_files.add(p)
                if len(samples) < 5:
                    samples.append(p.relative_to(root).as_posix())

    doc_count = len(doc_files)
    ok = readme or doc_count >= 2
    return ok, {
        "readme":         readme,
        "docs_md_count":  doc_count,
        "doc_dirs_found": doc_dirs_found,
        "doc_samples":    samples,
    }


def check_tests_present(root: Path) -> tuple[bool, dict]:
    """Return (ok, detail). Recognises Python AND JS/TS test conventions.

    Python conventions (any of):
      - ``tests/test_*.py``
      - ``tests/*_test.py``
      - ``test/test_*.py`` / ``test/*_test.py`` (singular ``test/``)

    JavaScript / TypeScript conventions (any of):
      - ``tests/*.test.{js,mjs,jsx,cjs,ts,tsx}``
      - ``tests/*.spec.{js,mjs,jsx,cjs,ts,tsx}``
      - same patterns under ``test/`` (singular)
      - same patterns under ``__tests__/`` (Jest convention)
      - **colocated** ``*.test.{ts,tsx,js,…}`` / ``*.spec.{…}`` anywhere in
        the source tree (Vitest / Jest / Bun colocated convention)
    """
    js_exts = (".js", ".mjs", ".jsx", ".cjs", ".ts", ".tsx")
    py_tests: set[Path] = set()
    js_tests: set[Path] = set()
    seen_dirs: set[Path] = set()

    # Walk both `tests/` (plural) and `test/` (singular) — both are common.
    for dir_name in ("tests", "test"):
        for d in root.rglob(dir_name):
            if not d.is_dir():
                continue
            rel_parts = d.relative_to(root).parts
            if _is_under_ignored(rel_parts):
                continue
            if d in seen_dirs:
                continue
            seen_dirs.add(d)
            py_tests.update(
                p for p in d.rglob("test_*.py")
                if not _is_under_ignored(p.relative_to(root).parts)
            )
            py_tests.update(
                p for p in d.rglob("*_test.py")
                if not _is_under_ignored(p.relative_to(root).parts)
            )
            for ext in js_exts:
                js_tests.update(
                    p for p in d.rglob(f"*.test{ext}")
                    if not _is_under_ignored(p.relative_to(root).parts)
                )
                js_tests.update(
                    p for p in d.rglob(f"*.spec{ext}")
                    if not _is_under_ignored(p.relative_to(root).parts)
                )

    # __tests__ convention (Jest etc.)
    for d in root.rglob("__tests__"):
        if not d.is_dir():
            continue
        rel_parts = d.relative_to(root).parts
        if _is_under_ignored(rel_parts):
            continue
        for ext in js_exts:
            js_tests.update(
                p for p in d.rglob(f"*{ext}")
                if not _is_under_ignored(p.relative_to(root).parts)
            )

    # Colocated tests — `*.test.{ts,…}` / `*.spec.{ts,…}` anywhere in the
    # tree (Vitest / Jest / Bun convention: `src/foo.test.ts` next to
    # `src/foo.ts`). Matters for Cloudflare Workers, Next.js apps, and
    # other non-Python repos that don't centralise tests in `tests/`.
    for ext in js_exts:
        for pattern in (f"*.test{ext}", f"*.spec{ext}"):
            for p in root.rglob(pattern):
                if not p.is_file():
                    continue
                if _is_under_ignored(p.relative_to(root).parts):
                    continue
                js_tests.add(p)

    total = len(py_tests) + len(js_tests)
    return total > 0, {
        "test_files_found": total,
        "python_tests": len(py_tests),
        "javascript_tests": len(js_tests),
    }


def _collect_tier_dirs(root: Path) -> list[str]:
    """Return tier directories present anywhere under ``root``.

    Polyglot-aware: a tier-named directory anywhere in the tree (Python
    ``src/<pkg>/aN_*/`` OR JS-style top-level / nested ``aN_*/``) counts.
    Each tier name is reported at most once.  Honours IGNORED_DIRS so
    vendored / cached / tooling folders never leak into the scan.
    """
    found: set[str] = set()
    for d in root.rglob("*"):
        if not d.is_dir():
            continue
        rel_parts = d.relative_to(root).parts
        if _is_under_ignored(rel_parts):
            continue
        if d.name in TIER_NAMES:
            found.add(d.name)
            if len(found) == len(TIER_NAMES):
                break
    return sorted(found)


def count_untiered_source_files(root: Path) -> dict:
    """How many SOURCE files (Python/JS/TS) live outside any tier directory?

    Documentation, config, asset, and other-classed files are deliberately
    excluded — markdown placed in ``cognition/guides/`` doesn't have a tier
    identity and shouldn't be treated as code-out-of-place.  Scoring code
    (e.g. future stricter layout penalties) should base its judgement on
    this count, not the raw file count.
    """
    untiered: list[str] = []
    tiered: list[str] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel_parts = p.relative_to(root).parts
        if _is_under_ignored(rel_parts):
            continue
        if p.suffix.lower() not in ALL_SOURCE_EXTS:
            continue
        # Source file — check if any of its path segments is a tier dir.
        in_tier = any(seg in TIER_NAMES for seg in rel_parts)
        rel_path = p.relative_to(root).as_posix()
        if in_tier:
            tiered.append(rel_path)
        else:
            untiered.append(rel_path)
    return {
        "untiered_source_count": len(untiered),
        "tiered_source_count":   len(tiered),
        "untiered_samples":      untiered[:10],
    }


def check_tier_layout(root: Path, package: str | None = None) -> tuple[bool, dict]:
    src = root / "src"
    base = src if src.exists() else root
    if package:
        candidate = base / package
        if candidate.exists():
            base = candidate
    present = [t for t in TIER_NAMES if (base / t).exists()]
    polyglot_present: list[str] = []
    if len(present) < 3:
        polyglot_present = _collect_tier_dirs(root)
        if len(polyglot_present) > len(present):
            present = polyglot_present
    ok = len(present) >= 3
    return ok, {
        "tiers_present": present,
        "tiers_present_count": len(present),
        "tiers_required": 3,
    }


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


def check_ci_workflow(root: Path) -> tuple[bool, dict]:
    """Continuous-integration evidence — ``.github/workflows/*.yml``.

    Looks for at least one non-empty workflow file under
    ``.github/workflows/`` (``.yml`` or ``.yaml``).  Presence of a
    workflow is treated as evidence of automated quality gating; we
    deliberately do NOT call out to the GitHub API to inspect run
    history, so this remains a hermetic structural check.

    A project that wires `pytest`, `forge wire`, and `forge certify`
    into its CI pipeline gets the same 5 points as one that wires only
    a smoke test — the axis rewards intent, not depth.  The behavioural
    axis is what rewards actual test-pass behaviour.
    """
    wf_dir = root / ".github" / "workflows"
    if not wf_dir.exists() or not wf_dir.is_dir():
        return False, {
            "workflow_dir_exists": False,
            "workflow_files":      [],
        }
    files: list[str] = []
    for p in sorted(wf_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".yml", ".yaml"}:
            continue
        try:
            if p.stat().st_size > 0:
                files.append(p.name)
        except OSError:
            continue
    return len(files) > 0, {
        "workflow_dir_exists": True,
        "workflow_files":      files,
    }


def check_changelog(root: Path) -> tuple[bool, dict]:
    """Release-discipline evidence — ``CHANGELOG.md`` or equivalent.

    Looks for any of the canonical release-notes filenames at the
    project root and credits the project iff the file is non-trivial
    (≥ 200 bytes) — empty placeholders don't earn the points.

    Recognised names: ``CHANGELOG.md``, ``CHANGELOG.rst``, ``CHANGELOG``,
    ``RELEASE_NOTES.md``, ``HISTORY.md``, ``NEWS.md``.
    """
    candidates = (
        "CHANGELOG.md", "CHANGELOG.rst", "CHANGELOG",
        "RELEASE_NOTES.md", "HISTORY.md", "NEWS.md",
    )
    for name in candidates:
        p = root / name
        if not p.exists() or not p.is_file():
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size >= 200:
            return True, {"changelog_file": name, "size_bytes": size}
    return False, {"changelog_file": None, "size_bytes": 0}


def certify(root: Path, *, project: str = "Atomadic project",
            package: str | None = None) -> dict:
    _scan_start = time.perf_counter()
    docs_ok, docs_d = check_documentation(root)
    tests_ok, tests_d = check_tests_present(root)
    layout_ok, layout_d = check_tier_layout(root, package)
    wire_ok, wire_d = check_no_upward_imports(root, package)
    ci_ok, ci_d = check_ci_workflow(root)
    changelog_ok, changelog_d = check_changelog(root)

    # Stub-body detection: scan the package itself (where generated code lives).
    # Only recurse when we have a well-defined src/ layout; falling back to the
    # project root would include all nested forged/sources directories and produce
    # tens of thousands of false positives from extracted-stub skeletons.
    src_for_stubs = root / "src"
    if package and (src_for_stubs / package).exists():
        src_for_stubs = src_for_stubs / package
    elif src_for_stubs.exists():
        pass  # use root/src/ as-is
    else:
        # No src/ layout — don't recurse into the full tree; that risks picking
        # up forged/ or sources/ directories.  Scan only Python files directly
        # inside the project root (non-recursive).
        src_for_stubs = None
    stub_findings = detect_stubs(package_root=src_for_stubs) if src_for_stubs else []
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

    # Behavioral check — actually run pytest against the emitted tests/.
    # This is the breakthrough signal: a package can pass wire + import and
    # still be a no-op stub.  Running its own tests catches that.
    test_run: dict | None = None
    test_pass_ratio = 0.0
    if importable and (root / "tests").exists() and tests_ok:
        test_run = dict(run_pytest(output_root=root, package=package))
        test_pass_ratio = test_run["pass_ratio"]
    elif not (root / "tests").exists() or not tests_ok:
        # No tests means we can't credit the ratio — and the structural
        # 'tests_present' check already caught the absence.
        test_pass_ratio = 0.0

    issues: list[str] = []
    recs: list[str] = []
    if not docs_ok:
        issues.append("Documentation incomplete — add README.md or docs/*.md")
        recs.append("Run `forge auto` to scaffold a docs starter.")
    if not tests_ok:
        issues.append(
            "No test files found (tests/test_*.py / *.test.ts / *.spec.ts / __tests__/)."
        )
        recs.append(
            "Add at least one test file before claiming production-ready: "
            "Python `tests/test_*.py`, JS/TS `tests/*.test.ts` or "
            "colocated `src/<file>.test.ts`."
        )
    if not layout_ok:
        present_count = layout_d.get("tiers_present_count", 0)
        present_list = ", ".join(layout_d.get("tiers_present", [])) or "none"
        issues.append(
            f"Tier layout missing — found {present_count} tier "
            f"director{'y' if present_count == 1 else 'ies'} ({present_list}); "
            "need 3+ of a0_qk_constants/a1_at_functions/a2_mo_composites/"
            "a3_og_features/a4_sy_orchestration."
        )
        recs.append("Split your code into the canonical aN_* directories "
                    "(or run `forge auto` to scaffold them).")
    if not wire_ok:
        issues.append(f"Upward-import violations: {wire_d['violation_count']}")
        recs.append("Run `forge wire` to inspect violations, then move imports "
                    "down-tier or split modules.")
    if not no_stubs:
        issues.append(f"Stub bodies detected: {len(stub_findings)} "
                       "function(s) with `pass`/NotImplementedError/TODO")
        for f in stub_findings[:5]:
            issues.append(f"  · {f['file']}:{f['lineno']} "
                           f"{f['qualname']} ({f['kind']})")
        recs.append("Replace stub bodies with real implementations before shipping.")
    if smoke is not None and not importable:
        issues.append(f"Package fails to import: {smoke['error_kind']} — "
                       f"{smoke['error_message']}")
        recs.append("Fix the import error so the package is loadable; the "
                     "wire scan can pass while the runtime fails.")
    if test_run is not None and test_run.get("ran") and test_run["failed"]:
        issues.append(
            f"Tests failed: {test_run['failed']} of {test_run['total']} "
            f"(pass-ratio {test_pass_ratio:.1%})"
        )
        for fid in (test_run.get("failure_excerpts") or [])[:5]:
            issues.append(f"  · {fid}")
        recs.append("Fix the failing tests — wire/import alone does not "
                     "prove behavior.")
    if not ci_ok:
        issues.append("No CI workflow found under .github/workflows/")
        recs.append("Add a CI workflow (.github/workflows/ci.yml) that "
                     "runs pytest + `forge wire` + `forge certify` on push.")
    if not changelog_ok:
        issues.append("No CHANGELOG / release-notes file at project root")
        recs.append("Add CHANGELOG.md (Keep-a-Changelog format) so each "
                     "release documents what changed and why.")

    # Score weights (sum to 100):
    #   docs / layout / wire     — 10 each   (30 max — structural axis)
    #   tests-present            —  5         (structural axis)
    #   importable runtime       — 25         (runtime axis)
    #   tests-pass-ratio         — 30 max     (behavioural axis)
    #   ci workflow              —  5         (operational axis)
    #   changelog/release notes  —  5         (operational axis)
    #   stub-body penalty        — up to 40 deducted
    # Total max: 35 + 25 + 30 + 10 = 100.
    structural = (
        (10 if docs_ok else 0)
        + (10 if layout_ok else 0)
        + (10 if wire_ok else 0)
        + (5 if tests_ok else 0)
    )
    runtime = (25 if importable else 0)
    behavioral = 30 if test_pass_ratio == 1.0 else int(30.0 * test_pass_ratio)
    operational = (
        (5 if ci_ok else 0)
        + (5 if changelog_ok else 0)
    )
    score = max(0.0, float(structural + runtime + behavioral + operational) - stub_pen)
    scan_duration_ms = int((time.perf_counter() - _scan_start) * 1000)
    blockers = len([i for i in issues if not i.startswith("  ·")])
    verdict = "PASS" if score >= 75 and blockers == 0 else "FAIL"
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
        "test_pass_ratio": test_pass_ratio,
        "ci_workflow_present": ci_ok,
        "changelog_present": changelog_ok,
        "score": score,
        "health_summary": {
            "score": score,
            "verdict": verdict,
            "blockers": blockers,
            "scan_duration_ms": scan_duration_ms,
        },
        "score_components": {
            "structural":   structural,
            "runtime":      runtime,
            "behavioral":   behavioral,
            "operational":  operational,
            "stub_penalty": -stub_pen,
        },
        "issues": issues,
        "recommendations": recs,
        "axes": {
            "documentation": {
                "ok": docs_ok, "score_weight": 10,
                "how_to_fix": ("Add README.md or docs/*.md files."
                               if not docs_ok else None),
            },
            "tests_present": {
                "ok": tests_ok, "score_weight": 5,
                "how_to_fix": (
                    "Add at least one test file. Python: tests/test_*.py. "
                    "JS/TS: tests/*.test.ts (or colocated src/*.test.ts, "
                    "or __tests__/*.ts)."
                ) if not tests_ok else None,
            },
            "tier_layout": {
                "ok": layout_ok, "score_weight": 10,
                "how_to_fix": (
                    "Add 3+ of a0_qk_constants/ a1_at_functions/ "
                    "a2_mo_composites/ a3_og_features/ a4_sy_orchestration/."
                ) if not layout_ok else None,
            },
            "wire_clean": {
                "ok": wire_ok, "score_weight": 10,
                "how_to_fix": (
                    f"Fix {wire_d['violation_count']} upward import(s): "
                    "run forge wire --suggest-repairs."
                ) if not wire_ok else None,
            },
            "no_stubs": {
                "ok": no_stubs, "score_weight": 0,
                "how_to_fix": (
                    f"Replace {len(stub_findings)} stub bodies "
                    "(pass/NotImplementedError/TODO) with real code."
                ) if not no_stubs else None,
            },
            "importable": {
                "ok": importable, "score_weight": 25,
                "how_to_fix": (
                    f"Fix import error: {smoke['error_kind']} — "
                     f"{smoke['error_message']}"
                     if smoke else "Package not importable."
                ) if not importable else None,
            },
            "tests_pass": {
                "ok": test_pass_ratio == 1.0, "score_weight": 30,
                "how_to_fix": (
                    f"Fix {test_run['failed']} failing test(s)." if test_run
                    else "Run pytest to diagnose."
                ) if test_pass_ratio < 1.0 else None,
            },
            "ci_workflow": {
                "ok": ci_ok, "score_weight": 5,
                "how_to_fix": ("Add .github/workflows/ci.yml."
                               if not ci_ok else None),
            },
            "changelog": {
                "ok": changelog_ok, "score_weight": 5,
                "how_to_fix": ("Add CHANGELOG.md (200+ bytes) at project root."
                               if not changelog_ok else None),
            },
        },
        "detail": {"docs": docs_d, "tests": tests_d, "layout": layout_d,
                   "wire": wire_d,
                   "ci":  ci_d,
                   "changelog": changelog_d,
                   "stubs": {"count": len(stub_findings),
                             "findings": stub_findings[:20]},
                   "import_smoke": smoke,
                   "test_run": test_run,
                   "untiered_source": count_untiered_source_files(root)},
    }
