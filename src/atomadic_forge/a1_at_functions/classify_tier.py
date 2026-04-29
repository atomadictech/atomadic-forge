"""Tier a1 — pure tier classification.

Word-boundary token matching (the substring-bug-fixed version) plus optional
body-aware promotion: any class with mutable instance state (``self.<attr>
= …``) is promoted to ``a2_mo_composites`` regardless of name signals.
"""

from __future__ import annotations

import re
from typing import Any

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")

_CONTRACT = frozenset({"constant", "const", "schema", "manifest", "token",
                       "invariant", "proof"})
_ATOM = frozenset({"button", "textarea", "input", "validator", "validate",
                   "format", "parse", "atom"})
_COMPOSITE = frozenset({"engine", "service", "client", "manager", "store",
                        "hook", "calculator", "molecule"})
_FEATURE = frozenset({"registry", "gateway", "vault", "module", "feature",
                      "workflow", "page", "screen", "organism"})
_ORCHESTRATION = frozenset({"server", "router", "orchestrator", "bridge",
                            "runtime", "system", "main", "mcp", "cli"})


def word_tokens(text: str) -> set[str]:
    """Tokenize on word boundaries and split camelCase.

    ``"AgenticSwarm"`` → ``{"agentic", "swarm"}``; ``"atomadic-v2"`` →
    ``{"atomadic", "v2"}`` — no false-positive on ``"atom"``.
    """
    raw = _WORD_RE.findall(text)
    out: set[str] = set()
    for word in raw:
        for piece in re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z0-9]+|[A-Z]+", word):
            if piece:
                out.add(piece.lower())
        out.add(word.lower())
    return out


def classify_tier(*, name: str, kind: str, path: str = "",
                  body_signals: dict[str, Any] | None = None) -> str:
    """Return the canonical tier directory for a symbol.

    ``body_signals`` (optional) carries ``has_self_assign`` /
    ``has_class_attr_collections`` flags from the body extractor.  When set,
    a class with mutable instance state is forced to a2.
    """
    tokens = word_tokens(f"{path} {name} {kind}")
    stateful = bool(body_signals and (
        body_signals.get("has_self_assign")
        or body_signals.get("has_class_attr_collections")
    ))

    if kind in ("class", "type") and stateful:
        if tokens & _ORCHESTRATION:
            return "a4_sy_orchestration"
        if tokens & _FEATURE:
            return "a3_og_features"
        return "a2_mo_composites"

    if tokens & _CONTRACT:
        return "a0_qk_constants"
    if tokens & _ATOM:
        return "a1_at_functions"
    if tokens & _COMPOSITE:
        return "a2_mo_composites"
    if tokens & _FEATURE:
        return "a3_og_features"
    if tokens & _ORCHESTRATION:
        return "a4_sy_orchestration"

    if kind == "function":
        return "a1_at_functions"
    if kind in ("class", "type"):
        return "a2_mo_composites"
    return "a1_at_functions"


_IO_ROOT_MODULES = frozenset({"urllib", "requests", "httpx", "socket",
                              "subprocess", "shutil", "os", "sqlite3",
                              "boto3", "smtplib"})
_IO_BUILTINS = frozenset({"open", "print", "input", "connect"})


def detect_effects(node: Any) -> list[str]:
    """Cheap effect inference on an ``ast.AST`` node body."""
    import ast

    effects: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            f = child.func
            if isinstance(f, ast.Name) and f.id in _IO_BUILTINS:
                effects.append("io")
            elif isinstance(f, ast.Attribute):
                root = f
                while isinstance(root, ast.Attribute):
                    root = root.value
                if isinstance(root, ast.Name) and root.id in _IO_ROOT_MODULES:
                    effects.append("io")
                if f.attr in ("write", "send", "post", "put", "delete",
                               "execute", "commit"):
                    effects.append("state")
        if isinstance(child, ast.Global | ast.Nonlocal):
            effects.append("state")
    if not effects:
        return ["pure"]
    seen: list[str] = []
    for e in effects:
        if e not in seen:
            seen.append(e)
    return seen
