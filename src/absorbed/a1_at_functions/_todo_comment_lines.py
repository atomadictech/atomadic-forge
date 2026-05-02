"""Tier a1 — pure stub-body detector.

When an LLM emits a file with ``pass``, ``raise NotImplementedError``, or
a ``# TODO`` / ``# Implement me!`` placeholder, the file *looks* like a
real symbol but won't run.  We must catch this so the certify score can't
be gamed by emitting empty shells.

The detector inspects function/class bodies via AST; placeholder comments
are matched via Python tokenization so docstrings and prompt text are not
mistaken for code stubs.  Returns one record per stub-shaped symbol with
the file path, qualname, and the specific stub kind detected.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from collections.abc import Iterable
from pathlib import Path
from typing import Literal, TypedDict

StubKind = Literal["pass_only", "not_implemented", "comment_only",
                   "todo_marker"]


class StubFinding(TypedDict):
    file: str            # repo-relative
    qualname: str
    lineno: int
    kind: StubKind
    excerpt: str         # one line, for prompt feedback


_TODO_RE = re.compile(
    r"#\s*(TODO|FIXME|XXX|HACK|implement\s+me|implement\s+this|"
    r"add\s+actual|fill\s+this)\b",
    re.IGNORECASE,
)


def _function_body_is_pass_only(fn: ast.AST) -> bool:
    if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
        return False
    body = list(fn.body)
    # Strip docstring.
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    if not body:
        return True
    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return True
    return False


def _function_body_raises_not_implemented(fn: ast.AST) -> bool:
    if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
        return False
    for node in ast.walk(fn):
        if isinstance(node, ast.Raise) and node.exc is not None:
            target = node.exc
            if isinstance(target, ast.Call):
                target = target.func
            if isinstance(target, ast.Name) and target.id == "NotImplementedError":
                return True
            if isinstance(target, ast.Attribute) and target.attr == "NotImplementedError":
                return True
    return False


def _todo_comment_lines(src: str) -> list[tuple[int, str]]:
    """Return placeholder comments only, excluding docstrings and strings."""
    out: list[tuple[int, str]] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(src).readline)
        for tok in tokens:
            if tok.type == tokenize.COMMENT and _TODO_RE.search(tok.string):
                out.append((tok.start[0], tok.line.rstrip()))
    except tokenize.TokenError:
        return []
    return out


def detect_stubs_in_file(path: Path, *, repo_root: Path | None = None
                         ) -> list[StubFinding]:
    """Return a finding per stub-shaped function/class in ``path``.

    Only reports public callables (no leading underscore) so we don't flag
    private helpers that legitimately ``pass``.
    """
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src, filename=str(path))
    except (SyntaxError, OSError):
        return []
    rel = (path.relative_to(repo_root).as_posix()
            if repo_root else path.as_posix())
    src_lines = src.splitlines()
    out: list[StubFinding] = []

    todo_lines = _todo_comment_lines(src)

    def add(qualname: str, lineno: int, kind: StubKind, excerpt: str) -> None:
        out.append(StubFinding(file=rel, qualname=qualname, lineno=lineno,
                                kind=kind, excerpt=excerpt[:120]))

    def visit(node: ast.AST, prefix: str = "") -> None:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name.startswith("_") and node.name != "__init__":
                return
            qual = f"{prefix}{node.name}" if prefix else node.name
            line = src_lines[node.lineno - 1] if 0 < node.lineno <= len(src_lines) else ""
            if _function_body_is_pass_only(node):
                add(qual, node.lineno, "pass_only", line)
            elif _function_body_raises_not_implemented(node):
                add(qual, node.lineno, "not_implemented", line)
            return
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                visit(sub, prefix=f"{node.name}.")
            return

    for node in tree.body:
        visit(node)

    # File-level TODO/FIXME markers — surface even when the body otherwise looks fine.
    for ln, line in todo_lines:
        if not any(f["lineno"] == ln for f in out):
            kind: StubKind = "todo_marker"
            add(f"<line {ln}>", ln, kind, line.strip())

    return out


def detect_stubs(*, package_root: Path,
                 only_emitted: Iterable[Path] | None = None
                 ) -> list[StubFinding]:
    """Walk a tier package (or a specific list of files) and aggregate stubs."""
    package_root = Path(package_root)
    files: Iterable[Path]
    if only_emitted is not None:
        files = [Path(p) for p in only_emitted]
    else:
        files = package_root.rglob("*.py")
    out: list[StubFinding] = []
    for f in files:
        if not f.exists() or "__pycache__" in f.parts or f.name == "__init__.py":
            continue
        out.extend(detect_stubs_in_file(f, repo_root=package_root))
    return out


def stub_penalty(findings: list[StubFinding]) -> int:
    """Cap-aware penalty for the certify score: 8 points per stub, max 40."""
    return min(40, 8 * len(findings))
