"""Tier a1 — pure signature harvesting for the Emergent Scan.

Walks a tier-organized package and emits a :class:`SymbolSignatureCard` per
public callable.  ``inputs`` and ``output`` are the type annotation texts as
they appear in source — we keep them as strings so the matcher can do
loose, normalized compatibility comparisons later (no real type system).
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable
from pathlib import Path

from ..a0_qk_constants.emergent_types import SymbolSignatureCard

_TIERS = (
    "a0_qk_constants", "a1_at_functions", "a2_mo_composites",
    "a3_og_features", "a4_sy_orchestration",
)
_PUBLIC = lambda name: not name.startswith("_") or name == "__init__"  # noqa: E731

# Effects we treat as "impure" for the heuristic.  Any function whose body
# touches one of these is marked ``is_pure=False``.
_IMPURE_HINTS = {
    "open", "print", "input", "exec", "eval",
    "Path", "subprocess", "socket", "requests", "urllib",
    "logging", "os.system", "os.environ",
}


def _module_for(file: Path, src_root: Path, package: str) -> str:
    rel = file.relative_to(src_root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join([package, *parts]) if parts else package


def _tier_of(file: Path, src_root: Path) -> str:
    parts = file.relative_to(src_root).parts
    for p in parts:
        if p in _TIERS:
            return p
    return ""


def _domain_of(stem: str) -> str:
    """Heuristic domain tag: pull the last meaningful slug from the file stem.

    ``a1_source_atomadic_v2_cherrypicker`` → ``cherrypicker``.
    ``commandsmith_render`` → ``commandsmith``.  ``ingest`` → ``ingest``.
    """
    cleaned = re.sub(r"^a\d_(?:source_)?", "", stem)
    cleaned = re.sub(r"^(atomadic_forge_seed_|atomadic_v2_)", "", cleaned)
    parts = cleaned.split("_")
    return parts[0].lower() if parts else "misc"


def _ann_text(node: ast.AST | None) -> str:
    if node is None:
        return "Any"
    try:
        return ast.unparse(node)
    except Exception:
        return "Any"


def _is_pure(fn: ast.AST) -> bool:
    for child in ast.walk(fn):
        if isinstance(child, ast.Call):
            f = child.func
            if isinstance(f, ast.Name) and f.id in _IMPURE_HINTS:
                return False
            if isinstance(f, ast.Attribute):
                root = f
                while isinstance(root, ast.Attribute):
                    root = root.value
                if isinstance(root, ast.Name) and root.id in _IMPURE_HINTS:
                    return False
        if isinstance(child, ast.Global | ast.Nonlocal):
            return False
    return True


def _docstring_first_line(node: ast.AST) -> str:
    doc = ast.get_docstring(node) or ""
    return (doc.strip().split("\n", 1)[0] if doc else "").strip()


def _harvest_function(fn: ast.AST, *, module: str, tier: str, domain: str,
                     class_qualifier: str = "") -> SymbolSignatureCard | None:
    if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
        return None
    if not _PUBLIC(fn.name):
        return None
    name = fn.name if not class_qualifier else f"{class_qualifier}.{fn.name}"
    inputs: list[tuple[str, str]] = []
    for arg in fn.args.args:
        if arg.arg in ("self", "cls"):
            continue
        inputs.append((arg.arg, _ann_text(arg.annotation)))
    for arg in fn.args.kwonlyargs:
        inputs.append((arg.arg, _ann_text(arg.annotation)))
    output = _ann_text(fn.returns)
    return SymbolSignatureCard(
        name=name,
        qualname=f"{module}.{name}",
        module=module,
        tier=tier,
        domain=domain,
        inputs=inputs,
        output=output,
        is_pure=_is_pure(fn),
        docstring=_docstring_first_line(fn),
    )


def _harvest_one_file(py_file: Path, *, module: str, tier: str,
                      domain: str) -> list[SymbolSignatureCard]:
    cards: list[SymbolSignatureCard] = []
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return cards
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            card = _harvest_function(node, module=module, tier=tier, domain=domain)
            if card:
                cards.append(card)
        elif isinstance(node, ast.ClassDef) and _PUBLIC(node.name):
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef | ast.AsyncFunctionDef):
                    card = _harvest_function(
                        sub, module=module, tier=tier, domain=domain,
                        class_qualifier=node.name,
                    )
                    if card:
                        cards.append(card)
    return cards


def _flat_tier_for(py_file: Path) -> str:
    """Best-effort tier guess for repos without a*_ folders.

    Uses pure naming heuristics from :func:`atomadic_forge.a1_at_functions.ingest.\
classify_tier` shape — but works on the file alone (good enough for the
    composition graph; mis-tier doesn't break compatibility).
    """
    name = py_file.stem.lower()
    if any(t in name for t in ("constant", "schema", "manifest", "type", "enum")):
        return "a0_qk_constants"
    if any(t in name for t in ("util", "helper", "validator", "parse", "format")):
        return "a1_at_functions"
    if any(t in name for t in ("client", "store", "registry", "manager", "core")):
        return "a2_mo_composites"
    if any(t in name for t in ("feature", "service", "pipeline", "gate", "tool")):
        return "a3_og_features"
    if any(t in name for t in ("cli", "main", "runner", "cmd", "orchestrat")):
        return "a4_sy_orchestration"
    return "a1_at_functions"


def harvest_signatures(
    src_root: Path,
    package: str = "atomadic_forge",
    tiers: Iterable[str] = _TIERS,
    *,
    skip_generated: bool = True,
) -> list[SymbolSignatureCard]:
    """Walk every ``a*/`` tier under ``src_root`` and harvest signatures.

    Falls back to **flat mode** if no tier folder is found under
    ``src_root/package/`` — so emergent-scan also works on legacy / non-ASS-ADE
    repositories (atomadic-v2-style flat layouts, the ``foo/bar.py`` shape, …).
    In flat mode each file's tier is guessed from its name and the catalogue
    contains every public callable under ``src_root``.

    ``skip_generated``: when True, skip files whose stems start with
    ``a*_source_*`` (verbatim assimilator output).
    """
    src_root = Path(src_root)
    cards: list[SymbolSignatureCard] = []
    pkg_root = src_root / package
    have_any_tier = pkg_root.exists() and any(
        (pkg_root / t).exists() for t in tiers
    )

    if have_any_tier:
        for tier in tiers:
            tdir = pkg_root / tier
            if not tdir.exists():
                continue
            for py_file in sorted(tdir.glob("*.py")):
                if py_file.name.startswith("_"):
                    continue
                if skip_generated and py_file.stem.startswith((
                        "a0_source_", "a1_source_", "a2_source_",
                        "a3_source_", "a4_source_")):
                    continue
                module = _module_for(py_file, src_root, package)
                domain = _domain_of(py_file.stem)
                cards.extend(_harvest_one_file(py_file, module=module,
                                               tier=tier, domain=domain))
        return cards

    # ── Flat mode — walk every .py, infer tier from filename heuristics.
    walk_root = src_root
    package_for_module = package
    if not pkg_root.exists():
        # Caller passed a repo root, not a src layout.  Use the repo as the
        # walk root and fabricate a one-level package alias from the directory.
        walk_root = src_root
        package_for_module = src_root.name.replace("-", "_")
    for py_file in sorted(walk_root.rglob("*.py")):
        if py_file.name.startswith("_"):
            continue
        # Use parts RELATIVE to walk_root so a hidden parent like
        # ``.pytest_basetemp`` doesn't accidentally exclude every test fixture.
        try:
            rel_parts = py_file.relative_to(walk_root).parts
        except ValueError:
            rel_parts = py_file.parts
        if any(part.startswith((".", "__pycache__")) for part in rel_parts):
            continue
        if any(part in {"tests", "test", "build", "dist", ".venv", "venv"}
               for part in rel_parts):
            continue
        try:
            rel = py_file.relative_to(walk_root).with_suffix("")
            module_parts = list(rel.parts)
            if module_parts and module_parts[-1] == "__init__":
                module_parts.pop()
            module = ".".join([package_for_module, *module_parts]) if module_parts else package_for_module
        except ValueError:
            module = package_for_module
        tier = _flat_tier_for(py_file)
        domain = _domain_of(py_file.stem)
        cards.extend(_harvest_one_file(py_file, module=module,
                                       tier=tier, domain=domain))
    return cards
