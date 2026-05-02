"""Tier a4 — `forge audit` verb: surface .atomadic-forge lineage.

Lane D1 of the post-audit plan. Closes the 'lineage exists but is
invisible' friction point: every --apply already writes to
.atomadic-forge/lineage.jsonl, but until now there was no verb to
query it short of `cat | jq`.

Subcommands:
  forge audit list <project> [--last N] [--json]
      Summary of distinct artifacts, run counts, and latest write times.

  forge audit show <project> <artifact> [--json]
      Pretty-print the named manifest (scout, cherry, wire, certify, …).

  forge audit log  <project> [--last N] [--json]
      Raw lineage entries (newest-last).

Future subcommands ('trend', 'replay') need lineage-shape extension
and are reserved for their own lane.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from ..a1_at_functions.error_hints import format_hint
from ..a1_at_functions.lineage_reader import (
    list_artifacts,
    load_manifest,
    read_lineage,
)

COMMAND_NAME = "audit"
COMMAND_HELP = (
    "Surface the .atomadic-forge lineage log: list runs, inspect "
    "saved manifests, replay history."
)

app = typer.Typer(no_args_is_help=True, help=COMMAND_HELP)


@app.command("list")
def list_cmd(
    project: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True,
        help="Project root containing .atomadic-forge/.")] = Path("."),
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Summarize each artifact: run count, latest write time, path."""
    entries = list_artifacts(project)
    if json_out:
        typer.echo(json.dumps(
            {"schema_version": "atomadic-forge.audit.list/v1",
             "project": str(project),
             "artifact_count": len(entries),
             "artifacts": entries},
            indent=2, default=str))
        return
    if not entries:
        typer.echo(f"\nNo lineage found at {project}/.atomadic-forge/lineage.jsonl")
        typer.echo("\nLineage is recorded automatically when you run any verb")
        typer.echo("with --apply (forge auto, forge cherry, forge finalize).")
        return
    typer.echo(f"\nForge audit — artifacts under {project}/.atomadic-forge/")
    typer.echo("-" * 60)
    for e in entries:
        typer.echo(
            f"  {e['artifact']:<20} runs={e['run_count']:<3} "
            f"latest={e['latest_ts_utc']}  ({e['path']})"
        )
    typer.echo(f"\n  {len(entries)} distinct artifact(s).")


@app.command("show")
def show_cmd(
    project: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)],
    artifact: Annotated[str, typer.Argument(
        help="Manifest name: scout | cherry | assimilate | wire | certify | "
             "auto | (custom).")],
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Pretty-print the JSON manifest for ``artifact``."""
    data = load_manifest(project, artifact)
    if data is None:
        raise typer.BadParameter(
            format_hint("not_a_forge_manifest",
                        path=project / ".atomadic-forge" / f"{artifact}.json")
        )
    if json_out:
        typer.echo(json.dumps(data, indent=2, default=str))
        return
    schema = data.get("schema_version", "(unknown)")
    typer.echo(f"\nForge audit — {artifact} ({schema})")
    typer.echo("-" * 60)
    # Compact summary lines: top-level keys with non-collection values,
    # plus collection sizes. Verbose dump available via --json.
    for key, value in data.items():
        if isinstance(value, dict):
            typer.echo(f"  {key}: <dict, {len(value)} keys>")
        elif isinstance(value, list):
            typer.echo(f"  {key}: <list, {len(value)} items>")
        else:
            typer.echo(f"  {key}: {value}")
    typer.echo("\n  (re-run with --json for full payload)")


@app.command("log")
def log_cmd(
    project: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)] = Path("."),
    last: Annotated[int, typer.Option("--last",
        help="Show only the most recent N entries.")] = 20,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Show raw lineage entries (newest-last)."""
    entries = read_lineage(project, last=last)
    if json_out:
        typer.echo(json.dumps(
            {"schema_version": "atomadic-forge.audit.log/v1",
             "project": str(project),
             "entry_count": len(entries),
             "entries": entries},
            indent=2, default=str))
        return
    if not entries:
        typer.echo(f"\nNo lineage entries at {project}/.atomadic-forge/lineage.jsonl")
        return
    typer.echo(f"\nForge audit — last {len(entries)} lineage entries")
    typer.echo("-" * 60)
    for e in entries:
        typer.echo(f"  {e.get('ts_utc', '?')}  "
                   f"{e.get('artifact', '?'):<20}  "
                   f"{e.get('path', '?')}")


def register(parent: typer.Typer) -> None:
    """Hook used by the unified CLI to mount this sub-app."""
    parent.add_typer(app, name=COMMAND_NAME, help=COMMAND_HELP)
