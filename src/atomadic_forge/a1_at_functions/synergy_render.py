"""Tier a1 — pure source synthesiser for a Synergy adapter.

Given a :class:`SynergyCandidateCard`, render a tiny ``commands/<name>.py``
Typer module that wires producer to consumer.  Four templates cover the
detected synergy kinds:

* ``json_artifact``    — producer emits ``--json-out PATH`` then consumer
                         reads PATH as its first positional argument.
* ``in_memory_pipe``   — both modules importable; run the producer's main
                         in-process, capture its return, hand to consumer.
* ``phase_omission``   — producer + consumer in the natural phase order
                         with a clear ``# review: arg alignment`` marker
                         since signatures may not match.
* ``shared_schema``    — like ``json_artifact`` but the adapter validates
                         the JSON against the shared schema before piping.

The right template is picked from ``card["kind"]``.
"""

from __future__ import annotations

from ..a0_qk_constants.synergy_types import SynergyCandidateCard


def render_synergy_adapter(card: SynergyCandidateCard) -> str:
    """Dispatch to the right per-kind renderer."""
    renderers = {
        "json_artifact": _render_json_artifact,
        "in_memory_pipe": _render_in_memory_pipe,
        "phase_omission": _render_phase_omission,
        "shared_schema": _render_shared_schema,
        "shared_vocabulary": _render_phase_omission,  # treat like a soft chain
    }
    return renderers.get(card["kind"], _render_json_artifact)(card)


def _header_lines(card: SynergyCandidateCard) -> list[str]:
    name = card["proposed_adapter_name"]
    safe_help = card["proposed_summary"].replace('"""', "'''")
    lines = [
        '"""',
        f"Auto-synthesized synergy adapter ({card['candidate_id']}).",
        "",
        f"Producer:  {card['producer']}",
        f"Consumer:  {card['consumer']}",
        f"Kind:      {card['kind']}",
        f"Score:     {card['score']:.0f}",
        "",
        "Why this synergy was detected:",
    ]
    for w in card["why"]:
        lines.append(f"  - {w}")
    lines.extend([
        "",
        "Re-emit with ``atomadic-forge synergy implement <id>`` after surfaces change.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "import json",
        "import subprocess",
        "import sys",
        "import tempfile",
        "from pathlib import Path",
        "from typing import Annotated",
        "",
        "import typer",
        "",
        f"COMMAND_NAME = {name!r}",
        f"COMMAND_HELP = {safe_help!r}",
        "",
        f'app = typer.Typer(no_args_is_help=False, help={safe_help!r})',
        "",
    ])
    return lines


def _render_json_artifact(card: SynergyCandidateCard) -> str:
    body = _header_lines(card)
    body.extend([
        "@app.callback(invoke_without_command=True)",
        "def run(",
        "    ctx: typer.Context,",
        "    producer_args: Annotated[list[str] | None, typer.Argument(",
        "        help='Args forwarded to the producer command.')] = None,",
        ") -> None:",
        f'    """Run {card["producer"]} → capture artifact → feed to {card["consumer"]}."""',
        "    if ctx.invoked_subcommand is not None:",
        "        return",
        "    producer_args = producer_args or []",
        "    with tempfile.TemporaryDirectory(prefix='synergy-') as tmp:",
        "        artifact = Path(tmp) / 'producer.json'",
        "        cmd_a = [sys.executable, '-m',",
        "                 'atomadic_forge.a4_sy_orchestration.unified_cli',",
        f"                 {card['producer']!r}, *producer_args,",
        "                 '--json-out', str(artifact)]",
        "        rc = subprocess.run(cmd_a, capture_output=False).returncode",
        "        if rc != 0:",
        "            typer.secho(f'producer exited {rc}', fg='red', err=True)",
        "            raise typer.Exit(rc)",
        "        cmd_b = [sys.executable, '-m',",
        "                 'atomadic_forge.a4_sy_orchestration.unified_cli',",
        f"                 {card['consumer']!r}, str(artifact)]",
        "        rc = subprocess.run(cmd_b, capture_output=False).returncode",
        "        if rc != 0:",
        "            typer.secho(f'consumer exited {rc}', fg='red', err=True)",
        "            raise typer.Exit(rc)",
        "        try:",
        "            data = json.loads(artifact.read_text(encoding='utf-8'))",
        "        except (OSError, json.JSONDecodeError):",
        "            data = None",
        "        typer.echo(json.dumps({",
        f"            'synergy': {card['candidate_id']!r},",
        f"            'producer': {card['producer']!r},",
        f"            'consumer': {card['consumer']!r},",
        "            'artifact_size_bytes': artifact.stat().st_size,",
        "            'producer_payload_keys': sorted(data.keys()) if isinstance(data, dict) else None,",
        "        }, indent=2))",
        "",
    ])
    return "\n".join(body) + "\n"


def _render_in_memory_pipe(card: SynergyCandidateCard) -> str:
    """Run producer + consumer in-process; pass producer return to consumer.

    Falls back to subprocess JSON-piping if either side isn't importable.
    """
    body = _header_lines(card)
    body.extend([
        "@app.callback(invoke_without_command=True)",
        "def run(ctx: typer.Context) -> None:",
        f'    """Run {card["producer"]} in-process and pass its return to {card["consumer"]}."""',
        "    if ctx.invoked_subcommand is not None:",
        "        return",
        "    # NOTE: in-memory pipe assumes producer and consumer expose a",
        "    # callable named `run` (or `main`) at module level.  Manual wiring",
        "    # required if signatures don't align — see arg-alignment marker.",
        "    try:",
        f"        from atomadic_forge.commands import {card['producer']!s} as _producer  # type: ignore[import-not-found]",
        f"        from atomadic_forge.commands import {card['consumer']!s} as _consumer  # type: ignore[import-not-found]",
        "    except ImportError as exc:",
        "        typer.secho(f'in-memory pipe unavailable: {exc}', fg='yellow', err=True)",
        "        raise typer.Exit(2) from exc",
        "    producer_fn = getattr(_producer, 'run', None) or getattr(_producer, 'main', None)",
        "    consumer_fn = getattr(_consumer, 'run', None) or getattr(_consumer, 'main', None)",
        "    if producer_fn is None or consumer_fn is None:",
        "        typer.secho('producer or consumer has no `run`/`main` callable', fg='red', err=True)",
        "        raise typer.Exit(2)",
        "    intermediate = producer_fn()",
        "    # review: arg alignment — consumer may need shaping of `intermediate`",
        "    result = consumer_fn(intermediate)",
        "    typer.echo(json.dumps({",
        f"        'synergy': {card['candidate_id']!r},",
        "        'result': str(result)[:2000],",
        "    }, indent=2))",
        "",
    ])
    return "\n".join(body) + "\n"


def _render_phase_omission(card: SynergyCandidateCard) -> str:
    """Producer at phase N → consumer at phase N+1.  Both via subprocess.

    Args may not align — emits a clear ``# review:`` marker so the operator
    knows to inspect.  Default behaviour is to run producer with no args
    then prompt for consumer args.
    """
    body = _header_lines(card)
    body.extend([
        "@app.callback(invoke_without_command=True)",
        "def run(",
        "    ctx: typer.Context,",
        "    producer_args: Annotated[list[str] | None, typer.Argument(",
        "        help='Args for producer (everything before --consumer-args).')] = None,",
        "    consumer_args: Annotated[list[str] | None, typer.Option('--consumer-args',",
        "        help='Args forwarded to consumer (space-separated).')] = None,",
        ") -> None:",
        f'    """Phase chain: {card["producer"]} (phase) → {card["consumer"]} (next phase)."""',
        "    if ctx.invoked_subcommand is not None:",
        "        return",
        "    # review: arg alignment — phase_omission synergies are heuristic.",
        "    # The producer and consumer were inferred from phase order alone, so",
        "    # their CLI signatures are almost certainly different.  Pass args",
        "    # explicitly via positional + --consumer-args until you hand-shape",
        "    # this adapter.",
        "    producer_args = producer_args or []",
        "    consumer_args = (consumer_args or '').split() if isinstance(consumer_args, str) else (consumer_args or [])",
        "    cmd_a = [sys.executable, '-m', 'atomadic_forge.a4_sy_orchestration.unified_cli',",
        f"             {card['producer']!r}, *producer_args]",
        "    rc = subprocess.run(cmd_a, capture_output=False).returncode",
        "    if rc != 0:",
        "        typer.secho(f'producer exited {rc}', fg='red', err=True)",
        "        raise typer.Exit(rc)",
        "    cmd_b = [sys.executable, '-m', 'atomadic_forge.a4_sy_orchestration.unified_cli',",
        f"             {card['consumer']!r}, *consumer_args]",
        "    rc = subprocess.run(cmd_b, capture_output=False).returncode",
        "    if rc != 0:",
        "        typer.secho(f'consumer exited {rc}', fg='red', err=True)",
        "        raise typer.Exit(rc)",
        "    typer.echo(json.dumps({",
        f"        'synergy': {card['candidate_id']!r},",
        f"        'phase_chain': [{card['producer']!r}, {card['consumer']!r}],",
        "    }, indent=2))",
        "",
    ])
    return "\n".join(body) + "\n"


def _render_shared_schema(card: SynergyCandidateCard) -> str:
    """Like json_artifact but validates the producer JSON before piping."""
    body = _header_lines(card)
    body.extend([
        "@app.callback(invoke_without_command=True)",
        "def run(",
        "    ctx: typer.Context,",
        "    producer_args: Annotated[list[str] | None, typer.Argument(",
        "        help='Args forwarded to the producer command.')] = None,",
        ") -> None:",
        f'    """Run {card["producer"]} → validate shared schema → feed to {card["consumer"]}."""',
        "    if ctx.invoked_subcommand is not None:",
        "        return",
        "    producer_args = producer_args or []",
        "    with tempfile.TemporaryDirectory(prefix='synergy-') as tmp:",
        "        artifact = Path(tmp) / 'producer.json'",
        "        cmd_a = [sys.executable, '-m', 'atomadic_forge.a4_sy_orchestration.unified_cli',",
        f"                 {card['producer']!r}, *producer_args, '--json-out', str(artifact)]",
        "        rc = subprocess.run(cmd_a, capture_output=False).returncode",
        "        if rc != 0:",
        "            raise typer.Exit(rc)",
        "        try:",
        "            payload = json.loads(artifact.read_text(encoding='utf-8'))",
        "        except (OSError, json.JSONDecodeError) as exc:",
        "            typer.secho(f'producer JSON invalid: {exc}', fg='red', err=True)",
        "            raise typer.Exit(2) from exc",
        "        schema_id = payload.get('schema_version') or payload.get('schema')",
        "        if not schema_id:",
        "            typer.secho('producer payload missing schema_version field', fg='yellow', err=True)",
        "        cmd_b = [sys.executable, '-m', 'atomadic_forge.a4_sy_orchestration.unified_cli',",
        f"                 {card['consumer']!r}, str(artifact)]",
        "        rc = subprocess.run(cmd_b, capture_output=False).returncode",
        "        if rc != 0:",
        "            raise typer.Exit(rc)",
        "        typer.echo(json.dumps({",
        f"            'synergy': {card['candidate_id']!r},",
        "            'schema_id': schema_id,",
        f"            'producer': {card['producer']!r},",
        f"            'consumer': {card['consumer']!r},",
        "        }, indent=2))",
        "",
    ])
    return "\n".join(body) + "\n"
