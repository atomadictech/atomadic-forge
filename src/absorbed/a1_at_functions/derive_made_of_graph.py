"""Source body extraction and made_of graph — Phase 3 pure logic (ported from atomadic-forge-v1)."""

from __future__ import annotations

import ast
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_MAX_FILE_BYTES = 2_000_000


@dataclass
class ExtractedBody:
    source_path: str
    source_line: int
    symbol_name: str
    language: str
    body: str
    imports: list[str]
    callers_of: list[str]
    exceptions_raised: list[str]
    # Sibling top-level names defined in the same source file that are
    # referenced from inside the extracted body.  After extraction these
    # become cross-file references and must be re-imported by the materializer.
    sibling_refs: list[str] = None  # type: ignore[assignment]
    # Tier-classification hints harvested from the body itself.  Two cheap
    # signals: ``has_self_assign`` (mutable instance state) and
    # ``has_class_attr_collections`` (mutable class-level dict/list/set).
    has_self_assign: bool = False
    has_class_attr_collections: bool = False

    def __post_init__(self) -> None:
        if self.sibling_refs is None:
            self.sibling_refs = []


def _collect_top_level_names(tree: ast.Module) -> set[str]:
    """Return every name bound at module top level (classes, functions, vars)."""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".", 1)[0])
    return names


def _detect_state_markers(target: ast.AST) -> tuple[bool, bool]:
    """Return ``(has_self_assign, has_class_attr_collections)``.

    ``has_self_assign``: the class/function body contains ``self.<attr> = …``
    (mutable instance state — strong signal for tier a2).
    ``has_class_attr_collections``: a class-level assignment like
    ``foo: list[str] = []`` (also a state signal).
    """
    has_self = False
    has_class_attr = False
    if isinstance(target, ast.ClassDef):
        for node in ast.walk(target):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if (isinstance(t, ast.Attribute)
                            and isinstance(t.value, ast.Name)
                            and t.value.id == "self"):
                        has_self = True
        for node in target.body:
            if isinstance(node, ast.Assign | ast.AnnAssign):
                value = getattr(node, "value", None)
                if isinstance(value, ast.List | ast.Dict | ast.Set | ast.ListComp | ast.DictComp | ast.SetComp):
                    has_class_attr = True
    return has_self, has_class_attr


def _extract_python_body(source_text: str, symbol_name: str) -> ExtractedBody | None:
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return None

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            imports.extend(f"{mod}.{alias.name}" if mod else alias.name for alias in node.names)

    target: ast.AST | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            if node.name == symbol_name:
                target = node
                break
    if target is None:
        return None

    lines = source_text.splitlines(keepends=True)
    start = max(0, target.lineno - 1)
    end = getattr(target, "end_lineno", None) or start + 1
    body = textwrap.dedent("".join(lines[start:end]))

    callers: list[str] = []
    for node in ast.walk(target):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                callers.append(func.id)
            elif isinstance(func, ast.Attribute):
                callers.append(func.attr)

    raised: list[str] = []
    for node in ast.walk(target):
        if isinstance(node, ast.Raise) and node.exc is not None:
            if isinstance(node.exc, ast.Name):
                raised.append(node.exc.id)
            elif isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                raised.append(node.exc.func.id)

    # ── Sibling references — names defined at module top level in the same
    # source file that are referenced from inside the extracted body.
    # After single-symbol extraction these become cross-file references.
    top_names = _collect_top_level_names(tree)
    referenced: set[str] = set()
    locally_bound: set[str] = {symbol_name}
    if isinstance(target, ast.FunctionDef | ast.AsyncFunctionDef):
        for arg in target.args.args + target.args.kwonlyargs:
            locally_bound.add(arg.arg)
        if target.args.vararg:
            locally_bound.add(target.args.vararg.arg)
        if target.args.kwarg:
            locally_bound.add(target.args.kwarg.arg)
    for node in ast.walk(target):
        if isinstance(node, ast.Name):
            referenced.add(node.id)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    locally_bound.add(t.id)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            locally_bound.add(node.name)
            for arg in node.args.args + node.args.kwonlyargs:
                locally_bound.add(arg.arg)
    sibling_refs = sorted(
        n for n in referenced
        if n in top_names and n != symbol_name and n not in locally_bound
    )

    has_self_assign, has_class_attr_collections = _detect_state_markers(target)

    return ExtractedBody(
        source_path="",
        source_line=target.lineno,
        symbol_name=symbol_name,
        language="python",
        body=body,
        imports=imports,
        callers_of=list(dict.fromkeys(callers)),
        exceptions_raised=list(dict.fromkeys(raised)),
        sibling_refs=sibling_refs,
        has_self_assign=has_self_assign,
        has_class_attr_collections=has_class_attr_collections,
    )


def _extract_regex_body(
    source_text: str, symbol_name: str, language: str
) -> ExtractedBody | None:
    pattern = re.compile(rf"\b{re.escape(symbol_name)}\b", re.MULTILINE)
    match = pattern.search(source_text)
    if not match:
        return None
    lines = source_text.splitlines(keepends=True)
    match_line = source_text.count("\n", 0, match.start())
    start = max(0, match_line - 2)
    end = min(len(lines), match_line + 40)
    body = textwrap.dedent("".join(lines[start:end]))
    body = re.sub(
        r"(?m)^\s*// Extracted from .*\n"
        r"(?:\s*// Component id: .*\n)?"
        r"\s*\n?",
        "",
        body,
    )
    if language == "rust":
        import_pat = re.compile(r"^\s*use\s+([\w:]+);", re.MULTILINE)
    else:
        import_pat = re.compile(
            r"^\s*(?:import|export)\s.*?from\s+['\"]([^'\"]+)", re.MULTILINE
        )
    imports = import_pat.findall(source_text)
    return ExtractedBody(
        source_path="",
        source_line=match_line + 1,
        symbol_name=symbol_name,
        language=language,
        body=body,
        imports=list(dict.fromkeys(imports)),
        callers_of=[],
        exceptions_raised=[],
    )


def extract_body(
    source_path: str | Path, symbol_name: str, language: str = "python"
) -> ExtractedBody | None:
    """Extract the body of one symbol from one source file. Returns None on failure."""
    p = Path(source_path)
    if not p.exists() or p.stat().st_size > _MAX_FILE_BYTES:
        return None
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    if language == "python" or p.suffix == ".py":
        result = _extract_python_body(text, symbol_name)
    else:
        result = _extract_regex_body(text, symbol_name, language)
    if result is not None:
        result.source_path = p.as_posix()
    return result


def enrich_components_with_bodies(
    plan: dict[str, Any],
    *,
    max_body_chars: int | None = None,
) -> dict[str, Any]:
    """Attach extracted source bodies to every proposed component. Mutates ``plan``.

    Also recomputes the tier when body extraction reveals a stateful class
    that was originally classified at a1 by name heuristics alone.  The
    recompute is conservative — it only PROMOTES (a1 → a2), never demotes.
    """
    for prop in plan.get("proposed_components") or []:
        sym = prop.get("source_symbol") or {}
        src_path = sym.get("path") or ""
        name = sym.get("name") or prop.get("name")
        lang = sym.get("language") or "python"
        if not src_path or not name:
            continue
        extracted = extract_body(src_path, str(name), str(lang))
        if extracted is None:
            continue
        if max_body_chars is None:
            prop["body"] = extracted.body
            prop["body_truncated"] = False
        else:
            prop["body"] = extracted.body[:max_body_chars]
            prop["body_truncated"] = len(extracted.body) > max_body_chars
        prop["imports"] = extracted.imports
        prop["callers_of"] = extracted.callers_of
        prop["exceptions_raised"] = extracted.exceptions_raised
        prop["sibling_refs"] = extracted.sibling_refs
        prop["has_self_assign"] = extracted.has_self_assign
        prop["has_class_attr_collections"] = extracted.has_class_attr_collections

        # Body-aware tier promotion: a class with mutable instance state
        # belongs in a2_mo_composites, not a1_at_functions.  Only promote;
        # don't demote (the assimilator may have legitimately placed it
        # higher because of name signals).
        kind = str(sym.get("kind") or "").lower()
        if (kind in ("class", "type")
                and (extracted.has_self_assign
                     or extracted.has_class_attr_collections)
                and prop.get("tier") == "a1_at_functions"):
            prop["tier"] = "a2_mo_composites"
            prop["tier_promotion_reason"] = (
                "body has self.<attr> = … or class-level mutable collection — "
                "ASS-ADE law promotes from a1 to a2"
            )
            # Re-stamp the component id so downstream stem/manifest paths
            # match the new tier prefix.
            cid = str(prop.get("id") or "")
            if cid.startswith("a1."):
                prop["id"] = "a2." + cid[3:]
    return plan


def derive_made_of_graph(plan: dict[str, Any]) -> dict[str, Any]:
    """Populate each component's ``made_of`` from call-graph analysis. Mutates ``plan``."""
    by_name: dict[str, str] = {}
    for prop in plan.get("proposed_components") or []:
        name = (prop.get("name") or "").lower()
        if name:
            by_name[name] = str(prop["id"])

    for prop in plan.get("proposed_components") or []:
        made_of: list[str] = list(prop.get("made_of") or [])
        for callee in prop.get("callers_of") or []:
            target_id = by_name.get((callee or "").lower())
            if target_id and target_id != prop["id"] and target_id not in made_of:
                made_of.append(target_id)
        prop["made_of"] = made_of
    return plan
