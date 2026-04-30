"""Atomadic Forge — unified CLI.

Public verbs:
    forge init        — interactive setup wizard (configure LLM, defaults)
    forge auto        — flagship: scout + cherry + assimilate + wire + certify
    forge recon       — scout walk only (writes scout.json)
    forge cherry      — cherry-pick from latest scout (writes cherry.json)
    forge finalize    — assimilate + wire + certify (consumes cherry.json)
    forge wire        — upward-import scanner over a tier-organized package
    forge certify     — score documentation/tests/layout/imports
    forge diff        — compare two Forge JSON manifests
    forge config      — show / set / test configuration

Specialty verbs (advanced):
    forge emergent    — symbol-level composition discovery
    forge synergy     — feature-pair discovery + auto-implement adapters
    forge commandsmith — auto-register/document/smoke CLI commands
    forge doctor      — environment diagnostic
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from typing import Annotated

import typer

from .. import __version__
from ..a1_at_functions.agent_context_pack import emit_context_pack
from ..a1_at_functions.agent_summary import (
    render_summary_text,
    summarize_blockers,
)
from ..a1_at_functions.card_renderer import render_receipt_card
from ..a1_at_functions.certify_checks import certify as certify_checks
from ..a1_at_functions.error_hints import format_hint
from ..a1_at_functions.manifest_diff import diff_manifests
from ..a1_at_functions.progress_reporter import make_stderr_reporter
from ..a1_at_functions.preflight_change import preflight_change
from ..a1_at_functions.recipes import all_recipes, get_recipe, list_recipes
from ..a1_at_functions.sidecar_parser import (
    find_sidecar_for,
    parse_sidecar_file,
)
from ..a1_at_functions.sidecar_validator import validate_sidecar
from ..a1_at_functions.receipt_emitter import build_receipt, receipt_to_json
from ..a1_at_functions.local_signer import sign_receipt_local
from ..a1_at_functions.sbom_emitter import emit_sbom
from ..a1_at_functions.scout_walk import harvest_repo
from ..a1_at_functions.wire_check import scan_violations
from ..a2_mo_composites.lineage_chain_store import LineageChainStore
from ..a2_mo_composites.plan_store import PlanStore
from ..a2_mo_composites.receipt_signer import sign_receipt
from ..a3_og_features.forge_enforce import run_enforce
from ..a3_og_features.forge_plan_apply import apply_all_applyable, apply_card
from ..a3_og_features.lsp_server import serve_stdio as lsp_serve_stdio
from ..a3_og_features.mcp_server import serve_stdio as mcp_serve_stdio
from ..a3_og_features.forge_pipeline import (
    run_auto,
    run_auto_plan,
    run_cherry,
    run_finalize,
    run_recon,
)

# Suppress SyntaxWarnings from third-party code in seed/forged directories.
warnings.filterwarnings("ignore", category=SyntaxWarning)


def _force_utf8() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"atomadic-forge {__version__}")
        raise typer.Exit()


app = typer.Typer(no_args_is_help=True,
                  help="Atomadic Forge — absorb · enforce · emerge.")


@app.callback()
def _root_callback(
    version: Annotated[bool | None, typer.Option(
        "--version", "-V",
        help="Show the Forge version and exit.",
        callback=_version_callback, is_eager=True,
    )] = None,
) -> None:
    """Root callback so --version works at the top level (Codex
    production-hardening: agents shouldn't get a usage error when
    asking for the version)."""
    return None


@app.command("init")
def init_cmd() -> None:
    """Interactive setup wizard — configure LLM, defaults, and workspace."""
    from atomadic_forge.a3_og_features.setup_wizard import run_wizard
    run_wizard(Path.cwd())


@app.command("auto")
def auto_cmd(
    target: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True,
        help="Source repository to absorb.")],
    output: Annotated[Path, typer.Argument(
        file_okay=False, dir_okay=True, resolve_path=True,
        help="Destination root for the materialized tier tree.")],
    package: Annotated[str, typer.Option("--package",
        help="Python package name to materialize under output/src/.")] = "absorbed",
    apply: Annotated[bool, typer.Option("--apply",
        help="Actually write files. Default is dry-run.")] = False,
    on_conflict: Annotated[str, typer.Option("--on-conflict",
        help="rename | first | last | fail")] = "rename",
    json_out: Annotated[bool, typer.Option("--json")] = False,
    progress: Annotated[bool | None, typer.Option(
        "--progress/--no-progress",
        help="Emit per-file scout progress to stderr. Default: auto "
             "(on when stderr is a TTY, off in CI / pipes / --json).")] = None,
    seed_determinism: Annotated[int | None, typer.Option(
        "--seed-determinism",
        help="Record a fixed RNG seed in the receipt for reproducibility audits (Lane G).",
    )] = None,
) -> None:
    """Flagship: scout → cherry-pick → assimilate → wire → certify in one shot."""
    output.mkdir(parents=True, exist_ok=True)
    reporter = make_stderr_reporter(
        enabled=False if json_out else progress, label="scout")
    report = run_auto(target=target, output=output, package=package,
                      apply=apply, on_conflict=on_conflict,
                      progress=reporter)
    if seed_determinism is not None:
        report.setdefault("extra", {})["seed_determinism"] = seed_determinism
    if json_out:
        typer.echo(json.dumps(report, indent=2, default=str))
        return
    typer.echo(f"\nAtomadic Forge — auto pipeline ({'APPLY' if apply else 'DRY-RUN'})")
    typer.echo("-" * 60)
    typer.echo(f"  source:        {target}")
    typer.echo(f"  destination:   {output}/{package}")
    typer.echo(f"  symbols:       {report['scout']['symbol_count']}")
    typer.echo(f"  cherry-picked: {report['cherry']['items']}")
    typer.echo(f"  components:    {report['finalize']['components_emitted']}")
    typer.echo(f"  tier_dist:     {report['finalize']['tier_distribution']}")
    typer.echo(f"  wire verdict:  {report['finalize']['wire'].get('verdict')}")
    typer.echo(f"  certify score: {report['finalize']['certify'].get('score', 0)}/100")
    if not apply:
        typer.echo("\n  (re-run with --apply to write the materialized tree)")


@app.command("recon")
def recon_cmd(
    target: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)],
    json_out: Annotated[bool, typer.Option("--json")] = False,
    progress: Annotated[bool | None, typer.Option(
        "--progress/--no-progress",
        help="Emit per-file scout progress to stderr. Default: auto "
             "(on when stderr is a TTY, off in CI / pipes / --json).")] = None,
) -> None:
    """Walk a repo, classify every public symbol, surface tier/effect distributions."""
    reporter = make_stderr_reporter(
        enabled=False if json_out else progress, label="scout")
    report = run_recon(target, progress=reporter)
    if json_out:
        typer.echo(json.dumps(report, indent=2, default=str))
        return
    typer.echo(f"\nRecon: {target}")
    typer.echo("-" * 60)
    typer.echo(f"  python files:     {report['python_file_count']}")
    typer.echo(f"  javascript files: {report.get('javascript_file_count', 0)}")
    typer.echo(f"  typescript files: {report.get('typescript_file_count', 0)}")
    primary = report.get("primary_language")
    if primary:
        typer.echo(f"  primary language: {primary}")
    typer.echo(f"  symbols:          {report['symbol_count']}")
    typer.echo(f"  tier dist:        {report['tier_distribution']}")
    typer.echo(f"  effect dist:      {report['effect_distribution']}")
    if report["recommendations"]:
        typer.echo("  recommendations:")
        for r in report["recommendations"]:
            typer.echo(f"    - {r}")


@app.command("cherry")
def cherry_cmd(
    target: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)],
    pick: Annotated[list[str] | None, typer.Option("--pick",
        help="Explicit qualnames. Pass --pick all to take everything.")] = None,
    only_tier: Annotated[str | None, typer.Option("--only-tier",
        help="Restrict to one tier guess.")] = None,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Build a cherry-pick manifest from the latest scout report."""
    pick_all = pick == ["all"]
    names = None if (pick_all or not pick) else pick
    manifest = run_cherry(target, names=names, pick_all=pick_all,
                           only_tier=only_tier)
    if json_out:
        typer.echo(json.dumps(manifest, indent=2, default=str))
        return
    typer.echo("\nCherry-pick manifest written to .atomadic-forge/cherry.json")
    typer.echo(f"  selected: {len(manifest['items'])}")


@app.command("finalize")
def finalize_cmd(
    target: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)],
    output: Annotated[Path, typer.Argument(
        file_okay=False, dir_okay=True, resolve_path=True)],
    package: Annotated[str, typer.Option("--package")] = "absorbed",
    apply: Annotated[bool, typer.Option("--apply")] = False,
    on_conflict: Annotated[str, typer.Option("--on-conflict")] = "rename",
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Assimilate cherry-picked symbols + run wire + certify."""
    output.mkdir(parents=True, exist_ok=True)
    report = run_finalize(target=target, output=output, package=package,
                           apply=apply, on_conflict=on_conflict)
    if json_out:
        typer.echo(json.dumps(report, indent=2, default=str))
        return
    typer.echo(f"\nFinalize ({'APPLY' if apply else 'DRY-RUN'}): {output}/{package}")
    typer.echo(f"  components: {report['components_emitted']}")
    typer.echo(f"  tier dist:  {report['tier_distribution']}")
    typer.echo(f"  wire:       {report['wire'].get('verdict')}")
    typer.echo(f"  certify:    {report['certify'].get('score', 0)}/100")


@app.command("wire")
def wire_cmd(
    source: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True,
        help="Tier-organized package root.")],
    json_out: Annotated[bool, typer.Option("--json")] = False,
    fail_on_violations: Annotated[bool, typer.Option(
        "--fail-on-violations",
        help="Exit 1 when any upward-import violations are found "
             "(for use in CI gates).")] = False,
    suggest_repairs: Annotated[bool, typer.Option(
        "--suggest-repairs",
        help="For every violation, propose a concrete mechanical fix "
             "(target tier, sketch shell command). Heuristic, for review "
             "before applying.")] = False,
    summary: Annotated[bool, typer.Option(
        "--summary",
        help="Emit ONLY the compact agent-native blocker summary (top "
             "5 actionable items + next-command) instead of the full "
             "violation list. Pairs with --json for machine consumers.")] = False,
) -> None:
    """Scan a tier tree for upward-import violations."""
    report = scan_violations(source, suggest_repairs=suggest_repairs)
    has_violations = report["violation_count"] > 0
    if summary:
        s = summarize_blockers(wire_report=report, package_root=str(source))
        if json_out:
            typer.echo(json.dumps(s, indent=2, default=str))
        else:
            typer.echo(render_summary_text(s))
        if fail_on_violations and has_violations:
            raise typer.Exit(code=1)
        return
    if json_out:
        typer.echo(json.dumps(report, indent=2, default=str))
        if fail_on_violations and has_violations:
            raise typer.Exit(code=1)
        return
    typer.echo(f"\nWire scan: {source}")
    typer.echo(f"  verdict:    {report['verdict']}")
    typer.echo(f"  violations: {report['violation_count']}")
    if suggest_repairs:
        typer.echo(f"  auto-fixable: {report['auto_fixable']}/{report['violation_count']}")
    for v in report["violations"][:10]:
        fcode = v.get("f_code", "")
        prefix = f"[{fcode}] " if fcode else ""
        line = (f"    - {prefix}{v['file']}: "
                f"{v['from_tier']} ⟵ {v['to_tier']}.{v['imported']}")
        typer.echo(line)
        if suggest_repairs and v.get("proposed_destination"):
            typer.echo(f"        → move to {v['proposed_destination']}/  "
                       f"({v.get('proposed_action', 'review_manually')})")
    if suggest_repairs and report.get("repair_suggestions"):
        typer.echo("\n  Repair plan (one entry per file):")
        for s in report["repair_suggestions"][:10]:
            dest = s.get("proposed_destination") or "(review manually)"
            typer.echo(
                f"    - {s['file']}: {s['violation_count']} violation(s) "
                f"→ {dest}"
            )
    if fail_on_violations and has_violations:
        typer.echo(f"  gate:       FAIL (--fail-on-violations set)")
        raise typer.Exit(code=1)
    if has_violations and not suggest_repairs and not json_out:
        typer.echo(
            "\n"
            + format_hint("wire_fail_with_violations",
                          count=report["violation_count"], path=source),
            err=True,
        )


@app.command("plan")
def plan_cmd(
    target: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True,
        help="Repo to inspect. The agent operates on it in-place "
             "(mode='improve', default) — Forge does NOT mutate.")],
    goal: Annotated[str, typer.Option("--goal",
        help="One-line description of what the agent is trying to achieve. "
             "Echoed back in the plan envelope.")] = "improve repo conformance",
    mode: Annotated[str, typer.Option("--mode",
        help="improve = operate in-place; absorb = scaffold a new "
             "tier-organized package from a flat repo.")] = "improve",
    package: Annotated[str | None, typer.Option("--package",
        help="Forwarded to forge certify when relevant.")] = None,
    top_n: Annotated[int, typer.Option("--top",
        help="Cap the action card list at N (action_count remains "
             "the full count).")] = 7,
    json_out: Annotated[bool, typer.Option("--json")] = False,
    save: Annotated[bool, typer.Option(
        "--save",
        help="Persist the plan under .atomadic-forge/plans/<id>.json "
             "so it can be addressed by `forge plan-step` / "
             "`forge plan-apply`.")] = False,
) -> None:
    """Codex-driven 'next best action card' generator (agent_plan/v1).

    Runs scout + wire + certify (and the optional emergent / synergy
    overlays when scans are present), ranks blockers and opportunities,
    and emits one ordered ``agent_plan/v1`` document. Each action card
    carries:

      id, kind, title, why, write_scope, risk, applyable,
      commands, related_fcodes, next_command, sample_path,
      score_delta_estimate

    The active agent inspects the cards, picks one (typically the
    first applyable), and runs its ``next_command``. Forge does NOT
    mutate the repo from this verb — the bounded write-step is
    delegated to verbs the cards reference (forge enforce, forge
    auto, forge synergy implement, forge emergent synthesize, etc.).
    """
    plan = run_auto_plan(target=target, goal=goal, mode=mode,
                          package=package, top_n=top_n)
    plan_id = None
    if save:
        plan_id = PlanStore(target).save_plan(plan)
        plan["id"] = plan_id  # so JSON / human output reflect the id
    if json_out:
        typer.echo(json.dumps(plan, indent=2, default=str))
        return
    typer.echo(f"\nForge plan ({plan['mode']}): {target}")
    typer.echo("-" * 60)
    typer.echo(f"  goal:          {plan['goal']}")
    typer.echo(f"  verdict:       {plan['verdict']}")
    typer.echo(f"  actions:       {plan['action_count']} "
                f"({plan['applyable_count']} applyable)")
    typer.echo("")
    for i, card in enumerate(plan["top_actions"], 1):
        tag = "AUTO" if card.get("applyable") else "REVIEW"
        risk = card.get("risk", "?")
        typer.echo(f"  {i}. [{tag}] [{risk}] [{card.get('kind', '?')}]"
                    f"  {card.get('title', '')}")
        typer.echo(f"     id:   {card.get('id', '')}")
        why = card.get("why", "").strip()
        if why:
            typer.echo(f"     why:  {why[:120]}")
        nc = card.get("next_command", "").strip()
        if nc:
            typer.echo(f"     next: {nc[:120]}")
        typer.echo("")
    typer.echo(f"  NEXT: {plan.get('next_command', '').strip()[:120]}")
    if plan_id:
        typer.echo(f"  saved: plan_id={plan_id}")
        typer.echo(f"        forge plan-show {plan_id} --project {target}")


@app.command("context-pack")
def context_pack_cmd(
    target: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True,
        help="Project root.")] = Path("."),
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Codex 'Copilot's Copilot' #1: first-call context bundle.

    Returns repo purpose + tier law + tier map + blockers + best
    next action + test commands + release gate + risky files +
    recent lineage in one read. The single tool every coding agent
    should call on first connect.
    """
    target = Path(target).resolve()
    try:
        scout = harvest_repo(target)
    except (OSError, ValueError):
        scout = None
    try:
        wire = scan_violations(target)
    except (OSError, ValueError):
        wire = None
    try:
        cert = certify_checks(target, project=target.name)
    except (OSError, RuntimeError, ValueError):
        cert = None
    pack = emit_context_pack(
        project_root=target,
        scout_report=scout, wire_report=wire, certify_report=cert,
    )
    if json_out:
        typer.echo(json.dumps(pack, indent=2, default=str))
        return
    typer.echo(f"\nForge context-pack: {target}")
    typer.echo("-" * 60)
    typer.echo(f"  purpose:   {pack['repo_purpose'][:200]}")
    typer.echo(f"  language:  {pack['primary_language']}")
    typer.echo(f"  tiers:     {pack['tier_map']}")
    bs = pack["blockers_summary"]
    typer.echo(f"  verdict:   {bs.get('verdict', '?')}  "
                f"({bs.get('blocker_count', 0)} blocker(s))")
    if pack.get("best_next_action"):
        n = pack["best_next_action"]
        typer.echo(f"  best next: {n.get('title', n.get('id', '?'))}")
        nc = n.get("next_command", "").strip()
        if nc:
            typer.echo(f"             {nc[:140]}")
    typer.echo(f"  tests:     {' | '.join(pack['test_commands'][:3])}")
    typer.echo(f"  gate:      {' && '.join(pack['release_gate'])}")
    if pack["risky_files"]:
        typer.echo("  risky files (most-edited):")
        for f in pack["risky_files"][:5]:
            typer.echo(f"    - {f['path']}  ({f['edit_count']}x)")


@app.command("preflight")
def preflight_cmd(
    intent: Annotated[str, typer.Argument(
        help="One-line description of what the agent intends to do.")],
    files: Annotated[list[str], typer.Argument(
        help="Proposed file paths the agent plans to write/modify.")],
    project: Annotated[Path, typer.Option(
        "--project",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)] = Path("."),
    scope_threshold: Annotated[int, typer.Option(
        "--scope-threshold",
        help="Warn when more than N files are in the write scope.")] = 8,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Codex 'Copilot's Copilot' #2: pre-edit guardrail.

    For each proposed file, returns the detected tier, forbidden
    imports, likely-affected tests, and sibling files to read first.
    Surfaces 'write_scope too broad' before the agent commits to a
    fragile multi-file patch.
    """
    report = preflight_change(
        intent=intent, proposed_files=list(files),
        project_root=project, scope_threshold=scope_threshold,
    )
    if json_out:
        typer.echo(json.dumps(report, indent=2, default=str))
        if report["write_scope_too_broad"]:
            raise typer.Exit(code=1)
        return
    typer.echo(f"\nForge preflight ({len(files)} file(s))")
    typer.echo("-" * 60)
    typer.echo(f"  intent: {intent[:200]}")
    if report["write_scope_too_broad"]:
        typer.echo(f"  ⚠ write_scope: {report['write_scope_size']} files "
                    f"(> {report['write_scope_threshold']} threshold)")
    for f in report["proposed_files"]:
        tier = f.get("detected_tier") or "(none)"
        typer.echo(f"\n  {f['path']}  [{tier}]")
        if f.get("forbidden_imports"):
            typer.echo(f"    forbidden: {f['forbidden_imports']}")
        if f.get("likely_tests"):
            typer.echo(f"    tests:     {f['likely_tests'][:3]}")
        if f.get("siblings_to_read"):
            typer.echo(f"    siblings:  {f['siblings_to_read'][:3]}")
        for note in f.get("notes", []):
            typer.echo(f"    note: {note}")
    for note in report.get("overall_notes", []):
        typer.echo(f"\n  ! {note}")
    if report["write_scope_too_broad"]:
        raise typer.Exit(code=1)


sidecar_app = typer.Typer(
    no_args_is_help=True,
    help=".forge sidecar tools: parse + validate the per-symbol "
         "effect / compose_with / proves contract (Lane D W8 / W11).",
)


@sidecar_app.command("parse")
def sidecar_parse_cmd(
    sidecar_file: Annotated[Path, typer.Argument(
        exists=True, file_okay=True, dir_okay=False, resolve_path=True)],
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Parse a .forge sidecar YAML file."""
    rep = parse_sidecar_file(sidecar_file)
    if json_out:
        typer.echo(json.dumps(rep, indent=2, default=str))
        if rep["errors"]:
            raise typer.Exit(code=1)
        return
    if rep["errors"]:
        typer.echo(f"\nSidecar parse FAILED: {sidecar_file}")
        for e in rep["errors"]:
            typer.echo(f"  ! {e}")
        raise typer.Exit(code=1)
    sc = rep["sidecar"]
    typer.echo(f"\nSidecar OK: {sc['target']}  "
                f"({len(sc['symbols'])} symbol(s))")
    for w in rep.get("warnings", []):
        typer.echo(f"  ⚠ {w}")
    for s in sc["symbols"]:
        typer.echo(f"  - {s.get('name')}  effect={s.get('effect')}  "
                    f"tier={s.get('tier', '?')}")


@sidecar_app.command("validate")
def sidecar_validate_cmd(
    source_file: Annotated[Path, typer.Argument(
        exists=True, file_okay=True, dir_okay=False, resolve_path=True,
        help="Source file to validate against (e.g. src/pkg/auth.py).")],
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Cross-check a .forge sidecar against its source AST.

    Looks for ``<source>.forge`` next to the source file. Reports
    drift across S0000–S0007 finding classes; exits 1 on FAIL.
    """
    sidecar_path = find_sidecar_for(source_file)
    parse = parse_sidecar_file(sidecar_path)
    if parse["errors"]:
        typer.echo(f"\nCould not parse sidecar at {sidecar_path}:")
        for e in parse["errors"]:
            typer.echo(f"  ! {e}")
        raise typer.Exit(code=1)
    try:
        source_text = source_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise typer.BadParameter(f"could not read {source_file}: {exc}")
    rep = validate_sidecar(
        parse["sidecar"], source_text=source_text, source_path=source_file,
    )
    if json_out:
        typer.echo(json.dumps(rep, indent=2, default=str))
        if rep["verdict"] == "FAIL":
            raise typer.Exit(code=1)
        return
    typer.echo(f"\nSidecar validate: {source_file}")
    typer.echo(f"  verdict:  {rep['verdict']}")
    typer.echo(f"  findings: {rep['finding_count']}")
    for f in rep["findings"]:
        sev = f.get("severity", "?").upper()
        typer.echo(f"  - [{f.get('code')}] [{sev:<5}] "
                    f"{f.get('symbol', '?')}: {f.get('message', '')}")
    if rep["verdict"] == "FAIL":
        raise typer.Exit(code=1)


app.add_typer(sidecar_app, name="sidecar",
               help="Parse / validate .forge sidecar files.")


@app.command("recipes")
def recipes_cmd(
    name: Annotated[str | None, typer.Argument(
        help="Recipe name to show; omit to list all.")] = None,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Codex #12: golden-path recipes catalogue.

    With no argument, lists every recipe. With a name, shows that
    recipe's checklist + file_scope_hints + validation_gate. Same
    surface as the MCP tools list_recipes / get_recipe.
    """
    if name is None:
        names = list_recipes()
        catalogue = all_recipes()
        if json_out:
            typer.echo(json.dumps(
                {"schema_version": "atomadic-forge.recipe.list/v1",
                 "recipes": names,
                 "catalogue": {n: r["description"] for n, r in catalogue.items()}},
                indent=2, default=str))
            return
        typer.echo("\nForge — golden-path recipes")
        typer.echo("-" * 60)
        for n in names:
            typer.echo(f"  {n:<22}  {catalogue[n]['description'][:60]}")
        typer.echo(f"\n  forge recipes <name>  — show one recipe")
        return
    recipe = get_recipe(name)
    if recipe is None:
        raise typer.BadParameter(
            f"unknown recipe: {name!r}. "
            f"Available: {', '.join(list_recipes())}"
        )
    if json_out:
        typer.echo(json.dumps(recipe, indent=2, default=str))
        return
    typer.echo(f"\nForge recipe: {recipe['name']}")
    typer.echo("-" * 60)
    typer.echo(f"  {recipe['description']}\n")
    typer.echo("  Checklist:")
    for i, step in enumerate(recipe.get("checklist", []), 1):
        typer.echo(f"    {i}. {step}")
    if recipe.get("file_scope_hints"):
        typer.echo("\n  File scope:")
        for f in recipe["file_scope_hints"]:
            typer.echo(f"    - {f}")
    if recipe.get("validation_gate"):
        typer.echo("\n  Validation gate:")
        for cmd in recipe["validation_gate"]:
            typer.echo(f"    $ {cmd}")
    if recipe.get("notes"):
        typer.echo("\n  Notes:")
        for n in recipe["notes"]:
            typer.echo(f"    {n}")


@app.command("plan-list")
def plan_list_cmd(
    project: Annotated[Path, typer.Option(
        "--project",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True,
        help="Project root the plans are stored under.")] = Path("."),
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """List saved agent_plan/v1 documents for ``--project``."""
    plans = PlanStore(project).list_plans()
    if json_out:
        typer.echo(json.dumps(
            {"schema_version": "atomadic-forge.plan.list/v1",
             "project": str(project),
             "plans": plans}, indent=2, default=str))
        return
    if not plans:
        typer.echo(f"\nNo saved plans under {project}/.atomadic-forge/plans/")
        typer.echo("Run `forge plan <target> --save` to persist one.")
        return
    typer.echo(f"\nForge — saved plans under {project}/.atomadic-forge/plans/")
    typer.echo("-" * 60)
    for p in plans:
        typer.echo(f"  {p['plan_id']}  {p['verdict']:<6}  "
                    f"actions={p['action_count']}  "
                    f"applyable={p['applyable_count']}  "
                    f"saved={p['saved_at_utc']}")
        typer.echo(f"    goal: {p['goal'][:80]}")


@app.command("plan-show")
def plan_show_cmd(
    plan_id: Annotated[str, typer.Argument(help="Plan id from plan-list.")],
    project: Annotated[Path, typer.Option(
        "--project",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)] = Path("."),
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Pretty-print a saved agent_plan/v1 by id."""
    store = PlanStore(project)
    plan = store.load_plan(plan_id)
    if plan is None:
        raise typer.BadParameter(
            f"plan id {plan_id!r} not found under "
            f"{project}/.atomadic-forge/plans/"
        )
    state = store.load_state(plan_id) or {}
    if json_out:
        typer.echo(json.dumps({"plan": plan, "state": state},
                                indent=2, default=str))
        return
    typer.echo(f"\nForge plan {plan_id}  ({plan.get('verdict', '?')})")
    typer.echo("-" * 60)
    typer.echo(f"  goal:    {plan.get('goal', '')}")
    typer.echo(f"  mode:    {plan.get('mode', '')}")
    typer.echo(f"  actions: {plan.get('action_count', 0)} "
                f"({plan.get('applyable_count', 0)} applyable)")
    for i, card in enumerate(plan.get("top_actions", []), 1):
        cid = card.get("id", "?")
        status = store.card_status(plan_id, cid)
        tag = "AUTO" if card.get("applyable") else "REVIEW"
        typer.echo(f"  {i}. [{tag}] [{status}] {card.get('title', '')}")
        typer.echo(f"     id: {cid}")


@app.command("plan-step")
def plan_step_cmd(
    plan_id: Annotated[str, typer.Argument(help="Plan id from plan-list.")],
    card_id: Annotated[str, typer.Argument(help="Card id from plan-show.")],
    project: Annotated[Path, typer.Option(
        "--project",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)] = Path("."),
    apply: Annotated[bool, typer.Option(
        "--apply",
        help="Actually execute the card. Default is dry-run.")] = False,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Apply ONE card from a saved plan (Codex's bounded-step verb)."""
    store = PlanStore(project)
    plan = store.load_plan(plan_id)
    if plan is None:
        raise typer.BadParameter(f"plan id {plan_id!r} not found")
    result = apply_card(project, plan, card_id, apply=apply)
    if json_out:
        typer.echo(json.dumps(result, indent=2, default=str))
        if result["status"] in {"failed", "rolled_back"}:
            raise typer.Exit(code=1)
        return
    typer.echo(f"\nForge plan-step ({'APPLY' if apply else 'DRY-RUN'}) "
                f"{plan_id}/{card_id}")
    typer.echo(f"  status: {result['status']}")
    detail = result.get("detail") or {}
    for key, value in detail.items():
        if isinstance(value, (dict, list)):
            value = json.dumps(value, default=str)[:120]
        typer.echo(f"  {key}: {value}")
    if result["status"] in {"failed", "rolled_back"}:
        raise typer.Exit(code=1)


@app.command("plan-apply")
def plan_apply_cmd(
    plan_id: Annotated[str, typer.Argument(help="Plan id from plan-list.")],
    project: Annotated[Path, typer.Option(
        "--project",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)] = Path("."),
    apply: Annotated[bool, typer.Option(
        "--apply",
        help="Actually execute every applyable card. Default is dry-run.")] = False,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Apply ALL applyable cards from a saved plan in order.

    Halts on the first ``rolled_back`` or ``failed`` outcome so the
    agent inspects before cascading further mutations.
    """
    store = PlanStore(project)
    plan = store.load_plan(plan_id)
    if plan is None:
        raise typer.BadParameter(f"plan id {plan_id!r} not found")
    result = apply_all_applyable(project, plan, apply=apply)
    if json_out:
        typer.echo(json.dumps(result, indent=2, default=str))
        if result.get("halted_on") in {"failed", "rolled_back"}:
            raise typer.Exit(code=1)
        return
    typer.echo(f"\nForge plan-apply ({'APPLY' if apply else 'DRY-RUN'}) "
                f"{plan_id}")
    typer.echo("-" * 60)
    typer.echo(f"  applied: {result['applied_count']}  "
                f"skipped: {result['skipped_count']}  "
                f"halted_on: {result.get('halted_on') or '-'}")
    for r in result["results"]:
        typer.echo(f"  - [{r['status']:<12s}] {r['card_id']}")
    if result.get("halted_on") in {"failed", "rolled_back"}:
        raise typer.Exit(code=1)


@app.command("enforce")
def enforce_cmd(
    package_root: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True,
        help="Tier-organized package root.")],
    apply: Annotated[bool, typer.Option(
        "--apply",
        help="Actually execute file moves. Default is dry-run.")] = False,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Plan (and optionally apply) mechanical fixes for wire violations.

    Routes by F-code (Lane A W5); rolls back any fix that increases the
    violation count. Default mode is dry-run — pass --apply to execute.
    """
    report = run_enforce(package_root, apply=apply)
    if json_out:
        typer.echo(json.dumps(report, indent=2, default=str))
        if apply and report["post_violations"] > report["pre_violations"]:
            raise typer.Exit(code=1)
        return
    plan = report["plan"]
    typer.echo(f"\nForge enforce ({'APPLY' if apply else 'DRY-RUN'}): "
               f"{package_root}")
    typer.echo("-" * 60)
    typer.echo(f"  pre  violations: {report['pre_violations']}")
    typer.echo(f"  post violations: {report['post_violations']}")
    typer.echo(f"  actions:         {plan['action_count']} "
               f"({plan['auto_apply_count']} auto, "
               f"{plan['review_count']} review)")
    if plan["by_fcode"]:
        typer.echo(f"  by F-code:       {plan['by_fcode']}")
    if not apply and plan["action_count"] > 0:
        typer.echo("\n  Planned moves:")
        for action in plan["actions"][:10]:
            tag = "AUTO" if action.get("auto_apply") else "REVIEW"
            if action.get("dest"):
                typer.echo(
                    f"    [{tag}] [{action['f_code']}] "
                    f"{action['src']}  →  {action['dest']}"
                )
            else:
                typer.echo(
                    f"    [{tag}] [{action['f_code']}] "
                    f"{action['src']}  →  (manual review)"
                )
            for w in action.get("warnings", [])[:2]:
                typer.echo(f"        ! {w}")
        typer.echo("\n  (re-run with --apply to execute the AUTO actions)")
    if apply:
        typer.echo("\n  Apply results:")
        for entry in report["applied"]:
            a = entry["action"]
            typer.echo(f"    [{entry['status'].upper():12s}] "
                       f"[{a['f_code']}] {a['src']}")
        if report["rollbacks"]:
            typer.echo(f"\n  Rolled back: {len(report['rollbacks'])} action(s) "
                       "(violations rose; reverted)")
        if report["post_violations"] > report["pre_violations"]:
            raise typer.Exit(code=1)


@app.command("certify")
def certify_cmd(
    project_root: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)],
    package: Annotated[str | None, typer.Option("--package")] = None,
    fail_under: Annotated[float | None, typer.Option("--fail-under",
        help="Exit 1 when the certify score is below this threshold.")] = None,
    json_out: Annotated[bool, typer.Option("--json")] = False,
    emit_receipt: Annotated[Path | None, typer.Option(
        "--emit-receipt",
        help="Write a Forge Receipt v1 JSON to PATH "
             "(see docs/RECEIPT.md for the schema).")] = None,
    print_card: Annotated[bool, typer.Option(
        "--print-card",
        help="Print the receipt as a 60-wide box-drawing card to stdout. "
             "Powers the '62 -> 5' viral demo.")] = False,
    sign: Annotated[bool, typer.Option(
        "--sign",
        help="Send the receipt to AAAA-Nexus /v1/verify/forge-receipt "
             "for Sigstore + AAAA-Nexus signing before emitting / "
             "rendering. Soft-fails if the endpoint is unavailable; the "
             "unsigned receipt is still emitted with a notes entry.")] = False,
    local_sign: Annotated[bool, typer.Option(
        "--local-sign/--no-local-sign",
        help="Sign the receipt with a local Ed25519 key (Lane G W5). "
             "Soft-fails if the key is absent or cryptography not installed.")] = False,
    local_sign_key: Annotated[Path | None, typer.Option(
        "--local-sign-key",
        help="Path to the Ed25519 PEM private key used by --local-sign. "
             "Defaults to forge-signing.pem in the project root.")] = None,
    summary: Annotated[bool, typer.Option(
        "--summary",
        help="Emit ONLY the compact agent-native blocker summary (top "
             "5 actionable items + next-command) instead of the full "
             "certify report. Pairs with --json for machine consumers.")] = False,
) -> None:
    """Score documentation, tests, tier layout, import discipline."""
    if fail_under is not None and not 0 <= fail_under <= 100:
        raise typer.BadParameter(
            format_hint("fail_under_out_of_range", value=fail_under)
        )
    report = certify_checks(project_root, project=project_root.name,
                             package=package)
    failed_gate = fail_under is not None and float(report["score"]) < fail_under
    if summary:
        # Pair certify with a fresh wire scan so the summary covers
        # both axes (Codex feedback: agents want one compact answer).
        wire_for_summary = scan_violations(project_root)
        s = summarize_blockers(
            wire_report=wire_for_summary,
            certify_report=report,
            package_root=package or project_root.name,
        )
        if json_out:
            typer.echo(json.dumps(s, indent=2, default=str))
        else:
            typer.echo(render_summary_text(s))
        if failed_gate:
            raise typer.Exit(code=1)
        return
    if json_out:
        typer.echo(json.dumps(report, indent=2, default=str))
        if failed_gate:
            raise typer.Exit(code=1)
        return
    typer.echo(f"\nCertify: {project_root}")
    typer.echo(f"  score: {report['score']}/100")
    typer.echo(f"  docs:  {'PASS' if report['documentation_complete'] else 'FAIL'}")
    typer.echo(f"  tests: {'PASS' if report['tests_present'] else 'FAIL'}")
    typer.echo(f"  layout:{'PASS' if report['tier_layout_present'] else 'FAIL'}")
    typer.echo(f"  wire:  {'PASS' if report['no_upward_imports'] else 'FAIL'}")
    for issue in report["issues"]:
        typer.echo(f"    - {issue}")
    if emit_receipt is not None or print_card or sign or local_sign:
        # The Receipt needs a scout summary; if scout didn't already
        # run via forge auto, harvest a cheap one now (no symbol dump
        # written; we only need counts + tier_distribution).
        scout_for_receipt = harvest_repo(project_root)
        wire_for_receipt = scan_violations(project_root)
        receipt = build_receipt(
            certify_result=report,
            wire_report=wire_for_receipt,
            scout_report=scout_for_receipt,
            project_name=project_root.name,
            project_root=project_root,
            forge_version=__version__,
            package=package,
            certify_threshold=fail_under or 100.0,
        )
        # Lane A W4: append a local lineage-chain link before signing
        # so signatures.aaaa_nexus can carry the lineage_path the
        # Vanguard endpoint sees. Skip on --no-lineage (future flag).
        receipt = LineageChainStore(project_root).link_and_append(receipt)
        if sign:
            receipt = sign_receipt(receipt)
        if local_sign:
            key = local_sign_key or (project_root / "forge-signing.pem")
            receipt = sign_receipt_local(receipt, key_path=key)
        if emit_receipt is not None:
            emit_receipt.parent.mkdir(parents=True, exist_ok=True)
            emit_receipt.write_text(receipt_to_json(receipt), encoding="utf-8")
        if print_card:
            typer.echo("")
            typer.echo(render_receipt_card(receipt))
    if failed_gate:
        typer.echo(f"  gate:  FAIL (score below --fail-under {fail_under:g})")
        typer.echo(
            "\n"
            + format_hint("certify_below_threshold",
                          score=report["score"],
                          threshold=int(fail_under) if float(fail_under).is_integer() else fail_under,
                          path=project_root),
            err=True,
        )
        raise typer.Exit(code=1)


@app.command("sbom")
def sbom_cmd(
    project: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True,
        help="Project root (must contain pyproject.toml).")] = Path("."),
    out: Annotated[Path | None, typer.Option(
        "--out",
        help="Write the SBOM JSON to this path instead of stdout.")] = None,
    json_out: Annotated[bool, typer.Option(
        "--json", help="Pretty-print the SBOM JSON to stdout.")] = False,
) -> None:
    """Generate a CycloneDX 1.5 SBOM from pyproject.toml (Lane G G3)."""
    try:
        scout = harvest_repo(project)
    except Exception:  # noqa: BLE001
        scout = None
    sbom = emit_sbom(project_root=project, scout_report=scout)
    sbom_json = json.dumps(sbom, indent=2, default=str)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(sbom_json, encoding="utf-8")
        typer.echo(f"SBOM written to {out}")
    elif json_out:
        typer.echo(sbom_json)
    else:
        typer.echo(f"SBOM: {project.name}")
        typer.echo(f"  format:     CycloneDX {sbom.get('specVersion', '1.5')}")
        typer.echo(f"  components: {len(sbom.get('components', []))}")
        typer.echo(f"  schema:     {sbom.get('schema_version', '')}")
        typer.echo("  (use --json or --out to emit the full CycloneDX JSON)")


@app.command("diff")
def diff_cmd(
    left: Annotated[Path, typer.Argument(
        exists=True, file_okay=True, dir_okay=False, resolve_path=True,
        help="Left (baseline) Forge JSON manifest.")],
    right: Annotated[Path, typer.Argument(
        exists=True, file_okay=True, dir_okay=False, resolve_path=True,
        help="Right (candidate) Forge JSON manifest.")],
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Compare two Forge JSON manifests (scout/cherry/assimilate/wire/certify/synergy/emergent)."""
    def _load(p: Path) -> dict:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise typer.BadParameter(
                format_hint("not_a_forge_manifest", path=p)
                + f"\n\nUnderlying parse error: {exc}"
            ) from exc
        if not isinstance(data, dict) or not isinstance(
                data.get("schema_version"), str) or not data["schema_version"].startswith(
                "atomadic-forge."):
            raise typer.BadParameter(
                format_hint("not_a_forge_manifest", path=p)
            )
        return data

    left_doc = _load(left)
    right_doc = _load(right)
    diff = diff_manifests(left_doc, right_doc)

    if json_out:
        typer.echo(json.dumps(diff, indent=2, default=str))
        return

    typer.echo(f"\nForge diff: {left.name} → {right.name}")
    typer.echo("-" * 60)
    typer.echo(f"  left:        {diff['left_schema']}")
    typer.echo(f"  right:       {diff['right_schema']}")
    typer.echo(f"  compatible:  {diff['compatible']}")
    if diff["summary"]:
        typer.echo("  summary:")
        for k, v in diff["summary"].items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                typer.echo(f"    {k}: {v}")
            elif isinstance(v, dict):
                typer.echo(f"    {k}: {v}")
            elif isinstance(v, list):
                typer.echo(f"    {k}: {len(v)} item(s)")
    typer.echo(
        f"  +{len(diff['added'])} added / "
        f"-{len(diff['removed'])} removed / "
        f"~{len(diff['changed'])} changed"
    )


mcp_app = typer.Typer(no_args_is_help=True,
                       help="MCP server surface — speak Forge to coding agents.")


@mcp_app.command("serve")
def mcp_serve_cmd(
    project: Annotated[Path, typer.Option(
        "--project",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True,
        help="Project root the MCP tools will operate against. "
             "Defaults to the current working directory.")] = Path("."),
) -> None:
    """Run the MCP stdio JSON-RPC server (Cursor / Claude Code / Aider / Devin).

    Add to your client's MCP config:

        {
          "mcpServers": {
            "atomadic-forge": {
              "command": "forge",
              "args": ["mcp", "serve", "--project", "/path/to/your/repo"]
            }
          }
        }

    Tools exposed (21):
      recon                 — scout the repo + classify symbols
      wire                  — upward-import scan; --suggest-repairs
      certify               — 4-axis score; --emit-receipt / --print-card
      enforce               — F-coded mechanical fixes; rollback-safe
      audit_list            — .atomadic-forge lineage summaries
      auto_plan             — agent_plan/v1 ranked action cards
      auto_step             — apply ONE card from a saved plan
      auto_apply            — apply ALL applyable cards (halts on regression)
      context_pack          — Codex 'first call' orientation bundle
      preflight_change      — pre-edit guardrail (forbidden imports etc.)
      score_patch           — patch risk scorer (architecture/api/release)
      select_tests          — minimum + full-confidence test sets
      rollback_plan         — files to remove + caches to clean
      explain_repo          — humane operational orientation
      adapt_plan            — capability-aware card filtering
      compose_tools         — tool-use planner per goal keyword
      load_policy           — read [tool.forge.agent] from pyproject.toml
      why_did_this_change   — agent memory: lineage + plan-event lookup
      what_failed_last_time — agent memory: failed/rolled_back events
      list_recipes          — golden-path recipes catalogue
      get_recipe            — fetch one named recipe

    Resources exposed (5):
      forge://docs/receipt           — Receipt v1 schema docs
      forge://docs/formalization     — AAM + BEP theorem citations
      forge://lineage/chain          — local Vanguard lineage chain
      forge://schema/receipt         — verdict enum + version constants
      forge://summary/blockers       — one-call 'what's blocking?' summary
    """
    rc = mcp_serve_stdio(project_root=project)
    if rc != 0:
        raise typer.Exit(code=rc)


app.add_typer(mcp_app, name="mcp",
               help="MCP server surface — speak Forge to coding agents.")


lsp_app = typer.Typer(
    no_args_is_help=True,
    help="Forge LSP — diagnostics + hover for .forge sidecar files "
         "(VS Code / Neovim / Helix / IntelliJ).",
)


@lsp_app.command("serve")
def lsp_serve_cmd() -> None:
    """Run the forge-lsp stdio JSON-RPC server.

    Add to your editor's LSP config:

      VS Code (settings.json or extension):
        "files.associations": { "*.forge": "yaml" },
        // launch forge-lsp with: command='forge', args=['lsp', 'serve']

      Neovim (lspconfig):
        require'lspconfig'.forge_lsp.setup{
          cmd = {'forge', 'lsp', 'serve'},
          filetypes = {'forge'},
          root_dir = require'lspconfig'.util.find_git_ancestor,
        }

    Provides:
      * publishDiagnostics (S0001 / S0003 / etc., F0100-coded) on
        every didOpen / didChange / didSave
      * textDocument/hover — markdown summary of the symbol's
        effect, tier, compose_with, proves clauses
      * textDocument/definition — goto-source from
        `name: login` line in foo.py.forge → foo.py:login
    """
    rc = lsp_serve_stdio()
    if rc != 0:
        raise typer.Exit(code=rc)


app.add_typer(lsp_app, name="lsp",
               help="Forge LSP — diagnostics + hover for .forge sidecar files.")


@app.command("doctor")
def doctor_cmd(
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Environment diagnostic."""
    info = {
        "atomadic_forge_version": __version__,
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": sys.platform,
        "stdout_encoding": getattr(sys.stdout, "encoding", "?"),
    }
    if json_out:
        typer.echo(json.dumps(info, indent=2))
        return
    typer.echo("\nAtomadic Forge — doctor")
    for k, v in info.items():
        typer.echo(f"  {k:24s} {v}")


@app.command("cs1")
def cs1_cmd(
    project: Annotated[str, typer.Argument(help="Project root path.")] = ".",
    receipt: Annotated[Path | None, typer.Option("--receipt", help="Path to receipt.json.")] = None,
    out: Annotated[Path | None, typer.Option("--out", help="Output path for CS-1.md.")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="Emit CS-1 as JSON instead of Markdown.")] = False,
) -> None:
    """Generate a Conformity Statement CS-1 v1 (EU AI Act / SR 11-7 / FDA PCCP / CMMC-AI)."""
    from ..a1_at_functions.cs1_renderer import render_cs1, render_cs1_markdown

    project_path = Path(project).resolve()
    if receipt is None:
        receipt = project_path / ".atomadic-forge" / "receipt.json"
    if not receipt.exists():
        typer.secho(f"Receipt not found at {receipt}. Run 'forge auto' first.", fg="red", err=True)
        raise typer.Exit(code=1)
    try:
        receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        typer.secho(f"Failed to load receipt: {exc}", fg="red", err=True)
        raise typer.Exit(code=1)
    try:
        cs1 = render_cs1(receipt_data)
    except ValueError as exc:
        typer.secho(f"Receipt validation failed: {exc}", fg="red", err=True)
        raise typer.Exit(code=1)
    if json_out:
        typer.echo(json.dumps(cs1, indent=2, default=str))
        return
    md = render_cs1_markdown(cs1)
    if out is None:
        out = project_path / ".atomadic-forge" / "CS-1.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    typer.secho(f"\nForge CS-1 — Conformity Statement written to {out}", fg="green")


# Specialty sub-apps — registered lazily so any import error in one doesn't
# break the others.
def _register_specialty_apps() -> None:
    for module_path, name, help_text in (
        ("atomadic_forge.commands.demo", "demo",
         "One-shot launch-video verb: preset evolve + DEMO.md artifact."),
        ("atomadic_forge.commands.iterate", "iterate",
         "LLM ↔ Forge loop: intent → architecturally-coherent code."),
        ("atomadic_forge.commands.evolve", "evolve",
         "Recursive self-improvement: iterate N times, growing catalog."),
        ("atomadic_forge.commands.chat", "chat",
         "Chat with a Forge-aware AI copilot over optional repo context."),
        ("atomadic_forge.commands.emergent", "emergent",
         "Symbol-level composition discovery."),
        ("atomadic_forge.commands.synergy", "synergy",
         "Feature-pair detection + auto-implement adapters."),
        ("atomadic_forge.commands.commandsmith", "commandsmith",
         "Auto-register / document / smoke CLI commands."),
        ("atomadic_forge.commands.feature_then_emergent", "feature-then-emergent",
         "Run any feature → fan its output into emergent scan."),
        ("atomadic_forge.commands.config_cmd", "config",
         "Configure Atomadic Forge — show / set / test config + wizard."),
        ("atomadic_forge.commands.audit", "audit",
         "Surface .atomadic-forge lineage: list / show / log."),
        ("atomadic_forge.commands.emergent_then_synergy", "emergent-then-synergy",
         "Run emergent → pipe JSON artifact to synergy."),
        ("atomadic_forge.commands.synergy_then_emergent", "synergy-then-emergent",
         "Run synergy → pipe JSON artifact to emergent."),
        ("atomadic_forge.commands.evolve_then_iterate", "evolve-then-iterate",
         "Run evolve → pipe JSON artifact to iterate."),
    ):
        try:
            mod = __import__(module_path, fromlist=["app"])
            sub_app = getattr(mod, "app", None)
            if sub_app is not None:
                app.add_typer(sub_app, name=name, help=help_text)
        except Exception as exc:  # noqa: BLE001
            typer.secho(f"[forge] could not register {name}: {exc}",
                         fg="yellow", err=True)


_register_specialty_apps()


def main() -> None:
    """Console-script entry."""
    _force_utf8()
    app()


if __name__ == "__main__":
    main()
