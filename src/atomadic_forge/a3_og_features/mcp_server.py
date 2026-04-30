"""Tier a3 — stdio JSON-RPC loop wrapping the pure MCP dispatcher.

Golden Path Lane C W4 deliverable, with the W5 subscription gate
layered on top. The pure dispatcher lives in
``a1_at_functions.mcp_protocol``; this module owns the I/O concerns:
read a line from stdin, parse it as JSON, hand to dispatch, write the
response to stdout. No SSE / HTTP transport today — that's a future
iteration; stdio is what every coding agent (Cursor, Claude Code,
Aider, Devin) uses on initial connect, so it's the right v0.

The server runs forever until stdin closes (the client disconnects)
or it receives a ``shutdown`` JSON-RPC method (per MCP spec). Errors
in JSON parsing or method dispatch never kill the loop — they're
surfaced as JSON-RPC error responses and the next request is
processed normally.

**Subscription requirement (Lane C W5).** Every ``tools/call`` is
gated behind a paid Forge subscription. The server reads the user's
``fk_live_*`` API key from the ``FORGE_API_KEY`` env variable, asks
the remote verify endpoint at ``forge-auth.atomadic.tech`` whether
the key is still active, and caches the answer for 5 minutes.

  * No key / wrong shape / verified-bad     → JSON-RPC error -32001
    with ``message="Forge subscription required"`` and an upgrade URL.
  * Read-only metadata methods (``initialize``, ``ping``,
    ``tools/list``, ``resources/list``, ``notifications/initialized``,
    ``shutdown``) bypass the gate so MCP clients can complete the
    handshake even before the user has logged in. Actual ``tools/call``
    and ``resources/read`` traffic require the gate to be open.

Use ``forge login`` to capture and store a key. See
``a4_sy_orchestration/login_cmd.py`` and ``docs/04-llm-loops.md`` for
the activation flow.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from pathlib import Path as _Path
from typing import IO

from ..a1_at_functions.forge_auth import (
    hash_project_path,
    read_api_key_from_env,
)
from ..a1_at_functions.mcp_protocol import (
    dispatch_request,
    register_auto_apply_handler,
    register_auto_plan_handler,
    register_auto_step_handler,
    register_enforce_handler,
)
from ..a2_mo_composites.forge_auth_client import ForgeAuthClient
from ..a2_mo_composites.plan_store import PlanStore as _PlanStore
from .forge_enforce import run_enforce as _run_enforce
from .forge_pipeline import run_auto_plan as _run_auto_plan
from .forge_plan_apply import (
    apply_all_applyable as _apply_all_applyable,
)
from .forge_plan_apply import (
    apply_card as _apply_card,
)


def _bound_enforce(project_root, args):
    """a3-side enforce handler — bound into the a1 dispatcher at
    module import time so the upward-import boundary stays clean."""
    src = _Path(args.get("source", project_root)).resolve()
    apply = bool(args.get("apply", False))
    return _run_enforce(src, apply=apply)


def _bound_auto_plan(project_root, args):
    """a3-side auto_plan handler — exposes the agent_plan/v1 emitter
    through the MCP dispatcher with the same a1↔a3 injection pattern
    used for enforce."""
    target = _Path(args.get("target", project_root)).resolve()
    plan = _run_auto_plan(
        target=target,
        goal=str(args.get("goal", "improve repo conformance")),
        mode=str(args.get("mode", "improve")),
        package=args.get("package"),
        top_n=int(args.get("top_n", 7)),
    )
    if bool(args.get("save", False)):
        plan_id = _PlanStore(target).save_plan(plan)
        plan["id"] = plan_id
    return plan


def _bound_auto_step(project_root, args):
    project = _Path(args.get("project", project_root)).resolve()
    plan_id = str(args["plan_id"])
    card_id = str(args["card_id"])
    apply = bool(args.get("apply", False))
    plan = _PlanStore(project).load_plan(plan_id)
    if plan is None:
        return {
            "schema_version": "atomadic-forge.plan_apply/v1",
            "plan_id": plan_id, "card_id": card_id, "apply": apply,
            "status": "failed",
            "detail": {"reason": f"plan id {plan_id!r} not found"},
        }
    return _apply_card(project, plan, card_id, apply=apply)


def _bound_auto_apply(project_root, args):
    project = _Path(args.get("project", project_root)).resolve()
    plan_id = str(args["plan_id"])
    apply = bool(args.get("apply", False))
    plan = _PlanStore(project).load_plan(plan_id)
    if plan is None:
        return {
            "schema_version": "atomadic-forge.plan_apply_all/v1",
            "plan_id": plan_id, "apply": apply,
            "results": [], "halted_on": "failed",
            "applied_count": 0, "skipped_count": 0,
            "detail": {"reason": f"plan id {plan_id!r} not found"},
        }
    return _apply_all_applyable(project, plan, apply=apply)


register_enforce_handler(_bound_enforce)
register_auto_plan_handler(_bound_auto_plan)
register_auto_step_handler(_bound_auto_step)
register_auto_apply_handler(_bound_auto_apply)


# ---- Lane C W5: subscription gate -------------------------------------

_AUTH_REQUIRED_METHODS = frozenset({"tools/call", "resources/read"})
"""JSON-RPC methods that require a paid subscription.

Everything else (``initialize``, ``ping``, ``tools/list``,
``resources/list``, ``notifications/initialized``, ``shutdown``) is
read-only metadata and stays open so MCP clients can finish their
handshake before the user has logged in.
"""

_AUTH_ERROR_CODE = -32001
_UPGRADE_URL = "https://atomadic.tech/forge"


def _auth_check(
    env: dict[str, str],
    *,
    client: ForgeAuthClient,
) -> tuple[bool, str, str]:
    """Return (ok, reason, api_key).

    ``ok`` is True when the gate should let the call through. ``reason``
    is the human-readable explanation (used to populate the JSON-RPC
    error ``details`` field on rejection). ``api_key`` is the raw key
    when present (so the caller can fire usage-log telemetry); empty
    string when no key was configured.
    """
    api_key = read_api_key_from_env(env)
    if not api_key:
        return False, "FORGE_API_KEY not set or wrong prefix", ""
    result = client.verify(api_key)
    if result.get("ok"):
        return True, str(result.get("reason", "")), api_key
    return False, str(result.get("reason", "verify failed")), api_key


def _auth_error_response(
    msg_id: object, *, reason: str,
) -> dict[str, object]:
    """Build the canonical -32001 error response."""
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {
            "code": _AUTH_ERROR_CODE,
            "message": "Forge subscription required",
            "data": {
                "upgrade_url": _UPGRADE_URL,
                "details": reason,
                "env": "FORGE_API_KEY",
                "login_command": "forge login",
            },
        },
    }


def serve_stdio(
    *,
    project_root: Path,
    stdin: IO[str] | None = None,
    stdout: IO[str] | None = None,
    stderr: IO[str] | None = None,
    auth_client: ForgeAuthClient | None = None,
    env: dict[str, str] | None = None,
) -> int:
    """Run the MCP stdio loop until stdin closes.

    Returns the exit code: 0 for clean shutdown, 1 for unrecoverable
    setup error. Per-request errors NEVER raise — they're returned to
    the client as JSON-RPC error responses.
    """
    src_in = stdin or sys.stdin
    src_out = stdout or sys.stdout
    src_err = stderr or sys.stderr
    eff_env: dict[str, str] = dict(env if env is not None else os.environ)
    client = auth_client or ForgeAuthClient()
    project_hash = hash_project_path(project_root)

    project_root = Path(project_root).resolve()
    if not project_root.exists():
        src_err.write(f"forge mcp serve: project_root not found: "
                       f"{project_root}\n")
        return 1
    src_err.write(f"forge mcp serve: ready (project_root={project_root})\n")
    src_err.flush()

    for raw in src_in:
        line = raw.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {exc}",
                },
            }
            _write(src_out, response)
            continue
        if isinstance(request, dict) and request.get("method") == "shutdown":
            _write(src_out, {"jsonrpc": "2.0",
                              "id": request.get("id"), "result": {}})
            break
        # Lane C W5: subscription gate. Read-only metadata methods
        # bypass the check so initialize/tools/list still succeed
        # before login; tools/call and resources/read are gated.
        method = request.get("method") if isinstance(request, dict) else None
        if method in _AUTH_REQUIRED_METHODS:
            ok, reason, api_key = _auth_check(eff_env, client=client)
            if not ok:
                _write(src_out, _auth_error_response(
                    request.get("id") if isinstance(request, dict) else None,
                    reason=reason,
                ))
                continue
            # Fire-and-forget usage telemetry for tools/call only.
            if method == "tools/call" and api_key:
                params = request.get("params") or {}
                tool_name = (
                    params.get("name") if isinstance(params, dict) else None
                ) or "?"
                try:
                    client.log_usage(api_key, str(tool_name), project_hash)
                except Exception:  # noqa: BLE001 — telemetry MUST NOT block
                    pass
        response = dispatch_request(request, project_root=project_root)
        if response is not None:
            _write(src_out, response)
    return 0


def _write(stream: IO[str], payload: dict) -> None:
    stream.write(json.dumps(payload, default=str) + "\n")
    stream.flush()
