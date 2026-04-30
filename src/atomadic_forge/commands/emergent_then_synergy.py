"""
Auto-synthesized synergy adapter (syn-e3622070).

Producer:  emergent
Consumer:  synergy
Kind:      json_artifact
Score:     42

Why this synergy was detected:
  - emergent emits json-out
  - synergy accepts json_out

Re-emit with ``atomadic-forge synergy implement <id>`` after surfaces change.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated

import typer

COMMAND_NAME = 'emergent-then-synergy'
COMMAND_HELP = 'Run emergent to emit a JSON artifact, then feed it to synergy for the next phase.'

app = typer.Typer(no_args_is_help=False, help='Run emergent to emit a JSON artifact, then feed it to synergy for the next phase.')

@app.callback(invoke_without_command=True)
def run(
    ctx: typer.Context,
    producer_args: Annotated[list[str] | None, typer.Argument(
        help='Args forwarded to the producer command.')] = None,
) -> None:
    """Run emergent → capture artifact → feed to synergy."""
    if ctx.invoked_subcommand is not None:
        return
    producer_args = producer_args or []
    with tempfile.TemporaryDirectory(prefix='synergy-') as tmp:
        artifact = Path(tmp) / 'producer.json'
        cmd_a = [sys.executable, '-m',
                 'atomadic_forge.a4_sy_orchestration.cli',
                 'emergent', *producer_args,
                 '--json-out', str(artifact)]
        rc = subprocess.run(cmd_a, capture_output=False).returncode
        if rc != 0:
            typer.secho(f'producer exited {rc}', fg='red', err=True)
            raise typer.Exit(rc)
        cmd_b = [sys.executable, '-m',
                 'atomadic_forge.a4_sy_orchestration.cli',
                 'synergy', str(artifact)]
        rc = subprocess.run(cmd_b, capture_output=False).returncode
        if rc != 0:
            typer.secho(f'consumer exited {rc}', fg='red', err=True)
            raise typer.Exit(rc)
        try:
            data = json.loads(artifact.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            data = None
        typer.echo(json.dumps({
            'synergy': 'syn-e3622070',
            'producer': 'emergent',
            'consumer': 'synergy',
            'artifact_size_bytes': artifact.stat().st_size,
            'producer_payload_keys': sorted(data.keys()) if isinstance(data, dict) else None,
        }, indent=2))

