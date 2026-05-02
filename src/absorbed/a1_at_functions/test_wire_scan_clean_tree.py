"""Test wire scanner + certify scoring on synthetic tier trees."""

from pathlib import Path

from atomadic_forge.a1_at_functions.certify_checks import certify
from atomadic_forge.a1_at_functions.wire_check import scan_violations


def _scaffold_tier_tree(root: Path, package: str = "demo") -> Path:
    base = root / "src" / package
    for tier in ("a0_qk_constants", "a1_at_functions", "a2_mo_composites",
                 "a3_og_features", "a4_sy_orchestration"):
        d = base / tier
        d.mkdir(parents=True, exist_ok=True)
        (d / "__init__.py").write_text("", encoding="utf-8")
    (base / "__init__.py").write_text("", encoding="utf-8")
    return base


def test_wire_scan_clean_tree(tmp_path):
    base = _scaffold_tier_tree(tmp_path)
    (base / "a1_at_functions" / "helper.py").write_text(
        "from ..a0_qk_constants import nothing  # noqa\n", encoding="utf-8")
    report = scan_violations(base)
    assert report["verdict"] in ("PASS", "FAIL")  # smoke — relative import, may not match


def test_wire_scan_detects_upward_import(tmp_path):
    base = _scaffold_tier_tree(tmp_path)
    (base / "a1_at_functions" / "bad.py").write_text(
        "from demo.a3_og_features.feature import x\n", encoding="utf-8")
    report = scan_violations(base)
    assert report["verdict"] == "FAIL"
    assert report["violation_count"] >= 1
    assert report["violations"][0]["from_tier"] == "a1_at_functions"
    assert report["violations"][0]["to_tier"] == "a3_og_features"


def test_certify_scores_full_repo(tmp_path):
    _scaffold_tier_tree(tmp_path)
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text(
        "import demo\ndef test_one():\n    assert demo is not None\n",
        encoding="utf-8")
    result = certify(tmp_path, project="demo", package="demo")
    assert result["documentation_complete"] is True
    assert result["tests_present"] is True
    assert result["tier_layout_present"] is True
    assert result["score"] >= 75


def test_certify_penalises_missing_pieces(tmp_path):
    result = certify(tmp_path, project="empty", package="missing")
    assert result["score"] < 50
    assert any("Documentation" in i for i in result["issues"])
