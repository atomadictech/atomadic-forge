"""Tier a1 — tests for the certify operational axis (CI + changelog)."""

from __future__ import annotations

from pathlib import Path

import pytest

from atomadic_forge.a1_at_functions.certify_checks import (
    certify,
    check_changelog,
    check_ci_workflow,
)

# ---------------------------------------------------------------------------
# check_ci_workflow — pure-helper tests
# ---------------------------------------------------------------------------

def test_ci_workflow_missing(tmp_path: Path) -> None:
    ok, detail = check_ci_workflow(tmp_path)
    assert ok is False
    assert detail["workflow_dir_exists"] is False
    assert detail["workflow_files"] == []


def test_ci_workflow_empty_dir(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    ok, detail = check_ci_workflow(tmp_path)
    assert ok is False
    assert detail["workflow_dir_exists"] is True
    assert detail["workflow_files"] == []


def test_ci_workflow_present_yml(tmp_path: Path) -> None:
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("name: CI\non: [push]\n", encoding="utf-8")
    ok, detail = check_ci_workflow(tmp_path)
    assert ok is True
    assert "ci.yml" in detail["workflow_files"]


def test_ci_workflow_present_yaml(tmp_path: Path) -> None:
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "release.yaml").write_text("name: release\n", encoding="utf-8")
    ok, detail = check_ci_workflow(tmp_path)
    assert ok is True
    assert "release.yaml" in detail["workflow_files"]


def test_ci_workflow_ignores_empty_files(tmp_path: Path) -> None:
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "empty.yml").write_text("", encoding="utf-8")
    ok, detail = check_ci_workflow(tmp_path)
    assert ok is False
    assert detail["workflow_files"] == []


def test_ci_workflow_ignores_non_yaml(tmp_path: Path) -> None:
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "README.md").write_text("hello", encoding="utf-8")
    ok, detail = check_ci_workflow(tmp_path)
    assert ok is False


# ---------------------------------------------------------------------------
# check_changelog — pure-helper tests
# ---------------------------------------------------------------------------

def test_changelog_missing(tmp_path: Path) -> None:
    ok, detail = check_changelog(tmp_path)
    assert ok is False
    assert detail["changelog_file"] is None
    assert detail["size_bytes"] == 0


def test_changelog_too_small(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text("# v1\n", encoding="utf-8")
    ok, detail = check_changelog(tmp_path)
    assert ok is False
    assert detail["changelog_file"] is None  # below 200-byte floor


def test_changelog_present_md(tmp_path: Path) -> None:
    body = "# Changelog\n\n## 0.1.0\n\n" + ("- entry\n" * 50)
    (tmp_path / "CHANGELOG.md").write_text(body, encoding="utf-8")
    ok, detail = check_changelog(tmp_path)
    assert ok is True
    assert detail["changelog_file"] == "CHANGELOG.md"
    assert detail["size_bytes"] >= 200


@pytest.mark.parametrize("name", [
    "CHANGELOG.rst", "CHANGELOG", "RELEASE_NOTES.md", "HISTORY.md", "NEWS.md",
])
def test_changelog_alternate_names(tmp_path: Path, name: str) -> None:
    body = "release notes\n" + ("x" * 250)
    (tmp_path / name).write_text(body, encoding="utf-8")
    ok, detail = check_changelog(tmp_path)
    assert ok is True
    assert detail["changelog_file"] == name


# ---------------------------------------------------------------------------
# certify() — operational axis integrated end-to-end
# ---------------------------------------------------------------------------

def _scaffold_pristine_pkg(tmp_path: Path) -> None:
    """Build a pristine demo package that earns the structural + runtime
    + behavioural axes.  Caller layers on .github/ + CHANGELOG.md when
    they want to test the operational axis."""
    pkg = tmp_path / "src" / "demo"
    pkg.mkdir(parents=True)
    for tier in ("a0_qk_constants", "a1_at_functions", "a2_mo_composites",
                 "a3_og_features", "a4_sy_orchestration"):
        d = pkg / tier
        d.mkdir()
        (d / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a1_at_functions" / "real.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text(
        "import demo\ndef test_x():\n    assert demo is not None\n",
        encoding="utf-8")


def test_certify_score_reaches_100_with_operational_axis(tmp_path: Path) -> None:
    """Pristine package + CI workflow + non-trivial CHANGELOG → 100/100."""
    _scaffold_pristine_pkg(tmp_path)
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("name: CI\non: [push]\n", encoding="utf-8")
    body = "# Changelog\n\n## 0.1.0\n\n" + ("- entry\n" * 50)
    (tmp_path / "CHANGELOG.md").write_text(body, encoding="utf-8")
    result = certify(tmp_path, project="demo", package="demo")
    # Score weights:
    #   structural:  35
    #   runtime:     25
    #   behavioral:  30 (1.0 pass-ratio)
    #   operational: 5 (ci) + 5 (changelog) = 10
    # Total: 100.
    assert result["score"] == 100
    assert result["ci_workflow_present"] is True
    assert result["changelog_present"] is True
    assert result["score_components"]["operational"] == 10


def test_certify_does_not_round_failed_tests_to_full_behavioral_score(tmp_path: Path) -> None:
    """Even a near-perfect test run must not receive full behavioural credit."""
    _scaffold_pristine_pkg(tmp_path)
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("name: CI\non: [push]\n", encoding="utf-8")
    body = "# Changelog\n\n## 0.1.0\n\n" + ("- entry\n" * 50)
    (tmp_path / "CHANGELOG.md").write_text(body, encoding="utf-8")
    (tmp_path / "tests" / "test_x.py").write_text(
        "import demo\n"
        "import pytest\n\n"
        "@pytest.mark.parametrize('value', range(64))\n"
        "def test_mostly_ok(value):\n"
        "    assert demo is not None\n"
        "    assert value != 63\n",
        encoding="utf-8",
    )

    result = certify(tmp_path, project="demo", package="demo")

    assert result["test_pass_ratio"] < 1.0
    assert result["score_components"]["behavioral"] == 29
    assert result["score"] == 99
    assert any("Tests failed" in issue for issue in result["issues"])


def test_certify_score_components_reports_operational_zero(tmp_path: Path) -> None:
    """Pristine package without ops axis files → score 90, operational 0."""
    _scaffold_pristine_pkg(tmp_path)
    result = certify(tmp_path, project="demo", package="demo")
    assert result["score"] == 90
    assert result["ci_workflow_present"] is False
    assert result["changelog_present"] is False
    assert result["score_components"]["operational"] == 0


def test_certify_only_ci_present_credits_5_points(tmp_path: Path) -> None:
    _scaffold_pristine_pkg(tmp_path)
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    result = certify(tmp_path, project="demo", package="demo")
    assert result["score"] == 95
    assert result["score_components"]["operational"] == 5


def test_certify_only_changelog_credits_5_points(tmp_path: Path) -> None:
    _scaffold_pristine_pkg(tmp_path)
    body = "# Changelog\n\n" + ("- entry\n" * 50)
    (tmp_path / "CHANGELOG.md").write_text(body, encoding="utf-8")
    result = certify(tmp_path, project="demo", package="demo")
    assert result["score"] == 95
    assert result["score_components"]["operational"] == 5


def test_certify_issues_recommend_ci_when_missing(tmp_path: Path) -> None:
    _scaffold_pristine_pkg(tmp_path)
    result = certify(tmp_path, project="demo", package="demo")
    assert any("CI workflow" in i for i in result["issues"])
    assert any("ci.yml" in r for r in result["recommendations"])


def test_certify_issues_recommend_changelog_when_missing(tmp_path: Path) -> None:
    _scaffold_pristine_pkg(tmp_path)
    result = certify(tmp_path, project="demo", package="demo")
    assert any("CHANGELOG" in i for i in result["issues"])
    assert any("Changelog" in r or "CHANGELOG" in r
                for r in result["recommendations"])
