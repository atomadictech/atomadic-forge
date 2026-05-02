"""Tier a1 — runtime trust gate for LLM responses.

Pure-AST hallucination detector for LLM-generated responses.
Catches the failure modes that bite production agents:

  1. Mentioned imports don't resolve (catches "import foo_bar"
     where foo_bar doesn't exist)
  2. Code blocks don't parse (fabricated syntax)
  3. False capability claims (when caller supplies a known list)
  4. Placeholder URLs (`example.com/...`, `<URL>`)
  5. Stub-pattern code (pass-only, return-None-only) inside blocks

Composes nothing. Pure stdlib.

Backported from forge-deluxe-seed cycle 13. Adapted: the false-claim
check is now driven by an optional ``known_capabilities`` argument
rather than a hardwired manifest import, so this gate is reusable
across any tier-clean repo (Forge, Forge Deluxe, third-party).
"""

from __future__ import annotations

import ast
import importlib.util
import re
import sys
from dataclasses import dataclass, field
from typing import Iterable

SCHEMA: str = "atomadic-forge.trust-gate-response/v1"

_CODE_BLOCK_RE = re.compile(
    r"```(?:python|py)?\n([\s\S]*?)```", re.MULTILINE)
_URL_RE = re.compile(r"https?://[^\s)\]]+")
_CLAIM_RE = re.compile(
    r"(?i)(?:has|provides|exposes|implements|ships)\s+`([a-z][a-z0-9_]+)`")

_KNOWN_STDLIB_HEADS = frozenset({
    "os", "sys", "io", "re", "math", "json", "csv", "time",
    "datetime", "pathlib", "collections", "itertools",
    "functools", "typing", "dataclasses", "subprocess",
    "threading", "asyncio", "urllib", "http", "socket", "ssl",
    "hashlib", "hmac", "base64", "uuid", "secrets", "random",
    "logging", "argparse", "ast", "tokenize", "inspect",
    "importlib", "tempfile", "shutil", "glob", "fnmatch",
    "sqlite3", "xml", "html", "email", "concurrent",
    "contextlib", "queue", "weakref", "copy", "pickle",
    "warnings", "abc", "enum", "decimal", "fractions",
    "statistics", "operator", "string", "textwrap",
    "unicodedata", "struct", "array", "heapq", "bisect",
})


@dataclass(frozen=True)
class TrustFinding:
    severity: str       # "HIGH" | "MED" | "LOW"
    category: str       # "unresolved_import" | "syntax_error" |
                          # "false_claim" | "bad_url" | "stub_pattern"
    detail: str
    evidence: str = ""


@dataclass(frozen=True)
class TrustVerdict:
    schema: str = SCHEMA
    response_preview: str = ""
    findings: tuple[TrustFinding, ...] = field(default_factory=tuple)
    score: float = 1.0
    safe_to_act: bool = True
    code_blocks_count: int = 0
    citations_count: int = 0


def _is_known_stdlib(head: str) -> bool:
    return head in _KNOWN_STDLIB_HEADS or head in sys.builtin_module_names


def _check_imports_in_block(tree: ast.AST,
                              local_pkg_prefix: str = ""
                              ) -> list[TrustFinding]:
    out: list[TrustFinding] = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names = [node.module]
        for n in names:
            head = n.split(".", 1)[0]
            if _is_known_stdlib(head):
                continue
            if local_pkg_prefix and n.startswith(local_pkg_prefix):
                continue
            try:
                spec = importlib.util.find_spec(n)
            except (ImportError, ValueError):
                spec = None
            if spec is None:
                out.append(TrustFinding(
                    "MED", "unresolved_import",
                    f"import '{n}' does not resolve",
                    evidence=n))
    return out


def _check_capability_claims(text: str,
                                known: set[str]) -> list[TrustFinding]:
    if not known:
        return []
    out: list[TrustFinding] = []
    for m in _CLAIM_RE.finditer(text):
        cap = m.group(1).lower()
        if cap not in known:
            out.append(TrustFinding(
                "HIGH", "false_claim",
                f"response claims capability '{cap}' but it is "
                f"not in the supplied known list",
                evidence=m.group(0)))
    return out


def _check_urls(text: str) -> list[TrustFinding]:
    out: list[TrustFinding] = []
    for m in _URL_RE.finditer(text):
        url = m.group(0)
        if "..." in url or "<" in url or url.endswith("/example"):
            out.append(TrustFinding(
                "LOW", "bad_url",
                "URL looks like a placeholder",
                evidence=url))
    return out


def _check_stub_pattern(code: str) -> bool:
    """Cheap heuristic: a code block is stub-shaped if every public
    function body is just `pass` or `return None`."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    funcs = [n for n in ast.walk(tree)
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not funcs:
        return False
    stub_count = 0
    for f in funcs:
        body = [b for b in f.body
                 if not (isinstance(b, ast.Expr)
                         and isinstance(b.value, ast.Constant))]
        if len(body) == 0:
            stub_count += 1
        elif len(body) == 1 and isinstance(body[0], ast.Pass):
            stub_count += 1
        elif (len(body) == 1
                and isinstance(body[0], ast.Return)
                and (body[0].value is None
                       or (isinstance(body[0].value, ast.Constant)
                           and body[0].value.value is None))):
            stub_count += 1
    return stub_count == len(funcs)


def gate_response(response: str,
                    *,
                    known_capabilities: Iterable[str] | None = None,
                    local_pkg_prefix: str = "",
                    ) -> TrustVerdict:
    """Run all trust checks against an LLM response.

    Pure: no I/O beyond the importlib.find_spec lookups for module
    resolvability. Same input -> same output (modulo the local
    Python environment's installed packages).

    Args:
      response: the LLM-generated text to check.
      known_capabilities: optional list of capability identifiers
        the caller's project actually ships. When supplied, false
        capability claims become detectable. When None, the
        false-claim check is skipped.
      local_pkg_prefix: optional dotted prefix (e.g. "atomadic_forge")
        that should be considered locally available even if not
        installed (e.g. when checking emits before installation).
    """
    findings: list[TrustFinding] = []
    known = set(known_capabilities or ())

    code_blocks = _CODE_BLOCK_RE.findall(response)
    for code in code_blocks:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            findings.append(TrustFinding(
                "HIGH", "syntax_error",
                f"code block does not parse: {e.msg}",
                evidence=code[:100]))
            continue
        findings.extend(_check_imports_in_block(tree, local_pkg_prefix))
        if _check_stub_pattern(code):
            findings.append(TrustFinding(
                "MED", "stub_pattern",
                "code block looks like a stub "
                "(every function body is pass/return-None)"))

    findings.extend(_check_capability_claims(response, known))
    findings.extend(_check_urls(response))

    cost = {"HIGH": 0.3, "MED": 0.1, "LOW": 0.05}
    deduction = sum(cost.get(f.severity, 0.0) for f in findings)
    score = max(0.0, 1.0 - deduction)
    safe = not any(f.severity == "HIGH" for f in findings)
    citations = len(_URL_RE.findall(response))

    return TrustVerdict(
        response_preview=response[:200],
        findings=tuple(findings),
        score=score,
        safe_to_act=safe,
        code_blocks_count=len(code_blocks),
        citations_count=citations,
    )
