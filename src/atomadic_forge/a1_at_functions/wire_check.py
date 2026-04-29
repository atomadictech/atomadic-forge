"""Tier a1 — pure upward-import scanner + auto-fix proposer.

Walks a tier-organized package and reports every import statement that
violates the upward-only law (lower tier importing from a higher tier).
Handles both Python (``from <pkg>.aN_… import …``) AND JavaScript / TypeScript
(``import "../aN_…/foo"`` or ``require("../aN_…/foo")``).

Lane D2 of the post-audit plan added the optional ``suggest_repairs``
mode: when enabled, every violation gets a concrete ``proposed_fix``
string and ``auto_fixable`` counts the suggestions whose minimum-edit
fix is mechanically obvious (move the violating file UP to the tier of
the symbol it imports). Heuristic, not a guarantee — the user still
decides whether the file should move or whether the import should
instead be inverted. Pure: no file writes, no exec.
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


def suggest_fix_for_violation(violation: dict) -> dict:
    """Return the violation augmented with a concrete repair proposal.

    Heuristic: when tier T imports tier U upward (T < U), the safest
    *mechanical* fix is to move the importing file from T to U — the
    file is doing higher-tier work (consuming state / orchestrating)
    and was misclassified. The alternative (push the imported symbol
    down to T) requires semantic judgement we don't have here.

    The returned dict has the original violation fields plus:
        proposed_action      — one of "move_file_up" | "review_manually"
        proposed_destination — target tier directory (e.g. "a2_mo_composites")
        fix_command          — single shell command sketch the user can adapt
        auto_fixable         — bool: is this a clean mechanical move?

    Pure: no I/O. Heuristic — for review, not auto-apply.
    """
    file = violation["file"]
    from_tier = violation["from_tier"]
    to_tier = violation["to_tier"]
    language = violation.get("language", "python")
    imported = violation.get("imported", "")

    auto_fixable = (
        from_tier in TIER_NAMES
        and to_tier in TIER_NAMES
        and from_tier != to_tier
        and language in ("python", "javascript", "typescript")
    )

    if auto_fixable:
        proposed_action = "move_file_up"
        proposed_destination = to_tier
        # File path under the package: the user's package root prefix
        # is unknown to this pure function, so the command is a sketch.
        fix_command = (
            f"mv <package_root>/{file} <package_root>/{to_tier}/"
            f"{Path(file).name}  "
            f"# then update imports referencing the old path"
        )
        reasoning = (
            f"{file} is at tier {from_tier} but imports from "
            f"tier {to_tier} (symbol: {imported!r}). The safest "
            f"mechanical fix is to relocate the file up to {to_tier}; "
            f"if the file is genuinely a {from_tier} citizen, the "
            f"imported symbol probably belongs at {from_tier} or "
            f"lower instead."
        )
    else:
        proposed_action = "review_manually"
        proposed_destination = ""
        fix_command = ""
        reasoning = (
            f"Could not auto-classify a destination for {file} "
            f"(from_tier={from_tier!r}, to_tier={to_tier!r}, "
            f"language={language!r}). Review manually."
        )

    return {
        **violation,
        "proposed_action": proposed_action,
        "proposed_destination": proposed_destination,
        "fix_command": fix_command,
        "reasoning": reasoning,
        "auto_fixable": auto_fixable,
    }


def scan_violations(
    package_root: Path,
    *,
    suggest_repairs: bool = False,
) -> dict:
    """Return a wire report dict keyed by ``schema_version``.

    Polyglot: scans Python ``.py`` AND JavaScript / TypeScript files. Each
    violation includes a ``language`` field so reports can group by source.

    ``suggest_repairs`` (Lane D2): when True, every violation is enriched
    with a ``proposed_fix`` string, the top-level ``auto_fixable`` count
    is the number of violations with a clean mechanical move, and the
    response includes a ``repair_suggestions`` summary (one entry per
    file, deduplicated). Default False keeps the v1 schema unchanged.
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

    repair_suggestions: list[dict] = []
    if suggest_repairs:
        for v in violations:
            enriched = suggest_fix_for_violation(v)
            v["proposed_fix"] = enriched["fix_command"] or enriched["reasoning"]
            v["proposed_action"] = enriched["proposed_action"]
            v["proposed_destination"] = enriched["proposed_destination"]
            if enriched["auto_fixable"]:
                auto_fixable += 1
        # One summary entry per (file, proposed_destination) pair.
        seen: set[tuple[str, str]] = set()
        for v in violations:
            key = (v["file"], v.get("proposed_destination", ""))
            if key in seen:
                continue
            seen.add(key)
            repair_suggestions.append({
                "file": v["file"],
                "from_tier": v["from_tier"],
                "proposed_action": v.get("proposed_action", "review_manually"),
                "proposed_destination": v.get("proposed_destination", ""),
                "violation_count": sum(1 for w in violations if w["file"] == v["file"]),
            })

    report: dict = {
        "schema_version": "atomadic-forge.wire/v1",
        "source_dir": str(package_root),
        "violation_count": len(violations),
        "auto_fixable": auto_fixable,
        "violations": violations,
        "verdict": "PASS" if not violations else "FAIL",
    }
    if suggest_repairs:
        report["repair_suggestions"] = repair_suggestions
    return report
