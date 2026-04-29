"""Tier a0 — atomadic-forge.policy/v1 schema.

Codex #10: 'Let repos declare their own agent rules.'

  > [tool.forge.agent]
  > protected_files = ["pyproject.toml", "docs/PAPER_v2.md"]
  > release_gate = ["ruff", "pytest", "build", "forge certify"]
  > max_files_per_patch = 8
  > require_human_review_for = ["license", "security", "public_api"]

This module declares the v1 policy shape. The reader (a1) parses
pyproject.toml's [tool.forge.agent] section into this dict. The
preflight + patch_scorer modules consume it.

a0 invariant: imports limited to __future__ + typing.
"""
from __future__ import annotations

from typing import TypedDict


SCHEMA_VERSION_POLICY_V1 = "atomadic-forge.policy/v1"


# Default values when no policy is declared. Lenient — Forge does
# not block on the absence of a policy file.
DEFAULT_PROTECTED_FILES: tuple[str, ...] = ()
DEFAULT_RELEASE_GATE: tuple[str, ...] = (
    "python -m ruff check .",
    "python -m pytest",
    "forge wire src --fail-on-violations",
    "forge certify . --fail-under 75",
)
DEFAULT_MAX_FILES_PER_PATCH: int = 8
DEFAULT_REQUIRE_HUMAN_REVIEW_FOR: tuple[str, ...] = (
    "license", "security", "public_api",
)


class AgentPolicy(TypedDict, total=False):
    """v1 policy shape — every field optional; reader fills defaults."""
    schema_version: str
    protected_files: list[str]
    release_gate: list[str]
    max_files_per_patch: int
    require_human_review_for: list[str]
    # Forward-compat: future versions may add fields. Consumers MUST
    # tolerate unknown keys.
    extra: dict[str, object]
