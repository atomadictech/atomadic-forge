"""Tier a1 — pure LSP JSON-RPC dispatcher for forge-lsp.

Golden Path Lane D W12 deliverable. The pure dispatcher lives here;
the stdio framing (Content-Length headers) lives in a3
``lsp_server.py``.

Implements the slice of the LSP spec that gives `.forge` sidecar
files diagnostics + hover in VS Code / Neovim:

  initialize / initialized                — capability handshake
  shutdown / exit                          — clean shutdown
  textDocument/didOpen                     — open file → diagnostics
  textDocument/didChange                   — re-validate on edit
  textDocument/didSave                     — re-validate on save
  textDocument/didClose                    — clear diagnostics
  textDocument/hover                       — show sidecar symbol info
  textDocument/publishDiagnostics          — server-initiated; emitted
                                             after each didOpen/Change/Save
  textDocument/definition                  — goto-source from
                                             `name: login` line in
                                             foo.py.forge → foo.py:login

Pure: takes a request + an in-memory document store and returns
zero or more responses + zero or more notifications. The stdio
loop owns the actual reading + writing.

Dispatcher state lives in a tiny ``LspState`` dict (open documents
text by URI). It IS mutated across calls — that's fine; the I/O
boundary is a3, not a1, and the state is per-session.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, TypedDict
from urllib.parse import unquote, urlparse

from .. import __version__
from ..a0_qk_constants.error_codes import SIDECAR_S_TO_F
from .sidecar_parser import parse_sidecar_text
from .sidecar_validator import validate_sidecar


SERVER_NAME = "forge-lsp"


# --- LSP error codes -------------------------------------------------------
_LSP_INVALID_REQUEST = -32600
_LSP_METHOD_NOT_FOUND = -32601
_LSP_INVALID_PARAMS = -32602
_LSP_INTERNAL = -32603


# --- session state --------------------------------------------------------

class LspState(TypedDict, total=False):
    documents: dict[str, str]   # uri → current text
    initialized: bool
    shutdown_requested: bool


def new_state() -> LspState:
    return LspState(documents={}, initialized=False,
                     shutdown_requested=False)


# --- helpers --------------------------------------------------------------

def uri_to_path(uri: str) -> Path:
    """Convert ``file:///c%3A/path/file.py`` to a Path."""
    parsed = urlparse(uri)
    path = unquote(parsed.path)
    # Windows file URIs come through as /C:/...
    if path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]
    return Path(path)


def _ok(msg_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _err(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id,
            "error": {"code": code, "message": message}}


def _notification(method: str, params: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "method": method, "params": params}


# --- diagnostics ----------------------------------------------------------

def _line_for_symbol_in_sidecar(text: str, symbol_name: str) -> int:
    """Best-effort: find the line a `name: <symbol_name>` appears on
    in the sidecar YAML. 0-indexed for LSP. Returns 0 when not found."""
    if not symbol_name:
        return 0
    # Look for `name: foo` or `- name: foo` patterns.
    pattern = re.compile(rf"^\s*-?\s*name\s*:\s*{re.escape(symbol_name)}\s*$",
                          re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return 0
    return text.count("\n", 0, m.start())


def compute_diagnostics(
    *,
    sidecar_text: str,
    sidecar_uri: str,
) -> list[dict[str, Any]]:
    """Run the sidecar parser + validator against the in-memory text
    and the sibling source file (resolved via the URI naming
    convention foo.py.forge → foo.py). Returns LSP Diagnostic[].
    """
    diagnostics: list[dict[str, Any]] = []
    parse = parse_sidecar_text(sidecar_text, source=sidecar_uri)
    for err in parse.get("errors", []):
        diagnostics.append({
            "range": {"start": {"line": 0, "character": 0},
                       "end":   {"line": 0, "character": 1}},
            "severity": 1,  # 1 = Error
            "source": "forge-lsp",
            "code": "F0100",
            "message": err,
        })
    if parse.get("sidecar") is None:
        return diagnostics

    sidecar_path = uri_to_path(sidecar_uri)
    # Strip the .forge suffix to get the source path.
    if sidecar_path.suffix.lower() != ".forge":
        return diagnostics
    source_path = sidecar_path.with_suffix("")
    if not source_path.exists():
        diagnostics.append({
            "range": {"start": {"line": 0, "character": 0},
                       "end":   {"line": 0, "character": 1}},
            "severity": 2,  # 2 = Warning
            "source": "forge-lsp",
            "code": "F0100",
            "message": (
                f"sidecar present but source file not found at "
                f"{source_path.name!r}; diagnostics limited"
            ),
        })
        return diagnostics
    try:
        source_text = source_path.read_text(encoding="utf-8")
    except OSError:
        return diagnostics

    rep = validate_sidecar(parse["sidecar"],
                            source_text=source_text,
                            source_path=source_path)
    for f in rep.get("findings", []):
        symbol = f.get("symbol", "")
        line = _line_for_symbol_in_sidecar(sidecar_text, symbol)
        sev = {"error": 1, "warn": 2, "info": 3}.get(f.get("severity", "warn"),
                                                       2)
        diagnostics.append({
            "range": {"start": {"line": line, "character": 0},
                       "end":   {"line": line, "character": 100}},
            "severity": sev,
            "source": "forge-lsp",
            "code": f.get("f_code") or f.get("code", ""),
            "message": f.get("message", ""),
        })
    return diagnostics


def compute_hover(
    *,
    sidecar_text: str,
    line: int,
) -> dict[str, Any] | None:
    """Return an LSP Hover dict when the cursor is on a `name:`
    line of a sidecar; otherwise None.

    The hover content is markdown summarising the symbol's effect,
    tier, compose_with, and proves clauses.
    """
    parse = parse_sidecar_text(sidecar_text)
    if parse.get("sidecar") is None:
        return None
    lines = sidecar_text.splitlines()
    if line < 0 or line >= len(lines):
        return None
    # Find which symbol block this line belongs to.
    target_name: str | None = None
    for i in range(line, -1, -1):
        m = re.match(r"^\s*-?\s*name\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*$",
                     lines[i])
        if m:
            target_name = m.group(1)
            break
    if not target_name:
        return None
    sc = parse["sidecar"]
    sym = next((s for s in sc.get("symbols", [])
                if s.get("name") == target_name), None)
    if sym is None:
        return None
    md_parts = [
        f"**{target_name}**",
        f"effect: `{sym.get('effect', '?')}`",
    ]
    if sym.get("tier"):
        md_parts.append(f"tier: `{sym['tier']}`")
    if sym.get("compose_with"):
        md_parts.append("composes with:\n"
                         + "\n".join(f"- `{c}`" for c in sym["compose_with"]))
    if sym.get("proves"):
        md_parts.append("proves:\n"
                         + "\n".join(f"- `{p}`" for p in sym["proves"]))
    if sym.get("notes"):
        md_parts.append("notes:\n"
                         + "\n".join(f"- {n}" for n in sym["notes"]))
    return {
        "contents": {"kind": "markdown", "value": "\n\n".join(md_parts)},
    }


def compute_definition(
    *,
    sidecar_text: str,
    sidecar_uri: str,
    line: int,
) -> dict[str, Any] | None:
    """Resolve goto-source: `- name: login` line in foo.py.forge
    → foo.py at the def/class line for `login`."""
    lines = sidecar_text.splitlines()
    if line < 0 or line >= len(lines):
        return None
    m = re.match(r"^\s*-?\s*name\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*$",
                 lines[line])
    if not m:
        return None
    target_name = m.group(1)
    sidecar_path = uri_to_path(sidecar_uri)
    if sidecar_path.suffix.lower() != ".forge":
        return None
    source_path = sidecar_path.with_suffix("")
    if not source_path.exists():
        return None
    try:
        source_text = source_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef)) and node.name == target_name:
            return {
                "uri": "file:///" + str(source_path).replace("\\", "/"),
                "range": {
                    "start": {"line": (node.lineno or 1) - 1, "character": 0},
                    "end":   {"line": (node.lineno or 1) - 1,
                               "character": 100},
                },
            }
    return None


# --- dispatch -------------------------------------------------------------

def dispatch_request(
    request: dict[str, Any],
    *,
    state: LspState,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Route one LSP request and return (responses, notifications).

    notifications are server-initiated messages (e.g. publishDiagnostics)
    emitted in response to didOpen / didChange / didSave.
    """
    if not isinstance(request, dict):
        return ([_err(None, _LSP_INVALID_REQUEST,
                       "request must be a JSON object")], [])
    method = request.get("method")
    msg_id = request.get("id")
    is_notification = "id" not in request
    params = request.get("params") or {}
    if not isinstance(method, str):
        return ([_err(msg_id, _LSP_INVALID_REQUEST,
                       "request missing string `method`")], [])

    if method == "initialize":
        state["initialized"] = True
        return ([_ok(msg_id, {
            "capabilities": {
                "textDocumentSync": {"openClose": True, "change": 1,
                                       "save": True},
                "hoverProvider": True,
                "definitionProvider": True,
            },
            "serverInfo": {"name": SERVER_NAME, "version": __version__},
        })], [])

    if method == "initialized":
        return ([], [])  # client → server; no reply

    if method == "shutdown":
        state["shutdown_requested"] = True
        return ([_ok(msg_id, None)], [])

    if method == "exit":
        return ([], [])

    if method == "textDocument/didOpen":
        td = params.get("textDocument") or {}
        uri = td.get("uri", "")
        text = td.get("text", "")
        state.setdefault("documents", {})[uri] = text
        diagnostics = compute_diagnostics(sidecar_text=text,
                                            sidecar_uri=uri)
        return ([], [_notification("textDocument/publishDiagnostics", {
            "uri": uri, "diagnostics": diagnostics,
        })])

    if method == "textDocument/didChange":
        td = params.get("textDocument") or {}
        uri = td.get("uri", "")
        changes = params.get("contentChanges") or []
        if changes and isinstance(changes[-1].get("text"), str):
            # We advertised TextDocumentSyncKind.Full (1), so the last
            # change is the full new text.
            text = changes[-1]["text"]
            state.setdefault("documents", {})[uri] = text
            diagnostics = compute_diagnostics(sidecar_text=text,
                                                sidecar_uri=uri)
            return ([], [_notification("textDocument/publishDiagnostics", {
                "uri": uri, "diagnostics": diagnostics,
            })])
        return ([], [])

    if method == "textDocument/didSave":
        td = params.get("textDocument") or {}
        uri = td.get("uri", "")
        text = state.get("documents", {}).get(uri, "")
        diagnostics = compute_diagnostics(sidecar_text=text,
                                            sidecar_uri=uri)
        return ([], [_notification("textDocument/publishDiagnostics", {
            "uri": uri, "diagnostics": diagnostics,
        })])

    if method == "textDocument/didClose":
        td = params.get("textDocument") or {}
        uri = td.get("uri", "")
        state.setdefault("documents", {}).pop(uri, None)
        return ([], [_notification("textDocument/publishDiagnostics", {
            "uri": uri, "diagnostics": [],  # clear
        })])

    if method == "textDocument/hover":
        td = params.get("textDocument") or {}
        pos = params.get("position") or {}
        uri = td.get("uri", "")
        text = state.get("documents", {}).get(uri, "")
        line = int(pos.get("line", 0))
        hover = compute_hover(sidecar_text=text, line=line)
        return ([_ok(msg_id, hover)], [])

    if method == "textDocument/definition":
        td = params.get("textDocument") or {}
        pos = params.get("position") or {}
        uri = td.get("uri", "")
        text = state.get("documents", {}).get(uri, "")
        line = int(pos.get("line", 0))
        loc = compute_definition(sidecar_text=text, sidecar_uri=uri,
                                   line=line)
        return ([_ok(msg_id, loc)], [])

    if is_notification:
        return ([], [])
    return ([_err(msg_id, _LSP_METHOD_NOT_FOUND,
                   f"unknown method: {method!r}")], [])
