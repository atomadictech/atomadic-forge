"""Tier a4 — config management CLI commands (show, set, test, wizard)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from atomadic_forge.a0_qk_constants.config_defaults import (
    CONFIG_FILE_NAME,
    GLOBAL_CONFIG_DIR,
    LOCAL_CONFIG_DIR,
)
from atomadic_forge.a1_at_functions.config_io import (
    load_config,
    read_config_file,
    save_config,
    validate_config,
)
from atomadic_forge.a1_at_functions.provider_detect import test_provider

COMMAND_NAME = "config"
COMMAND_HELP = "Configure Atomadic Forge — setup wizard + config management."

app = typer.Typer(no_args_is_help=True, help=COMMAND_HELP)

_CWD = Path(".")


@app.command("wizard")
def wizard_cmd(
    project_dir: Annotated[
        Path,
        typer.Option("--project", file_okay=False, dir_okay=True, resolve_path=True,
                     help="Project directory (default: cwd)."),
    ] = _CWD,
) -> None:
    """Interactive setup wizard — configure LLM, defaults, and workspace."""
    from atomadic_forge.a3_og_features.setup_wizard import run_wizard
    run_wizard(project_dir.resolve())


@app.command("show")
def show_cmd(
    project_dir: Annotated[
        Path,
        typer.Option("--project", file_okay=False, dir_okay=True, resolve_path=True,
                     help="Project directory (default: cwd)."),
    ] = _CWD,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Print the current merged config (local → global → defaults)."""
    config = load_config(project_dir.resolve())
    issues = validate_config(config)

    if json_out:
        typer.echo(json.dumps({"config": config, "issues": issues}, indent=2))
        return

    typer.echo("\nAtomadic Forge — config")
    typer.echo("-" * 44)
    for k, v in config.items():
        if "key" in k and v:
            s = str(v)
            display = s[:8] + "..." + s[-4:] if len(s) > 12 else "***"
        else:
            display = str(v) if v is not None else "(not set)"
        typer.echo(f"  {k:28s} {display}")

    if issues:
        typer.echo("\nValidation issues:")
        for issue in issues:
            typer.secho(f"  - {issue}", fg="yellow")
    else:
        typer.secho("\n  Config is valid.", fg="green")


@app.command("set")
def set_cmd(
    key: Annotated[str, typer.Argument(help="Config key to set.")],
    value: Annotated[str, typer.Argument(help="Value to assign.")],
    project_dir: Annotated[
        Path,
        typer.Option("--project", file_okay=False, dir_okay=True, resolve_path=True,
                     help="Project directory (default: cwd)."),
    ] = _CWD,
    global_: Annotated[
        bool,
        typer.Option("--global", help="Write to global config (~/.atomadic-forge/config.json)."),
    ] = False,
) -> None:
    """Set a single config key in the local (or --global) config file."""
    if global_:
        config_path = Path(GLOBAL_CONFIG_DIR).expanduser() / CONFIG_FILE_NAME
    else:
        config_path = project_dir.resolve() / LOCAL_CONFIG_DIR / CONFIG_FILE_NAME

    current = read_config_file(config_path)

    # Coerce obvious types so booleans and numbers round-trip cleanly.
    coerced: object = value
    if value.lower() in ("true", "false"):
        coerced = value.lower() == "true"
    else:
        try:
            coerced = float(value) if "." in value else int(value)
        except ValueError:
            pass

    current[key] = coerced
    save_config(current, config_path)
    typer.echo(f"  Set {key!r} = {coerced!r}  →  {config_path}")


@app.command("test")
def test_cmd(
    project_dir: Annotated[
        Path,
        typer.Option("--project", file_okay=False, dir_okay=True, resolve_path=True,
                     help="Project directory (default: cwd)."),
    ] = _CWD,
    provider: Annotated[
        str | None,
        typer.Option("--provider", help="Override provider to test."),
    ] = None,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Test the configured LLM provider connection."""
    config = load_config(project_dir.resolve())
    p = provider or config.get("provider", "auto")
    result = test_provider(p, config)

    if json_out:
        typer.echo(json.dumps(result, indent=2))
        return

    color = "green" if result["ok"] else "red"
    typer.secho(f"\nProvider test — {p}", bold=True)
    typer.secho(f"  Status:    {'OK' if result['ok'] else 'FAIL'}", fg=color)
    typer.echo(f"  Model:     {result['model']}")
    typer.echo(f"  Latency:   {result['latency_ms']}ms")
    if result["error"]:
        typer.secho(f"  Error:     {result['error']}", fg="yellow")
