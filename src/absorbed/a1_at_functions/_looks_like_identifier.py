"""Tier a1 — exported-API-vs-docstring check.

Pure-AST gate that catches the failure mode where a module's
docstring promises a public function/class that is never actually
defined. (Real example from a sister project: a body-fill emit
shipped a docstring claiming ``release_notes_from_rows`` while
the actual file held only the dataclasses + a private helper.)

Existing certify gates (tier-law / wire / pytest) all passed on
that file. This check would have caught it.

Patterns recognised in the docstring:
  * Backticked identifiers in code spans:    ``release_notes_from_rows``
  * Sphinx-style signature blocks:           ``foo_bar(x, y)``

A claim resolves when the identifier appears as a top-level
FunctionDef / AsyncFunctionDef / ClassDef / Assign / AnnAssign /
Import. Snake_case unresolved claims are fatal in permissive
mode (they look like function names that MUST be defined);
PascalCase tolerated unless ``strict=True``.

Backported from forge-deluxe-seed cycle 15.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

SCHEMA: str = "atomadic-forge.exported-api-check/v1"

_IGNORE = frozenset({
    "self", "cls", "args", "kwargs", "True", "False", "None",
    "str", "int", "list", "dict", "tuple", "set", "bool", "float",
    "bytes", "Path", "Any", "Optional", "Callable", "Union",
    "Dict", "List", "Tuple", "Set", "Iterator", "Iterable",
    "AsyncIterator", "Generator", "Awaitable", "Final", "ClassVar",
    "ASCII", "JSON", "YAML", "XML", "HTML", "CSS", "API", "CLI",
    "MCP", "URL", "HTTP", "HTTPS",
})

_BACKTICK_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]+)`")
_SIGNATURE_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]+)\s*\(", re.MULTILINE)


@dataclass(frozen=True)
class APIClaim:
    name: str
    source: str       # "backtick" | "signature"


@dataclass(frozen=True)
class APICheckResult:
    schema: str = SCHEMA
    claims_found: tuple[APIClaim, ...] = field(default_factory=tuple)
    resolved: tuple[str, ...] = field(default_factory=tuple)
    unresolved: tuple[str, ...] = field(default_factory=tuple)
    ok: bool = True
    detail: str = ""


def _extract_module_docstring(tree: ast.Module) -> str:
    if not tree.body:
        return ""
    first = tree.body[0]
    if (isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)):
        return first.value.value
    return ""


def _top_level_names(tree: ast.Module) -> set[str]:
    out: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    out.add(tgt.id)
                elif isinstance(tgt, ast.Tuple):
                    for elt in tgt.elts:
                        if isinstance(elt, ast.Name):
                            out.add(elt.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                out.add(node.target.id)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                out.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                out.add(alias.asname or alias.name.split(".")[0])
    return out


def _looks_like_identifier(token: str) -> bool:
    if not token:
        return False
    if token in _IGNORE:
        return False
    if len(token) < 4:
        return False
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", token):
        return False
    return True


def extract_claims(docstring: str) -> list[APIClaim]:
    """Pure: docstring -> list of APIClaim (named exports the
    docstring promises)."""
    out: list[APIClaim] = []
    seen: set[str] = set()
    for m in _BACKTICK_RE.finditer(docstring):
        name = m.group(1)
        if name in seen or not _looks_like_identifier(name):
            continue
        seen.add(name)
        out.append(APIClaim(name=name, source="backtick"))
    for m in _SIGNATURE_RE.finditer(docstring):
        name = m.group(1)
        if name in seen or not _looks_like_identifier(name):
            continue
        seen.add(name)
        out.append(APIClaim(name=name, source="signature"))
    return out


def check_exported_api(source: str,
                          *, strict: bool = False
                          ) -> APICheckResult:
    """Verify every public-API claim in the module docstring resolves
    to a top-level definition.

    ``strict``: require ALL claims to resolve (snake_case AND
    PascalCase). Permissive (default): only snake_case claims are
    fatal — PascalCase often comes from imports we don't track.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return APICheckResult(ok=False,
                                detail=f"syntax error: {e.msg}")

    docstring = _extract_module_docstring(tree)
    if not docstring:
        return APICheckResult(
            ok=True, detail="no module docstring; nothing to check")

    claims = extract_claims(docstring)
    top_names = _top_level_names(tree)

    resolved: list[str] = []
    unresolved: list[str] = []
    for c in claims:
        if c.name in top_names:
            resolved.append(c.name)
        else:
            unresolved.append(c.name)

    fatal_unresolved: list[str] = []
    for name in unresolved:
        is_snake = "_" in name and name == name.lower()
        if strict or is_snake:
            fatal_unresolved.append(name)

    ok = len(fatal_unresolved) == 0

    if ok and unresolved:
        detail = (f"{len(resolved)} resolved, "
                    f"{len(unresolved)} unresolved (non-fatal)")
    elif ok:
        detail = f"all {len(resolved)} claim(s) resolved"
    else:
        detail = (f"{len(fatal_unresolved)} claimed identifier(s) "
                    f"not defined: {', '.join(fatal_unresolved)}")

    return APICheckResult(
        claims_found=tuple(claims),
        resolved=tuple(resolved),
        unresolved=tuple(unresolved),
        ok=ok,
        detail=detail,
    )
