"""``atomadic-forge commandsmith`` — manage the auto-wired CLI command registry.

This is the operator-facing surface for the Commandsmith feature.  Every
ASS-ADE assimilation cycle ends by adding new symbols (classes, functions)
under ``atomadic_forge/``.  Commandsmith turns those symbols into invocable CLI
verbs without any hand-editing of ``unified_cli.py``.

Sub-commands:

* ``atomadic-forge commandsmith discover``     — list discoverable command modules.
* ``atomadic-forge commandsmith sync``         — regenerate registry + docs + manifest.
* ``atomadic-forge commandsmith wrap``         — generate a Typer wrapper around a class.
* ``atomadic-forge commandsmith smoke``        — run ``--help`` against every command.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from atomadic_forge.a3_og_features.commandsmith_feature import Commandsmith

app = typer.Typer(
    no_args_is_help=True,
    help="Auto-register, document, and smoke-test ASS-ADE CLI commands.",
)


def _resolve_package_root() -> Path:
    """Locate ``src/atomadic_forge`` from this file's location."""
    here = Path(__file__).resolve()
    return here.parent.parent  # commands/ -> atomadic_forge/


@app.command("discover")
def discover_cmd(
    json_out: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    """List discoverable command modules under ``atomadic_forge/commands/``."""
    cs = Commandsmith(package_root=_resolve_package_root())
    cards = cs.discover()
    if json_out:
        typer.echo(json.dumps(cards, indent=2))
        return
    typer.echo(f"Discovered {len(cards)} command module(s):")
    for c in cards:
        flag = " [hidden]" if c["hidden"] else ""
        typer.echo(f"  - {c['name']:24s} {c['surface']:14s} {c['module']}{flag}")


@app.command("sync")
def sync_cmd(
    smoke: Annotated[bool, typer.Option("--smoke",
        help="Also smoke-test every command's --help.")] = False,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Rebuild registry, per-command docs, and the manifest."""
    cs = Commandsmith(package_root=_resolve_package_root())
    manifest = cs.sync(smoke=smoke)
    if json_out:
        typer.echo(json.dumps(manifest, indent=2))
        return
    typer.echo(f"Wrote registry → {cs.commands_dir / '_registry.py'}")
    typer.echo(f"Wrote docs    → {cs.docs_root}")
    typer.echo(f"Manifest      → {cs.manifest_dir / 'commandsmith_manifest.json'}")
    typer.echo(f"Total verbs:    {len(manifest['commands'])}")
    if smoke:
        passed = sum(1 for v in manifest["smoke_results"].values() if v)
        typer.echo(f"Smoke:          {passed}/{len(manifest['smoke_results'])} passed")


@app.command("wrap")
def wrap_cmd(
    target_module: Annotated[str, typer.Argument(
        help="Importable module path of the class to wrap.")],
    target_class: Annotated[str, typer.Argument(
        help="Class name to wrap (must be importable).")],
    command_name: Annotated[str, typer.Option("--name", "-n",
        help="CLI verb to expose (kebab-case).")] = "",
    help_text: Annotated[str, typer.Option("--help-text",
        help="One-line help string for the generated subcommand group.")] = "",
    out_dir: Annotated[Path | None, typer.Option("--out-dir",
        help="Where to write the wrapper module (defaults to commands/).",
        file_okay=False, dir_okay=True, resolve_path=True)] = None,
) -> None:
    """Generate a Typer wrapper around an importable class."""
    cs = Commandsmith(package_root=_resolve_package_root())
    name = command_name or target_class.lower()
    name = "".join("-" + c.lower() if c.isupper() and i > 0 else c.lower()
                   for i, c in enumerate(target_class)).lstrip("-")
    name = command_name or name
    out = cs.wrap_class(
        target_module=target_module,
        target_class=target_class,
        command_name=name,
        help_text=help_text or f"Auto-wrapped {target_class}",
        out_dir=out_dir,
    )
    typer.echo(f"Wrote wrapper → {out}")
    typer.echo("Run ``atomadic-forge commandsmith sync`` to register it.")


_CORE_VERBS = [
    "init", "auto", "recon", "cherry", "finalize", "wire", "plan",
    "context-pack", "preflight", "recipes", "plan-list", "plan-show",
    "plan-step", "plan-apply", "enforce", "certify", "sbom", "diff",
    "doctor", "cs1", "sidecar", "mcp", "status",
]


@app.command("smoke")
def smoke_cmd(
    include_core: Annotated[bool, typer.Option(
        "--include-core/--no-core",
        help="Also smoke-test core verbs (init, wire, certify, etc.).")] = True,
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Run ``<verb> --help`` for every registered command and report."""
    import os
    import subprocess
    cs = Commandsmith(package_root=_resolve_package_root())
    cards = cs.discover()
    results = cs.smoke(cards)
    if include_core:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        cli = [sys.executable, "-m", "atomadic_forge.a4_sy_orchestration.cli"]
        for verb in _CORE_VERBS:
            if verb in results:
                continue
            try:
                rc = subprocess.run(
                    cli + [verb, "--help"],
                    capture_output=True, timeout=20, env=env,
                ).returncode
            except (subprocess.TimeoutExpired, FileNotFoundError):
                rc = 1
            results[verb] = rc == 0
    if json_out:
        typer.echo(json.dumps(results, indent=2))
        return
    pad = max((len(n) for n in results), default=0)
    for name, ok in sorted(results.items()):
        mark = "PASS" if ok else "FAIL"
        typer.echo(f"  {mark:5s} {name:<{pad}}")
    failed = [n for n, ok in results.items() if not ok]
    if failed:
        typer.echo(f"\n{len(failed)} verb(s) failed --help:", err=True)
        raise typer.Exit(1)


@app.command("repair-imports")
def repair_imports_cmd(
    package_root: Annotated[Path, typer.Argument(
        help="Path to <output>/src/<package>/ produced by atomadic-forge assimilate.",
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)],
    apply: Annotated[bool, typer.Option("--apply",
        help="Write changes (default: dry-run).")] = False,
) -> None:
    """Repair broken cross-symbol imports in an assimilated tier tree.

    The assimilator emits one file per symbol but does not always rewrite
    intra-package references (``from <flat-name> import X``).  This pass
    looks each name up in the tier-local sibling files and rewrites the
    import to a relative sibling reference.
    """
    from atomadic_forge.a1_at_functions.commandsmith_import_repair import (
        repair_assimilation_output,
    )
    diffs = repair_assimilation_output(package_root, dry_run=not apply)
    total = sum(len(v) for v in diffs.values())
    for tier, items in diffs.items():
        typer.echo(f"  {tier}: {len(items)} files {'rewritten' if apply else 'would change'}")
    typer.echo(f"TOTAL: {total} files {'rewritten' if apply else 'would change'} ({'applied' if apply else 'dry-run'})")
