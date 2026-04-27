"""``atomadic-forge synergy`` — find producer/consumer pairs that aren't wired yet,
optionally implement an adapter that wires them.

Operates one level above ``emergent``: emergent looks at *symbol* compositions
inside the type graph; synergy looks at *feature/CLI verb* relationships
across the operator surface (file artifacts, schemas, phase order).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from atomadic_forge.a3_og_features.synergy_feature import SynergyScan


COMMAND_NAME = "synergy"
COMMAND_HELP = ("Find feature/CLI synergies (producer-consumer pairs that "
                "aren't wired together) and optionally implement adapters.")


app = typer.Typer(no_args_is_help=True, help=COMMAND_HELP)


def _resolve_src_root() -> Path:
    here = Path(__file__).resolve()
    return here.parent.parent.parent  # commands/ -> atomadic_forge/ -> src/


@app.command("scan")
def scan_cmd(
    package: Annotated[str, typer.Option("--package")] = "atomadic_forge",
    src_root: Annotated[Path | None, typer.Option("--src-root",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)] = None,
    top_n: Annotated[int, typer.Option("--top-n")] = 20,
    json_out: Annotated[bool, typer.Option("--json")] = False,
    save: Annotated[Path | None, typer.Option("--save",
        file_okay=True, dir_okay=False, resolve_path=True)] = None,
) -> None:
    """Walk the CLI surface and report top-scoring synergy candidates."""
    root = src_root or _resolve_src_root()
    scanner = SynergyScan(src_root=root, package=package)
    report = scanner.scan(top_n=top_n)
    if save:
        SynergyScan.save_report(report, save)
    if json_out:
        typer.echo(json.dumps(report, indent=2, default=str))
        return

    typer.echo(f"\nSynergy scan — {package}")
    typer.echo("-" * 60)
    typer.echo(f"  features harvested: {report['feature_count']}")
    typer.echo(f"  candidates:         {report['candidate_count']}\n")
    for i, c in enumerate(report["candidates"], 1):
        typer.echo(f"  #{i:2d}  {c['candidate_id']}  score={c['score']:.0f}")
        typer.echo(f"        kind:     {c['kind']}")
        typer.echo(f"        wire:     {c['producer']}  →  {c['consumer']}")
        typer.echo(f"        adapter:  {c['proposed_adapter_name']}")
        typer.echo(f"        why:      {'; '.join(c['why'])}")
        typer.echo("")


@app.command("implement")
def implement_cmd(
    candidate_id: Annotated[str, typer.Argument()],
    report_path: Annotated[Path, typer.Argument(
        exists=True, file_okay=True, dir_okay=False, resolve_path=True)],
    package: Annotated[str, typer.Option("--package")] = "atomadic_forge",
    src_root: Annotated[Path | None, typer.Option("--src-root",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)] = None,
) -> None:
    """Materialize one candidate as a new commands/<name>.py adapter."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    scanner = SynergyScan(src_root=src_root or _resolve_src_root(),
                          package=package)
    target = scanner.implement(candidate_id, report)
    typer.echo(f"Wrote {target}")
    typer.echo("Run ``atomadic-forge commandsmith sync`` to register the new verb.")


@app.command("show")
def show_cmd(
    candidate_id: Annotated[str, typer.Argument()],
    report_path: Annotated[Path, typer.Argument(
        exists=True, file_okay=True, dir_okay=False, resolve_path=True)],
) -> None:
    """Print one candidate's full breakdown."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    match = next((c for c in report["candidates"]
                  if c["candidate_id"] == candidate_id), None)
    if match is None:
        typer.secho(f"candidate {candidate_id} not in report", fg="red", err=True)
        raise typer.Exit(1)
    typer.echo(json.dumps(match, indent=2))
