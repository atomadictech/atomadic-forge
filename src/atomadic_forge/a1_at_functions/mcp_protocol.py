"""Tier a1 — pure MCP JSON-RPC dispatch for `forge mcp serve`.

Golden Path Lane C W4 deliverable. The dispatcher is a pure function
``dispatch_request(req, ctx) -> response`` — no I/O, no global state.
The transport (stdio loop) lives in a3 ``mcp_server.py``.

Implements the slice of the MCP spec that coding agents actually
consume on first connect:

  * ``initialize``      — capability handshake; returns serverInfo +
                          supported protocol version + tool/resource
                          capability flags.
  * ``ping``            — liveness check (returns ``{}``).
  * ``tools/list``      — names + JSON Schemas for the 4 Forge tools.
  * ``tools/call``      — runs one of the named tools and returns
                          the result wrapped in MCP's ``content`` shape.
  * ``resources/list``  — Forge documentation + lineage URIs.
  * ``resources/read``  — read a Forge resource (docs, lineage, schema).

Tools today (Lane C W4):
  recon, wire, certify, enforce, audit_list

Resources today:
  forge://docs/receipt           — docs/RECEIPT.md
  forge://docs/formalization     — docs/FORMALIZATION.md (citations)
  forge://lineage/chain          — local lineage chain JSONL
  forge://schema/receipt         — Receipt v1 JSON schema reference

The dispatcher returns proper JSON-RPC 2.0 responses, including
``-32601`` (method not found) and ``-32602`` (invalid params) error
codes when it can't honor a request. Pure function — exceptions raised
by tool handlers are caught and converted to ``-32000`` (server error)
responses; callers never see a Python traceback.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .. import __version__
from ..a0_qk_constants.receipt_schema import SCHEMA_VERSION_V1
from .agent_summary import summarize_blockers
from .certify_checks import certify
from .lineage_chain import canonical_receipt_hash, verify_chain_link
from .lineage_reader import list_artifacts, read_lineage
from .receipt_emitter import build_receipt
from .scout_walk import harvest_repo
from .wire_check import scan_violations


PROTOCOL_VERSION = "2024-11-05"   # MCP spec rev the server advertises
SERVER_NAME = "atomadic-forge"


_JSON_RPC_VERSION = "2.0"
_ERR_PARSE = -32700
_ERR_INVALID_REQUEST = -32600
_ERR_METHOD_NOT_FOUND = -32601
_ERR_INVALID_PARAMS = -32602
_ERR_INTERNAL = -32603
_ERR_SERVER = -32000


# --- Tool registry (pure: handlers receive a project_root path) ----------

ToolHandler = Callable[[Path, dict[str, Any]], dict[str, Any]]


def _tool_recon(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    target = Path(args.get("target", project_root)).resolve()
    return harvest_repo(target)


def _tool_wire(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    src = Path(args.get("source", project_root)).resolve()
    return scan_violations(
        src,
        suggest_repairs=bool(args.get("suggest_repairs", False)),
    )


def _tool_certify(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    root = Path(args.get("project_root", project_root)).resolve()
    package = args.get("package")
    cert = certify(root, project=root.name, package=package)
    if not args.get("emit_receipt"):
        return cert
    # When emit_receipt is requested, build a v1 Receipt around the
    # certify result and return both for the caller's convenience.
    wire = scan_violations(root)
    scout = harvest_repo(root)
    receipt = build_receipt(
        certify_result=cert,
        wire_report=wire,
        scout_report=scout,
        project_name=root.name,
        project_root=root,
        forge_version=__version__,
        package=package,
    )
    return {"certify": cert, "receipt": receipt}


def _tool_enforce_unbound(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Default enforce handler — a3 binds the real implementation at
    import time via ``register_enforce_handler``. Until a3 has loaded
    (e.g. when only a1 is imported in tests), this stub returns a
    structured 'unwired' response so callers can detect the state.
    """
    return {
        "schema_version": "atomadic-forge.enforce/v1",
        "wired": False,
        "note": (
            "forge enforce tool not yet wired — import "
            "atomadic_forge.a3_og_features.mcp_server (or any code "
            "under a3) to register the real handler."
        ),
    }


_enforce_handler: ToolHandler = _tool_enforce_unbound


def _tool_enforce(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return _enforce_handler(project_root, args)


def register_enforce_handler(handler: ToolHandler) -> None:
    """Bind the real ``run_enforce``-backed handler from a3.

    Pure module-state replacement (a global within this a1 module).
    a3's mcp_server.py calls this at import time so when the CLI
    surface (a4) imports a3.mcp_server, the dispatcher's enforce
    handler is wired automatically — no upward import in a1.
    """
    global _enforce_handler
    _enforce_handler = handler


def _tool_audit_list(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    root = Path(args.get("project_root", project_root)).resolve()
    return {
        "schema_version": "atomadic-forge.audit.list/v1",
        "project": str(root),
        "artifacts": list_artifacts(root),
    }


def _tool_auto_plan_unbound(project_root: Path,
                             args: dict[str, Any]) -> dict[str, Any]:
    """auto_plan stub — a3 binds the real ``run_auto_plan`` at import
    time via ``register_auto_plan_handler``. Same a1↔a3 injection
    pattern the enforce tool uses (see Lane C W4 commit msg).
    """
    return {
        "schema_version": "atomadic-forge.agent_plan/v1",
        "wired": False,
        "note": (
            "auto_plan tool not yet wired — import "
            "atomadic_forge.a3_og_features.mcp_server (or any code "
            "under a3) to register the real handler."
        ),
    }


_auto_plan_handler: ToolHandler = _tool_auto_plan_unbound


def _tool_auto_plan(project_root: Path,
                     args: dict[str, Any]) -> dict[str, Any]:
    return _auto_plan_handler(project_root, args)


def register_auto_plan_handler(handler: ToolHandler) -> None:
    """Bind the real auto_plan handler from a3 (mirror of
    register_enforce_handler)."""
    global _auto_plan_handler
    _auto_plan_handler = handler


TOOLS: dict[str, dict[str, Any]] = {
    "recon": {
        "name": "recon",
        "description": "Walk a repo and classify every public symbol "
                        "into one of the 5 monadic tiers. Returns a "
                        "scout report with tier_distribution + symbols.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string",
                            "description": "Repo path; defaults to project_root."},
            },
            "additionalProperties": False,
        },
        "handler": _tool_recon,
    },
    "wire": {
        "name": "wire",
        "description": "Scan a tier-organized package for upward-import "
                        "violations. With suggest_repairs=true, emits "
                        "auto_fixable count + repair_suggestions per file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "suggest_repairs": {"type": "boolean", "default": False},
            },
            "additionalProperties": False,
        },
        "handler": _tool_wire,
    },
    "certify": {
        "name": "certify",
        "description": "Score documentation + tests + tier layout + import "
                        "discipline. With emit_receipt=true, also emits a "
                        "Forge Receipt v1 JSON.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "package": {"type": ["string", "null"]},
                "emit_receipt": {"type": "boolean", "default": False},
            },
            "additionalProperties": False,
        },
        "handler": _tool_certify,
    },
    "enforce": {
        "name": "enforce",
        "description": "Plan (or apply) mechanical fixes for wire "
                        "violations. F-code routed; rolls back any fix "
                        "that increases the violation count.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "apply": {"type": "boolean", "default": False},
            },
            "additionalProperties": False,
        },
        "handler": _tool_enforce,
    },
    "audit_list": {
        "name": "audit_list",
        "description": "Summarize every artifact written under "
                        ".atomadic-forge/lineage.jsonl: name, run count, "
                        "latest write timestamp, path.",
        "inputSchema": {
            "type": "object",
            "properties": {"project_root": {"type": "string"}},
            "additionalProperties": False,
        },
        "handler": _tool_audit_list,
    },
    "auto_plan": {
        "name": "auto_plan",
        "description": (
            "Codex's 'next best action card' generator. Runs scout + "
            "wire + certify and emits an agent_plan/v1 with top-N "
            "ranked AgentActionCard entries (kind, why, write_scope, "
            "risk, applyable, commands, next_command). The active "
            "agent picks one card and runs its next_command; Forge "
            "does NOT mutate the repo from this tool."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target":   {"type": "string"},
                "goal":     {"type": "string",
                              "default": "improve repo conformance"},
                "mode":     {"type": "string",
                              "enum": ["improve", "absorb"],
                              "default": "improve"},
                "package":  {"type": ["string", "null"]},
                "top_n":    {"type": "integer", "default": 7},
            },
            "additionalProperties": False,
        },
        "handler": _tool_auto_plan,
    },
}


# --- Resource registry ---------------------------------------------------

ResourceLoader = Callable[[Path], str]


def _resource_doc_receipt(project_root: Path) -> str:
    return _read_repo_doc(project_root, "docs/RECEIPT.md")


def _resource_doc_formalization(project_root: Path) -> str:
    return _read_repo_doc(project_root, "docs/FORMALIZATION.md")


def _resource_lineage(project_root: Path) -> str:
    entries = read_lineage(project_root)
    return json.dumps({
        "schema_version": "atomadic-forge.audit.log/v1",
        "project": str(project_root),
        "entry_count": len(entries),
        "entries": entries,
    }, indent=2)


def _resource_schema(project_root: Path) -> str:
    return json.dumps({
        "schema_version": SCHEMA_VERSION_V1,
        "doc": "see forge://docs/receipt for the full v1 schema",
        "valid_verdicts": ["PASS", "FAIL", "REFINE", "QUARANTINE"],
    }, indent=2)


def _resource_summary_blockers(project_root: Path) -> str:
    """Single-call 'what's blocking release?' — runs wire + certify
    and returns the compact summary. Codex feedback: this is the
    resource agents should hit FIRST on every connect."""
    try:
        wire = scan_violations(project_root)
    except (OSError, ValueError):
        wire = None
    try:
        cert = certify(project_root, project=project_root.name)
    except (OSError, ValueError, RuntimeError):
        cert = None
    s = summarize_blockers(
        wire_report=wire, certify_report=cert,
        package_root=project_root.name,
    )
    return json.dumps(s, indent=2, default=str)


def _read_repo_doc(project_root: Path, rel: str) -> str:
    """Read a doc that lives in this Forge install's repo, not the
    consuming project. Falls back to '(not available)' when missing."""
    candidate = Path(__file__).resolve().parents[3] / rel
    if not candidate.exists():
        candidate = Path(project_root) / rel
    try:
        return candidate.read_text(encoding="utf-8")
    except OSError:
        return f"(resource {rel!r} not available in this install)"


RESOURCES: dict[str, dict[str, Any]] = {
    "forge://docs/receipt": {
        "uri": "forge://docs/receipt",
        "name": "Forge Receipt v1 wire-format docs",
        "mimeType": "text/markdown",
        "loader": _resource_doc_receipt,
    },
    "forge://docs/formalization": {
        "uri": "forge://docs/formalization",
        "name": "AAM v1.0 + BEP v1.0 theorem citations for Forge gates",
        "mimeType": "text/markdown",
        "loader": _resource_doc_formalization,
    },
    "forge://lineage/chain": {
        "uri": "forge://lineage/chain",
        "name": "Local Vanguard lineage chain (chronological JSONL)",
        "mimeType": "application/json",
        "loader": _resource_lineage,
    },
    "forge://schema/receipt": {
        "uri": "forge://schema/receipt",
        "name": "Receipt v1 schema sketch (verdicts + version constants)",
        "mimeType": "application/json",
        "loader": _resource_schema,
    },
    "forge://summary/blockers": {
        "uri": "forge://summary/blockers",
        "name": "Top-5 blockers (Codex feedback): wire + certify in one call",
        "mimeType": "application/json",
        "loader": _resource_summary_blockers,
    },
}


# --- Dispatch ------------------------------------------------------------

def _ok(msg_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": _JSON_RPC_VERSION, "id": msg_id, "result": result}


def _err(msg_id: Any, code: int, message: str,
          data: Any | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": _JSON_RPC_VERSION, "id": msg_id, "error": error}


def _summary_for_tool(name: str, result: Any) -> dict[str, Any] | None:
    """Compute the agent-native summary for a tool result, when applicable.

    Codex feedback: agents thrive on 'here are the 2 things blocking
    release' more than huge manifests. We compute a top-5 summary
    inline so MCP clients can branch on a 4-line response instead of
    parsing kilobytes of JSON.
    """
    if not isinstance(result, dict):
        return None
    schema = result.get("schema_version", "")
    if schema == "atomadic-forge.wire/v1":
        return summarize_blockers(wire_report=result)
    if schema == "atomadic-forge.certify/v1":
        return summarize_blockers(certify_report=result)
    if name == "certify" and isinstance(result.get("receipt"), dict):
        # The certify-with-emit_receipt path returns a wrapped dict.
        return summarize_blockers(certify_report=result.get("certify"))
    if schema == "atomadic-forge.agent_plan/v1":
        # Plans already ARE summary-shaped — surface a tiny digest
        # so MCP clients can branch without re-parsing the full plan.
        return {
            "schema_version": "atomadic-forge.summary/v1",
            "verdict": result.get("verdict", "?"),
            "score": 0,
            "blocker_count": result.get("action_count", 0),
            "auto_fixable_count": result.get("applyable_count", 0),
            "blockers": [],
            "next_command": result.get("next_command", ""),
        }
    return None


def _serialize_result(value: Any, *, name: str = "") -> dict[str, Any]:
    """Wrap a tool result in MCP's ``content`` envelope so coding-agent
    clients see a uniform shape (text + parsed JSON).

    When we can derive an agent-native summary, prepend it as a SECOND
    text block so a sloppy client reading only ``content[0]`` still
    gets the full payload (back-compat) while a smart client can read
    ``content[1]`` for the compact form. Both are valid MCP shapes.
    """
    full = json.dumps(value, indent=2, default=str)
    blocks: list[dict[str, Any]] = [{"type": "text", "text": full}]
    summary = _summary_for_tool(name, value) if name else None
    if summary is not None:
        blocks.append({
            "type": "text",
            "text": "_summary:\n" + json.dumps(summary, indent=2, default=str),
        })
    return {"content": blocks, "_summary": summary}


def _list_tools() -> dict[str, Any]:
    return {
        "tools": [
            {"name": t["name"],
             "description": t["description"],
             "inputSchema": t["inputSchema"]}
            for t in TOOLS.values()
        ],
    }


def _list_resources() -> dict[str, Any]:
    return {
        "resources": [
            {"uri": r["uri"], "name": r["name"], "mimeType": r["mimeType"]}
            for r in RESOURCES.values()
        ],
    }


def _initialize_response() -> dict[str, Any]:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "serverInfo": {
            "name": SERVER_NAME,
            "version": __version__,
        },
        "capabilities": {
            "tools": {"listChanged": False},
            "resources": {"subscribe": False, "listChanged": False},
        },
    }


def dispatch_request(
    request: dict[str, Any],
    *,
    project_root: Path,
) -> dict[str, Any] | None:
    """Route one JSON-RPC request to its handler and return the response.

    Returns ``None`` for valid notifications (no ``id`` field) — the
    transport must NOT write a response in that case.
    """
    if not isinstance(request, dict):
        return _err(None, _ERR_INVALID_REQUEST, "request must be a JSON object")
    method = request.get("method")
    if not isinstance(method, str):
        return _err(request.get("id"), _ERR_INVALID_REQUEST,
                     "request missing string `method`")
    msg_id = request.get("id")
    is_notification = "id" not in request
    params = request.get("params") or {}

    if method == "initialize":
        return _ok(msg_id, _initialize_response())
    if method == "ping":
        return _ok(msg_id, {})
    if method == "notifications/initialized":
        return None  # client → server; server replies nothing
    if method == "tools/list":
        return _ok(msg_id, _list_tools())
    if method == "resources/list":
        return _ok(msg_id, _list_resources())
    if method == "tools/call":
        if is_notification:
            return None
        name = params.get("name")
        args = params.get("arguments") or {}
        if not isinstance(name, str) or name not in TOOLS:
            return _err(msg_id, _ERR_METHOD_NOT_FOUND,
                         f"unknown tool: {name!r}")
        try:
            result = TOOLS[name]["handler"](project_root, args)
        except (ValueError, OSError, RuntimeError) as exc:
            return _err(msg_id, _ERR_SERVER,
                         f"{type(exc).__name__}: {exc}")
        return _ok(msg_id, _serialize_result(result, name=name))
    if method == "resources/read":
        if is_notification:
            return None
        uri = params.get("uri")
        if uri not in RESOURCES:
            return _err(msg_id, _ERR_INVALID_PARAMS,
                         f"unknown resource: {uri!r}")
        loader = RESOURCES[uri]["loader"]
        try:
            text = loader(project_root)
        except OSError as exc:
            return _err(msg_id, _ERR_SERVER,
                         f"could not read resource: {exc}")
        return _ok(msg_id, {
            "contents": [{
                "uri": uri,
                "mimeType": RESOURCES[uri]["mimeType"],
                "text": text,
            }],
        })

    return _err(msg_id, _ERR_METHOD_NOT_FOUND,
                 f"unknown method: {method!r}")


__all__ = [
    "PROTOCOL_VERSION",
    "RESOURCES",
    "SERVER_NAME",
    "TOOLS",
    "dispatch_request",
    # Lane B Studio's Topology Map renders against these helpers.
    "canonical_receipt_hash",
    "verify_chain_link",
]
