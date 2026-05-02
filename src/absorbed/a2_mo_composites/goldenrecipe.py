"""Tier a1 — golden-path recipes (Codex #12).

Codex's prescription:

  > For common agent tasks: recipe_release_hardening,
  > recipe_add_cli_command, recipe_fix_wire_violation,
  > recipe_add_feature, recipe_publish_mcp. Each returns a
  > checklist, file scope, and validation gate. Agents love rails.

Pure: a recipe is a static dict. ``get_recipe(name)`` returns it,
``list_recipes()`` returns the catalogue.
"""
from __future__ import annotations

from typing import TypedDict

SCHEMA_VERSION_RECIPE_V1 = "atomadic-forge.recipe/v1"


class GoldenRecipe(TypedDict, total=False):
    schema_version: str
    name: str
    description: str
    checklist: list[str]
    file_scope_hints: list[str]
    validation_gate: list[str]
    notes: list[str]


_RECIPES: dict[str, GoldenRecipe] = {
    "release_hardening": GoldenRecipe(
        schema_version=SCHEMA_VERSION_RECIPE_V1,
        name="release_hardening",
        description=(
            "Add CI + CHANGELOG entry + version bump + signed Receipt "
            "before tagging a release."
        ),
        checklist=[
            "Add or update .github/workflows/ci.yml",
            "Append a CHANGELOG.md entry under the new version",
            "Bump version in pyproject.toml (or package.json)",
            "Run forge certify . --emit-receipt --sign",
            "Run forge wire src --fail-on-violations",
            "Tag the commit with the new version",
        ],
        file_scope_hints=[
            ".github/workflows/ci.yml",
            "CHANGELOG.md",
            "pyproject.toml",
        ],
        validation_gate=[
            "python -m ruff check .",
            "python -m pytest",
            "forge wire src --fail-on-violations",
            "forge certify . --fail-under 90",
        ],
        notes=[
            "Lane G1 ships --fail-under and --fail-on-violations natively; "
            "use them instead of python -c JSON-parse fallbacks.",
        ],
    ),
    "add_cli_command": GoldenRecipe(
        schema_version=SCHEMA_VERSION_RECIPE_V1,
        name="add_cli_command",
        description=(
            "Add a new top-level Forge verb (or sibling-tool verb) "
            "with tier-clean wiring."
        ),
        checklist=[
            "Decide whether the logic is pure (a1), stateful (a2), or "
            "feature-orchestrating (a3); CLI wrapper goes in a4.",
            "Implement the pure helper in the right tier.",
            "Add the @app.command(...) handler in cli.py with --json "
            "and (where applicable) --fail-on flags.",
            "Add a smoke test in tests/test_cli_smoke.py + a unit test "
            "for the pure helper.",
            "Run forge wire src --fail-on-violations to confirm tier "
            "discipline; bump CHANGELOG.",
        ],
        file_scope_hints=[
            "src/atomadic_forge/aN_*/<your_module>.py",
            "src/atomadic_forge/a4_sy_orchestration/cli.py",
            "tests/test_cli_smoke.py",
            "CHANGELOG.md",
        ],
        validation_gate=[
            "python -m pytest tests/test_cli_smoke.py",
            "forge wire src/atomadic_forge --fail-on-violations",
        ],
    ),
    "fix_wire_violation": GoldenRecipe(
        schema_version=SCHEMA_VERSION_RECIPE_V1,
        name="fix_wire_violation",
        description=(
            "Resolve a tier upward-import violation surfaced by "
            "forge wire (F0040–F0049)."
        ),
        checklist=[
            "Run forge wire <pkg> --suggest-repairs to read the "
            "F-code + suggested move.",
            "Decide: move the file UP to the higher tier (default), "
            "or invert the import direction by extracting the symbol "
            "DOWN to a lower tier.",
            "Run forge enforce <pkg> --apply for F0041..F0046 "
            "(rollback-safe orchestrator).",
            "Re-run forge wire to confirm zero violations.",
            "Re-run forge certify to confirm score recovered.",
        ],
        file_scope_hints=[
            "src/<pkg>/aN_*/<violating_file>.py",
        ],
        validation_gate=[
            "forge wire <pkg> --fail-on-violations",
            "python -m pytest",
            "forge certify . --fail-under 75",
        ],
    ),
    "add_feature": GoldenRecipe(
        schema_version=SCHEMA_VERSION_RECIPE_V1,
        name="add_feature",
        description=(
            "Implement a feature that combines existing a1 helpers "
            "and a2 composites under an a3 module."
        ),
        checklist=[
            "Read existing a3 features for tone + shape.",
            "Add the feature module under a3_og_features/.",
            "If the feature has a CLI surface, add a thin wrapper in "
            "a4_sy_orchestration/cli.py.",
            "Tests cover the pure parts at a1 level + the feature at a3.",
            "Run forge wire to confirm no upward imports.",
        ],
        file_scope_hints=[
            "src/atomadic_forge/a3_og_features/<feature>.py",
            "src/atomadic_forge/a4_sy_orchestration/cli.py",
            "tests/test_<feature>.py",
        ],
        validation_gate=[
            "python -m pytest",
            "forge wire src/atomadic_forge --fail-on-violations",
            "forge certify . --fail-under 75",
        ],
    ),
    "publish_mcp": GoldenRecipe(
        schema_version=SCHEMA_VERSION_RECIPE_V1,
        name="publish_mcp",
        description=(
            "Register Forge as an MCP server in a coding-agent client "
            "(Cursor / Claude Code / Aider / Devin)."
        ),
        checklist=[
            "Install Forge: pip install -e . (or pip install "
            "atomadic-forge once on PyPI).",
            "Add a 'forge' entry to the client's mcpServers map.",
            "command = 'forge'; args = ['mcp', 'serve', '--project', "
            "'/path/to/your/repo'].",
            "Reconnect the client; expect tools/list to expose 11 "
            "tools incl. context_pack, preflight_change, score_patch.",
            "Hit forge://summary/blockers as the agent's first call "
            "for orientation.",
        ],
        file_scope_hints=[
            "<your-mcp-config>.json",
        ],
        validation_gate=[
            "forge mcp serve --project . < /dev/null",
        ],
        notes=[
            "On Windows, use absolute paths with forward slashes in "
            "the MCP config to avoid escape-character issues.",
        ],
    ),
}


def list_recipes() -> list[str]:
    return sorted(_RECIPES.keys())


def get_recipe(name: str) -> GoldenRecipe | None:
    return _RECIPES.get(name)


def all_recipes() -> dict[str, GoldenRecipe]:
    """Return the full recipe catalogue (read-only-by-convention)."""
    return dict(_RECIPES)
