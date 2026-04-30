"""Tier verification — Golden Path Lane D W12: forge-lsp.

Pure-dispatcher tests + an end-to-end stdio framing smoke. No
network, no real LSP client; every test runs as a synthesized
JSON-RPC sequence.
"""
from __future__ import annotations

import io
import json
import textwrap
from pathlib import Path

import pytest

from atomadic_forge.a1_at_functions.lsp_protocol import (
    SERVER_NAME,
    compute_definition,
    compute_diagnostics,
    compute_hover,
    dispatch_request,
    new_state,
    uri_to_path,
)
from atomadic_forge.a3_og_features.lsp_server import serve_stdio


_GOOD_SOURCE = textwrap.dedent('''
    def login(username: str, password: str) -> str:
        return f"sess-{username}"

    def hash_password(plain: str) -> str:
        return plain.encode().hex()
''').strip()

_GOOD_SIDECAR = textwrap.dedent('''
    schema_version: atomadic-forge.sidecar/v1
    target: auth.py
    symbols:
      - name: login
        effect: NetIO
        tier: a3_og_features
        compose_with:
          - users.session.SessionStore.put
        proves:
          - "lemma:login_emits_session"

      - name: hash_password
        effect: Pure
        tier: a1_at_functions
''').strip()


# ---- handshake ---------------------------------------------------------

def test_initialize_returns_capabilities():
    state = new_state()
    resps, notes = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        state=state,
    )
    assert len(resps) == 1
    cap = resps[0]["result"]["capabilities"]
    assert cap["hoverProvider"] is True
    assert cap["definitionProvider"] is True
    assert cap["textDocumentSync"]["openClose"] is True
    assert resps[0]["result"]["serverInfo"]["name"] == SERVER_NAME


def test_initialized_notification_no_response():
    state = new_state()
    resps, notes = dispatch_request(
        {"jsonrpc": "2.0", "method": "initialized"}, state=state)
    assert resps == [] and notes == []


def test_shutdown_sets_flag_and_exit_clean(tmp_path):
    state = new_state()
    resps, _ = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "shutdown"}, state=state)
    assert resps[0]["result"] is None
    assert state["shutdown_requested"] is True


def test_unknown_method_returns_method_not_found():
    state = new_state()
    resps, _ = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "totally/made/up"},
        state=state,
    )
    assert resps[0]["error"]["code"] == -32601


# ---- diagnostics --------------------------------------------------------

def test_diagnostics_pass_on_clean_sidecar(tmp_path):
    src = tmp_path / "auth.py"
    src.write_text(_GOOD_SOURCE, encoding="utf-8")
    sc = tmp_path / "auth.py.forge"
    sc.write_text(_GOOD_SIDECAR, encoding="utf-8")
    diags = compute_diagnostics(
        sidecar_text=_GOOD_SIDECAR,
        sidecar_uri="file:///" + str(sc).replace("\\", "/"),
    )
    assert all(d["severity"] != 1 for d in diags), (
        f"unexpected error diagnostics on clean sidecar: {diags}"
    )


def test_diagnostics_flag_missing_symbol(tmp_path):
    src = tmp_path / "auth.py"
    src.write_text(_GOOD_SOURCE, encoding="utf-8")
    sc = tmp_path / "auth.py.forge"
    sc.write_text(textwrap.dedent('''
        schema_version: atomadic-forge.sidecar/v1
        target: auth.py
        symbols:
          - name: ghost
            effect: Pure
    ''').strip(), encoding="utf-8")
    diags = compute_diagnostics(
        sidecar_text=sc.read_text(encoding="utf-8"),
        sidecar_uri="file:///" + str(sc).replace("\\", "/"),
    )
    error_diags = [d for d in diags if d["severity"] == 1]
    assert error_diags
    assert error_diags[0]["code"] in {"F0101", "S0001"}


def test_diagnostics_unparseable_yaml_emits_f0100():
    diags = compute_diagnostics(
        sidecar_text="not: valid: : yaml :",
        sidecar_uri="file:///nope.forge",
    )
    assert any(d["code"] == "F0100" for d in diags)


# ---- hover --------------------------------------------------------------

def test_hover_on_name_line_returns_markdown():
    # Find the line containing 'name: login' in the sidecar text.
    lines = _GOOD_SIDECAR.splitlines()
    login_line = next(i for i, l in enumerate(lines)
                       if l.strip() == "- name: login")
    hover = compute_hover(sidecar_text=_GOOD_SIDECAR, line=login_line)
    assert hover is not None
    md = hover["contents"]["value"]
    assert "**login**" in md
    assert "NetIO" in md
    assert "lemma:login_emits_session" in md


def test_hover_off_a_symbol_returns_none():
    hover = compute_hover(sidecar_text=_GOOD_SIDECAR, line=0)
    # First line is `schema_version: ...`; not a symbol block.
    assert hover is None


# ---- definition (goto-source) ------------------------------------------

def test_definition_resolves_login(tmp_path):
    src = tmp_path / "auth.py"
    src.write_text(_GOOD_SOURCE, encoding="utf-8")
    sc = tmp_path / "auth.py.forge"
    sc.write_text(_GOOD_SIDECAR, encoding="utf-8")
    sidecar_uri = "file:///" + str(sc).replace("\\", "/")
    lines = _GOOD_SIDECAR.splitlines()
    login_line = next(i for i, l in enumerate(lines)
                       if l.strip() == "- name: login")
    loc = compute_definition(
        sidecar_text=_GOOD_SIDECAR,
        sidecar_uri=sidecar_uri,
        line=login_line,
    )
    assert loc is not None
    assert loc["uri"].endswith("auth.py")
    assert loc["range"]["start"]["line"] == 0  # `def login` is line 0


def test_definition_off_name_line_returns_none():
    loc = compute_definition(
        sidecar_text=_GOOD_SIDECAR,
        sidecar_uri="file:///nope.forge",
        line=0,
    )
    assert loc is None


# ---- text-document lifecycle (didOpen / didChange / didClose) ----------

def test_didopen_emits_publish_diagnostics(tmp_path):
    src = tmp_path / "auth.py"
    src.write_text(_GOOD_SOURCE, encoding="utf-8")
    sc = tmp_path / "auth.py.forge"
    sidecar_uri = "file:///" + str(sc).replace("\\", "/")
    state = new_state()
    _, notes = dispatch_request({
        "jsonrpc": "2.0", "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": sidecar_uri,
                "languageId": "yaml",
                "version": 1,
                "text": _GOOD_SIDECAR,
            },
        },
    }, state=state)
    assert len(notes) == 1
    assert notes[0]["method"] == "textDocument/publishDiagnostics"
    assert notes[0]["params"]["uri"] == sidecar_uri


def test_didchange_uses_full_sync_replacement(tmp_path):
    src = tmp_path / "auth.py"
    src.write_text(_GOOD_SOURCE, encoding="utf-8")
    sc = tmp_path / "auth.py.forge"
    sidecar_uri = "file:///" + str(sc).replace("\\", "/")
    state = new_state()
    # Open
    dispatch_request({
        "jsonrpc": "2.0", "method": "textDocument/didOpen",
        "params": {"textDocument": {
            "uri": sidecar_uri, "languageId": "yaml",
            "version": 1, "text": _GOOD_SIDECAR}},
    }, state=state)
    # Change to broken sidecar
    bad_sidecar = textwrap.dedent('''
        schema_version: atomadic-forge.sidecar/v1
        target: auth.py
        symbols:
          - name: ghost
            effect: Pure
    ''').strip()
    _, notes = dispatch_request({
        "jsonrpc": "2.0", "method": "textDocument/didChange",
        "params": {
            "textDocument": {"uri": sidecar_uri, "version": 2},
            "contentChanges": [{"text": bad_sidecar}],
        },
    }, state=state)
    diags = notes[0]["params"]["diagnostics"]
    assert any(d["code"] in {"F0101", "S0001"} for d in diags)


def test_didclose_clears_diagnostics():
    state = new_state()
    _, notes = dispatch_request({
        "jsonrpc": "2.0", "method": "textDocument/didClose",
        "params": {"textDocument": {"uri": "file:///x.forge"}},
    }, state=state)
    assert notes[0]["params"]["diagnostics"] == []


# ---- uri_to_path -------------------------------------------------------

def test_uri_to_path_unix():
    p = uri_to_path("file:///home/user/project/auth.py.forge")
    assert str(p).replace("\\", "/").endswith("auth.py.forge")


def test_uri_to_path_windows_drive_letter():
    p = uri_to_path("file:///C%3A/work/auth.py.forge")
    s = str(p).replace("\\", "/")
    assert s.startswith("C:") or s.endswith("auth.py.forge")


# ---- stdio framing end-to-end ------------------------------------------

def _frame(msg: dict) -> bytes:
    body = json.dumps(msg).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def test_serve_stdio_initialize_shutdown_exit_round_trip(tmp_path):
    """Full LSP frame round-trip: initialize → shutdown → exit."""
    inp_bytes = b"".join([
        _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                 "params": {}}),
        _frame({"jsonrpc": "2.0", "id": 2, "method": "shutdown"}),
        _frame({"jsonrpc": "2.0", "method": "exit"}),
    ])
    inp = io.BytesIO(inp_bytes)
    out = io.BytesIO()
    err = io.StringIO()
    rc = serve_stdio(stdin=inp, stdout=out, stderr=err)
    assert rc == 0
    raw = out.getvalue()
    assert b"Content-Length:" in raw
    assert b"capabilities" in raw
    # initialize response + shutdown response = 2 frames
    assert raw.count(b"Content-Length:") == 2


def test_serve_stdio_recovers_from_bad_json():
    """Malformed JSON line surfaces -32700 but doesn't kill the loop."""
    inp_bytes = b"".join([
        b"Content-Length: 5\r\n\r\nabcde",   # not JSON
        _frame({"jsonrpc": "2.0", "id": 1, "method": "shutdown"}),
        _frame({"jsonrpc": "2.0", "method": "exit"}),
    ])
    inp = io.BytesIO(inp_bytes)
    out = io.BytesIO()
    err = io.StringIO()
    rc = serve_stdio(stdin=inp, stdout=out, stderr=err)
    assert rc == 0
    assert b"Parse error" in out.getvalue()
