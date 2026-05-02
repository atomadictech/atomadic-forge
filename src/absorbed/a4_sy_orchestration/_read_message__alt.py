"""Tier a3 — LSP stdio loop wrapping the pure dispatcher.

Golden Path Lane D W12 deliverable. The pure dispatcher lives at
``a1_at_functions.lsp_protocol``; this module owns the LSP framing
(Content-Length headers + JSON body) over stdin/stdout, exactly the
shape every LSP client (VS Code, Neovim, Helix, Sublime, IntelliJ)
expects on first connect.
"""
from __future__ import annotations

import json
import sys
from typing import IO

from ..a1_at_functions.lsp_protocol import (
    LspState,
    dispatch_request,
    new_state,
)


def serve_stdio(
    *,
    stdin: IO[bytes] | None = None,
    stdout: IO[bytes] | None = None,
    stderr: IO[str] | None = None,
) -> int:
    """Read LSP messages from stdin (Content-Length framed) and write
    responses + notifications to stdout. Exits 0 on clean shutdown."""
    src_in = stdin if stdin is not None else sys.stdin.buffer
    src_out = stdout if stdout is not None else sys.stdout.buffer
    src_err = stderr if stderr is not None else sys.stderr

    state: LspState = new_state()
    src_err.write("forge-lsp: ready (Content-Length framed JSON-RPC)\n")
    src_err.flush()

    while True:
        msg = _read_message(src_in)
        if msg is None:
            break  # client closed stdin
        try:
            request = json.loads(msg.decode("utf-8"))
        except json.JSONDecodeError:
            _write_message(src_out, {
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            })
            continue
        responses, notifications = dispatch_request(request, state=state)
        for resp in responses:
            _write_message(src_out, resp)
        for note in notifications:
            _write_message(src_out, note)
        if request.get("method") == "exit":
            return 0 if state.get("shutdown_requested") else 1
    return 0


def _read_message(stream: IO[bytes]) -> bytes | None:
    """Read one LSP message frame: headers terminated by \\r\\n\\r\\n
    followed by Content-Length bytes of body."""
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if not line:
            return None  # EOF
        s = line.decode("ascii").rstrip("\r\n")
        if s == "":
            break
        if ":" not in s:
            continue
        key, _, value = s.partition(":")
        headers[key.strip().lower()] = value.strip()
    length_str = headers.get("content-length", "0")
    try:
        length = int(length_str)
    except ValueError:
        return None
    if length <= 0:
        return b""
    body = b""
    remaining = length
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            return None  # EOF mid-message
        body += chunk
        remaining -= len(chunk)
    return body


def _write_message(stream: IO[bytes], payload: dict) -> None:
    body = json.dumps(payload, default=str).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    stream.write(header)
    stream.write(body)
    stream.flush()
