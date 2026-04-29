"""Tier verification — Codex-2: agent_plan/v1.

Codex's prescription:

  > Forge outputs 'next best action cards.' The active agent does
  > what agents are good at — inspect, edit, run tests, decide
  > whether the suggestion was actually good. Forge stays the
  > architectural conscience and candidate generator.

Tests pin:
  * v1 schema (TypedDicts + required fields + version constants)
  * pure emit_agent_plan ranking + card construction
  * forge plan CLI verb (--json round-trip; human output renders)
  * MCP auto_plan tool dispatch (a1↔a3 injection; correct binding)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import typer.testing

from atomadic_forge.a0_qk_constants.agent_plan_schema import (
    ACTION_KINDS,
    PLAN_MODES,
    REQUIRED_PLAN_FIELDS,
    RISK_LEVELS,
    SCHEMA_VERSION_AGENT_ACTION_V1,
    SCHEMA_VERSION_AGENT_PLAN_V1,
)
from atomadic_forge.a1_at_functions.agent_plan_emitter import emit_agent_plan
# Importing the a3 mcp_server module wires the auto_plan handler.
import atomadic_forge.a3_og_features.mcp_server  # noqa: F401
from atomadic_forge.a1_at_functions.mcp_protocol import dispatch_request
from atomadic_forge.a4_sy_orchestration.cli import app

runner = typer.testing.CliRunner()


# ---- a0 schema constants ----------------------------------------------

def test_schema_version_constants_pinned():
    assert SCHEMA_VERSION_AGENT_PLAN_V1 == "atomadic-forge.agent_plan/v1"
    assert SCHEMA_VERSION_AGENT_ACTION_V1 == "atomadic-forge.agent_action/v1"


def test_action_kinds_pinned():
    assert set(ACTION_KINDS) == {
        "operational", "architectural", "composition",
        "synthesis", "release",
    }


def test_plan_modes_pinned():
    assert set(PLAN_MODES) == {"improve", "absorb"}


def test_risk_levels_pinned():
    assert set(RISK_LEVELS) == {"low", "medium", "high"}


def test_required_plan_fields_pinned():
    assert set(REQUIRED_PLAN_FIELDS) == {
        "schema_version", "generated_at_utc", "verdict", "goal",
        "mode", "project_root", "top_actions",
    }


# ---- pure emitter ------------------------------------------------------

_WIRE_FAIL = {
    "schema_version": "atomadic-forge.wire/v1",
    "verdict": "FAIL",
    "violation_count": 1,
    "auto_fixable": 1,
    "violations": [
        {"file": "a1_at_functions/h.py",
         "from_tier": "a1_at_functions",
         "to_tier": "a3_og_features",
         "imported": "F", "language": "python", "f_code": "F0042",
         "proposed_fix": ""},
    ],
}

_CERTIFY_PARTIAL = {
    "schema_version": "atomadic-forge.certify/v1",
    "score": 50.0,
    "documentation_complete": False,
    "tests_present": True,
    "tier_layout_present": True,
    "no_upward_imports": False,
    "issues": [],
}


def test_emit_returns_v1_schema():
    plan = emit_agent_plan(
        project_root="/tmp/demo", goal="ship",
        wire_report=_WIRE_FAIL, certify_report=_CERTIFY_PARTIAL,
        package="demo",
    )
    assert plan["schema_version"] == SCHEMA_VERSION_AGENT_PLAN_V1
    for f in REQUIRED_PLAN_FIELDS:
        assert f in plan, f"missing required {f!r}"


def test_emit_action_count_full_top_actions_capped():
    plan = emit_agent_plan(
        project_root="/tmp/demo", goal="ship",
        wire_report=_WIRE_FAIL, certify_report=_CERTIFY_PARTIAL,
        package="demo", top_n=1,
    )
    assert plan["action_count"] >= 2  # docs + wire
    assert len(plan["top_actions"]) == 1


def test_emit_top_n_must_be_positive():
    with pytest.raises(ValueError):
        emit_agent_plan(project_root="/tmp", goal="x", top_n=0)


def test_emit_invalid_mode_raises():
    with pytest.raises(ValueError):
        emit_agent_plan(project_root="/tmp", goal="x", mode="bogus")


def test_emit_each_card_has_v1_action_schema():
    plan = emit_agent_plan(
        project_root="/tmp/demo", goal="ship",
        wire_report=_WIRE_FAIL, certify_report=_CERTIFY_PARTIAL,
        package="demo",
    )
    for card in plan["top_actions"]:
        assert card["schema_version"] == SCHEMA_VERSION_AGENT_ACTION_V1
        assert card["kind"] in ACTION_KINDS
        assert card["risk"] in RISK_LEVELS
        assert isinstance(card["applyable"], bool)
        assert card["id"]
        assert card["title"]
        assert card["why"]
        assert card["next_command"]


def test_emit_ranks_applyable_first():
    """Applyable cards (forge enforce, etc.) rank above review-manually
    cards regardless of kind. The first card's next_command becomes
    plan.next_command."""
    plan = emit_agent_plan(
        project_root="/tmp/demo", goal="ship",
        wire_report=_WIRE_FAIL, certify_report=_CERTIFY_PARTIAL,
        package="demo",
    )
    first = plan["top_actions"][0]
    assert first["applyable"] is True
    assert plan["next_command"] == first["next_command"]


def test_emit_clean_repo_passes():
    """No wire violations + all certify axes pass + score=100 → PASS."""
    clean_wire = {"schema_version": "atomadic-forge.wire/v1",
                   "verdict": "PASS", "violation_count": 0,
                   "auto_fixable": 0, "violations": []}
    clean_cert = {"schema_version": "atomadic-forge.certify/v1",
                   "score": 100.0, "documentation_complete": True,
                   "tests_present": True, "tier_layout_present": True,
                   "no_upward_imports": True, "issues": []}
    plan = emit_agent_plan(
        project_root="/tmp", goal="ship",
        wire_report=clean_wire, certify_report=clean_cert,
    )
    assert plan["verdict"] == "PASS"
    assert plan["action_count"] == 0
    assert plan["top_actions"] == []


def test_emit_records_source_provenance():
    plan = emit_agent_plan(
        project_root="/tmp", goal="ship",
        wire_report=_WIRE_FAIL, certify_report=_CERTIFY_PARTIAL,
    )
    sources = plan["sources"]
    assert sources["wire"] == "atomadic-forge.wire/v1"
    assert sources["certify"] == "atomadic-forge.certify/v1"


def test_emit_id_is_stable_slug():
    """Card ids must be deterministic and url-safe so the agent can
    use them to address future `step` / `apply` calls."""
    plan = emit_agent_plan(
        project_root="/tmp/demo", goal="ship",
        wire_report=_WIRE_FAIL, certify_report=_CERTIFY_PARTIAL,
        package="demo",
    )
    for card in plan["top_actions"]:
        assert re.match(r"^[a-z0-9.-]+$", card["id"]), (
            f"non-slug id: {card['id']!r}"
        )


# ---- forge plan CLI verb ------------------------------------------------

def test_cli_plan_json_round_trip(tmp_path):
    pkg = tmp_path / "pkg"
    a1 = pkg / "a1_at_functions"; a1.mkdir(parents=True)
    a3 = pkg / "a3_og_features"; a3.mkdir(parents=True)
    (a3 / "feat.py").write_text(
        '"""a3."""\nclass F:\n    pass\n', encoding="utf-8")
    (a1 / "h.py").write_text(
        "from ..a3_og_features.feat import F\n", encoding="utf-8")
    result = runner.invoke(app, ["plan", str(pkg), "--json", "--top", "3"])
    assert result.exit_code == 0
    plan = json.loads(result.stdout)
    assert plan["schema_version"] == SCHEMA_VERSION_AGENT_PLAN_V1
    assert plan["mode"] == "improve"
    assert plan["action_count"] >= 1
    assert len(plan["top_actions"]) <= 3


def test_cli_plan_human_renders(tmp_path):
    pkg = tmp_path / "pkg"
    a1 = pkg / "a1_at_functions"; a1.mkdir(parents=True)
    a3 = pkg / "a3_og_features"; a3.mkdir(parents=True)
    (a3 / "feat.py").write_text(
        '"""a3."""\nclass F:\n    pass\n', encoding="utf-8")
    (a1 / "h.py").write_text(
        "from ..a3_og_features.feat import F\n", encoding="utf-8")
    result = runner.invoke(app, ["plan", str(pkg)])
    assert result.exit_code == 0
    out = result.stdout
    assert "Forge plan" in out
    assert "verdict:" in out
    assert "[AUTO]" in out or "[REVIEW]" in out
    assert "NEXT:" in out


def test_cli_plan_invalid_mode_rejected(tmp_path):
    result = runner.invoke(app, ["plan", str(tmp_path), "--mode", "bogus"])
    assert result.exit_code != 0


# ---- MCP auto_plan tool ------------------------------------------------

def test_mcp_auto_plan_tool_dispatches(tmp_path):
    pkg = tmp_path / "pkg"
    a1 = pkg / "a1_at_functions"; a1.mkdir(parents=True)
    a3 = pkg / "a3_og_features"; a3.mkdir(parents=True)
    (a3 / "feat.py").write_text(
        '"""a3."""\nclass F:\n    pass\n', encoding="utf-8")
    (a1 / "h.py").write_text(
        "from ..a3_og_features.feat import F\n", encoding="utf-8")
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "auto_plan",
                    "arguments": {"target": str(pkg), "top_n": 5}}},
        project_root=tmp_path,
    )
    assert "result" in resp
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["schema_version"] == SCHEMA_VERSION_AGENT_PLAN_V1
    # The dispatcher attaches a digest summary to plan results.
    summary = resp["result"]["_summary"]
    assert summary is not None
    assert summary["schema_version"] == "atomadic-forge.summary/v1"


def test_mcp_auto_plan_tool_in_tools_list(tmp_path):
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        project_root=tmp_path,
    )
    names = {t["name"] for t in resp["result"]["tools"]}
    assert "auto_plan" in names


def test_mcp_auto_plan_tool_input_schema_validates_mode():
    """The tool's inputSchema must declare mode as enum
    ['improve', 'absorb'] so MCP clients reject bad modes locally."""
    from atomadic_forge.a1_at_functions.mcp_protocol import TOOLS
    schema = TOOLS["auto_plan"]["inputSchema"]
    mode_prop = schema["properties"]["mode"]
    assert set(mode_prop["enum"]) == {"improve", "absorb"}
