"""``forge demo`` — one-shot launch-video verb.

Run a preset evolve trajectory + post-run CLI invocation + DEMO.md artifact.
Designed to produce a recordable 90-second showcase from a single command.

    forge demo run                      # default preset (calc), auto provider
    forge demo run --preset kv          # KV-store preset
    forge demo run --preset slug --provider gemini
    forge demo list                     # show all presets
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
from atomadic_forge.a3_og_features.demo_runner import (
    list_presets, run_demo,
)


COMMAND_NAME = "demo"
COMMAND_HELP = "One-shot launch-video verb: preset evolve + DEMO.md artifact."


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
        return OllamaClient(
            model=os.environ.get("FORGE_OLLAMA_MODEL", "qwen2.5-coder:7b"),
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
    if name == "auto":
        return resolve_default_client()
    raise typer.BadParameter(f"unknown provider: {name!r}")


@app.command("list")
def list_cmd(
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """List available demo presets."""
    presets = list_presets()
    if json_out:
        typer.echo(json.dumps([
            {"name": p.name, "headline": p.headline, "package": p.package,
              "rounds": p.rounds, "iterations": p.iterations,
              "target_score": p.target_score}
            for p in presets
        ], indent=2))
        return
    typer.echo("\nForge demo presets:")
    for p in presets:
        typer.echo(f"  {p.name:8s} — {p.headline}")


@app.command("run")
def run_cmd(
    preset: Annotated[str, typer.Option("--preset", "-p",
        help="Preset name (use `forge demo list` to see options).")] = "calc",
    output: Annotated[Path | None, typer.Option("--output", "-o",
        help="Output directory.  Defaults to ./forge-demo-<preset>.",
        file_okay=False, dir_okay=True, resolve_path=True)] = None,
    provider: Annotated[str, typer.Option("--provider",
        help="auto | gemini | anthropic | openai | ollama | stub")] = "auto",
    rounds: Annotated[int | None, typer.Option("--rounds",
        help="Override the preset's round count.")] = None,
    iterations: Annotated[int | None, typer.Option("--iterations",
        help="Override the preset's iterations-per-round.")] = None,
    skip_cli_demo: Annotated[bool, typer.Option("--skip-cli-demo")] = False,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Run the preset and produce a DEMO.md artifact."""
    llm = _resolve_provider(provider)
    result = run_demo(
        preset_name=preset,
        output=output,
        llm=llm,                      # type: ignore[arg-type]
        rounds=rounds,
        iterations=iterations,
        skip_cli_demo=skip_cli_demo,
    )
    if json_out:
        from dataclasses import asdict
        typer.echo(json.dumps(asdict(result), indent=2, default=str))
        return

    arc = " → ".join(f"{s:.0f}" for s in result.score_trajectory)
    # Showcase presets bypass the LLM entirely — print "static showcase"
    # in the LLM slot so output stays consistent across both kinds.
    from atomadic_forge.a3_og_features.demo_runner import get_preset
    try:
        preset_obj = get_preset(preset)
    except KeyError:
        preset_obj = None
    is_showcase = preset_obj is not None and preset_obj.kind == "showcase"
    llm_label = "static showcase (no LLM)" if is_showcase else llm.name

    typer.echo("")
    typer.echo("=" * 60)
    typer.echo(f"  forge demo: {preset}")
    typer.echo("=" * 60)
    typer.echo("")
    typer.echo(f"  {result.headline}")
    typer.echo("")
    typer.echo(f"  llm:          {llm_label}")
    typer.echo(f"  package:      {result.package}")
    typer.echo(f"  rounds:       {result.rounds_completed}")
    typer.echo(f"  trajectory:   {arc}")
    typer.echo(f"  final score:  {result.final_score:.0f}/100")
    typer.echo(f"  converged:    {result.converged}")
    typer.echo(f"  duration:     {result.duration_s:.1f}s")
    typer.echo("")
    if result.cli_demo_command:
        typer.echo("  Generated CLI:")
        typer.echo(f"    $ {' '.join(result.cli_demo_command)}")
        for line in (result.cli_demo_stdout or "(no output)").splitlines()[:6]:
            typer.echo(f"    {line}")
        typer.echo("")
    typer.echo(f"  Artifact:     {result.artifact_md_path}")
    typer.echo(f"  Output:       {result.output_root}")
    typer.echo("")
