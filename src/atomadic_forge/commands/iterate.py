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
import os
from pathlib import Path
from typing import Annotated

import typer

from atomadic_forge.a1_at_functions.llm_client import (
    AnthropicClient, GeminiClient, OllamaClient, OpenAIClient,
    StubLLMClient, resolve_default_client,
)
from atomadic_forge.a3_og_features.forge_loop import run_iterate


COMMAND_NAME = "iterate"
COMMAND_HELP = ("Architecturally-coherent code generation: LLM emits, "
                "Forge enforces, loop iterates until certify clears.")


app = typer.Typer(no_args_is_help=True, help=COMMAND_HELP)


def _resolve_provider(name: str) -> object:
    name = name.lower()
    if name == "stub":
        return StubLLMClient()
    if name in ("anthropic", "claude"):
        return AnthropicClient()
    if name in ("openai", "gpt"):
        return OpenAIClient()
    if name in ("gemini", "google"):
        return GeminiClient(model=os.environ.get("FORGE_GEMINI_MODEL",
                                                   "gemini-2.5-flash"))
    if name == "ollama":
        return OllamaClient()
    if name == "auto":
        return resolve_default_client()
    raise typer.BadParameter(f"unknown provider: {name!r}")


@app.command("run")
def run_cmd(
    intent: Annotated[str, typer.Argument(help="One-paragraph description "
        "of what to build.")],
    output: Annotated[Path, typer.Argument(
        file_okay=False, dir_okay=True, resolve_path=True)],
    package: Annotated[str, typer.Option("--package")] = "generated",
    seed_repo: Annotated[Path | None, typer.Option("--seed",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True,
        help="Sibling repo whose catalog is offered to the LLM as building blocks.")] = None,
    provider: Annotated[str, typer.Option("--provider",
        help="auto | gemini | anthropic | openai | ollama | stub")] = "auto",
    max_iterations: Annotated[int, typer.Option("--max-iterations")] = 5,
    target_score: Annotated[float, typer.Option("--target-score")] = 75.0,
    apply: Annotated[bool, typer.Option("--apply/--no-apply")] = True,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Run the iterate loop."""
    output.mkdir(parents=True, exist_ok=True)
    llm = _resolve_provider(provider)
    report = run_iterate(
        intent,
        output=output,
        package=package,
        seed_repo=seed_repo,
        llm=llm,                       # type: ignore[arg-type]
        max_iterations=max_iterations,
        target_score=target_score,
        apply=apply,
    )
    if json_out:
        typer.echo(json.dumps(report, indent=2, default=str))
        return
    typer.echo(f"\nForge iterate ({'APPLY' if apply else 'PRE-FLIGHT'})")
    typer.echo("-" * 60)
    typer.echo(f"  llm:           {report.get('llm')}")
    typer.echo(f"  package:       {report.get('package')}")
    if not apply:
        typer.echo(f"  output_root:   (none — pre-flight)")
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
        pack_initial_intent, system_prompt,
    )
    from atomadic_forge.a1_at_functions.scout_walk import harvest_repo

    seeds = harvest_repo(seed_repo)["symbols"] if seed_repo else None
    typer.echo("# === SYSTEM PROMPT ===\n")
    typer.echo(system_prompt())
    typer.echo("\n# === FIRST USER PROMPT ===\n")
    typer.echo(pack_initial_intent(intent, package=package,
                                     seed_catalog=seeds))
