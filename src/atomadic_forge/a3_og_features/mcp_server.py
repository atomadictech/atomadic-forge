"""Tier a3 — stdio JSON-RPC loop wrapping the pure MCP dispatcher.

Golden Path Lane C W4 deliverable. The pure dispatcher lives in
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
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from pathlib import Path as _Path
from typing import IO

from ..a1_at_functions.mcp_protocol import (
    dispatch_request,
    register_auto_apply_handler,
    register_auto_plan_handler,
    register_auto_step_handler,
    register_enforce_handler,
)
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


def serve_stdio(
    *,
    project_root: Path,
    stdin: IO[str] | None = None,
    stdout: IO[str] | None = None,
    stderr: IO[str] | None = None,
) -> int:
    """Run the MCP stdio loop until stdin closes.

    Returns the exit code: 0 for clean shutdown, 1 for unrecoverable
    setup error. Per-request errors NEVER raise — they're returned to
    the client as JSON-RPC error responses.
    """
    src_in = stdin or sys.stdin
    src_out = stdout or sys.stdout
    src_err = stderr or sys.stderr

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
        response = dispatch_request(request, project_root=project_root)
        if response is not None:
            _write(src_out, response)
    return 0


def _write(stream: IO[str], payload: dict) -> None:
    stream.write(json.dumps(payload, default=str) + "\n")
    stream.flush()
