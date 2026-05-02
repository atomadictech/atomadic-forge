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
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .. import __version__
from ..a0_qk_constants.receipt_schema import SCHEMA_VERSION_V1
from .agent_context_pack import emit_context_pack
from .agent_memory import what_failed_last_time, why_did_this_change
from .agent_summary import summarize_blockers
from .certify_checks import certify
from .lineage_chain import canonical_receipt_hash, verify_chain_link
from .lineage_reader import list_artifacts, read_lineage
from .manifest_diff import diff_manifests as _diff_manifests
from .patch_scorer import score_patch as _score_patch
from .plan_adapter import adapt_plan as _adapt_plan
from .policy_loader import load_policy as _load_policy
from .preflight_change import preflight_change as _preflight_change
from .receipt_emitter import build_receipt
from .recipes import all_recipes, get_recipe, list_recipes
from .repo_explainer import explain_repo as _explain_repo
from .scout_walk import harvest_repo
from .sidecar_parser import find_sidecar_for as _find_sidecar_for
from .sidecar_parser import parse_sidecar_file as _parse_sidecar_file
from .sidecar_validator import validate_sidecar as _validate_sidecar
from .test_selector import select_tests as _select_tests
from .tool_composer import compose_tools as _compose_tools
from .wire_check import scan_violations
from .worktree_status import worktree_status as _worktree_status

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
    verbose = bool(args.get("verbose", False))
    report = harvest_repo(target)
    if not verbose:
        report = {k: v for k, v in report.items() if k != "symbols"}
    return report


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


def _tool_context_pack(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Codex 'Copilot's Copilot' #1 — first-call context pack."""
    root = Path(args.get("target", project_root)).resolve()
    focus = args.get("focus")
    intent = str(args.get("intent", ""))
    files = list(args.get("files") or args.get("target_files") or [])
    try:
        scout = harvest_repo(root)
    except (OSError, ValueError):
        scout = None
    try:
        wire = scan_violations(root)
    except (OSError, ValueError):
        wire = None
    try:
        cert = certify(root, project=root.name)
    except (OSError, RuntimeError, ValueError):
        cert = None
    return emit_context_pack(
        project_root=root,
        scout_report=scout, wire_report=wire, certify_report=cert,
        focus=str(focus) if focus is not None else None,
        intent=intent,
        files=[str(f) for f in files],
    )


def _tool_preflight_change(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Codex 'Copilot's Copilot' #2 — pre-edit guardrail."""
    root = Path(args.get("project_root", project_root)).resolve()
    intent = str(args.get("intent", ""))
    proposed = list(args.get("proposed_files") or [])
    threshold = int(args.get("scope_threshold", 8))
    if not intent:
        return {"schema_version": "atomadic-forge.preflight/v1",
                "error": "intent is required"}
    if not proposed:
        return {"schema_version": "atomadic-forge.preflight/v1",
                "error": "proposed_files must be non-empty"}
    return _preflight_change(
        intent=intent, proposed_files=proposed,
        project_root=root, scope_threshold=threshold,
    )


def _tool_score_patch(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Codex 'Copilot's Copilot' #3 — pre-merge patch risk scorer."""
    diff = str(args.get("diff", ""))
    root = Path(args.get("project_root", project_root)).resolve()
    return _score_patch(diff, project_root=root)


def _tool_select_tests(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Codex #7 — minimum + full-confidence test set per intent."""
    root = Path(args.get("project_root", project_root)).resolve()
    return _select_tests(
        intent=str(args.get("intent", "")),
        changed_files=list(args.get("changed_files") or []),
        project_root=root,
    )


def _tool_rollback_plan(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Codex #11 — reversible-move guidance."""
    from .rollback_planner import rollback_plan as _rb
    root = Path(args.get("project_root", project_root)).resolve()
    return _rb(
        changed_files=list(args.get("changed_files") or []),
        project_root=root,
    )


def _tool_explain_repo(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Codex #6 — humane operational orientation."""
    root = Path(args.get("project_root", project_root)).resolve()
    try:
        scout = harvest_repo(root)
    except (OSError, ValueError):
        scout = None
    try:
        wire = scan_violations(root)
    except (OSError, ValueError):
        wire = None
    try:
        cert = certify(root, project=root.name)
    except (OSError, RuntimeError, ValueError):
        cert = None
    pack = emit_context_pack(project_root=root, scout_report=scout,
                              wire_report=wire, certify_report=cert)
    return _explain_repo(
        project_root=root,
        repo_purpose=pack.get("repo_purpose", ""),
        scout_report=scout, wire_report=wire, certify_report=cert,
        depth=str(args.get("depth", "agent")),
    )


def _tool_adapt_plan(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Codex #8 — capability-aware card filtering."""
    plan = args.get("plan") or {}
    if not isinstance(plan, dict):
        return {"error": "plan must be an agent_plan/v1 object"}
    return _adapt_plan(
        plan,
        agent_capabilities=list(args.get("agent_capabilities") or []),
    )


def _tool_compose_tools(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Codex #9 — tool-use planner."""
    return _compose_tools(goal=str(args.get("goal", "")))


def _tool_load_policy(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Codex #10 — read [tool.forge.agent] from pyproject.toml."""
    root = Path(args.get("project_root", project_root)).resolve()
    return _load_policy(root)


def _tool_why_did_this_change(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Codex #5 — agent memory: lineage + plan-event lookup."""
    root = Path(args.get("project_root", project_root)).resolve()
    return why_did_this_change(file=str(args.get("file", "")), project_root=root)


def _tool_what_failed_last_time(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Codex #5 — failed/rolled_back plan events for an area."""
    root = Path(args.get("project_root", project_root)).resolve()
    return what_failed_last_time(area=str(args.get("area", "")), project_root=root)


def _tool_list_recipes(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Codex #12 — list golden-path recipes."""
    return {
        "schema_version": "atomadic-forge.recipe.list/v1",
        "recipes": list_recipes(),
        "recipe_count": len(list_recipes()),
        "catalogue": {n: r["description"] for n, r in all_recipes().items()},
    }


def _tool_get_recipe(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Codex #12 — fetch a named recipe."""
    name = str(args.get("name", ""))
    recipe = get_recipe(name)
    if recipe is None:
        return {"error": f"unknown recipe: {name!r}"}
    return recipe


def _tool_worktree_status(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Agent worktree orientation: git, remote, version, stale command."""
    root = Path(args.get("project_root", project_root)).resolve()
    return _worktree_status(
        project_root=root,
        max_files=int(args.get("max_files", 20)),
    )


def _tool_trust_gate_response(project_root: Path,
                                  args: dict[str, Any]) -> dict[str, Any]:
    """Backport from Forge Deluxe cycle 13. Run deterministic
    hallucination checks against an LLM response. No LLM in the
    loop; pure AST + regex over code blocks + URLs + claims."""
    from .trust_gate_response import gate_response
    response = str(args.get("response", ""))
    known = args.get("known_capabilities") or []
    local_prefix = str(args.get("local_pkg_prefix", ""))
    if not response:
        return {"error": "missing 'response' argument"}
    verdict = gate_response(
        response,
        known_capabilities=list(known) if known else None,
        local_pkg_prefix=local_prefix,
    )
    return {
        "schema": verdict.schema,
        "score": verdict.score,
        "safe_to_act": verdict.safe_to_act,
        "code_blocks_count": verdict.code_blocks_count,
        "citations_count": verdict.citations_count,
        "findings": [
            {"severity": f.severity, "category": f.category,
              "detail": f.detail, "evidence": f.evidence}
            for f in verdict.findings
        ],
    }


def _tool_exported_api_check(project_root: Path,
                                  args: dict[str, Any]) -> dict[str, Any]:
    """Backport from Forge Deluxe cycle 15. Verify a module's
    docstring claims actually resolve to top-level definitions.
    Catches the failure mode where a body-fill emit ships a
    docstring promising a public function that isn't there."""
    from .exported_api_check import check_exported_api
    source = args.get("source")
    if not source and args.get("path"):
        try:
            source = Path(args["path"]).read_text(encoding="utf-8")
        except OSError as e:
            return {"error": f"cannot read path: {e}"}
    if not source:
        return {"error": "missing 'source' or 'path' argument"}
    strict = bool(args.get("strict", False))
    result = check_exported_api(source, strict=strict)
    return {
        "schema": result.schema,
        "ok": result.ok,
        "detail": result.detail,
        "claims_found": [
            {"name": c.name, "source": c.source}
            for c in result.claims_found
        ],
        "resolved": list(result.resolved),
        "unresolved": list(result.unresolved),
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


def _tool_auto_step_unbound(project_root, args):
    return {
        "schema_version": "atomadic-forge.plan_apply/v1",
        "wired": False,
        "note": "auto_step not wired — import a3.mcp_server.",
    }


def _tool_auto_apply_unbound(project_root, args):
    return {
        "schema_version": "atomadic-forge.plan_apply_all/v1",
        "wired": False,
        "note": "auto_apply not wired — import a3.mcp_server.",
    }


_auto_step_handler: ToolHandler = _tool_auto_step_unbound
_auto_apply_handler: ToolHandler = _tool_auto_apply_unbound


def _tool_auto_step(project_root, args):
    return _auto_step_handler(project_root, args)


def _tool_auto_apply(project_root, args):
    return _auto_apply_handler(project_root, args)


def register_auto_step_handler(handler: ToolHandler) -> None:
    global _auto_step_handler
    _auto_step_handler = handler


def register_auto_apply_handler(handler: ToolHandler) -> None:
    global _auto_apply_handler
    _auto_apply_handler = handler


def _tool_emergent_scan_unbound(project_root: Path,
                                 args: dict[str, Any]) -> dict[str, Any]:
    """emergent_scan stub — a3 binds the real EmergentScan at import time via
    ``register_emergent_scan_handler``.  Same a1↔a3 injection pattern used by
    enforce, auto_plan, auto_step, and auto_apply."""
    return {
        "schema_version": "atomadic-forge.emergent.scan/v1",
        "wired": False,
        "note": (
            "emergent_scan not yet wired — import "
            "atomadic_forge.a3_og_features.mcp_server (or any code "
            "under a3) to register the real handler."
        ),
    }


def _tool_synergy_scan_unbound(project_root: Path,
                                args: dict[str, Any]) -> dict[str, Any]:
    """synergy_scan stub — same pattern as emergent_scan."""
    return {
        "schema_version": "atomadic-forge.synergy.scan/v1",
        "wired": False,
        "note": (
            "synergy_scan not yet wired — import "
            "atomadic_forge.a3_og_features.mcp_server (or any code "
            "under a3) to register the real handler."
        ),
    }


_emergent_scan_handler: ToolHandler = _tool_emergent_scan_unbound
_synergy_scan_handler: ToolHandler = _tool_synergy_scan_unbound


def _tool_emergent_scan(project_root: Path,
                         args: dict[str, Any]) -> dict[str, Any]:
    return _emergent_scan_handler(project_root, args)


def _tool_synergy_scan(project_root: Path,
                        args: dict[str, Any]) -> dict[str, Any]:
    return _synergy_scan_handler(project_root, args)


def _tool_doctor(project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Environment diagnostic — Forge version, Python info, optional deps.

    Same data the `forge doctor` CLI verb prints, returned as JSON. Useful
    as the first call after `initialize` to confirm the runtime is healthy
    and to discover which optional dependencies (`complexipy`,
    `cryptography`, `tomli`) are wired in.
    """
    import importlib

    def _check(dep: str) -> str:
        try:
            importlib.import_module(dep)
            return "ok"
        except ImportError:
            return "missing"

    return {
        "schema_version": "atomadic-forge.doctor/v1",
        "atomadic_forge_version": __version__,
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": sys.platform,
        "stdout_encoding": getattr(sys.stdout, "encoding", "?"),
        "optional_deps": {
            "complexipy": _check("complexipy"),
            "cryptography": _check("cryptography"),
            "tomli": _check("tomli"),
        },
    }


def _tool_sidecar_validate(project_root: Path,
                            args: dict[str, Any]) -> dict[str, Any]:
    """Cross-check a `.forge` sidecar against its source AST.

    Looks for ``<source>.forge`` next to the source file. Reports drift
    across S0000–S0007 finding classes. Pure: no exec, no LLM.
    """
    src_arg = args.get("source_file") or args.get("path")
    if not src_arg:
        return {"error": "missing 'source_file' argument"}
    src_path = Path(str(src_arg))
    if not src_path.is_absolute():
        src_path = (project_root / src_path).resolve()
    if not src_path.is_file():
        return {"error": f"source_file not found: {src_path}"}
    sidecar_path = _find_sidecar_for(src_path)
    parse = _parse_sidecar_file(sidecar_path)
    if parse["errors"]:
        return {
            "schema_version": "atomadic-forge.sidecar_validate/v1",
            "verdict": "FAIL",
            "sidecar_path": str(sidecar_path),
            "parse_errors": parse["errors"],
            "findings": [],
        }
    try:
        source_text = src_path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"error": f"could not read {src_path}: {exc}"}
    rep = _validate_sidecar(
        parse["sidecar"], source_text=source_text, source_path=src_path,
    )
    return {
        "schema_version": "atomadic-forge.sidecar_validate/v1",
        "source_file": str(src_path),
        "sidecar_path": str(sidecar_path),
        **rep,
    }


def _tool_manifest_diff(project_root: Path,
                         args: dict[str, Any]) -> dict[str, Any]:
    """Schema-aware diff between two Forge manifests.

    Accepts either inline dicts (``left`` / ``right``) or filesystem paths
    (``left_path`` / ``right_path``) to JSON manifests. Reports added /
    removed / moved symbols, tier-distribution deltas, effect-distribution
    deltas, and certify-score deltas.
    """
    def _resolve(side: str) -> tuple[dict | None, str | None]:
        inline = args.get(side)
        if isinstance(inline, dict) and inline:
            return inline, None
        path_key = f"{side}_path"
        path_arg = args.get(path_key)
        if not path_arg:
            return None, f"missing '{side}' or '{path_key}'"
        p = Path(str(path_arg))
        if not p.is_absolute():
            p = (project_root / p).resolve()
        if not p.is_file():
            return None, f"{path_key} not found: {p}"
        try:
            return json.loads(p.read_text(encoding="utf-8")), None
        except (OSError, json.JSONDecodeError) as exc:
            return None, f"could not parse {p}: {exc}"

    left, lerr = _resolve("left")
    if lerr:
        return {"error": lerr}
    right, rerr = _resolve("right")
    if rerr:
        return {"error": rerr}
    try:
        delta = _diff_manifests(left, right)
    except ValueError as exc:
        return {"error": str(exc)}
    return {
        "schema_version": "atomadic-forge.manifest_diff/v1",
        **delta,
    }


def register_emergent_scan_handler(handler: ToolHandler) -> None:
    """Bind the real EmergentScan-backed handler from a3."""
    global _emergent_scan_handler
    _emergent_scan_handler = handler


def register_synergy_scan_handler(handler: ToolHandler) -> None:
    """Bind the real SynergyScan-backed handler from a3."""
    global _synergy_scan_handler
    _synergy_scan_handler = handler


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
                "save":     {"type": "boolean", "default": False,
                              "description": "Persist the plan + return its id."},
            },
            "additionalProperties": False,
        },
        "handler": _tool_auto_plan,
    },
    "auto_step": {
        "name": "auto_step",
        "description": (
            "Apply ONE card from a saved plan. apply=False is dry-run "
            "(default); apply=True executes the bounded change. The "
            "card's outcome (applied / rolled_back / skipped / failed) "
            "is recorded in the plan's state file."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project":  {"type": "string"},
                "plan_id":  {"type": "string"},
                "card_id":  {"type": "string"},
                "apply":    {"type": "boolean", "default": False},
            },
            "required": ["plan_id", "card_id"],
            "additionalProperties": False,
        },
        "handler": _tool_auto_step,
    },
    "auto_apply": {
        "name": "auto_apply",
        "description": (
            "Apply ALL applyable cards from a saved plan in order. "
            "Halts on the first rolled_back or failed outcome so the "
            "agent can inspect before cascading further mutations."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project":  {"type": "string"},
                "plan_id":  {"type": "string"},
                "apply":    {"type": "boolean", "default": False},
            },
            "required": ["plan_id"],
            "additionalProperties": False,
        },
        "handler": _tool_auto_apply,
    },
    "context_pack": {
        "name": "context_pack",
        "description": (
            "Codex 'Copilot's Copilot' #1 — first-call context bundle. "
            "Returns repo purpose, the architecture law, tier map, "
            "current blockers, best next action, test commands, "
            "release gate, risky files, and recent lineage. The single "
            "tool every coding agent should call on connect."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string",
                            "description": "Project path; defaults to project_root."},
                "focus": {
                    "type": "string",
                    "enum": ["orientation", "change", "release", "debug"],
                    "description": (
                        "Optional mode. 'change' adds file-targeted "
                        "preflight/test context; 'release' emphasizes the "
                        "gate; 'debug' emphasizes lineage."
                    ),
                },
                "intent": {
                    "type": "string",
                    "description": "One-line task intent for suggestions.",
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Target or changed files for focused context.",
                },
            },
            "additionalProperties": False,
        },
        "handler": _tool_context_pack,
    },
    "preflight_change": {
        "name": "preflight_change",
        "description": (
            "Codex 'Copilot's Copilot' #2 — pre-edit guardrail. Given "
            "an intent string + a list of proposed_files, returns each "
            "file's detected tier, forbidden imports, likely affected "
            "tests, sibling files to read first, and whether the "
            "write_scope is too broad. Most agent mistakes happen "
            "BEFORE code is written; this surfaces them in advance."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root":    {"type": "string"},
                "intent":          {"type": "string"},
                "proposed_files":  {"type": "array",
                                     "items": {"type": "string"}},
                "scope_threshold": {"type": "integer", "default": 8},
            },
            "required": ["intent", "proposed_files"],
            "additionalProperties": False,
        },
        "handler": _tool_preflight_change,
    },
    "score_patch": {
        "name": "score_patch",
        "description": (
            "Codex 'Copilot's Copilot' #3 — patch risk scorer. Submit "
            "a unified-diff string and get back architecture risk, "
            "test risk, public_API risk, release risk, a "
            "needs_human_review boolean, and suggested validation "
            "commands. Forge becomes a PR reviewer BEFORE the PR exists."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "diff": {"type": "string",
                          "description": "Unified-diff text "
                                          "(git diff / patch format)."},
                "project_root": {"type": "string"},
            },
            "required": ["diff"],
            "additionalProperties": False,
        },
        "handler": _tool_score_patch,
    },
    "select_tests": {
        "name": "select_tests",
        "description": (
            "Codex #7 — minimum + full-confidence test sets per "
            "intent. Returns mirror-name matches plus tier-mate tests; "
            "agents stop over-running or under-running tests."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root":  {"type": "string"},
                "intent":        {"type": "string"},
                "changed_files": {"type": "array",
                                    "items": {"type": "string"}},
            },
            "required": ["changed_files"],
            "additionalProperties": False,
        },
        "handler": _tool_select_tests,
    },
    "rollback_plan": {
        "name": "rollback_plan",
        "description": (
            "Codex #11 — structured undo plan: files to remove, caches "
            "to clean, docs to restore, tests to rerun, risk level."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root":  {"type": "string"},
                "changed_files": {"type": "array",
                                    "items": {"type": "string"}},
            },
            "required": ["changed_files"],
            "additionalProperties": False,
        },
        "handler": _tool_rollback_plan,
    },
    "explain_repo": {
        "name": "explain_repo",
        "description": (
            "Codex #6 — humane operational orientation. One-liner + "
            "core flow + do_not_break list + important tests + "
            "release state. Different from context_pack (which is "
            "data-rich); this is decision-oriented."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "depth":        {"type": "string", "default": "agent"},
            },
            "additionalProperties": False,
        },
        "handler": _tool_explain_repo,
    },
    "adapt_plan": {
        "name": "adapt_plan",
        "description": (
            "Codex #8 — capability-aware card filtering. Tag each "
            "card with recommended_handling: apply / delegate / "
            "ask_human / report_only based on agent_capabilities."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan":               {"type": "object"},
                "agent_capabilities": {"type": "array",
                                         "items": {"type": "string"}},
            },
            "required": ["plan"],
            "additionalProperties": False,
        },
        "handler": _tool_adapt_plan,
    },
    "compose_tools": {
        "name": "compose_tools",
        "description": (
            "Codex #9 — tool-use planner. Match a goal keyword to a "
            "named recipe (orient / release_check / fix_violation / "
            "before_edit / verify_patch) and return the ordered tool "
            "sequence the agent should run."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"goal": {"type": "string"}},
            "additionalProperties": False,
        },
        "handler": _tool_compose_tools,
    },
    "load_policy": {
        "name": "load_policy",
        "description": (
            "Codex #10 — read [tool.forge.agent] from the project's "
            "pyproject.toml. Returns the v1 policy dict with "
            "protected_files / release_gate / max_files_per_patch / "
            "require_human_review_for fields populated (defaults "
            "applied where the user didn't override)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"project_root": {"type": "string"}},
            "additionalProperties": False,
        },
        "handler": _tool_load_policy,
    },
    "why_did_this_change": {
        "name": "why_did_this_change",
        "description": (
            "Codex #5 — agent memory: every lineage entry + plan "
            "event that references the named file. Helps the next "
            "agent see what was tried, by whom, and when."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "file":         {"type": "string"},
            },
            "required": ["file"],
            "additionalProperties": False,
        },
        "handler": _tool_why_did_this_change,
    },
    "what_failed_last_time": {
        "name": "what_failed_last_time",
        "description": (
            "Codex #5 — failed / rolled_back plan events matching an "
            "area substring. Surfaces the failures the agent should "
            "expect to confront."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "area":         {"type": "string"},
            },
            "required": ["area"],
            "additionalProperties": False,
        },
        "handler": _tool_what_failed_last_time,
    },
    "list_recipes": {
        "name": "list_recipes",
        "description": (
            "Codex #12 — list named golden-path recipes "
            "(release_hardening, add_cli_command, fix_wire_violation, "
            "add_feature, bump_version, fix_test_detection, publish_mcp). "
            "Pair with get_recipe."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "handler": _tool_list_recipes,
    },
    "get_recipe": {
        "name": "get_recipe",
        "description": (
            "Codex #12 — fetch one named recipe (checklist + "
            "file_scope_hints + validation_gate)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
        "handler": _tool_get_recipe,
    },
    "worktree_status": {
        "name": "worktree_status",
        "description": (
            "Agent worktree orientation: reports git root, branch, "
            "upstream drift, dirty files, remotes, declared/package "
            "versions, resolved forge command path/version, and "
            "recommendations before an agent mutates a checkout."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "max_files": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum dirty status lines to include.",
                },
            },
            "additionalProperties": False,
        },
        "handler": _tool_worktree_status,
    },
    "trust_gate_response": {
        "name": "trust_gate_response",
        "description": (
            "Backport from Forge Deluxe cycle 13. Pure-AST "
            "hallucination detector for LLM responses: catches "
            "unresolved imports, syntax errors in code blocks, "
            "stub-pattern code, false capability claims, and "
            "placeholder URLs. No LLM in the loop."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "response": {
                    "type": "string",
                    "description": "The LLM response to gate.",
                },
                "known_capabilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional list of capability ids the "
                        "caller's project actually ships. When "
                        "supplied, false-claim detection becomes "
                        "active."
                    ),
                },
                "local_pkg_prefix": {
                    "type": "string",
                    "description": (
                        "Dotted prefix considered locally "
                        "available (e.g. 'atomadic_forge')."
                    ),
                },
            },
            "required": ["response"],
            "additionalProperties": False,
        },
        "handler": _tool_trust_gate_response,
    },
    "exported_api_check": {
        "name": "exported_api_check",
        "description": (
            "Backport from Forge Deluxe cycle 15. Verify a "
            "Python module's docstring promises (backticked + "
            "signature-pattern identifiers) actually resolve to "
            "top-level definitions. Catches the body-fill emit "
            "that ships a docstring claiming a public function "
            "that was never defined."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Python source to check.",
                },
                "path": {
                    "type": "string",
                    "description": (
                        "Alternative to source: read from this "
                        "file."
                    ),
                },
                "strict": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "When true, also fail on unresolved "
                        "PascalCase claims (default: only "
                        "snake_case unresolved are fatal)."
                    ),
                },
            },
            "additionalProperties": False,
        },
        "handler": _tool_exported_api_check,
    },
    "emergent_scan": {
        "name": "emergent_scan",
        "description": (
            "Discover novel function/composite compositions across all tiers. "
            "Walks a0/a1/a2/a3 symbols and finds type-compatible chains where "
            "the output of one symbol feeds the input of another — surfacing "
            "capabilities that don't exist yet as a3 features. Scored on: "
            "domain-crossing (+12 each), tier-spanning (+8 each), gap bonus "
            "(+20 when the domain pair has no existing a3 feature), specificity "
            "(+5 per typed bridge), and novel composition (+10 when all symbols "
            "come from distinct modules). Primitive and Any seeds are filtered "
            "to keep results domain-specific and actionable."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": "Repo root; defaults to the server's project_root.",
                },
                "package": {
                    "type": "string",
                    "default": "atomadic_forge",
                    "description": "Python package name to scan.",
                },
                "top_n": {
                    "type": "integer",
                    "default": 25,
                    "description": "Number of top candidates to return.",
                },
                "max_depth": {
                    "type": "integer",
                    "default": 3,
                    "description": "Maximum chain length.",
                },
            },
            "additionalProperties": False,
        },
        "handler": _tool_emergent_scan,
    },
    "synergy_scan": {
        "name": "synergy_scan",
        "description": (
            "Discover feature-level synergies across CLI verbs, a3 features, "
            "and a2 composites. Eight detection signals: json_artifact (file "
            "handoff), in_memory_pipe (vocab overlap), shared_schema (same "
            "schema string), shared_vocabulary (Jaccard ≥ 0.4), phase_omission "
            "(unwired phase chain), feedback_loop (certify↔materialize iterate "
            "cycle), type_pipeline (named-type direct in-memory pipe), and "
            "data_flow_gap (same specific type in different tiers, no adapter). "
            "Returns ranked SynergyCandidateCards; call 'forge synergy implement "
            "<id>' to materialise the top candidate as a commands/ adapter."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": "Repo root; defaults to the server's project_root.",
                },
                "package": {
                    "type": "string",
                    "default": "atomadic_forge",
                    "description": "Python package name to scan.",
                },
                "top_n": {
                    "type": "integer",
                    "default": 25,
                    "description": "Number of top candidates to return.",
                },
            },
            "additionalProperties": False,
        },
        "handler": _tool_synergy_scan,
    },
    "doctor": {
        "name": "doctor",
        "description": (
            "Environment diagnostic — Forge version, Python info, "
            "platform, stdout encoding, and optional dependency status "
            "(complexipy, cryptography, tomli). Useful as the first "
            "call after `initialize` to confirm the runtime is healthy."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "handler": _tool_doctor,
    },
    "sidecar_validate": {
        "name": "sidecar_validate",
        "description": (
            "Cross-check a `.forge` sidecar declaration against its "
            "source AST. Pure: parses both inputs, no exec, no LLM. "
            "Reports drift across S0000–S0007 finding classes — "
            "missing/extra symbols, purity violations, tier mismatches."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_file": {
                    "type": "string",
                    "description": (
                        "Path to the source file (relative to "
                        "project_root or absolute). The matching "
                        "<source>.forge sidecar is auto-located."
                    ),
                },
            },
            "required": ["source_file"],
            "additionalProperties": False,
        },
        "handler": _tool_sidecar_validate,
    },
    "manifest_diff": {
        "name": "manifest_diff",
        "description": (
            "Schema-aware diff between two Forge manifests "
            "(scout.json / certify.json / wire.json). Reports added / "
            "removed / moved symbols, tier-distribution deltas, "
            "effect-distribution deltas, and certify-score deltas with "
            "component breakdown. Use to compare baseline vs head in "
            "PR review or to track repo trajectory across runs."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "left": {
                    "type": "object",
                    "description": (
                        "Inline left manifest dict. Mutually exclusive "
                        "with `left_path`."
                    ),
                },
                "left_path": {
                    "type": "string",
                    "description": "Path to the left manifest JSON file.",
                },
                "right": {
                    "type": "object",
                    "description": (
                        "Inline right manifest dict. Mutually "
                        "exclusive with `right_path`."
                    ),
                },
                "right_path": {
                    "type": "string",
                    "description": "Path to the right manifest JSON file.",
                },
            },
            "additionalProperties": False,
        },
        "handler": _tool_manifest_diff,
    },
}

_CLI_FALLBACKS: dict[str, str] = {
    "recon": "forge recon <repo> --json",
    "wire": "forge wire <tier-root> --json",
    "certify": "forge certify <project-root> --json",
    "enforce": "forge enforce <tier-root>",
    "audit_list": "forge audit list --json",
    "auto_plan": "forge plan <repo> --json",
    "auto_step": "forge plan-step <plan-id> <card-id> --project <repo>",
    "auto_apply": "forge plan-apply <plan-id> --project <repo>",
    "context_pack": (
        "forge context-pack <project-root> "
        "[--focus change --intent <intent> --file <path>] --json"
    ),
    "preflight_change": "forge preflight <intent> <file...> --project <repo> --json",
    "score_patch": "git diff | forge score-patch --project-root <repo>",
    "select_tests": "forge select-tests --file <path> --project-root <repo> <intent>",
    "rollback_plan": "forge rollback-plan --file <path> --project-root <repo>",
    "explain_repo": "forge explain-repo <project-root>",
    "adapt_plan": "forge adapt-plan --file <plan.json>",
    "compose_tools": "forge compose-tools <goal>",
    "load_policy": "forge load-policy <project-root>",
    "why_did_this_change": "forge why-did-this-change <file> --project-root <repo>",
    "what_failed_last_time": "forge what-failed-last-time <area> --project-root <repo>",
    "list_recipes": "forge recipes --json",
    "get_recipe": "forge recipes <name> --json",
    "worktree_status": "forge worktree status <project-root> --json",
    "trust_gate_response": "MCP-only: trust_gate_response",
    "exported_api_check": "MCP-only: exported_api_check",
    "emergent_scan": "forge emergent scan <repo> --json",
    "synergy_scan": "forge synergy scan <repo> --json",
    "doctor": "forge doctor --json",
    "sidecar_validate": "forge sidecar validate <source-file> --json",
    "manifest_diff": "forge diff <left-manifest> <right-manifest> --json",
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
    if schema == "atomadic-forge.context_pack/v1":
        # Re-surface the embedded blockers_summary.
        return result.get("blockers_summary")
    if schema == "atomadic-forge.preflight/v1":
        too_broad = result.get("write_scope_too_broad", False)
        n = result.get("write_scope_size", 0)
        return {
            "schema_version": "atomadic-forge.summary/v1",
            "verdict": "REFINE" if too_broad else "PASS",
            "score": None,
            "blocker_count": len(result.get("overall_notes") or []),
            "auto_fixable_count": 0,
            "blockers": [],
            "next_command": (
                f"# write_scope size {n} > threshold; split the change"
                if too_broad
                else "# preflight clean; proceed with bounded edit"
            ),
        }
    if schema == "atomadic-forge.patch_score/v1":
        return {
            "schema_version": "atomadic-forge.summary/v1",
            "verdict": "REFINE" if result.get("needs_human_review") else "PASS",
            "score": None,
            "blocker_count": (
                int(result.get("architectural_risk", False))
                + int(result.get("test_risk", False))
                + int(result.get("public_api_risk", False))
                + int(result.get("release_risk", False))
            ),
            "auto_fixable_count": 0,
            "blockers": [],
            "next_command": (
                "# needs_human_review=True — block auto-merge"
                if result.get("needs_human_review")
                else "# score_patch clean; proceed with merge"
            ),
        }
    if schema == "atomadic-forge.agent_plan/v1":
        # Plans already ARE summary-shaped — surface a tiny digest
        # so MCP clients can branch without re-parsing the full plan.
        # Codex feedback (round 3): the plan now carries a 'score'
        # field; inherit it so MCP _summary matches forge://summary/blockers.
        return {
            "schema_version": "atomadic-forge.summary/v1",
            "verdict": result.get("verdict", "?"),
            "score": result.get("score"),
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
    server_source_path = str(Path(__file__).resolve())
    return {
        "serverInfo": {
            "name": SERVER_NAME,
            "version": __version__,
            "source_path": server_source_path,
            "python_executable": sys.executable,
        },
        "tools": [
            {"name": t["name"],
             "description": t["description"],
             "inputSchema": t["inputSchema"],
             "cli_command": _CLI_FALLBACKS.get(t["name"], ""),
             "forge_version": __version__,
             "server_source_path": server_source_path}
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
    if method in {"notifications/initialized", "initialized"}:
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
    "register_emergent_scan_handler",
    "register_synergy_scan_handler",
    # Lane B Studio's Topology Map renders against these helpers.
    "canonical_receipt_hash",
    "verify_chain_link",
]
