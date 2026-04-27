"""Tests for the round-0 scaffolders (pyproject + README + tests dir)."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest

from atomadic_forge.a1_at_functions.scaffold_pyproject import render_pyproject
from atomadic_forge.a1_at_functions.scaffold_starter import (
    render_gitignore, render_readme, render_tests_conftest, render_tests_init,
)
from atomadic_forge.a1_at_functions.llm_client import StubLLMClient
from atomadic_forge.a3_og_features.forge_loop import run_iterate


def test_pyproject_parses_as_valid_toml():
    src = render_pyproject(package="demo", description="my pkg")
    data = tomllib.loads(src)
    assert data["project"]["name"] == "demo"
    assert data["project"]["readme"] == "README.md"
    assert "build-system" in data


def test_pyproject_emits_console_script_when_target_given():
    src = render_pyproject(
        package="demo",
        console_script_target="a4_sy_orchestration.cli:main",
    )
    data = tomllib.loads(src)
    assert data["project"]["scripts"]["demo"] == "demo.a4_sy_orchestration.cli:main"


def test_pyproject_omits_scripts_when_no_target():
    src = render_pyproject(package="demo")
    data = tomllib.loads(src)
    assert "scripts" not in data.get("project", {})


def test_pyproject_includes_setuptools_packages_find():
    src = render_pyproject(package="demo")
    data = tomllib.loads(src)
    assert data["tool"]["setuptools"]["packages"]["find"]["where"] == ["src"]


def test_readme_includes_intent_and_tier_table():
    md = render_readme(package="demo", intent="A test project")
    assert "# demo" in md
    assert "A test project" in md
    assert "a0_qk_constants" in md
    assert "a4_sy_orchestration" in md


def test_gitignore_excludes_atomadic_dir():
    gi = render_gitignore()
    assert ".atomadic-forge/" in gi
    assert "__pycache__/" in gi


def test_conftest_adds_src_to_sys_path():
    cf = render_tests_conftest(package="demo")
    assert "sys.path.insert" in cf
    assert "SRC = ROOT / 'src'" in cf


def test_iterate_round0_scaffolds_full_package(tmp_path):
    """End-to-end: run_iterate with a stub LLM should leave a complete
    pip-installable package scaffold even if the LLM emits nothing."""
    output = tmp_path / "out"
    output.mkdir()
    llm = StubLLMClient(canned=["[]"])
    run_iterate(
        "build a thing",
        output=output,
        package="thing",
        llm=llm,
        max_iterations=1,
        target_score=200.0,  # never converge — force full setup
    )
    # All scaffolds present and parseable.
    assert (output / "pyproject.toml").exists()
    assert (output / "README.md").exists()
    assert (output / ".gitignore").exists()
    assert (output / "tests" / "__init__.py").exists()
    assert (output / "tests" / "conftest.py").exists()
    # Tier dirs.
    for tier in ("a0_qk_constants", "a1_at_functions", "a2_mo_composites",
                 "a3_og_features", "a4_sy_orchestration"):
        assert (output / "src" / "thing" / tier / "__init__.py").exists()
    # pyproject parses + has the expected metadata.
    data = tomllib.loads((output / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "thing"


def test_iterate_does_not_clobber_existing_scaffolds(tmp_path):
    """Re-running iterate must NOT overwrite a hand-improved README."""
    output = tmp_path / "out"
    output.mkdir()
    (output / "README.md").write_text("# my custom README\n", encoding="utf-8")
    run_iterate(
        "thing",
        output=output,
        package="thing",
        llm=StubLLMClient(canned=["[]"]),
        max_iterations=1,
        target_score=200.0,
    )
    assert "my custom README" in (output / "README.md").read_text(encoding="utf-8")
