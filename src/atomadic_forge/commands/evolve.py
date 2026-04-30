"""``forge evolve`` — recursive self-improvement: iterate that iterates.

Each round, the package generated last time becomes the seed catalog for
the next round.  The LLM sees its own prior output as building blocks via
emergent + reuse feedback.  The catalog grows; compositions multiply; the
LLM (in principle) gets richer context every round.

This is **narrow self-improvement** — same shape as AlphaEvolve / Voyager.
NOT a path to AGI.  Bounded by underlying LLM quality and the realism of
the certify/wire signals.  Honest about what it is.

Examples
--------
    forge evolve "discord bot that summarises PDFs" ./out --auto 5

    # Sit-back mode: 8 rounds, 4 LLM turns per round, max score 90:
    forge evolve "..." ./out --auto 8 --target-score 90

    # Stop early if score regresses:
    forge evolve "..." ./out --auto 5 --stop-on-regression

    # Resume from an existing growing seed:
    forge evolve "..." ./out --auto 3 --seed ./out/src/evolved
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import click
import typer

from atomadic_forge.a1_at_functions.provider_resolver import (
    PROVIDER_HELP,
    resolve_provider,
)
from atomadic_forge.a3_og_features.forge_evolve import run_evolve

COMMAND_NAME = "evolve"
COMMAND_HELP = ("Recursive self-improvement: run iterate N times, each "
                "round seeded by the previous round's growing catalog.")


app = typer.Typer(no_args_is_help=True, help=COMMAND_HELP)


def _resolve_provider(name: str) -> object:
    try:
        return resolve_provider(name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("run")
def run_cmd(
    intent: Annotated[str, typer.Argument(help="One-paragraph description.")],
    output: Annotated[Path, typer.Argument(
        file_okay=False, dir_okay=True, resolve_path=True)],
    auto: Annotated[int, typer.Option("--auto",
        help="Number of evolve rounds — sit-back parameter.")] = 3,
    iterations_per_round: Annotated[int, typer.Option("--iterations")] = 4,
    target_score: Annotated[float, typer.Option("--target-score")] = 75.0,
    package: Annotated[str, typer.Option("--package")] = "evolved",
    seed_repo: Annotated[Path | None, typer.Option("--seed",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)] = None,
    provider: Annotated[str, typer.Option("--provider",
        help=PROVIDER_HELP)] = "auto",
    language: Annotated[str, typer.Option("--language", "-l",
        help="Output language: python | javascript | typescript")] = "python",
    stop_on_regression: Annotated[bool, typer.Option("--stop-on-regression")] = False,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Run the recursive evolve loop and watch the show."""
    output.mkdir(parents=True, exist_ok=True)
    llm = _resolve_provider(provider)
    try:
        report = run_evolve(
            intent,
            output=output,
            package=package,
            seed_repo=seed_repo,
            llm=llm,                       # type: ignore[arg-type]
            rounds=auto,
            iterations_per_round=iterations_per_round,
            target_score=target_score,
            stop_on_regression=stop_on_regression,
            language=language,
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_out:
        typer.echo(json.dumps(report, indent=2, default=str))
        return

    # Output path varies by language: python uses src/, JS/TS uses pkg root directly.
    lang = report.get("language", "python")
    pkg_path = (f"src/{report['package']}" if lang == "python"
                else report["package"])
    typer.echo(f"\nForge evolve — {auto} round(s) requested, "
                f"{report['rounds_completed']} completed")
    typer.echo("-" * 60)
    typer.echo(f"  llm:      {report['llm']}")
    typer.echo(f"  package:  {report['package']}")
    typer.echo(f"  language: {lang}")
    typer.echo(f"  output:   {report['output_root']}/{pkg_path}")
    typer.echo("")
    typer.echo("  Round │ Iters │ Files │ Symbols (Δ)    │ Score (Δ)      │ Wire │ Conv")
    typer.echo("  ──────┼───────┼───────┼────────────────┼────────────────┼──────┼──────")
    for r in report["rounds"]:
        sym = f"{r['symbol_count']:3d} ({r['delta_symbols']:+d})"
        sco = f"{r['score']:.0f} ({r['delta_score']:+.1f})"
        wire = r["wire_verdict"][:4]
        conv = "Y" if r["converged"] else "n"
        typer.echo(f"   {r['round']:3d}  │  {r['iterations']:3d}  │ {r['files_written']:3d}   │ "
                    f"{sym:<14s} │ {sco:<14s} │ {wire:<4s} │  {conv}")
    typer.echo("")
    typer.echo(f"  final score:    {report['final_score']:.0f}/100")
    typer.echo(f"  final symbols:  {report['final_symbol_count']}")
    typer.echo(f"  trajectory:     {report['score_trajectory']}")
    typer.echo(f"  converged:      {report['converged']}")
