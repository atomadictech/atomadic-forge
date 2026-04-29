"""Tier verification — Golden Path Lane C W4: forge mcp serve.

Two layers of coverage:

  Pure dispatch (mcp_protocol.py):
    * initialize handshake returns the pinned protocolVersion +
      serverInfo + capability flags
    * tools/list and resources/list return the pinned set
    * tools/call routes recon / wire / certify / enforce / audit_list
      and wraps results in the MCP content envelope
    * resources/read serves docs + lineage
    * unknown methods surface JSON-RPC -32601, unknown tools / bad
      params surface -32601 / -32602; tool exceptions surface -32000
      WITHOUT crashing the dispatcher

  Stdio loop (mcp_server.py):
    * end-to-end ping round-trip via in-memory stdin/stdout
    * shutdown method exits the loop cleanly with rc=0
"""
from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

import pytest

from atomadic_forge.a1_at_functions.mcp_protocol import (
    PROTOCOL_VERSION,
    RESOURCES,
    SERVER_NAME,
    TOOLS,
    dispatch_request,
)
from atomadic_forge.a3_og_features.mcp_server import serve_stdio


# ---- handshake ---------------------------------------------------------

def test_initialize_returns_pinned_protocol(tmp_path):
    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
           "params": {"clientInfo": {"name": "test"}}}
    resp = dispatch_request(req, project_root=tmp_path)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    result = resp["result"]
    assert result["protocolVersion"] == PROTOCOL_VERSION
    assert result["serverInfo"]["name"] == SERVER_NAME
    assert "tools" in result["capabilities"]
    assert "resources" in result["capabilities"]


def test_ping_returns_empty_object(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 99, "method": "ping"},
        project_root=tmp_path,
    )
    assert resp["result"] == {}


def test_initialized_notification_returns_none(tmp_path):
    """notifications/initialized has no id and gets no response."""
    resp = dispatch_request(
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        project_root=tmp_path,
    )
    assert resp is None


# ---- tools/list + resources/list ---------------------------------------

def test_tools_list_pinned(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        project_root=tmp_path,
    )
    names = {t["name"] for t in resp["result"]["tools"]}
    pinned = {
        "recon", "wire", "certify", "enforce", "audit_list",
        "auto_plan", "auto_step", "auto_apply",
        "context_pack", "preflight_change", "score_patch",
        "select_tests", "rollback_plan", "explain_repo",
        "adapt_plan", "compose_tools", "load_policy",
        "why_did_this_change", "what_failed_last_time",
        "list_recipes", "get_recipe",
    }
    assert pinned == names == set(TOOLS.keys()), (
        f"tools/list drifted: returned {names}, expected {pinned}"
    )
    # Every tool must have a JSON Schema for inputs.
    for tool in resp["result"]["tools"]:
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"


def test_resources_list_pinned(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 3, "method": "resources/list"},
        project_root=tmp_path,
    )
    uris = {r["uri"] for r in resp["result"]["resources"]}
    pinned = {
        "forge://docs/receipt",
        "forge://docs/formalization",
        "forge://lineage/chain",
        "forge://schema/receipt",
        "forge://summary/blockers",
    }
    assert uris == pinned == set(RESOURCES.keys())


# ---- tools/call --------------------------------------------------------

def _sample_tier_tree(root: Path) -> Path:
    pkg = root / "src" / "demo"
    a1 = pkg / "a1_at_functions"
    a1.mkdir(parents=True)
    (pkg / "__init__.py").write_text('"""demo."""\n', encoding="utf-8")
    (a1 / "__init__.py").write_text('"""a1."""\n', encoding="utf-8")
    (a1 / "ok.py").write_text(
        '"""a1 helper."""\ndef ok(x):\n    return x\n', encoding="utf-8")
    return pkg


def test_tools_call_recon(tmp_path):
    pkg = _sample_tier_tree(tmp_path)
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "recon", "arguments": {"target": str(pkg)}}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["schema_version"] == "atomadic-forge.scout/v1"
    assert body["primary_language"] == "python"


def test_tools_call_wire_pass(tmp_path):
    pkg = _sample_tier_tree(tmp_path)
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "wire", "arguments": {"source": str(pkg)}}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["verdict"] == "PASS"


def test_tools_call_wire_with_suggest_repairs(tmp_path):
    pkg = tmp_path / "pkg"
    a1 = pkg / "a1_at_functions"; a1.mkdir(parents=True)
    a3 = pkg / "a3_og_features"; a3.mkdir(parents=True)
    (a3 / "feat.py").write_text(
        '"""a3."""\nclass F:\n    pass\n', encoding="utf-8")
    (a1 / "h.py").write_text(
        "from ..a3_og_features.feat import F\n", encoding="utf-8")
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
         "params": {"name": "wire",
                    "arguments": {"source": str(pkg),
                                   "suggest_repairs": True}}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["verdict"] == "FAIL"
    assert body["auto_fixable"] >= 1
    assert "repair_suggestions" in body


def test_tools_call_enforce_dry_run(tmp_path):
    pkg = _sample_tier_tree(tmp_path)
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 7, "method": "tools/call",
         "params": {"name": "enforce",
                    "arguments": {"source": str(pkg)}}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["schema_version"] == "atomadic-forge.enforce/v1"
    assert body["apply"] is False
    assert body["pre_violations"] == 0


def test_tools_call_audit_list_empty(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 8, "method": "tools/call",
         "params": {"name": "audit_list",
                    "arguments": {"project_root": str(tmp_path)}}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["schema_version"] == "atomadic-forge.audit.list/v1"
    assert body["artifacts"] == []


def test_tools_call_unknown_tool_returns_method_not_found(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 9, "method": "tools/call",
         "params": {"name": "definitely-not-a-tool"}},
        project_root=tmp_path,
    )
    assert resp["error"]["code"] == -32601


def test_tools_call_handler_exception_does_not_crash(tmp_path, monkeypatch):
    """A tool whose handler raises must surface a JSON-RPC error,
    never a Python traceback that kills the dispatcher."""
    from atomadic_forge.a1_at_functions import mcp_protocol as proto

    def boom(_root, _args):
        raise ValueError("synthetic test error")

    original = proto.TOOLS["recon"]["handler"]
    proto.TOOLS["recon"]["handler"] = boom
    try:
        resp = dispatch_request(
            {"jsonrpc": "2.0", "id": 10, "method": "tools/call",
             "params": {"name": "recon", "arguments": {}}},
            project_root=tmp_path,
        )
    finally:
        proto.TOOLS["recon"]["handler"] = original
    assert "error" in resp
    assert resp["error"]["code"] in {-32000, -32603}
    assert "synthetic test error" in resp["error"]["message"]


# ---- resources/read ----------------------------------------------------

def test_resources_read_lineage_empty(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 11, "method": "resources/read",
         "params": {"uri": "forge://lineage/chain"}},
        project_root=tmp_path,
    )
    contents = resp["result"]["contents"]
    assert contents[0]["uri"] == "forge://lineage/chain"
    assert contents[0]["mimeType"] == "application/json"
    body = json.loads(contents[0]["text"])
    assert body["entries"] == []


def test_resources_read_schema(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 12, "method": "resources/read",
         "params": {"uri": "forge://schema/receipt"}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["contents"][0]["text"])
    assert body["schema_version"] == "atomadic-forge.receipt/v1"
    assert "PASS" in body["valid_verdicts"]


def test_resources_read_unknown_uri(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 13, "method": "resources/read",
         "params": {"uri": "forge://nope/123"}},
        project_root=tmp_path,
    )
    assert resp["error"]["code"] == -32602


# ---- error paths -------------------------------------------------------

def test_unknown_method_returns_method_not_found(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 14, "method": "totally/made/up"},
        project_root=tmp_path,
    )
    assert resp["error"]["code"] == -32601


def test_non_dict_request_returns_invalid_request(tmp_path):
    resp = dispatch_request("not-a-dict", project_root=tmp_path)  # type: ignore[arg-type]
    assert resp["error"]["code"] == -32600


def test_request_without_method_returns_invalid_request(tmp_path):
    resp = dispatch_request({"jsonrpc": "2.0", "id": 15},
                              project_root=tmp_path)
    assert resp["error"]["code"] == -32600


# ---- stdio loop --------------------------------------------------------

def test_serve_stdio_ping_round_trip(tmp_path):
    """Send an initialize + ping + shutdown sequence and confirm the
    loop responds + exits cleanly with rc=0."""
    inp = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}) + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}) + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 3, "method": "shutdown"}) + "\n"
    )
    out = io.StringIO()
    err = io.StringIO()
    rc = serve_stdio(project_root=tmp_path, stdin=inp, stdout=out, stderr=err)
    assert rc == 0
    lines = [ln for ln in out.getvalue().splitlines() if ln.strip()]
    # initialize + ping + shutdown all produce one response each.
    assert len(lines) == 3
    init_resp = json.loads(lines[0])
    assert init_resp["result"]["serverInfo"]["name"] == SERVER_NAME
    ping_resp = json.loads(lines[1])
    assert ping_resp["result"] == {}
    shutdown_resp = json.loads(lines[2])
    assert shutdown_resp["id"] == 3


def test_serve_stdio_recovers_from_bad_json(tmp_path):
    """A malformed line surfaces parse error but the loop continues."""
    inp = io.StringIO(
        "this is not json\n"
        + json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "shutdown"}) + "\n"
    )
    out = io.StringIO()
    rc = serve_stdio(project_root=tmp_path, stdin=inp, stdout=out,
                      stderr=io.StringIO())
    assert rc == 0
    lines = [ln for ln in out.getvalue().splitlines() if ln.strip()]
    parse_err = json.loads(lines[0])
    assert parse_err["error"]["code"] == -32700
    ping_ok = json.loads(lines[1])
    assert ping_ok["result"] == {}


def test_serve_stdio_missing_project_returns_rc_1():
    rc = serve_stdio(project_root=Path("/definitely/not/a/path/anywhere"),
                      stdin=io.StringIO(""), stdout=io.StringIO(),
                      stderr=io.StringIO())
    assert rc == 1
