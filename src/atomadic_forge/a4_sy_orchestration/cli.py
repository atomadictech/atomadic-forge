"""Atomadic Forge — unified CLI.

Public verbs:
    forge init        — interactive setup wizard (configure LLM, defaults)
    forge auto        — flagship: scout + cherry + assimilate + wire + certify
    forge recon       — scout walk only (writes scout.json)
    forge cherry      — cherry-pick from latest scout (writes cherry.json)
    forge finalize    — assimilate + wire + certify (consumes cherry.json)
    forge wire        — upward-import scanner over a tier-organized package
    forge certify     — score documentation/tests/layout/imports
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
from pathlib import Path
from typing import Annotated

import typer

from .. import __version__
from ..a3_og_features.forge_pipeline import (
    run_auto, run_cherry, run_finalize, run_recon,
)
from ..a1_at_functions.wire_check import scan_violations
from ..a1_at_functions.certify_checks import certify as certify_checks


def _force_utf8() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


app = typer.Typer(no_args_is_help=True,
                  help="Atomadic Forge — absorb · enforce · emerge.")


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
) -> None:
    """Flagship: scout → cherry-pick → assimilate → wire → certify in one shot."""
    output.mkdir(parents=True, exist_ok=True)
    report = run_auto(target=target, output=output, package=package,
                      apply=apply, on_conflict=on_conflict)
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
) -> None:
    """Walk a repo, classify every public symbol, surface tier/effect distributions."""
    report = run_recon(target)
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
    typer.echo(f"\nCherry-pick manifest written to .atomadic-forge/cherry.json")
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
) -> None:
    """Scan a tier tree for upward-import violations."""
    report = scan_violations(source)
    if json_out:
        typer.echo(json.dumps(report, indent=2, default=str))
        return
    typer.echo(f"\nWire scan: {source}")
    typer.echo(f"  verdict:    {report['verdict']}")
    typer.echo(f"  violations: {report['violation_count']}")
    for v in report["violations"][:10]:
        typer.echo(f"    - {v['file']}: {v['from_tier']} ⟵ {v['to_tier']}.{v['imported']}")


@app.command("certify")
def certify_cmd(
    project_root: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)],
    package: Annotated[str | None, typer.Option("--package")] = None,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Score documentation, tests, tier layout, import discipline."""
    report = certify_checks(project_root, project=project_root.name,
                             package=package)
    if json_out:
        typer.echo(json.dumps(report, indent=2, default=str))
        return
    typer.echo(f"\nCertify: {project_root}")
    typer.echo(f"  score: {report['score']}/100")
    typer.echo(f"  docs:  {'PASS' if report['documentation_complete'] else 'FAIL'}")
    typer.echo(f"  tests: {'PASS' if report['tests_present'] else 'FAIL'}")
    typer.echo(f"  layout:{'PASS' if report['tier_layout_present'] else 'FAIL'}")
    typer.echo(f"  wire:  {'PASS' if report['no_upward_imports'] else 'FAIL'}")
    for issue in report["issues"]:
        typer.echo(f"    - {issue}")


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
