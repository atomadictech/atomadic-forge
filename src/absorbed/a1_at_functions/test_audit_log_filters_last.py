"""Tier verification — Lane D1: forge audit list/show/log.

Covers the pure lineage_reader and the three CLI subcommands. Each
test seeds .atomadic-forge/lineage.jsonl and the corresponding
manifest files in a tmp_path, then asserts the verb output.
"""
from __future__ import annotations

import json
from pathlib import Path

import typer.testing

from atomadic_forge.a1_at_functions.lineage_reader import (
    lineage_path,
    list_artifacts,
    load_manifest,
    read_lineage,
)
from atomadic_forge.a2_mo_composites.manifest_store import ManifestStore
from atomadic_forge.a4_sy_orchestration.cli import app

runner = typer.testing.CliRunner()


def _seed(project: Path) -> None:
    """Drop a small lineage history under .atomadic-forge/."""
    store = ManifestStore(project)
    store.save("scout", {"schema_version": "atomadic-forge.scout/v1",
                          "symbol_count": 12,
                          "tier_distribution": {"a1_at_functions": 12}})
    store.save("cherry", {"schema_version": "atomadic-forge.cherry/v1",
                           "items": [{"name": "x"}, {"name": "y"}]})
    store.save("certify", {"schema_version": "atomadic-forge.certify/v1",
                            "score": 75,
                            "documentation_complete": True,
                            "tests_present": True,
                            "tier_layout_present": True,
                            "no_upward_imports": True,
                            "issues": []})
    # Re-save scout to give it run_count == 2 in summaries.
    store.save("scout", {"schema_version": "atomadic-forge.scout/v1",
                          "symbol_count": 14,
                          "tier_distribution": {"a1_at_functions": 14}})


# ---- pure-function tests -----------------------------------------------

def test_lineage_path_resolves(tmp_path):
    p = lineage_path(tmp_path)
    assert p.name == "lineage.jsonl"
    assert p.parent.name == ".atomadic-forge"


def test_read_lineage_empty(tmp_path):
    assert read_lineage(tmp_path) == []


def test_read_lineage_skips_corrupt_lines(tmp_path):
    lineage_dir = tmp_path / ".atomadic-forge"
    lineage_dir.mkdir()
    log = lineage_dir / "lineage.jsonl"
    log.write_text(
        '{"ts_utc":"2026-01-01T00:00:00+00:00","artifact":"scout","path":"x"}\n'
        "this-is-not-json\n"
        '{"ts_utc":"2026-01-02T00:00:00+00:00","artifact":"wire","path":"y"}\n',
        encoding="utf-8",
    )
    entries = read_lineage(tmp_path)
    assert len(entries) == 2
    assert {e["artifact"] for e in entries} == {"scout", "wire"}


def test_read_lineage_last(tmp_path):
    _seed(tmp_path)
    entries = read_lineage(tmp_path)
    assert len(entries) == 4
    last2 = read_lineage(tmp_path, last=2)
    assert len(last2) == 2
    assert last2[-1]["artifact"] == "scout"  # the second scout save


def test_list_artifacts_groups_and_counts(tmp_path):
    _seed(tmp_path)
    summaries = list_artifacts(tmp_path)
    by_name = {s["artifact"]: s for s in summaries}
    assert set(by_name.keys()) == {"scout", "cherry", "certify"}
    assert by_name["scout"]["run_count"] == 2
    assert by_name["cherry"]["run_count"] == 1


def test_load_manifest_round_trip(tmp_path):
    _seed(tmp_path)
    scout = load_manifest(tmp_path, "scout")
    assert scout is not None
    assert scout["schema_version"] == "atomadic-forge.scout/v1"
    # Re-save with later content overwrites — load returns the latest.
    assert scout["symbol_count"] == 14


def test_load_manifest_missing(tmp_path):
    _seed(tmp_path)
    assert load_manifest(tmp_path, "definitely-not-a-real-artifact") is None


# ---- CLI tests ----------------------------------------------------------

def test_audit_list_human(tmp_path):
    _seed(tmp_path)
    result = runner.invoke(app, ["audit", "list", str(tmp_path)])
    assert result.exit_code == 0
    assert "Forge audit — artifacts" in result.stdout
    assert "scout" in result.stdout and "runs=2" in result.stdout
    assert "certify" in result.stdout
    assert "3 distinct artifact" in result.stdout


def test_audit_list_json(tmp_path):
    _seed(tmp_path)
    result = runner.invoke(app, ["audit", "list", str(tmp_path), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["schema_version"] == "atomadic-forge.audit.list/v1"
    assert data["artifact_count"] == 3
    assert any(a["artifact"] == "scout" and a["run_count"] == 2
               for a in data["artifacts"])


def test_audit_list_empty(tmp_path):
    result = runner.invoke(app, ["audit", "list", str(tmp_path)])
    assert result.exit_code == 0
    assert "No lineage found" in result.stdout


def test_audit_show_human(tmp_path):
    _seed(tmp_path)
    result = runner.invoke(app, ["audit", "show", str(tmp_path), "certify"])
    assert result.exit_code == 0
    assert "atomadic-forge.certify/v1" in result.stdout
    assert "score: 75" in result.stdout


def test_audit_show_json(tmp_path):
    _seed(tmp_path)
    result = runner.invoke(app, ["audit", "show", str(tmp_path), "scout", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["schema_version"] == "atomadic-forge.scout/v1"
    assert data["symbol_count"] == 14


def test_audit_show_missing_uses_hint(tmp_path):
    _seed(tmp_path)
    result = runner.invoke(app, ["audit", "show", str(tmp_path), "ghost"])
    assert result.exit_code != 0
    out = result.stdout + (result.stderr or "")
    assert "not a Forge JSON manifest" in out


def test_audit_log_filters_last(tmp_path):
    _seed(tmp_path)
    result = runner.invoke(
        app, ["audit", "log", str(tmp_path), "--last", "2", "--json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["entry_count"] == 2
    # Most recent two saves were certify, then scout (re-save).
    assert data["entries"][-1]["artifact"] == "scout"
