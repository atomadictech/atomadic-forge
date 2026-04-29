"""Tier a1 — pure upward-import scanner + auto-fix proposer.

Walks a tier-organized package and reports every import statement that
violates the upward-only law (lower tier importing from a higher tier).
Handles both Python (``from <pkg>.aN_… import …``) AND JavaScript / TypeScript
(``import "../aN_…/foo"`` or ``require("../aN_…/foo")``).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from ..a0_qk_constants.lang_extensions import (
    JAVASCRIPT_EXTS,
    PYTHON_EXTS,
    TYPESCRIPT_EXTS,
)
from ..a0_qk_constants.tier_names import TIER_NAMES, can_import
from .js_parser import parse_imports

_TIER_PATH_RE = re.compile(r"\.(?P<tier>a\d_[a-z_]+)\.")
_TIER_SLASH_RE = re.compile(r"(?P<tier>a\d_[a-z_]+)(?:/|$)")


def _tier_of_module(module: str) -> str | None:
    m = _TIER_PATH_RE.search(f".{module}.")
    if m:
        tier = m.group("tier")
        if tier in TIER_NAMES:
            return tier
    return None


def _tier_of_specifier(spec: str) -> str | None:
    """Pull a tier name out of a JS module specifier.

    ``"../a3_og_features/feature"`` → ``"a3_og_features"``.
    """
    if not spec:
        return None
    m = _TIER_SLASH_RE.search(spec.replace("\\", "/"))
    if m:
        tier = m.group("tier")
        if tier in TIER_NAMES:
            return tier
    return None


def _tier_of_file(path: Path, package_root: Path) -> str | None:
    parts = path.relative_to(package_root).parts
    for p in parts:
        if p in TIER_NAMES:
            return p
    return None


def _scan_python_file(py: Path, package_root: Path,
                      from_tier: str, violations: list[dict]) -> None:
    try:
        tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"),
                          filename=str(py))
    except (SyntaxError, OSError):
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        mod = node.module or ""
        to_tier = _tier_of_module(mod)
        if to_tier is None:
            continue
        if can_import(from_tier, to_tier):
            continue
        for alias in node.names:
            violations.append({
                "file": str(py.relative_to(package_root).as_posix()),
                "from_tier": from_tier,
                "to_tier": to_tier,
                "imported": alias.name,
                "language": "python",
                "proposed_fix": "",
            })


def _scan_js_file(js: Path, package_root: Path,
                   from_tier: str, language: str,
                   violations: list[dict]) -> None:
    try:
        text = js.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for spec in parse_imports(text):
        to_tier = _tier_of_specifier(spec)
        if to_tier is None:
            continue
        if can_import(from_tier, to_tier):
            continue
        violations.append({
            "file": str(js.relative_to(package_root).as_posix()),
            "from_tier": from_tier,
            "to_tier": to_tier,
            "imported": spec,
            "language": language,
            "proposed_fix": "",
        })


def scan_violations(package_root: Path) -> dict:
    """Return a wire report dict keyed by ``schema_version``.

    Polyglot: scans Python ``.py`` AND JavaScript / TypeScript files. Each
    violation includes a ``language`` field so reports can group by source.
    """
    package_root = Path(package_root).resolve()
    violations: list[dict] = []
    auto_fixable = 0

    for f in package_root.rglob("*"):
        if not f.is_file():
            continue
        if "__pycache__" in f.parts or "node_modules" in f.parts:
            continue
        from_tier = _tier_of_file(f, package_root)
        if from_tier is None:
            continue
        suffix = f.suffix.lower()
        if suffix in PYTHON_EXTS:
            _scan_python_file(f, package_root, from_tier, violations)
        elif suffix in JAVASCRIPT_EXTS:
            _scan_js_file(f, package_root, from_tier, "javascript", violations)
        elif suffix in TYPESCRIPT_EXTS:
            _scan_js_file(f, package_root, from_tier, "typescript", violations)

    return {
        "schema_version": "atomadic-forge.wire/v1",
        "source_dir": str(package_root),
        "violation_count": len(violations),
        "auto_fixable": auto_fixable,
        "violations": violations,
        "verdict": "PASS" if not violations else "FAIL",
    }
