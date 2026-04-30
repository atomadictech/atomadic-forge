"""Tier verification — Codex-6: policy enforcement + recipes CLI +
Receipt v1.1 polyglot_breakdown.
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import typer.testing

from atomadic_forge.a1_at_functions.patch_scorer import score_patch
from atomadic_forge.a1_at_functions.preflight_change import preflight_change
from atomadic_forge.a1_at_functions.receipt_emitter import build_receipt
from atomadic_forge.a4_sy_orchestration.cli import app

runner = typer.testing.CliRunner()


def _seed_pyproject_with_policy(tmp_path: Path, *, max_files: int = 2,
                                  protected: tuple[str, ...] = ("pyproject.toml",)) -> None:
    body = textwrap.dedent(f'''
        [project]
        name = "demo"
        version = "0.0.1"

        [tool.forge.agent]
        max_files_per_patch = {max_files}
        protected_files = {list(protected)!r}
    ''').strip()
    (tmp_path / "pyproject.toml").write_text(body, encoding="utf-8")


# ---- preflight: policy enforcement -------------------------------------

def test_preflight_uses_policy_max_files(tmp_path):
    _seed_pyproject_with_policy(tmp_path, max_files=2)
    rep = preflight_change(
        intent="x",
        proposed_files=["a.py", "b.py", "c.py"],
        project_root=tmp_path,
    )
    assert rep["write_scope_threshold"] == 2
    assert rep["write_scope_too_broad"] is True


def test_preflight_explicit_threshold_overrides_policy(tmp_path):
    _seed_pyproject_with_policy(tmp_path, max_files=2)
    rep = preflight_change(
        intent="x",
        proposed_files=["a.py", "b.py", "c.py"],
        project_root=tmp_path,
        scope_threshold=20,   # explicit caller wins
    )
    assert rep["write_scope_threshold"] == 20
    assert rep["write_scope_too_broad"] is False


def test_preflight_flags_protected_files(tmp_path):
    _seed_pyproject_with_policy(tmp_path,
                                 protected=("pyproject.toml", "LICENSE"))
    rep = preflight_change(
        intent="bump version",
        proposed_files=["pyproject.toml", "src/x.py"],
        project_root=tmp_path,
    )
    pp_file = next(f for f in rep["proposed_files"]
                   if f["path"] == "pyproject.toml")
    assert any("protected_files" in n for n in pp_file["notes"])
    assert any("protected file" in n for n in rep["overall_notes"])


def test_preflight_no_policy_uses_default_threshold(tmp_path):
    rep = preflight_change(
        intent="x",
        proposed_files=[f"f{i}.py" for i in range(5)],
        project_root=tmp_path,
    )
    assert rep["write_scope_threshold"] == 8
    assert rep["write_scope_too_broad"] is False


# ---- score_patch: policy enforcement -----------------------------------

_DIFF_TOUCHES_PROTECTED = """\
diff --git a/PAPER.md b/PAPER.md
--- a/PAPER.md
+++ b/PAPER.md
@@ -1,1 +1,2 @@
 # Paper
+more content
"""


def test_score_patch_no_project_root_no_policy_check():
    rep = score_patch(_DIFF_TOUCHES_PROTECTED)
    # No protected-file note; release files alone don't trigger here.
    assert rep["needs_human_review"] is False


def test_score_patch_with_policy_flags_protected(tmp_path):
    _seed_pyproject_with_policy(tmp_path,
                                 protected=("PAPER.md",))
    rep = score_patch(_DIFF_TOUCHES_PROTECTED, project_root=tmp_path)
    assert rep["needs_human_review"] is True
    assert any("protected_files" in n for n in rep["notes"])


# ---- recipes CLI -------------------------------------------------------

def test_cli_recipes_lists_all():
    result = runner.invoke(app, ["recipes"])
    assert result.exit_code == 0
    assert "release_hardening" in result.stdout
    assert "publish_mcp" in result.stdout


def test_cli_recipes_lists_json():
    result = runner.invoke(app, ["recipes", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["schema_version"] == "atomadic-forge.recipe.list/v1"
    assert "fix_wire_violation" in data["recipes"]


def test_cli_recipes_show_one_human():
    result = runner.invoke(app, ["recipes", "release_hardening"])
    assert result.exit_code == 0
    assert "Checklist:" in result.stdout
    assert "Validation gate:" in result.stdout


def test_cli_recipes_unknown_errors():
    result = runner.invoke(app, ["recipes", "definitely-not-a-recipe"])
    assert result.exit_code != 0
    assert "unknown recipe" in (result.stdout + (result.stderr or ""))


# ---- Receipt v1.1 polyglot_breakdown -----------------------------------

def _sample_scout_polyglot() -> dict:
    return {
        "schema_version": "atomadic-forge.scout/v1",
        "symbol_count": 3,
        "tier_distribution": {"a1_at_functions": 3},
        "effect_distribution": {"pure": 3, "state": 0, "io": 0},
        "primary_language": "python",
        "language_distribution": {"python": 5, "javascript": 2,
                                    "typescript": 1},
        "symbols": [
            {"name": "a", "language": "python"},
            {"name": "b", "language": "python"},
            {"name": "c", "language": "javascript"},
        ],
    }


def test_receipt_carries_polyglot_breakdown():
    receipt = build_receipt(
        certify_result={"score": 100.0, "documentation_complete": True,
                         "tests_present": True, "tier_layout_present": True,
                         "no_upward_imports": True, "issues": [],
                         "schema_version": "atomadic-forge.certify/v1"},
        wire_report={"verdict": "PASS", "violation_count": 0,
                      "auto_fixable": 0, "violations": [],
                      "schema_version": "atomadic-forge.wire/v1"},
        scout_report=_sample_scout_polyglot(),
        project_name="demo",
        project_root=Path("/tmp/demo"),
        forge_version="0.3.0-test",
        compute_artifact_hashes=False,
    )
    pb = receipt["polyglot_breakdown"]
    assert pb["file_count"] == 8
    assert pb["languages"] == {"python": 5, "javascript": 2,
                                "typescript": 1}
    assert pb["primary_language"] == "python"
    # Symbols with explicit language attributes count per language.
    assert pb["symbols_by_language"]["python"] == 2
    assert pb["symbols_by_language"]["javascript"] == 1


def test_polyglot_breakdown_handles_missing_scout_fields():
    """Empty scout still produces a structurally-valid breakdown."""
    receipt = build_receipt(
        certify_result={"score": 0.0, "documentation_complete": False,
                         "tests_present": False, "tier_layout_present": False,
                         "no_upward_imports": False, "issues": [],
                         "schema_version": "atomadic-forge.certify/v1"},
        wire_report={"verdict": "FAIL", "violation_count": 0,
                      "auto_fixable": 0, "violations": [],
                      "schema_version": "atomadic-forge.wire/v1"},
        scout_report={"schema_version": "atomadic-forge.scout/v1"},
        project_name="empty",
        project_root=Path("/tmp/empty"),
        forge_version="0.3.0-test",
        compute_artifact_hashes=False,
    )
    pb = receipt["polyglot_breakdown"]
    assert pb["file_count"] == 0
    assert pb["languages"] == {}
    assert pb["symbol_count"] == 0
