"""``atomadic-forge feature-then-emergent`` — universal pipeline:
run any feature's JSON-emitting verb, then fan its payload into emergent scan.

This is the Item-1 synergy from the roadmap: every feature in the catalog
becomes a producer; emergent scan becomes the universal consumer.  The
adapter is generic (it doesn't bake in any single feature) so adding a new
feature later automatically participates without code changes.

Examples:
    atomadic-forge feature-then-emergent scout C:/path/to/repo --no-llm
    atomadic-forge feature-then-emergent commandsmith discover --json
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated

import typer

from atomadic_forge.a3_og_features.emergent_pipeline_integration import (
    emergent_overlay_for_path,
)


COMMAND_NAME = "feature-then-emergent"
COMMAND_HELP = ("Run any feature, then fan its JSON output into emergent "
                "scan to surface novel compositions.")


app = typer.Typer(no_args_is_help=False, help=COMMAND_HELP)


def _try_extract_repo_root(payload: dict) -> Path | None:
    """Try to find a repo path in the producer's JSON payload.

    We probe a few common keys (``repo``, ``src_root``, ``project_path``,
    ``primary_root``).  This makes the adapter useful even when the producer
    isn't scout-shaped.
    """
    for key in ("src_root", "primary_root", "repo", "project_path", "repo_root"):
        if key in payload and isinstance(payload[key], str):
            p = Path(payload[key])
            if p.exists():
                return p
    return None


@app.command("run",
             context_settings={"allow_extra_args": True,
                               "ignore_unknown_options": True})
def run(
    ctx: typer.Context,
    feature: Annotated[str, typer.Argument(
        help="ASS-ADE verb to run as the producer (e.g. scout, commandsmith).")],
    explicit_repo: Annotated[Path | None, typer.Option("--repo",
        help="Override repo root used for the emergent scan; otherwise inferred.",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)] = None,
    package: Annotated[str, typer.Option("--package")] = "atomadic_forge",
    top_n: Annotated[int, typer.Option("--top-n")] = 10,
) -> None:
    """Run ``atomadic-forge <feature> <args>``, then run emergent scan over its scope.

    Forwarded args go after ``--``.  Example::

        atomadic-forge feature-then-emergent run scout --top-n 3 -- C:/repo --no-llm
        # → producer args = ["C:/repo", "--no-llm"], adapter top_n = 3
    """
    feature_args = list(ctx.args)  # everything after the recognised options
    with tempfile.TemporaryDirectory(prefix="feature-emergent-") as tmp:
        artifact = Path(tmp) / "producer.json"
        cmd = [sys.executable, "-m",
               "atomadic_forge.a4_sy_orchestration.unified_cli",
               feature, *feature_args, "--json-out", str(artifact)]
        rc = subprocess.run(cmd, capture_output=False).returncode
        if rc != 0:
            typer.secho(f"producer `{feature}` exited {rc}", fg="red", err=True)
            raise typer.Exit(rc)

        try:
            payload = json.loads(artifact.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            typer.secho(f"producer JSON invalid: {exc}", fg="red", err=True)
            raise typer.Exit(2) from exc

        repo_root = explicit_repo or _try_extract_repo_root(payload)
        if repo_root is None:
            typer.secho(
                "could not infer a repo root from producer payload; "
                "pass --repo PATH to set it explicitly",
                fg="yellow", err=True,
            )
            raise typer.Exit(2)

        overlay = emergent_overlay_for_path(repo_root, phase="scout",
                                             package=package)
        # Only keep the top-N candidates the operator actually wants to see.
        overlay["candidates"] = overlay["candidates"][:top_n]

        typer.echo(json.dumps({
            "synergy": "feature_then_emergent",
            "feature": feature,
            "feature_args": feature_args,
            "producer_payload_keys": sorted(payload.keys()) if isinstance(payload, dict) else None,
            "emergent_repo_root": str(repo_root),
            "emergent_summary": overlay.get("summary_line"),
            "candidates": overlay["candidates"],
        }, indent=2, default=str))
