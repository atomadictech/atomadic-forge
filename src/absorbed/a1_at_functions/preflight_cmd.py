"""``forge iterate`` — LLM ↔ Forge loop (the headline play).

Plug Forge's tier-law substrate in front of any LLM (Anthropic / OpenAI /
Ollama / a stub for offline runs) and produce architecturally-coherent
code from intent.  Forge enforces the 5-tier law every turn; the LLM only
ships when wire passes and certify clears the threshold.

Examples
--------
    # With Anthropic (set ANTHROPIC_API_KEY):
    forge iterate "discord bot that summarises uploaded PDFs" ./out

    # Pre-flight (no LLM call) — show the system + first prompt:
    forge iterate "..." ./out --no-apply

    # Local Ollama:
    FORGE_OLLAMA=1 FORGE_OLLAMA_MODEL=qwen2.5-coder:7b \\
        forge iterate "..." ./out

    # Stub mode (deterministic, for tests):
    forge iterate "..." ./out --provider stub
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
from atomadic_forge.a3_og_features.forge_loop import run_iterate

COMMAND_NAME = "iterate"
COMMAND_HELP = ("Architecturally-coherent code generation: LLM emits, "
                "Forge enforces, loop iterates until certify clears.")


app = typer.Typer(no_args_is_help=True, help=COMMAND_HELP)


def _resolve_provider(name: str) -> object:
    try:
        return resolve_provider(name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("run")
def run_cmd(
    intent: Annotated[str, typer.Argument(help="One-paragraph description "
        "of what to build.")],
    output: Annotated[Path, typer.Argument(
        file_okay=False, dir_okay=True, resolve_path=True)],
    package: Annotated[str, typer.Option("--package")] = "generated",
    seed_repo: Annotated[list[Path] | None, typer.Option("--seed",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True,
        help="Sibling repo(s) whose catalog is offered to the LLM as building blocks. Repeatable.")] = None,
    provider: Annotated[str, typer.Option("--provider",
        help=PROVIDER_HELP)] = "auto",
    max_iterations: Annotated[int, typer.Option("--max-iterations")] = 5,
    max_fix_rounds: Annotated[int, typer.Option(
        "--max-fix-rounds",
        help="Per-turn budget for compiler-feedback fix rounds (Lane A W3). "
             "When the just-emitted package fails import_smoke, the loop "
             "sends the LLM the error trace and asks for a minimal patch, "
             "up to N times before continuing to the next iterate turn. "
             "Default 0 = disabled.")] = 0,
    target_score: Annotated[float, typer.Option("--target-score")] = 75.0,
    apply: Annotated[bool, typer.Option("--apply/--no-apply")] = True,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Run the iterate loop."""
    output.mkdir(parents=True, exist_ok=True)
    llm = _resolve_provider(provider)
    try:
        report = run_iterate(
            intent,
            output=output,
            package=package,
            seed_repo=seed_repo,
            llm=llm,                       # type: ignore[arg-type]
            max_iterations=max_iterations,
            max_fix_rounds=max_fix_rounds,
            target_score=target_score,
            apply=apply,
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_out:
        typer.echo(json.dumps(report, indent=2, default=str))
        return
    typer.echo(f"\nForge iterate ({'APPLY' if apply else 'PRE-FLIGHT'})")
    typer.echo("-" * 60)
    typer.echo(f"  llm:           {report.get('llm')}")
    typer.echo(f"  package:       {report.get('package')}")
    if not apply:
        typer.echo("  output_root:   (none — pre-flight)")
        typer.echo(f"  first_prompt:  {len(report.get('first_prompt', ''))} chars")
        typer.echo(f"  system_prompt: {len(report.get('system_prompt', ''))} chars")
        return
    typer.echo(f"  output:        {report['output_root']}/src/{report['package']}")
    typer.echo(f"  iterations:    {report['iterations']}")
    typer.echo(f"  files written: {report['files_written_total']}")
    typer.echo(f"  converged:     {report['converged']}")
    final_wire = report.get('final_wire') or {}
    final_cert = report.get('final_certify') or {}
    typer.echo(f"  final wire:    {final_wire.get('verdict', '?')} "
                f"({final_wire.get('violation_count', 0)} violations)")
    typer.echo(f"  final score:   {final_cert.get('score', 0)}/100")
    if final_cert.get("issues"):
        for issue in final_cert["issues"]:
            typer.echo(f"    - {issue}")


@app.command("preflight")
def preflight_cmd(
    intent: Annotated[str, typer.Argument()],
    package: Annotated[str, typer.Option("--package")] = "generated",
    seed_repo: Annotated[Path | None, typer.Option("--seed",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)] = None,
) -> None:
    """Print the system prompt + first user prompt without calling any LLM."""
    from atomadic_forge.a1_at_functions.forge_feedback import (
        pack_initial_intent,
        system_prompt,
    )
    from atomadic_forge.a1_at_functions.scout_walk import harvest_repo

    seeds = harvest_repo(seed_repo)["symbols"] if seed_repo else None
    typer.echo("# === SYSTEM PROMPT ===\n")
    typer.echo(system_prompt())
    typer.echo("\n# === FIRST USER PROMPT ===\n")
    typer.echo(pack_initial_intent(intent, package=package,
                                     seed_catalog=seeds))
