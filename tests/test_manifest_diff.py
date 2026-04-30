"""Tests for atomadic_forge.a1_at_functions.manifest_diff."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from atomadic_forge.a1_at_functions.manifest_diff import diff_manifests
from atomadic_forge.a4_sy_orchestration.cli import app

# --------------------------------------------------------------------------- #
# pure-function tests
# --------------------------------------------------------------------------- #

def test_certify_score_delta_and_axis_flips() -> None:
    left = {
        "schema_version": "atomadic-forge.certify/v1",
        "score": 70,
        "documentation_complete": True,
        "tests_present": False,
        "tier_layout_present": True,
        "no_upward_imports": True,
        "test_pass_ratio": 0.5,
    }
    right = {
        "schema_version": "atomadic-forge.certify/v1",
        "score": 85,
        "documentation_complete": True,
        "tests_present": True,
        "tier_layout_present": True,
        "no_upward_imports": True,
        "test_pass_ratio": 1.0,
    }
    diff = diff_manifests(left, right)
    assert diff["schema_version"] == "atomadic-forge.diff/v1"
    assert diff["compatible"] is True
    assert diff["summary"]["score_delta"] == "+15"
    assert diff["summary"]["test_pass_ratio_delta"] == "+0.5"
    flips = diff["summary"]["axis_flips"]
    assert any(f["axis"] == "tests_present" and f["direction"] == "improved"
               for f in flips)


def test_wire_violations_delta_and_new_fixed() -> None:
    v_a = {"file": "x.py", "from_tier": "a1_at_functions",
           "to_tier": "a3_og_features", "imported": "boom"}
    v_b = {"file": "y.py", "from_tier": "a0_qk_constants",
           "to_tier": "a2_mo_composites", "imported": "thing"}
    v_c = {"file": "z.py", "from_tier": "a1_at_functions",
           "to_tier": "a4_sy_orchestration", "imported": "cli"}

    left = {
        "schema_version": "atomadic-forge.wire/v1",
        "verdict": "FAIL",
        "violation_count": 5,
        "violations": [v_a, v_b, v_c, dict(v_a, file="x2.py"),
                       dict(v_a, file="x3.py")],
    }
    right = {
        "schema_version": "atomadic-forge.wire/v1",
        "verdict": "FAIL",
        "violation_count": 3,
        # b stays, c stays, plus one fresh violation; a-trio is gone (4 fixed)
        # Net: 5 - 4 fixed + 1 new = 2 less. We want -2 delta -> count=3.
        # Reset to make math line up: keep b,c and add 1 new -> 3. Fixed=4, new=1.
        "violations": [v_b, v_c,
                       {"file": "new.py", "from_tier": "a2_mo_composites",
                        "to_tier": "a3_og_features", "imported": "fresh"}],
    }
    diff = diff_manifests(left, right)
    assert diff["summary"]["violations_delta"] == "-2"
    new_keys = {(v["file"], v["imported"]) for v in diff["summary"]["new_violations"]}
    assert ("new.py", "fresh") in new_keys
    fixed_files = {v["file"] for v in diff["summary"]["fixed_violations"]}
    assert {"x.py", "x2.py", "x3.py"}.issubset(fixed_files)


def test_scout_tier_distribution_and_symbol_count_delta() -> None:
    left = {
        "schema_version": "atomadic-forge.scout/v1",
        "symbol_count": 100,
        "tier_distribution": {"a0_qk_constants": 10, "a1_at_functions": 40,
                               "a2_mo_composites": 30, "a3_og_features": 20},
    }
    right = {
        "schema_version": "atomadic-forge.scout/v1",
        "symbol_count": 130,
        "tier_distribution": {"a0_qk_constants": 12, "a1_at_functions": 40,
                               "a2_mo_composites": 28, "a3_og_features": 50},
    }
    diff = diff_manifests(left, right)
    assert diff["summary"]["symbol_count_delta"] == "+30"
    td = diff["summary"]["tier_distribution_delta"]
    assert td["a0_qk_constants"] == "+2"
    assert td["a2_mo_composites"] == "-2"
    assert td["a3_og_features"] == "+30"
    assert "a1_at_functions" not in td  # unchanged tier omitted


def test_synergy_candidate_diff() -> None:
    left = {
        "schema_version": "atomadic-forge.synergy.scan/v1",
        "candidate_count": 2,
        "candidates": [{"candidate_id": "syn-1"}, {"candidate_id": "syn-2"}],
    }
    right = {
        "schema_version": "atomadic-forge.synergy.scan/v1",
        "candidate_count": 3,
        "candidates": [{"candidate_id": "syn-2"}, {"candidate_id": "syn-3"},
                        {"candidate_id": "syn-4"}],
    }
    diff = diff_manifests(left, right)
    assert diff["summary"]["candidate_count_delta"] == "+1"
    assert diff["summary"]["new_candidates"] == ["syn-3", "syn-4"]
    assert diff["summary"]["dropped_candidates"] == ["syn-1"]


def test_generic_fallback_for_unknown_forge_schema() -> None:
    left = {"schema_version": "atomadic-forge.weird/v1",
            "alpha": 1, "beta": [1, 2, 3], "gamma": {"x": 1}}
    right = {"schema_version": "atomadic-forge.weird/v1",
             "alpha": 2, "beta": [1, 2, 3], "delta": "new", "gamma": {"x": 2}}
    diff = diff_manifests(left, right)
    assert diff["compatible"] is True
    assert diff["summary"] == {}  # no per-schema summary
    added_paths = [a["path"] for a in diff["added"]]
    removed_paths = [r["path"] for r in diff["removed"]]
    changed_paths = [c["path"] for c in diff["changed"]]
    assert "delta" in added_paths
    assert removed_paths == []
    assert "alpha" in changed_paths
    assert "gamma.x" in changed_paths


def test_mismatched_schema_family_marks_incompatible() -> None:
    left = {"schema_version": "atomadic-forge.certify/v1", "score": 50}
    right = {"schema_version": "atomadic-forge.wire/v1",
             "violation_count": 0, "violations": [], "verdict": "PASS"}
    diff = diff_manifests(left, right)
    assert diff["compatible"] is False
    # No friendly summary, but generic walk still produces something.
    assert diff["summary"] == {}
    assert diff["added"] or diff["changed"] or diff["removed"]


def test_non_forge_json_raises_value_error() -> None:
    with pytest.raises(ValueError):
        diff_manifests({"foo": "bar"}, {"schema_version": "atomadic-forge.wire/v1"})
    with pytest.raises(ValueError):
        diff_manifests({"schema_version": "atomadic-forge.wire/v1"}, {"foo": "bar"})
    with pytest.raises(ValueError):
        diff_manifests({"schema_version": "openai.foo/v1"},
                        {"schema_version": "atomadic-forge.wire/v1"})


# --------------------------------------------------------------------------- #
# CLI smoke tests
# --------------------------------------------------------------------------- #

def test_cli_diff_happy_path(tmp_path: Path) -> None:
    runner = CliRunner()
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    left.write_text(json.dumps({
        "schema_version": "atomadic-forge.certify/v1",
        "score": 60,
        "documentation_complete": True,
    }), encoding="utf-8")
    right.write_text(json.dumps({
        "schema_version": "atomadic-forge.certify/v1",
        "score": 90,
        "documentation_complete": True,
    }), encoding="utf-8")

    result = runner.invoke(app, ["diff", str(left), str(right), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "atomadic-forge.diff/v1"
    assert payload["summary"]["score_delta"] == "+30"

    # Default human output mentions the score_delta.
    result_h = runner.invoke(app, ["diff", str(left), str(right)])
    assert result_h.exit_code == 0, result_h.output
    assert "score_delta" in result_h.output


def test_cli_diff_rejects_non_forge_input(tmp_path: Path) -> None:
    runner = CliRunner()
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    left.write_text(json.dumps({"schema_version": "atomadic-forge.wire/v1",
                                  "violation_count": 0, "violations": [],
                                  "verdict": "PASS"}), encoding="utf-8")
    # right is a plain JSON object with no schema_version.
    right.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    result = runner.invoke(app, ["diff", str(left), str(right)])
    assert result.exit_code != 0
    assert "Forge manifest" in result.output or "schema_version" in result.output
