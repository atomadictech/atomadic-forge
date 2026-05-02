"""Tier a0 — types for the Commandsmith CLI command-management phase.

Commandsmith discovers Python modules that expose CLI commands (existing
or freshly assimilated) and emits:

  1. A registry manifest (JSON) describing every known command.
  2. An auto-wired Python registry module that registers all commands on a
     Typer app (replacing the hand-maintained ``register_commands`` shim).
  3. Per-command Markdown docs and an INDEX.

These TypedDicts are the wire format for that pipeline.  No logic here —
only data shapes.
"""

from __future__ import annotations

from typing import Literal, TypedDict

CommandSurface = Literal["typer_app", "register_fn", "wrapped_class"]


class CommandSignatureCard(TypedDict):
    """One sub-command's parameter signature as a small dict-of-strings."""

    name: str
    parameters: list[str]   # e.g. ["repo: Path", "--tier (a0|a1|...): str"]
    return_type: str        # e.g. "ReconReport"
    docstring: str


class RegisteredCommandCard(TypedDict):
    """Static description of one CLI command discovered by Commandsmith."""

    name: str                       # CLI verb (e.g. "cherry-pick")
    module: str                     # Python module path
    surface: CommandSurface         # how the module exposes commands
    help_text: str                  # one-line description
    hidden: bool
    sub_commands: list[CommandSignatureCard]
    source_root: str                # which root contributed it ("atomadic_forge_seed", "atomadic_v2", ...)


class RegistryManifestCard(TypedDict):
    """Persistent registry of every command Commandsmith has wired."""

    schema_version: str            # "atomadic-forge.commandsmith.registry/v1"
    generated_at_utc: str
    commands: list[RegisteredCommandCard]
    smoke_results: dict[str, bool]  # cmd-name -> --help exit 0?
