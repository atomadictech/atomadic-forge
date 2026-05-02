"""Tests for the runtime import smoke check."""

from pathlib import Path

from atomadic_forge.a1_at_functions.import_smoke import import_smoke


def _scaffold(root: Path, package: str, body: str = "") -> None:
    pkg = root / "src" / package
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text(body, encoding="utf-8")


def test_import_smoke_passes_for_clean_package(tmp_path):
    _scaffold(tmp_path, "good", '"""Good package."""\n__version__ = "0.1"\n')
    rep = import_smoke(output_root=tmp_path, package="good")
    assert rep["importable"] is True
    assert rep["error_kind"] == ""
    assert rep["duration_ms"] >= 0


def test_import_smoke_catches_syntax_error(tmp_path):
    _scaffold(tmp_path, "bad",
              '"""bad."""\ndef broken(\n    return 1\n')
    rep = import_smoke(output_root=tmp_path, package="bad")
    assert rep["importable"] is False
    assert rep["error_kind"] in ("SyntaxError", "Other")
    assert "broken" in rep["traceback_excerpt"] or rep["traceback_excerpt"]


def test_import_smoke_catches_module_not_found(tmp_path):
    _scaffold(tmp_path, "imp_bad",
              "from nonexistent_module_42 import something\n")
    rep = import_smoke(output_root=tmp_path, package="imp_bad")
    assert rep["importable"] is False
    assert rep["error_kind"] in ("ModuleNotFoundError", "ImportError")


def test_import_smoke_handles_missing_package(tmp_path):
    rep = import_smoke(output_root=tmp_path, package="not_there")
    assert rep["importable"] is False
    assert rep["error_kind"] == "ModuleNotFoundError"


def test_import_smoke_with_tier_layout(tmp_path):
    """Confirm the realistic forge-layout package imports cleanly."""
    pkg = tmp_path / "src" / "tiered"
    for tier in ("a0_qk_constants", "a1_at_functions", "a2_mo_composites",
                 "a3_og_features", "a4_sy_orchestration"):
        d = pkg / tier
        d.mkdir(parents=True, exist_ok=True)
        (d / "__init__.py").write_text("", encoding="utf-8")
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text('"""tiered."""\n', encoding="utf-8")
    (pkg / "a1_at_functions" / "add.py").write_text(
        '"""Tier a1."""\ndef add(a, b):\n    return a + b\n', encoding="utf-8")
    rep = import_smoke(output_root=tmp_path, package="tiered")
    assert rep["importable"] is True
