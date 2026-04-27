"""Tier a1 — pure repo walker + symbol harvester for the scout phase."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

from .body_extractor import _detect_state_markers
from .classify_tier import classify_tier, detect_effects


_SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules",
              "build", "dist", ".tox", ".mypy_cache", ".pytest_cache",
              ".ruff_cache", ".wrangler"}


def iter_python_files(root: Path) -> Iterable[Path]:
    root = root.resolve()
    for p in root.rglob("*.py"):
        if any(part in _SKIP_DIRS or part.startswith(".") for part in p.relative_to(root).parts):
            continue
        if p.name.startswith("_"):
            continue
        yield p


def harvest_repo(root: Path) -> dict:
    """Walk a repo, classify every public symbol, return a scout-shaped dict."""
    root = Path(root).resolve()
    py_files = list(iter_python_files(root))
    symbols: list[dict] = []
    tier_dist: dict[str, int] = {}
    effect_dist: dict[str, int] = {"pure": 0, "state": 0, "io": 0}

    for f in py_files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text, filename=str(f))
        except (SyntaxError, OSError):
            continue
        rel = f.relative_to(root).as_posix()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _collect_symbol(symbols, node, rel, kind="function",
                                qualname=node.name, tier_dist=tier_dist,
                                effect_dist=effect_dist)
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                self_assign, class_collect = _detect_state_markers(node)
                _collect_symbol(symbols, node, rel, kind="class",
                                qualname=node.name, tier_dist=tier_dist,
                                effect_dist=effect_dist,
                                body_signals={
                                    "has_self_assign": self_assign,
                                    "has_class_attr_collections": class_collect,
                                })
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if sub.name.startswith("_") and sub.name != "__init__":
                            continue
                        _collect_symbol(symbols, sub, rel, kind="method",
                                        qualname=f"{node.name}.{sub.name}",
                                        tier_dist=tier_dist,
                                        effect_dist=effect_dist)

    recommendations: list[str] = []
    if tier_dist.get("a4_sy_orchestration", 0) > tier_dist.get("a1_at_functions", 0):
        recommendations.append("Top-heavy at a4 — extract pure helpers into a1.")
    total = sum(effect_dist.values()) or 1
    if effect_dist["io"] / total > 0.3:
        recommendations.append("High I/O ratio — consider pushing I/O to a4 boundaries.")
    if tier_dist.get("a1_at_functions", 0) == 0 and symbols:
        recommendations.append("No pure functions detected — extract validators/parsers.")

    return {
        "schema_version": "atomadic-forge.scout/v1",
        "repo": str(root),
        "file_count": len(list(root.rglob("*"))),
        "python_file_count": len(py_files),
        "symbol_count": len(symbols),
        "tier_distribution": tier_dist,
        "effect_distribution": effect_dist,
        "symbols": symbols,
        "recommendations": recommendations,
    }


def _collect_symbol(symbols: list, node, rel_path: str, *, kind: str,
                     qualname: str, tier_dist: dict, effect_dist: dict,
                     body_signals: dict | None = None) -> None:
    effects = detect_effects(node) if not isinstance(node, ast.ClassDef) else ["pure"]
    tier = classify_tier(name=qualname, kind=kind, path=rel_path,
                         body_signals=body_signals)
    rec = {
        "name": getattr(node, "name", qualname),
        "qualname": qualname,
        "kind": kind,
        "file": rel_path,
        "lineno": getattr(node, "lineno", 0),
        "tier_guess": tier,
        "effects": effects,
        "complexity": len(ast.dump(node)),
        "has_self_assign": bool(body_signals and body_signals.get("has_self_assign")),
    }
    symbols.append(rec)
    tier_dist[tier] = tier_dist.get(tier, 0) + 1
    for e in effects:
        if e in effect_dist:
            effect_dist[e] += 1
