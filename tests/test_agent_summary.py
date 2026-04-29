"""Tier verification — Codex feedback: agent-native blocker summary.

Codex's review of the earlier Forge release named the gap explicitly:
'agents thrive on "here are the 2 things blocking release" more than
huge manifests'. This module + the --summary CLI flag + the new
forge://summary/blockers MCP resource are the response.

These tests pin:
  * the contract (schema_version, fields, ranking order)
  * the deterministic ranking under fixed inputs
  * --summary on forge wire / forge certify produces only the
    compact form (back-compat: --json without --summary unchanged)
  * MCP tools/call results carry a non-null _summary alongside the
    full content payload
  * the new forge://summary/blockers resource serves the same shape
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer.testing

from atomadic_forge.a1_at_functions.agent_summary import (
    render_summary_text,
    summarize_blockers,
)
from atomadic_forge.a1_at_functions.mcp_protocol import dispatch_request
from atomadic_forge.a4_sy_orchestration.cli import app

runner = typer.testing.CliRunner()


_WIRE_FAIL_A1_TO_A3 = {
    "schema_version": "atomadic-forge.wire/v1",
    "verdict": "FAIL",
    "violation_count": 2,
    "auto_fixable": 0,
    "violations": [
        {"file": "a1_at_functions/h.py",
         "from_tier": "a1_at_functions",
         "to_tier": "a3_og_features",
         "imported": "F", "language": "python", "f_code": "F0042",
         "proposed_fix": ""},
        {"file": "a1_at_functions/h.py",
         "from_tier": "a1_at_functions",
         "to_tier": "a3_og_features",
         "imported": "G", "language": "python", "f_code": "F0042",
         "proposed_fix": ""},
    ],
}

_CERTIFY_THREE_AXES_FAIL = {
    "schema_version": "atomadic-forge.certify/v1",
    "score": 25.0,
    "documentation_complete": False,
    "tests_present": False,
    "tier_layout_present": True,
    "no_upward_imports": False,
    "issues": [],
}


# ---- pure summary contract ---------------------------------------------

def test_summary_schema_version_pinned():
    s = summarize_blockers(certify_report=_CERTIFY_THREE_AXES_FAIL)
    assert s["schema_version"] == "atomadic-forge.summary/v1"


def test_summary_required_fields():
    s = summarize_blockers(wire_report=_WIRE_FAIL_A1_TO_A3,
                            certify_report=_CERTIFY_THREE_AXES_FAIL)
    for f in ("schema_version", "verdict", "score", "blocker_count",
              "auto_fixable_count", "blockers", "next_command"):
        assert f in s, f"summary missing required field {f!r}"


def test_summary_blocker_count_reflects_full_set_not_top_n():
    s = summarize_blockers(
        certify_report={
            "documentation_complete": False,
            "tests_present": False,
            "tier_layout_present": False,
            "no_upward_imports": False,
            "score": 0.0,
        },
        top_n=2,
    )
    assert s["blocker_count"] == 4
    assert len(s["blockers"]) == 2


def test_summary_top_n_must_be_positive():
    with pytest.raises(ValueError):
        summarize_blockers(top_n=0)


def test_summary_clean_repo_no_blockers():
    s = summarize_blockers(
        wire_report={"verdict": "PASS", "violation_count": 0,
                      "auto_fixable": 0, "violations": []},
        certify_report={
            "documentation_complete": True, "tests_present": True,
            "tier_layout_present": True, "no_upward_imports": True,
            "score": 100.0,
        },
    )
    assert s["verdict"] == "PASS"
    assert s["blocker_count"] == 0
    assert "PASS" in s["next_command"] or "no blockers" in s["next_command"].lower() \
        or "already" in s["next_command"].lower()


# ---- ranking determinism -----------------------------------------------

def test_summary_ranks_auto_fixable_first():
    """When mixing F0042 (auto_fixable) with F0040 (not auto_fixable),
    the auto_fixable blocker must come first."""
    wire = {
        "schema_version": "atomadic-forge.wire/v1",
        "verdict": "FAIL", "violation_count": 2, "auto_fixable": 0,
        "violations": [
            {"file": "a0_qk_constants/c.py",
             "from_tier": "a0_qk_constants",
             "to_tier": "a3_og_features",
             "imported": "F", "language": "python", "f_code": "F0040",
             "proposed_fix": ""},
            {"file": "a1_at_functions/h.py",
             "from_tier": "a1_at_functions",
             "to_tier": "a3_og_features",
             "imported": "F", "language": "python", "f_code": "F0042",
             "proposed_fix": ""},
        ],
    }
    s = summarize_blockers(wire_report=wire)
    fcodes = [b["f_code"] for b in s["blockers"]]
    f42_idx = fcodes.index("F0042")
    f40_idx = fcodes.index("F0040")
    assert f42_idx < f40_idx, (
        f"auto_fixable F0042 must rank above F0040 (got {fcodes})"
    )


def test_summary_groups_repeat_violations_by_fcode():
    """Two F0042 violations of the same file collapse into ONE
    blocker with occurrences=2; the agent gets a clean list, not
    duplicated noise."""
    s = summarize_blockers(wire_report=_WIRE_FAIL_A1_TO_A3)
    f42 = next(b for b in s["blockers"] if b["f_code"] == "F0042")
    assert f42["occurrences"] == 2


def test_summary_next_command_is_first_blocker_command():
    s = summarize_blockers(wire_report=_WIRE_FAIL_A1_TO_A3)
    assert s["next_command"] == s["blockers"][0]["next_command"]


# ---- text rendering ----------------------------------------------------

def test_render_summary_text_contains_verdict_and_blockers():
    s = summarize_blockers(certify_report=_CERTIFY_THREE_AXES_FAIL)
    text = render_summary_text(s)
    assert "FAIL" in text
    assert "F0050" in text or "F0051" in text
    assert "NEXT:" in text


def test_render_summary_text_width_validation():
    s = summarize_blockers(certify_report=_CERTIFY_THREE_AXES_FAIL)
    with pytest.raises(ValueError):
        render_summary_text(s, width=20)


def test_render_summary_text_caps_long_titles():
    """The blocker title + command lines must fit within width;
    the verdict header may be slightly wider (it's a single line of
    short fixed labels)."""
    s = summarize_blockers(certify_report=_CERTIFY_THREE_AXES_FAIL)
    text = render_summary_text(s, width=40)
    for line in text.splitlines():
        # Blocker rows start with " 1." / " 2." or "    →" — those
        # MUST be trimmed to width+5.
        if line.lstrip().startswith(("1.", "2.", "3.", "4.", "5.")) or \
                line.lstrip().startswith("→"):
            assert len(line) <= 40 + 5, f"blocker line too wide: {line}"


# ---- CLI: --summary on wire and certify --------------------------------

def test_cli_wire_summary_outputs_compact_json(tmp_path):
    pkg = tmp_path / "pkg"
    a1 = pkg / "a1_at_functions"; a1.mkdir(parents=True)
    a3 = pkg / "a3_og_features"; a3.mkdir(parents=True)
    (a3 / "feat.py").write_text(
        '"""a3."""\nclass F:\n    pass\n', encoding="utf-8")
    (a1 / "h.py").write_text(
        "from ..a3_og_features.feat import F\n", encoding="utf-8")
    result = runner.invoke(app, ["wire", str(pkg), "--summary", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["schema_version"] == "atomadic-forge.summary/v1"
    assert data["blocker_count"] >= 1
    assert any(b["f_code"] == "F0042" for b in data["blockers"])


def test_cli_wire_summary_human_renders_compactly(tmp_path):
    pkg = tmp_path / "pkg"
    a1 = pkg / "a1_at_functions"; a1.mkdir(parents=True)
    a3 = pkg / "a3_og_features"; a3.mkdir(parents=True)
    (a3 / "feat.py").write_text(
        '"""a3."""\nclass F:\n    pass\n', encoding="utf-8")
    (a1 / "h.py").write_text(
        "from ..a3_og_features.feat import F\n", encoding="utf-8")
    result = runner.invoke(app, ["wire", str(pkg), "--summary"])
    assert result.exit_code == 0
    out = result.stdout
    # Compact: no full violation list, but verdict + F-code + NEXT line.
    assert "FAIL" in out
    assert "F0042" in out
    assert "NEXT:" in out
    # No giant JSON manifest leaked through.
    assert '"violations":' not in out


def test_cli_certify_summary_pairs_wire(tmp_path):
    """--summary on certify pulls wire+certify in one shot — exactly
    what Codex asked for ('one compact answer')."""
    result = runner.invoke(app, ["certify", str(tmp_path),
                                  "--summary", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["schema_version"] == "atomadic-forge.summary/v1"
    # Empty repo: certify will fail every axis -> blockers populated.
    assert data["blocker_count"] >= 1
    assert any(b["f_code"] in {"F0050", "F0051", "F0052"}
               for b in data["blockers"])


def test_cli_wire_without_summary_unchanged(tmp_path):
    """--json without --summary still emits the full wire/v1 schema —
    backward compatibility for existing CI consumers."""
    pkg = tmp_path / "clean"
    a1 = pkg / "a1_at_functions"; a1.mkdir(parents=True)
    (a1 / "ok.py").write_text("def ok(): return 1\n", encoding="utf-8")
    result = runner.invoke(app, ["wire", str(pkg), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["schema_version"] == "atomadic-forge.wire/v1"
    assert "blockers" not in data


# ---- MCP: _summary on tool results + new resource ----------------------

def test_mcp_tools_call_wire_attaches_summary(tmp_path):
    pkg = tmp_path / "pkg"
    a1 = pkg / "a1_at_functions"; a1.mkdir(parents=True)
    a3 = pkg / "a3_og_features"; a3.mkdir(parents=True)
    (a3 / "feat.py").write_text(
        '"""a3."""\nclass F:\n    pass\n', encoding="utf-8")
    (a1 / "h.py").write_text(
        "from ..a3_og_features.feat import F\n", encoding="utf-8")
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "wire", "arguments": {"source": str(pkg)}}},
        project_root=tmp_path,
    )
    result = resp["result"]
    # Top-level _summary field on every tool result that carries
    # an addressable schema_version.
    assert "_summary" in result
    summary = result["_summary"]
    assert summary["schema_version"] == "atomadic-forge.summary/v1"
    assert summary["blocker_count"] >= 1
    # Content envelope has TWO text blocks: full + summary.
    assert len(result["content"]) == 2
    assert "_summary:" in result["content"][1]["text"]


def test_mcp_tools_call_certify_attaches_summary(tmp_path):
    """certify (without emit_receipt) returns a CertifyResult; the
    dispatcher must derive a summary for it."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "certify",
                    "arguments": {"project_root": str(pkg)}}},
        project_root=tmp_path,
    )
    summary = resp["result"]["_summary"]
    assert summary is not None
    assert summary["blocker_count"] >= 1


def test_mcp_summary_blockers_resource(tmp_path):
    """forge://summary/blockers resource — Codex's 'first call agents
    should make' surface."""
    pkg = tmp_path / "pkg"
    a1 = pkg / "a1_at_functions"; a1.mkdir(parents=True)
    a3 = pkg / "a3_og_features"; a3.mkdir(parents=True)
    (a3 / "feat.py").write_text(
        '"""a3."""\nclass F:\n    pass\n', encoding="utf-8")
    (a1 / "h.py").write_text(
        "from ..a3_og_features.feat import F\n", encoding="utf-8")
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "resources/read",
         "params": {"uri": "forge://summary/blockers"}},
        project_root=pkg,
    )
    contents = resp["result"]["contents"]
    body = json.loads(contents[0]["text"])
    assert body["schema_version"] == "atomadic-forge.summary/v1"
    assert body["blocker_count"] >= 1


def test_mcp_recon_result_has_no_summary(tmp_path):
    """Recon doesn't carry blockers, just inventory — the dispatcher
    should NOT invent a summary for it. _summary present but None."""
    a1 = tmp_path / "a1_at_functions"; a1.mkdir()
    (a1 / "ok.py").write_text("def ok(): return 1\n", encoding="utf-8")
    resp = dispatch_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "recon", "arguments": {"target": str(tmp_path)}}},
        project_root=tmp_path,
    )
    assert resp["result"]["_summary"] is None
    # Content envelope falls back to a single text block.
    assert len(resp["result"]["content"]) == 1
