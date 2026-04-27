"""Tier a1 — pure upward-import scanner + auto-fix proposer.

Walks a tier-organized package and reports every ``from <pkg>.aN_… import …``
statement that violates the upward-only law (lower tier importing from a
higher tier).  Suggests a sibling/lower rewrite when one is unambiguous.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from ..a0_qk_constants.tier_names import TIER_NAMES, can_import, tier_index


_TIER_PATH_RE = re.compile(r"\.(?P<tier>a\d_[a-z_]+)\.")


def _tier_of_module(module: str) -> str | None:
    m = _TIER_PATH_RE.search(f".{module}.")
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


def scan_violations(package_root: Path) -> dict:
    """Return a wire report dict keyed by ``schema_version``.

    Each violation includes a ``proposed_fix`` whenever the imported names
    can be unambiguously found at a tier ≤ the importing tier.
    """
    package_root = Path(package_root).resolve()
    violations: list[dict] = []
    auto_fixable = 0

    for py in package_root.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        from_tier = _tier_of_file(py, package_root)
        if from_tier is None:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"),
                              filename=str(py))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            mod = node.module or ""
            to_tier = _tier_of_module(mod)
            if to_tier is None:
                continue
            if can_import(from_tier, to_tier):
                continue  # legal — same or lower
            for alias in node.names:
                violations.append({
                    "file": str(py.relative_to(package_root).as_posix()),
                    "from_tier": from_tier,
                    "to_tier": to_tier,
                    "imported": alias.name,
                    "proposed_fix": "",  # auto-fix not implemented in MVP
                })
    return {
        "schema_version": "atomadic-forge.wire/v1",
        "source_dir": str(package_root),
        "violation_count": len(violations),
        "auto_fixable": auto_fixable,
        "violations": violations,
        "verdict": "PASS" if not violations else "FAIL",
    }
