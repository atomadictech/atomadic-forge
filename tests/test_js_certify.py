"""Certify scoring honours JS/TS layout and JS test conventions."""

from pathlib import Path

from atomadic_forge.a1_at_functions.certify_checks import (
    certify, check_tests_present, check_tier_layout,
)


def test_check_tests_present_recognises_js_test(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "cognition.test.js").write_text(
        "import { test } from 'node:test';\n", encoding="utf-8")
    ok, detail = check_tests_present(tmp_path)
    assert ok is True
    assert detail["javascript_tests"] == 1


def test_check_tests_present_recognises_ts_spec(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "store.spec.ts").write_text("", encoding="utf-8")
    ok, detail = check_tests_present(tmp_path)
    assert ok is True
    assert detail["javascript_tests"] >= 1


def test_check_tests_present_jest_dunder(tmp_path):
    (tmp_path / "src" / "__tests__").mkdir(parents=True)
    (tmp_path / "src" / "__tests__" / "math.js").write_text("",
                                                              encoding="utf-8")
    ok, detail = check_tests_present(tmp_path)
    assert ok is True


def test_check_tier_layout_polyglot_tier_dirs(tmp_path):
    # JS-style top-level tier dirs (no Python src/<pkg>/ form)
    for tier in ("a0_qk_constants", "a1_at_functions", "a4_sy_orchestration"):
        (tmp_path / tier).mkdir()
    ok, detail = check_tier_layout(tmp_path)
    assert ok is True
    assert detail["tiers_present_count"] >= 3


def test_check_tier_layout_specific_failure_reason(tmp_path):
    (tmp_path / "a1_at_functions").mkdir()
    ok, detail = check_tier_layout(tmp_path)
    assert ok is False
    assert detail["tiers_present_count"] == 1
    assert detail["tiers_required"] == 3


def test_certify_passes_for_js_repo_with_tests_and_tiers(tmp_path):
    for tier in ("a0_qk_constants", "a1_at_functions", "a4_sy_orchestration"):
        (tmp_path / tier).mkdir()
    (tmp_path / "README.md").write_text("# js project\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "smoke.test.js").write_text(
        "import { test } from 'node:test';\ntest('ok', () => {});\n",
        encoding="utf-8",
    )
    result = certify(tmp_path, project="jsproject")
    assert result["documentation_complete"] is True
    assert result["tests_present"] is True
    assert result["tier_layout_present"] is True


def test_certify_layout_failure_message_specific(tmp_path):
    (tmp_path / "a1_at_functions").mkdir()
    (tmp_path / "README.md").write_text("# x\n", encoding="utf-8")
    result = certify(tmp_path, project="x")
    assert result["tier_layout_present"] is False
    layout_issues = [i for i in result["issues"] if "Tier layout" in i]
    assert layout_issues
    assert "found 1 tier" in layout_issues[0]
    assert "need 3" in layout_issues[0]
