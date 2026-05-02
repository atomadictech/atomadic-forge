"""Tier verification — Lane D2: forge wire --suggest-repairs.

Pure-function and CLI-end coverage of the repair-suggestion mode added
to scan_violations. The function itself is pure (no I/O beyond the
package walk that was already there); these tests build synthesized
illegal trees in a tmp_path and assert the suggestion shape.
"""
from __future__ import annotations

import json
from pathlib import Path

import typer.testing

from atomadic_forge.a1_at_functions.wire_check import (
    scan_violations,
    suggest_fix_for_violation,
)
from atomadic_forge.a4_sy_orchestration.cli import app

runner = typer.testing.CliRunner()


def _make_a1_to_a2_violation(tmp_path: Path) -> Path:
    """Build a tiny tier tree with one illegal a1 -> a2 import."""
    pkg = tmp_path / "pkg"
    a1 = pkg / "a1_at_functions"
    a2 = pkg / "a2_mo_composites"
    a1.mkdir(parents=True)
    a2.mkdir(parents=True)
    (a2 / "store.py").write_text(
        '"""a2 store."""\nclass Store:\n    pass\n', encoding="utf-8")
    (a1 / "helper.py").write_text(
        '"""a1 helper with illegal upward import."""\n'
        "from ..a2_mo_composites.store import Store\n\n"
        "def use(s: Store):\n    return s\n",
        encoding="utf-8",
    )
    return pkg


def test_suggest_fix_for_violation_pure_function():
    """suggest_fix_for_violation is a pure transformer over a violation dict."""
    v = {
        "file": "a1_at_functions/helper.py",
        "from_tier": "a1_at_functions",
        "to_tier": "a2_mo_composites",
        "imported": "Store",
        "language": "python",
    }
    enriched = suggest_fix_for_violation(v)
    assert enriched["auto_fixable"] is True
    assert enriched["proposed_action"] == "move_file_up"
    assert enriched["proposed_destination"] == "a2_mo_composites"
    assert "mv" in enriched["fix_command"]
    assert "Store" in enriched["reasoning"]


def test_suggest_fix_for_violation_unrecognised_tier():
    v = {
        "file": "weird/foo.py",
        "from_tier": "not_a_tier",
        "to_tier": "a2_mo_composites",
        "imported": "X",
        "language": "python",
    }
    enriched = suggest_fix_for_violation(v)
    assert enriched["auto_fixable"] is False
    assert enriched["proposed_action"] == "review_manually"


def test_scan_violations_no_suggest_keeps_v1_schema(tmp_path):
    """Default scan_violations keeps the original v1 schema unchanged."""
    pkg = _make_a1_to_a2_violation(tmp_path)
    report = scan_violations(pkg)
    assert report["schema_version"] == "atomadic-forge.wire/v1"
    assert report["auto_fixable"] == 0
    assert "repair_suggestions" not in report
    # Existing fields are still there.
    assert report["violation_count"] >= 1
    assert report["verdict"] == "FAIL"


def test_scan_violations_with_suggest_repairs(tmp_path):
    pkg = _make_a1_to_a2_violation(tmp_path)
    report = scan_violations(pkg, suggest_repairs=True)
    assert report["auto_fixable"] >= 1
    assert "repair_suggestions" in report
    suggestions = report["repair_suggestions"]
    assert len(suggestions) >= 1
    s = suggestions[0]
    assert s["proposed_destination"] == "a2_mo_composites"
    assert s["proposed_action"] == "move_file_up"
    # Each violation now has the proposed_fix string populated.
    for v in report["violations"]:
        assert v.get("proposed_action") in {"move_file_up", "review_manually"}
        # The original v1 'proposed_fix' empty string is replaced.
        assert v["proposed_fix"]


def test_scan_violations_clean_tree_no_suggestions(tmp_path):
    """A clean tier tree has nothing to suggest."""
    pkg = tmp_path / "clean"
    a1 = pkg / "a1_at_functions"
    a1.mkdir(parents=True)
    (a1 / "ok.py").write_text(
        '"""pure helper."""\ndef ok(x):\n    return x\n', encoding="utf-8")
    report = scan_violations(pkg, suggest_repairs=True)
    assert report["verdict"] == "PASS"
    assert report["violation_count"] == 0
    assert report["auto_fixable"] == 0
    assert report.get("repair_suggestions") == []


def test_cli_wire_suggest_repairs_json(tmp_path):
    """forge wire --suggest-repairs --json populates the new fields."""
    pkg = _make_a1_to_a2_violation(tmp_path)
    result = runner.invoke(
        app, ["wire", str(pkg), "--suggest-repairs", "--json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["auto_fixable"] >= 1
    assert "repair_suggestions" in data
    assert any(v.get("proposed_destination") == "a2_mo_composites"
               for v in data["violations"])


def test_cli_wire_suggest_repairs_human(tmp_path):
    """Human output mentions the repair plan and the destination tier."""
    pkg = _make_a1_to_a2_violation(tmp_path)
    result = runner.invoke(app, ["wire", str(pkg), "--suggest-repairs"])
    assert result.exit_code == 0
    assert "auto-fixable" in result.stdout
    assert "Repair plan" in result.stdout
    assert "a2_mo_composites" in result.stdout


def test_cli_wire_suggest_repairs_combines_with_fail_on_violations(tmp_path):
    """--suggest-repairs and --fail-on-violations stack; exit 1 on FAIL."""
    pkg = _make_a1_to_a2_violation(tmp_path)
    result = runner.invoke(
        app, ["wire", str(pkg), "--suggest-repairs", "--fail-on-violations"]
    )
    assert result.exit_code == 1
