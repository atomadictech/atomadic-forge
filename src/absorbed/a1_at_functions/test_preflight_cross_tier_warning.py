"""Tier verification — Codex 'Copilot's Copilot' three primitives.

Covers context_pack, preflight_change, score_patch end-to-end:
pure emitters, CLI verbs, MCP tools.
"""
from __future__ import annotations

import json
from pathlib import Path

import typer.testing

from atomadic_forge.a1_at_functions.agent_context_pack import (
    SCHEMA_VERSION_CONTEXT_PACK_V1,
    emit_context_pack,
)
from atomadic_forge.a1_at_functions.mcp_protocol import (
    dispatch_request,
)
from atomadic_forge.a1_at_functions.patch_scorer import (
    SCHEMA_VERSION_PATCH_SCORE_V1,
    score_patch,
)
from atomadic_forge.a1_at_functions.preflight_change import (
    SCHEMA_VERSION_PREFLIGHT_V1,
    preflight_change,
)
from atomadic_forge.a4_sy_orchestration.cli import app

runner = typer.testing.CliRunner()


# ============================================================
# context_pack
# ============================================================

def _seed_repo(tmp_path: Path) -> Path:
    """A minimal Python repo: README + pyproject + a1 helper."""
    (tmp_path / "README.md").write_text(
        "# demo\n\nA tiny example for context_pack tests.\n",
        encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndescription = "demo project"\n',
        encoding="utf-8")
    a1 = tmp_path / "src" / "demo" / "a1_at_functions"
    a1.mkdir(parents=True)
    (a1 / "ok.py").write_text(
        '"""a1."""\ndef ok(x):\n    return x\n', encoding="utf-8")
    return tmp_path


def test_context_pack_v1_schema(tmp_path):
    repo = _seed_repo(tmp_path)
    pack = emit_context_pack(project_root=repo)
    assert pack["schema_version"] == SCHEMA_VERSION_CONTEXT_PACK_V1
    assert pack["project_root"] == str(repo)


def test_context_pack_repo_purpose_from_readme(tmp_path):
    repo = _seed_repo(tmp_path)
    pack = emit_context_pack(project_root=repo)
    assert "tiny example" in pack["repo_purpose"]


def test_context_pack_falls_back_to_pyproject(tmp_path):
    """No README → pyproject description used."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndescription = "Just a description"\n',
        encoding="utf-8")
    pack = emit_context_pack(project_root=tmp_path)
    assert pack["repo_purpose"] == "Just a description"


def test_context_pack_test_commands_detected(tmp_path):
    repo = _seed_repo(tmp_path)
    pack = emit_context_pack(project_root=repo)
    assert "python -m pytest" in pack["test_commands"]


def test_context_pack_release_gate_includes_certify(tmp_path):
    repo = _seed_repo(tmp_path)
    pack = emit_context_pack(project_root=repo)
    assert any("certify" in c for c in pack["release_gate"])


def test_context_pack_pinned_resources():
    pack = emit_context_pack(project_root=Path("/tmp"))
    assert "forge://docs/receipt" in pack["pinned_resources"]
    assert "forge://summary/blockers" in pack["pinned_resources"]


def test_context_pack_uses_plan_top_action_when_provided(tmp_path):
    fake_plan = {
        "top_actions": [
            {"id": "fix-something", "title": "Fix the thing",
             "next_command": "forge enforce src --apply",
             "kind": "architectural"},
        ],
    }
    pack = emit_context_pack(project_root=tmp_path, plan=fake_plan)
    assert pack["best_next_action"]["id"] == "fix-something"


def test_context_pack_cli_renders(tmp_path):
    repo = _seed_repo(tmp_path)
    result = runner.invoke(app, ["context-pack", str(repo)])
    assert result.exit_code == 0
    assert "context-pack" in result.stdout
    assert "purpose:" in result.stdout
    assert "tiers:" in result.stdout
    assert "tests:" in result.stdout


def test_context_pack_cli_json(tmp_path):
    repo = _seed_repo(tmp_path)
    result = runner.invoke(app, ["context-pack", str(repo), "--json"])
    assert result.exit_code == 0
    pack = json.loads(result.stdout)
    assert pack["schema_version"] == SCHEMA_VERSION_CONTEXT_PACK_V1


def test_mcp_context_pack_tool(tmp_path):
    repo = _seed_repo(tmp_path)
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "context_pack",
                    "arguments": {"target": str(repo)}}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["schema_version"] == SCHEMA_VERSION_CONTEXT_PACK_V1
    summary = resp["result"]["_summary"]
    assert summary is not None
    assert summary["schema_version"] == "atomadic-forge.summary/v1"


# ============================================================
# preflight_change
# ============================================================

def test_preflight_v1_schema():
    rep = preflight_change(
        intent="Add a helper", proposed_files=["src/x/a1_at_functions/helper.py"],
        project_root=Path("/tmp"),
    )
    assert rep["schema_version"] == SCHEMA_VERSION_PREFLIGHT_V1


def test_preflight_detects_tier():
    rep = preflight_change(
        intent="x", proposed_files=["src/pkg/a1_at_functions/helper.py"],
        project_root=Path("/tmp"),
    )
    f = rep["proposed_files"][0]
    assert f["detected_tier"] == "a1_at_functions"


def test_preflight_forbidden_imports_for_a1():
    rep = preflight_change(
        intent="x", proposed_files=["src/pkg/a1_at_functions/helper.py"],
        project_root=Path("/tmp"),
    )
    forbidden = rep["proposed_files"][0]["forbidden_imports"]
    assert "a2_mo_composites" in forbidden
    assert "a3_og_features" in forbidden


def test_preflight_likely_tests_mirror_path():
    rep = preflight_change(
        intent="x", proposed_files=["src/pkg/a1_at_functions/helper.py"],
        project_root=Path("/tmp"),
    )
    tests = rep["proposed_files"][0]["likely_tests"]
    assert any("test_helper.py" in t for t in tests)


def test_preflight_scope_too_broad_at_default_threshold():
    rep = preflight_change(
        intent="x",
        proposed_files=[f"src/pkg/a1_at_functions/h{i}.py"
                         for i in range(10)],
        project_root=Path("/tmp"),
    )
    assert rep["write_scope_too_broad"] is True


def test_preflight_within_threshold_clean():
    rep = preflight_change(
        intent="x",
        proposed_files=[f"src/pkg/a1_at_functions/h{i}.py"
                         for i in range(3)],
        project_root=Path("/tmp"),
    )
    assert rep["write_scope_too_broad"] is False


def test_preflight_cross_tier_warning():
    rep = preflight_change(
        intent="x",
        proposed_files=["src/pkg/a1_at_functions/h.py",
                         "src/pkg/a3_og_features/feat.py"],
        project_root=Path("/tmp"),
    )
    assert any("spans" in n for n in rep["overall_notes"])


def test_preflight_cli_json(tmp_path):
    result = runner.invoke(app, [
        "preflight",
        "Add a helper",
        "src/pkg/a1_at_functions/helper.py",
        "--project", str(tmp_path),
        "--json",
    ])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["schema_version"] == SCHEMA_VERSION_PREFLIGHT_V1


def test_preflight_cli_too_broad_exits_1(tmp_path):
    files = [f"src/pkg/a1_at_functions/h{i}.py" for i in range(12)]
    result = runner.invoke(
        app, ["preflight", "x", *files, "--project", str(tmp_path)])
    assert result.exit_code == 1


def test_mcp_preflight_change_tool(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "preflight_change",
                    "arguments": {
                        "project_root": str(tmp_path),
                        "intent": "Add helper",
                        "proposed_files": ["src/pkg/a1_at_functions/h.py"],
                    }}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["schema_version"] == SCHEMA_VERSION_PREFLIGHT_V1
    assert "_summary" in resp["result"]


def test_mcp_preflight_missing_intent_returns_error_shape(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "preflight_change",
                    "arguments": {"project_root": str(tmp_path),
                                   "proposed_files": ["x"]}}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert "error" in body


# ============================================================
# score_patch
# ============================================================

_DIFF_TESTS_ONLY = """\
diff --git a/tests/test_x.py b/tests/test_x.py
--- a/tests/test_x.py
+++ b/tests/test_x.py
@@ -1,1 +1,3 @@
 import x
+
+def test_y(): assert x
"""

_DIFF_PUBLIC_API = """\
diff --git a/src/pkg/__init__.py b/src/pkg/__init__.py
--- a/src/pkg/__init__.py
+++ b/src/pkg/__init__.py
@@ -1,1 +1,2 @@
 from .a import foo
+from .b import bar
"""

_DIFF_RELEASE = """\
diff --git a/pyproject.toml b/pyproject.toml
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -1,2 +1,2 @@
-version = "0.2.0"
+version = "0.3.0"
"""

_DIFF_ARCH_RISK = """\
diff --git a/src/pkg/a1_at_functions/h.py b/src/pkg/a1_at_functions/h.py
--- a/src/pkg/a1_at_functions/h.py
+++ b/src/pkg/a1_at_functions/h.py
@@ -1,1 +1,2 @@
 def x(): pass
+from pkg.a3_og_features.feat import F
"""

_DIFF_CODE_NO_TESTS = """\
diff --git a/src/pkg/a1_at_functions/h.py b/src/pkg/a1_at_functions/h.py
--- a/src/pkg/a1_at_functions/h.py
+++ b/src/pkg/a1_at_functions/h.py
@@ -1,1 +1,2 @@
 def x(): pass
+def y(): pass
"""


def test_score_patch_v1_schema():
    rep = score_patch(_DIFF_TESTS_ONLY)
    assert rep["schema_version"] == SCHEMA_VERSION_PATCH_SCORE_V1


def test_score_patch_empty_diff_safe():
    rep = score_patch("")
    assert rep["needs_human_review"] is False
    assert rep["file_count"] == 0


def test_score_patch_public_api_flagged():
    rep = score_patch(_DIFF_PUBLIC_API)
    assert rep["public_api_risk"] is True
    assert rep["needs_human_review"] is True


def test_score_patch_release_file_flagged():
    rep = score_patch(_DIFF_RELEASE)
    assert rep["release_risk"] is True


def test_score_patch_architectural_risk_on_upward_import():
    rep = score_patch(_DIFF_ARCH_RISK)
    assert rep["architectural_risk"] is True
    assert rep["needs_human_review"] is True


def test_score_patch_test_risk_when_code_changed_without_tests():
    rep = score_patch(_DIFF_CODE_NO_TESTS)
    assert rep["test_risk"] is True


def test_score_patch_tests_only_no_test_risk():
    rep = score_patch(_DIFF_TESTS_ONLY)
    assert rep["test_risk"] is False


def test_mcp_score_patch_tool(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "score_patch",
                    "arguments": {"diff": _DIFF_PUBLIC_API}}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["schema_version"] == SCHEMA_VERSION_PATCH_SCORE_V1
    assert body["public_api_risk"] is True
    summary = resp["result"]["_summary"]
    assert summary["verdict"] == "REFINE"
