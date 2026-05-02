"""Tier verification — Codex round-5: completing the 'Copilot's
Copilot' 12-item enumeration. One file per concern, kept tight:

  #5  agent_memory:    why_did_this_change, what_failed_last_time
  #6  repo_explainer:  explain_repo
  #7  test_selector:   select_tests
  #8  plan_adapter:    adapt_plan
  #9  tool_composer:   compose_tools
  #10 policy_loader:   load_policy + file_is_protected
  #11 rollback_planner: rollback_plan
  #12 recipes:         list_recipes / get_recipe
"""
from __future__ import annotations

import json

# Importing a3.mcp_server wires every a1↔a3 injected handler.
import atomadic_forge.a3_og_features.mcp_server  # noqa: F401
from atomadic_forge.a0_qk_constants.policy_schema import (
    SCHEMA_VERSION_POLICY_V1,
)
from atomadic_forge.a1_at_functions.agent_memory import (
    SCHEMA_VERSION_WHAT_FAILED_V1,
    SCHEMA_VERSION_WHY_V1,
    what_failed_last_time,
    why_did_this_change,
)
from atomadic_forge.a1_at_functions.mcp_protocol import (
    dispatch_request,
)
from atomadic_forge.a1_at_functions.plan_adapter import (
    SCHEMA_VERSION_ADAPTED_PLAN_V1,
    adapt_plan,
)
from atomadic_forge.a1_at_functions.policy_loader import (
    default_policy,
    file_is_protected,
    load_policy,
)
from atomadic_forge.a1_at_functions.recipes import (
    SCHEMA_VERSION_RECIPE_V1,
    all_recipes,
    get_recipe,
    list_recipes,
)
from atomadic_forge.a1_at_functions.repo_explainer import (
    SCHEMA_VERSION_EXPLAIN_V1,
    explain_repo,
)
from atomadic_forge.a1_at_functions.rollback_planner import (
    SCHEMA_VERSION_ROLLBACK_V1,
    rollback_plan,
)
from atomadic_forge.a1_at_functions.test_selector import (
    SCHEMA_VERSION_TEST_SELECT_V1,
    select_tests,
)
from atomadic_forge.a1_at_functions.tool_composer import (
    SCHEMA_VERSION_COMPOSE_V1,
    compose_tools,
)

# ============================================================
# select_tests (#7)
# ============================================================

def test_select_tests_v1(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_helper.py").write_text("def test_x(): pass\n")
    rep = select_tests(
        intent="add helper", changed_files=["src/pkg/helper.py"],
        project_root=tmp_path,
    )
    assert rep["schema_version"] == SCHEMA_VERSION_TEST_SELECT_V1
    assert "tests/test_helper.py" in rep["minimum_tests"]


def test_select_tests_falls_back_to_full_when_no_match(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_other.py").write_text("def test_x(): pass\n")
    rep = select_tests(
        intent="add new thing", changed_files=["src/pkg/brand_new.py"],
        project_root=tmp_path,
    )
    assert "tests/test_other.py" in rep["full_tests"]


def test_select_tests_javascript_repo_uses_npm_verify(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"scripts":{"verify":"npm run check && npm test","test":"node --test"}}',
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "cognition.test.js").write_text(
        "import test from 'node:test';\ntest('x', () => {});\n",
        encoding="utf-8",
    )
    rep = select_tests(
        intent="change cognition", changed_files=["cognition/worker.js"],
        project_root=tmp_path,
    )
    assert rep["minimum_command"] == "npm run verify"
    assert rep["full_command"] == "npm run verify"


def test_select_tests_non_code_artifact_has_no_mirror_requirement(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"scripts":{"verify":"npm run verify"}}', encoding="utf-8")
    rep = select_tests(
        intent="add research note",
        changed_files=["research/forge-agent-review.md"],
        project_root=tmp_path,
    )
    assert any("non-code artifact" in r for r in rep["rationale"])
    assert rep["minimum_command"] == "npm run verify"


def test_mcp_select_tests_tool(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_a(): pass\n")
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "select_tests",
                    "arguments": {"project_root": str(tmp_path),
                                   "intent": "x",
                                   "changed_files": ["src/x.py"]}}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["schema_version"] == SCHEMA_VERSION_TEST_SELECT_V1


# ============================================================
# rollback_plan (#11)
# ============================================================

def test_rollback_plan_v1(tmp_path):
    rep = rollback_plan(
        changed_files=["src/x.py", "tests/test_x.py", "build/x"],
        project_root=tmp_path,
    )
    assert rep["schema_version"] == SCHEMA_VERSION_ROLLBACK_V1
    assert "build/x" in rep["files_to_remove"]
    assert "tests/test_x.py" in rep["tests_to_rerun"]


def test_rollback_plan_high_risk_on_release_file(tmp_path):
    rep = rollback_plan(
        changed_files=["pyproject.toml"], project_root=tmp_path)
    assert rep["risk_level"] == "high"


def test_rollback_plan_low_risk_on_caches_only(tmp_path):
    rep = rollback_plan(
        changed_files=["__pycache__/x.pyc", ".pytest_cache/v/cache/lastfailed"],
        project_root=tmp_path,
    )
    assert rep["risk_level"] == "low"


def test_mcp_rollback_plan_tool(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "rollback_plan",
                    "arguments": {"project_root": str(tmp_path),
                                   "changed_files": ["pyproject.toml"]}}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["risk_level"] == "high"


# ============================================================
# load_policy (#10)
# ============================================================

def test_load_policy_default_when_no_pyproject(tmp_path):
    pol = load_policy(tmp_path)
    assert pol["schema_version"] == SCHEMA_VERSION_POLICY_V1
    assert pol["max_files_per_patch"] == 8


def test_load_policy_reads_pyproject_section(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.forge.agent]\n'
        'protected_files = ["pyproject.toml", "docs/PAPER.md"]\n'
        'max_files_per_patch = 4\n',
        encoding="utf-8",
    )
    pol = load_policy(tmp_path)
    assert pol["max_files_per_patch"] == 4
    assert "pyproject.toml" in pol["protected_files"]


def test_file_is_protected_exact_and_basename():
    pol = default_policy()
    pol["protected_files"] = ["pyproject.toml", "docs/PAPER.md"]
    assert file_is_protected("pyproject.toml", pol) is True
    assert file_is_protected("src/pyproject.toml", pol) is True
    assert file_is_protected("docs/PAPER.md", pol) is True
    assert file_is_protected("pyproject_helper.py", pol) is False


def test_mcp_load_policy_tool(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "load_policy",
                    "arguments": {"project_root": str(tmp_path)}}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["schema_version"] == SCHEMA_VERSION_POLICY_V1


# ============================================================
# agent memory (#5)
# ============================================================

def test_why_did_this_change_returns_v1_when_empty(tmp_path):
    rep = why_did_this_change(file="src/x.py", project_root=tmp_path)
    assert rep["schema_version"] == SCHEMA_VERSION_WHY_V1
    assert rep["related_lineage"] == []
    assert rep["related_plan_events"] == []


def test_why_did_this_change_finds_lineage(tmp_path):
    d = tmp_path / ".atomadic-forge"
    d.mkdir()
    (d / "lineage.jsonl").write_text(
        json.dumps({"ts_utc": "2026-04-29T00:00:00+00:00",
                     "artifact": "scout",
                     "path": ".atomadic-forge/scout.json"}) + "\n",
        encoding="utf-8",
    )
    rep = why_did_this_change(
        file=".atomadic-forge/scout.json", project_root=tmp_path)
    assert len(rep["related_lineage"]) == 1


def test_what_failed_last_time_v1_empty(tmp_path):
    rep = what_failed_last_time(area="x", project_root=tmp_path)
    assert rep["schema_version"] == SCHEMA_VERSION_WHAT_FAILED_V1
    assert rep["failures"] == []


def test_mcp_why_did_this_change_tool(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "why_did_this_change",
                    "arguments": {"project_root": str(tmp_path),
                                   "file": "src/x.py"}}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["schema_version"] == SCHEMA_VERSION_WHY_V1


# ============================================================
# explain_repo (#6)
# ============================================================

def test_explain_repo_v1(tmp_path):
    rep = explain_repo(
        project_root=tmp_path, repo_purpose="A demo repo for tests.",
    )
    assert rep["schema_version"] == SCHEMA_VERSION_EXPLAIN_V1
    assert rep["one_liner"].startswith("A demo")
    assert any("tier law" in s for s in rep["do_not_break"])


def test_explain_repo_release_state_block(tmp_path):
    rep = explain_repo(
        project_root=tmp_path, repo_purpose="x",
        wire_report={"verdict": "FAIL", "violation_count": 1,
                      "auto_fixable": 1, "violations": []},
    )
    assert "BLOCKED" in rep["release_state"]


def test_mcp_explain_repo_tool(tmp_path):
    (tmp_path / "README.md").write_text("# x\n\nshort.\n", encoding="utf-8")
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "explain_repo",
                    "arguments": {"project_root": str(tmp_path)}}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["schema_version"] == SCHEMA_VERSION_EXPLAIN_V1


# ============================================================
# adapt_plan (#8)
# ============================================================

def _fake_plan_with_three_cards():
    return {
        "schema_version": "atomadic-forge.agent_plan/v1",
        "top_actions": [
            {"id": "a", "kind": "operational", "applyable": True,
              "risk": "low"},
            {"id": "b", "kind": "architectural", "applyable": True,
              "risk": "low"},
            {"id": "c", "kind": "synthesis", "applyable": False,
              "risk": "high"},
        ],
    }


def test_adapt_plan_apply_when_caps_present():
    p = adapt_plan(_fake_plan_with_three_cards(),
                    agent_capabilities=["edit_files", "run_commands"])
    assert p["schema_version"] == SCHEMA_VERSION_ADAPTED_PLAN_V1
    assert p["top_actions"][0]["recommended_handling"] == "apply"


def test_adapt_plan_report_only_without_edit_caps():
    p = adapt_plan(_fake_plan_with_three_cards(),
                    agent_capabilities=["review"])
    handlings = {c["id"]: c["recommended_handling"]
                  for c in p["top_actions"]}
    assert handlings["a"] == "report_only"
    assert handlings["b"] == "report_only"
    assert handlings["c"] == "ask_human"


def test_adapt_plan_unknown_caps_recorded():
    p = adapt_plan(_fake_plan_with_three_cards(),
                    agent_capabilities=["edit_files", "telepathy"])
    assert "telepathy" in p["unknown_capabilities"]


def test_mcp_adapt_plan_tool(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "adapt_plan",
                    "arguments": {
                        "plan": _fake_plan_with_three_cards(),
                        "agent_capabilities": ["edit_files"],
                    }}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["schema_version"] == SCHEMA_VERSION_ADAPTED_PLAN_V1


# ============================================================
# compose_tools (#9)
# ============================================================

def test_compose_tools_release_recipe():
    plan = compose_tools(goal="ready to ship the release")
    assert plan["schema_version"] == SCHEMA_VERSION_COMPOSE_V1
    assert plan["matched_recipe"] == "release_check"
    tools = [s["tool"] for s in plan["steps"]]
    assert "wire" in tools and "certify" in tools


def test_compose_tools_falls_back_to_orient():
    plan = compose_tools(goal="something obscure")
    assert plan["matched_recipe"] == "orient"


def test_compose_tools_fix_violation_recipe():
    plan = compose_tools(goal="fix the F0042 wire violation")
    assert plan["matched_recipe"] == "fix_violation"
    tools = [s["tool"] for s in plan["steps"]]
    assert "auto_apply" in tools


def test_compose_tools_exact_verify_patch_recipe():
    plan = compose_tools(goal="verify_patch")
    assert plan["matched_recipe"] == "verify_patch"
    tools = [s["tool"] for s in plan["steps"]]
    assert tools == ["score_patch", "select_tests", "wire", "certify"]


def test_mcp_compose_tools_tool(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "compose_tools",
                    "arguments": {"goal": "before edit"}}},
        project_root=tmp_path,
    )
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["matched_recipe"] == "before_edit"


# ============================================================
# recipes (#12)
# ============================================================

def test_list_recipes_pinned_set():
    names = set(list_recipes())
    assert {
        "release_hardening", "add_cli_command", "fix_wire_violation",
        "add_feature", "publish_mcp",
    }.issubset(names)


def test_get_recipe_known():
    r = get_recipe("release_hardening")
    assert r is not None
    assert r["schema_version"] == SCHEMA_VERSION_RECIPE_V1
    assert any("CHANGELOG" in c for c in r["checklist"])


def test_get_recipe_unknown():
    assert get_recipe("nope") is None


def test_all_recipes_v1_schema():
    for r in all_recipes().values():
        assert r["schema_version"] == SCHEMA_VERSION_RECIPE_V1


def test_mcp_list_and_get_recipe(tmp_path):
    list_resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "list_recipes", "arguments": {}}},
        project_root=tmp_path,
    )
    body = json.loads(list_resp["result"]["content"][0]["text"])
    assert "release_hardening" in body["recipes"]
    get_resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "get_recipe",
                    "arguments": {"name": "fix_wire_violation"}}},
        project_root=tmp_path,
    )
    body = json.loads(get_resp["result"]["content"][0]["text"])
    assert body["schema_version"] == SCHEMA_VERSION_RECIPE_V1


# ============================================================
# Production-hardening: --version
# ============================================================

def test_forge_version_flag_works():
    """Codex production-hardening: forge --version should not error."""
    import typer.testing

    from atomadic_forge import __version__
    from atomadic_forge.a4_sy_orchestration.cli import app
    runner = typer.testing.CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout
