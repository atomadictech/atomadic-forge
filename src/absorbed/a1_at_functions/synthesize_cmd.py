"""``atomadic-forge emergent`` — discover and synthesise emergent feature candidates.

Once you've assimilated a sibling repo (or just grown the catalog), every
function and class in the tier folders is a *building block*.  This command
walks the catalog, finds typed compositions nobody wrote yet, scores them on
cross-domain / cross-tier / purity / novelty, and (optionally) materialises
the top candidate as a new ``a3_og_features/<name>_emergent.py`` for review.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from atomadic_forge.a3_og_features.emergent_feature import EmergentScan

COMMAND_NAME = "emergent"
COMMAND_HELP = "Synthesise new feature candidates from existing components."


app = typer.Typer(no_args_is_help=True, help=COMMAND_HELP)


def _resolve_src_root() -> Path:
    """Locate ``<repo>/src`` from this file's location."""
    here = Path(__file__).resolve()
    return here.parent.parent.parent  # commands/ -> atomadic_forge/ -> src/


@app.command("scan")
def scan_cmd(
    package: Annotated[str, typer.Option("--package",
        help="Importable package under src/ to scan.")] = "atomadic_forge",
    src_root: Annotated[Path, typer.Option("--src-root",
        help="Path to the src directory containing the package.",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)] = None,  # type: ignore[assignment]
    max_depth: Annotated[int, typer.Option("--max-depth",
        help="Max chain length.")] = 3,
    top_n: Annotated[int, typer.Option("--top-n",
        help="Return at most this many candidates.")] = 15,
    require_pure: Annotated[bool, typer.Option("--require-pure",
        help="Restrict to chains where every step is heuristically pure.")] = False,
    no_domain_jump: Annotated[bool, typer.Option("--no-domain-jump",
        help="Allow same-domain chains (default: require ≥2 distinct domains).")] = False,
    json_out: Annotated[bool, typer.Option("--json",
        help="Emit machine-readable JSON.")] = False,
    save: Annotated[Path | None, typer.Option("--save",
        help="Persist the report at this path.",
        file_okay=True, dir_okay=False, resolve_path=True)] = None,
) -> None:
    """Walk the catalog and report top-scoring composition candidates."""
    root = src_root or _resolve_src_root()
    scanner = EmergentScan(src_root=root, package=package)
    report = scanner.scan(
        max_depth=max_depth,
        top_n=top_n,
        require_pure=require_pure,
        domain_jump_required=not no_domain_jump,
    )
    if save:
        EmergentScan.save_report(report, save)

    if json_out:
        typer.echo(json.dumps(report, indent=2, default=str))
        return

    typer.echo(f"\nEmergent scan — {package}")
    typer.echo("-" * 60)
    typer.echo(f"  catalog size:       {report['catalog_size']}")
    typer.echo(f"  chains considered:  {report['chain_count_considered']}")
    typer.echo(f"  domains:            {len(report['domain_inventory'])}")
    typer.echo(f"  candidates:         {len(report['candidates'])}\n")

    for i, c in enumerate(report["candidates"], 1):
        typer.echo(f"  #{i:2d}  {c['candidate_id']}  score={c['score']:.0f}")
        typer.echo(f"        name:  {c['name']}")
        typer.echo(f"        tier:  {c['suggested_tier']}")
        typer.echo(f"        chain: {' → '.join(c['chain']['domains'])}")
        if c["novelty_signals"]:
            typer.echo(f"        why:   {'; '.join(c['novelty_signals'])}")
        typer.echo("")


@app.command("synthesize")
def synthesize_cmd(
    candidate_id: Annotated[str, typer.Argument(
        help="Candidate id from a prior `scan` (e.g. emrg-abc12345).")],
    report_path: Annotated[Path, typer.Argument(
        help="Saved report JSON from `scan --save …`.",
        exists=True, file_okay=True, dir_okay=False, resolve_path=True)],
    package: Annotated[str, typer.Option("--package")] = "atomadic_forge",
    src_root: Annotated[Path | None, typer.Option("--src-root",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)] = None,
    out_dir: Annotated[Path | None, typer.Option("--out-dir",
        help="Where to write the new feature file (defaults to a3_og_features/).",
        file_okay=False, dir_okay=True, resolve_path=True)] = None,
) -> None:
    """Materialize a candidate as a new a3 feature module."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    scanner = EmergentScan(src_root=src_root or _resolve_src_root(),
                           package=package)
    target = scanner.synthesize(candidate_id, report, out_dir=out_dir)
    typer.echo(f"Wrote {target}")
    typer.echo("Review carefully before committing — this is scaffolding,")
    typer.echo("not a finished feature.  Methods need their receiver wired.")


@app.command("show")
def show_cmd(
    candidate_id: Annotated[str, typer.Argument()],
    report_path: Annotated[Path, typer.Argument(
        exists=True, file_okay=True, dir_okay=False, resolve_path=True)],
) -> None:
    """Print one candidate's full chain + score breakdown."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    match = next((c for c in report["candidates"] if c["candidate_id"] == candidate_id),
                 None)
    if match is None:
        typer.secho(f"candidate {candidate_id} not in report", fg="red", err=True)
        raise typer.Exit(1)
    typer.echo(json.dumps(match, indent=2))
