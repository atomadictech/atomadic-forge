"""Tier a1 — pure repo walker + symbol harvester for the scout phase.

Walks Python AND JavaScript / TypeScript. Each file is classified into a
monadic tier and reduced to a list of ``symbols`` with the same shape across
languages so downstream stages (cherry, finalize, certify) work polyglot.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

from ..a0_qk_constants.lang_extensions import (
    ALL_SOURCE_EXTS,
    IGNORED_DIRS,
    JAVASCRIPT_EXTS,
    PYTHON_EXTS,
    TYPESCRIPT_EXTS,
    file_class_for_path,
    path_parts_contain_ignored_dir,
)
from .body_extractor import _detect_state_markers
from .classify_tier import classify_tier, detect_effects
from .js_parser import classify_js_tier, detect_js_effects, parse_surface

# Backwards-compatible alias — keep _SKIP_DIRS available for any third-party
# code that imports it.  The canonical list lives in lang_extensions.IGNORED_DIRS.
_SKIP_DIRS = IGNORED_DIRS


def _under_skip_dir(rel_parts: tuple[str, ...]) -> bool:
    """Return True if any segment of the path is an ignored directory.

    A leading-dot segment is only treated as ignored when it matches an
    entry in IGNORED_DIRS (e.g. ``.github``, ``.venv``).  Application
    folders that legitimately start with a dot (none today, but keeping
    the door open) won't be skipped just for the leading dot — only for
    being on the explicit list.
    """
    return path_parts_contain_ignored_dir(rel_parts)


def iter_python_files(root: Path) -> Iterable[Path]:
    root = root.resolve()
    for p in root.rglob("*.py"):
        if _under_skip_dir(p.relative_to(root).parts):
            continue
        if p.name.startswith("_"):
            continue
        yield p


def iter_source_files(root: Path) -> Iterable[Path]:
    """Yield every Python / JS / TS file under ``root`` we want to classify.

    Filters out vendored / build / cache directories. Hidden filenames
    starting with ``_`` (Python convention) are skipped, but JS files
    starting with ``_`` are kept — the underscore is meaningless in JS.
    """
    root = root.resolve()
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        suffix = p.suffix.lower()
        if suffix not in ALL_SOURCE_EXTS:
            continue
        rel_parts = p.relative_to(root).parts
        if _under_skip_dir(rel_parts):
            continue
        if suffix in PYTHON_EXTS and p.name.startswith("_"):
            continue
        yield p


def _harvest_python_file(f: Path, rel: str, *, symbols: list[dict],
                          tier_dist: dict[str, int],
                          effect_dist: dict[str, int]) -> None:
    try:
        text = f.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(text, filename=str(f))
    except (SyntaxError, OSError):
        return
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
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
                if isinstance(sub, ast.FunctionDef | ast.AsyncFunctionDef):
                    if sub.name.startswith("_") and sub.name != "__init__":
                        continue
                    _collect_symbol(symbols, sub, rel, kind="method",
                                    qualname=f"{node.name}.{sub.name}",
                                    tier_dist=tier_dist,
                                    effect_dist=effect_dist)


def _harvest_js_file(f: Path, rel: str, language: str, *, symbols: list[dict],
                      tier_dist: dict[str, int],
                      effect_dist: dict[str, int]) -> None:
    try:
        text = f.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    surface = parse_surface(text)
    file_tier = classify_js_tier(path=rel, surface=surface)
    file_effects = detect_js_effects(text)

    # Track the file itself as a symbol so even an empty-export module
    # (e.g. an HTML-glue static page) shows up in scout output.
    file_record = {
        "name": f.name,
        "qualname": f.stem,
        "kind": "module",
        "file": rel,
        "lineno": 1,
        "tier_guess": file_tier,
        "suggested_tier": file_tier,
        "effects": file_effects,
        "complexity": surface.statement_count,
        "has_self_assign": False,
        "language": language,
        "exports": surface.all_exports,
        "imports": surface.imports,
    }
    symbols.append(file_record)
    tier_dist[file_tier] = tier_dist.get(file_tier, 0) + 1
    for e in file_effects:
        if e in effect_dist:
            effect_dist[e] += 1

    # Also surface each named export as its own symbol so cherry-pick + emergent
    # treat JS like Python: pick by qualname.
    for name in surface.exported_functions:
        _push_js_symbol(symbols, name, "function", rel, file_tier,
                         language, ["pure"], tier_dist, effect_dist)
    for name in surface.exported_classes:
        _push_js_symbol(symbols, name, "class", rel, file_tier,
                         language, ["state"], tier_dist, effect_dist)
    for name in surface.exported_consts:
        _push_js_symbol(symbols, name, "const", rel, file_tier,
                         language, ["pure"], tier_dist, effect_dist)


def _push_js_symbol(symbols: list[dict], name: str, kind: str, rel: str,
                     tier: str, language: str, effects: list[str],
                     tier_dist: dict[str, int],
                     effect_dist: dict[str, int]) -> None:
    rec = {
        "name": name,
        "qualname": name,
        "kind": kind,
        "file": rel,
        "lineno": 0,
        "tier_guess": tier,
        "suggested_tier": tier,
        "effects": effects,
        "complexity": 0,
        "has_self_assign": False,
        "language": language,
    }
    symbols.append(rec)
    tier_dist[tier] = tier_dist.get(tier, 0) + 1
    for e in effects:
        if e in effect_dist:
            effect_dist[e] += 1


def _file_class_counts(root: Path) -> dict[str, int]:
    """Count every file under ``root`` by class (source / docs / config /
    asset / other), respecting IGNORED_DIRS.  Used by harvest_repo and
    by certify so non-source files don't harsh the layout score."""
    counts = {"source": 0, "documentation": 0, "config": 0, "asset": 0, "other": 0}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel_parts = p.relative_to(root).parts
        if _under_skip_dir(rel_parts):
            continue
        cls = file_class_for_path(p.as_posix())
        counts[cls] = counts.get(cls, 0) + 1
    return counts


def harvest_repo(root: Path) -> dict:
    """Walk a repo, classify every public symbol, return a scout-shaped dict."""
    root = Path(root).resolve()
    src_files = list(iter_source_files(root))
    file_class_counts = _file_class_counts(root)
    symbols: list[dict] = []
    tier_dist: dict[str, int] = {}
    effect_dist: dict[str, int] = {"pure": 0, "state": 0, "io": 0}

    py_count = 0
    js_count = 0
    ts_count = 0

    for f in src_files:
        rel = f.relative_to(root).as_posix()
        suffix = f.suffix.lower()
        if suffix in PYTHON_EXTS:
            py_count += 1
            _harvest_python_file(f, rel, symbols=symbols,
                                  tier_dist=tier_dist,
                                  effect_dist=effect_dist)
        elif suffix in JAVASCRIPT_EXTS:
            js_count += 1
            _harvest_js_file(f, rel, "javascript", symbols=symbols,
                              tier_dist=tier_dist,
                              effect_dist=effect_dist)
        elif suffix in TYPESCRIPT_EXTS:
            ts_count += 1
            _harvest_js_file(f, rel, "typescript", symbols=symbols,
                              tier_dist=tier_dist,
                              effect_dist=effect_dist)

    languages = {
        "python": py_count,
        "javascript": js_count,
        "typescript": ts_count,
    }
    primary = max(languages, key=lambda k: languages[k]) if any(languages.values()) else "python"

    recommendations: list[str] = []
    if tier_dist.get("a4_sy_orchestration", 0) > tier_dist.get("a1_at_functions", 0):
        recommendations.append("Top-heavy at a4 — extract pure helpers into a1.")
    total = sum(effect_dist.values()) or 1
    if effect_dist["io"] / total > 0.3:
        recommendations.append("High I/O ratio — consider pushing I/O to a4 boundaries.")
    if tier_dist.get("a1_at_functions", 0) == 0 and symbols:
        recommendations.append("No pure functions detected — extract validators/parsers.")
    if js_count + ts_count > 0 and not any(
        f"/{t}/" in s["file"] or s["file"].startswith(f"{t}/")
        for s in symbols if s.get("language") in ("javascript", "typescript")
        for t in ("a0_qk_constants", "a1_at_functions", "a2_mo_composites",
                   "a3_og_features", "a4_sy_orchestration")
    ):
        recommendations.append(
            "JS/TS files are not yet split into aN_* tier directories — "
            "see suggested_tier per file in symbols[]."
        )

    return {
        "schema_version": "atomadic-forge.scout/v1",
        "repo": str(root),
        # `file_count` is the raw rglob walk (legacy) — matches v1 callers.
        "file_count": len(list(root.rglob("*"))),
        # `file_class_counts` excludes IGNORED_DIRS and breaks files into
        # source / documentation / config / asset / other.  Tier-layout
        # scoring should use this, not the raw walk.
        "file_class_counts": file_class_counts,
        "python_file_count": py_count,
        "javascript_file_count": js_count,
        "typescript_file_count": ts_count,
        "language_distribution": languages,
        "primary_language": primary,
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
