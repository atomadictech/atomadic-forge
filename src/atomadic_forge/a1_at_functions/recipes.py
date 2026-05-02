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
    "bump_version": GoldenRecipe(
        schema_version=SCHEMA_VERSION_RECIPE_V1,
        name="bump_version",
        description=(
            "Bump the package version in pyproject.toml, add a CHANGELOG "
            "entry, and create a git tag."
        ),
        checklist=[
            "Decide patch / minor / major bump (semver).",
            "Edit version in pyproject.toml (and package.json if present).",
            "Update __version__ in src/<pkg>/__init__.py.",
            "Prepend a CHANGELOG.md entry under the new version.",
            "Run forge certify . --fail-under 75.",
            "Commit with message 'chore(release): v<version>'.",
            "Tag: git tag v<version> && git push --tags.",
        ],
        file_scope_hints=[
            "pyproject.toml",
            "src/<pkg>/__init__.py",
            "CHANGELOG.md",
        ],
        validation_gate=[
            "python -m pytest",
            "forge certify . --fail-under 75",
            "forge wire src/<pkg> --fail-on-violations",
        ],
        notes=[
            "If vscode-forge-extension/package.json exists, keep its "
            "version field in sync — test_vscode_extension_manifest.py "
            "asserts the versions match.",
        ],
    ),
    "fix_test_detection": GoldenRecipe(
        schema_version=SCHEMA_VERSION_RECIPE_V1,
        name="fix_test_detection",
        description=(
            "Debug and fix when forge certify reports ran=False or "
            "pass_ratio=0 despite pytest passing locally."
        ),
        checklist=[
            "Run forge certify . --json and inspect "
            "detail.test_run.ran + detail.test_run.pytest_summary.",
            "Check for xfailed/xpassed in pytest output: the old "
            "_FINAL_LINE_RE regex choked on unknown status words — "
            "upgrade to the 5-independent-regex fix in test_runner.py.",
            "Confirm PYTHONPATH includes src/ so imports resolve inside "
            "subprocess.",
            "Check that test files import the target package (package= "
            "filter rejects unrelated tests).",
            "Re-run forge certify after the fix to confirm "
            "pass_ratio > 0.",
        ],
        file_scope_hints=[
            "src/atomadic_forge/a1_at_functions/test_runner.py",
        ],
        validation_gate=[
            "python -m pytest tests/test_test_runner.py",
            "forge certify . --json | python -c "
            "\"import sys,json; r=json.load(sys.stdin); "
            "assert r['test_pass_ratio']>0,'still broken'\"",
        ],
        notes=[
            "P1 bug (v0.6.0): _FINAL_LINE_RE was a single monolithic "
            "pattern; xfailed/xpassed between 'passed' and 'in Xs' "
            "broke the match. Fix: 5 independent per-metric regexes.",
        ],
    ),
    "dev_cycle": GoldenRecipe(
        schema_version=SCHEMA_VERSION_RECIPE_V1,
        name="dev_cycle",
        description=(
            "Complete agent development cycle: orient → preflight → edit → "
            "validate → end-of-cycle scan. Enforces monadic tier law, "
            "CNA naming conventions, and closes with emergent/synergy/certify."
        ),
        checklist=[
            # ── Phase 1: Orient ──────────────────────────────────────────────
            "PHASE 1 — ORIENT: call context_pack first (always).",
            "Run wire to confirm zero tier violations before starting.",
            "Check audit_list to see what Forge has already written.",
            # ── Phase 2: Preflight ───────────────────────────────────────────
            "PHASE 2 — PREFLIGHT: before every file edit, call preflight_change "
            "with intent + proposed_files. Abort if write_scope_too_broad=True.",
            "Call select_tests to know which tests to run after the edit.",
            # ── Phase 3: Edit ────────────────────────────────────────────────
            "PHASE 3 — EDIT: apply the bounded change in the correct tier.",
            "  a0 file? Use suffix: *_config/_constants/_types/_enums.",
            "  a1 file? Use suffix: *_utils/_helpers/_validators/_parsers/_compose/_rank/_render.",
            "  a2 file? Use suffix: *_client/_core/_store/_registry.",
            "  a3 file? Use suffix: *_feature/_service/_pipeline/_gate.",
            "  a4 file? Use suffix: *_cmd/_cli/_runner/_main.",
            "After every edit: run wire + select_tests minimum set.",
            "If any test fails, fix it before proceeding.",
            # ── Phase 4: End of cycle ────────────────────────────────────────
            "PHASE 4 — END OF CYCLE: run emergent_scan to find novel compositions.",
            "Run synergy_scan to find feature-pair gaps.",
            "Run certify — score must be ≥ 75 to close the cycle.",
            "If certify < 75, run auto_plan for ranked repair cards.",
        ],
        file_scope_hints=[
            "src/<pkg>/aN_*/<new_file>.py",
            "tests/test_<feature>.py",
        ],
        validation_gate=[
            "forge wire src/<pkg> --fail-on-violations",
            "python -m pytest",
            "forge certify . --fail-under 75",
            "forge emergent scan . --json",
            "forge synergy scan . --json",
        ],
        notes=[
            "This recipe is the canonical agent dev cycle for Forge-shaped repos.",
            "Agents that skip context_pack or preflight_change violate the protocol.",
            "emergent_scan and synergy_scan surface new a3 features to implement next.",
            "CNA = Convention Naming Adherence — file names must match their tier suffix.",
        ],
    ),
    "naming_check": GoldenRecipe(
        schema_version=SCHEMA_VERSION_RECIPE_V1,
        name="naming_check",
        description=(
            "Audit every source file's name against the CNA (Convention Naming "
            "Adherence) rules for its tier. Files that don't follow the convention "
            "are flagged; rename them or move them to the correct tier."
        ),
        checklist=[
            "Run forge wire src/<pkg> to get the tier map.",
            "For each tier directory, check file suffixes:",
            "  a0_qk_constants/ → must end in _config/_constants/_types/_enums.py",
            "  a1_at_functions/ → must end in _utils/_helpers/_validators/_parsers/"
            "_functions/_compose/_rank/_render/_extract/_detect/_check/_protocol.py",
            "  a2_mo_composites/ → must end in _client/_core/_store/_registry.py",
            "  a3_og_features/ → must end in _feature/_service/_pipeline/_gate.py",
            "  a4_sy_orchestration/ → must end in _cmd/_cli/_runner/_main.py",
            "Rename any file that violates the convention.",
            "Re-run forge wire to confirm no side effects from the rename.",
        ],
        file_scope_hints=[
            "src/<pkg>/a0_qk_constants/",
            "src/<pkg>/a1_at_functions/",
            "src/<pkg>/a2_mo_composites/",
            "src/<pkg>/a3_og_features/",
            "src/<pkg>/a4_sy_orchestration/",
        ],
        validation_gate=[
            "forge wire src/<pkg>",
            "python -m pytest",
        ],
        notes=[
            "CNA enforcement is heuristic — __init__.py and _*.py private files "
            "are exempt. The convention is about PUBLIC module interfaces.",
            "Renaming a file in a4 requires updating the CLI entry-point name; "
            "check pyproject.toml [project.scripts].",
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
