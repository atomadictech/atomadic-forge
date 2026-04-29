"""Tests for the behavioral pytest runner — the breakthrough check."""

from __future__ import annotations

from pathlib import Path

from atomadic_forge.a1_at_functions.test_runner import run_pytest


def _scaffold(tmp_path: Path, package: str = "demo") -> Path:
    pkg = tmp_path / "src" / package
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    return tmp_path


def test_no_tests_dir_returns_did_not_run(tmp_path):
    _scaffold(tmp_path)
    rep = run_pytest(output_root=tmp_path, package="demo")
    assert rep["ran"] is False
    assert rep["passed"] == 0
    assert rep["pass_ratio"] == 0.0


def test_runs_passing_tests_and_credits_full_ratio(tmp_path):
    root = _scaffold(tmp_path)
    pkg = root / "src" / "demo"
    (pkg / "add.py").write_text("def add(a, b):\n    return a + b\n",
                                  encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("", encoding="utf-8")
    (tests / "conftest.py").write_text(
        "import sys\nfrom pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))\n",
        encoding="utf-8")
    (tests / "test_add.py").write_text(
        "from demo.add import add\n"
        "def test_add(): assert add(2, 3) == 5\n",
        encoding="utf-8")
    rep = run_pytest(output_root=root, package="demo")
    assert rep["ran"] is True
    assert rep["passed"] == 1
    assert rep["failed"] == 0
    assert rep["pass_ratio"] == 1.0


def test_runner_ignores_parent_pytest_addopts(tmp_path):
    parent = tmp_path / "parent"
    parent.mkdir()
    (parent / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\naddopts = '-q'\n",
        encoding="utf-8",
    )
    root = _scaffold(parent / "generated")
    pkg = root / "src" / "demo"
    (pkg / "add.py").write_text("def add(a, b):\n    return a + b\n",
                                  encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_add.py").write_text(
        "from demo.add import add\n"
        "def test_add(): assert add(2, 3) == 5\n",
        encoding="utf-8",
    )

    rep = run_pytest(output_root=root, package="demo")

    assert rep["ran"] is True
    assert rep["passed"] == 1
    assert rep["pass_ratio"] == 1.0


def test_catches_failing_tests(tmp_path):
    """The breakthrough behavior: identity-function stubs fail real tests."""
    root = _scaffold(tmp_path)
    pkg = root / "src" / "demo"
    # Identity-function stub — gamed wire and import in earlier refines.
    (pkg / "uppercase.py").write_text(
        "def uppercase(text):\n    return text\n",
        encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("", encoding="utf-8")
    (tests / "conftest.py").write_text(
        "import sys\nfrom pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))\n",
        encoding="utf-8")
    (tests / "test_uppercase.py").write_text(
        "from demo.uppercase import uppercase\n"
        "def test_uppercase():\n    assert uppercase('hi') == 'HI'\n",
        encoding="utf-8")
    rep = run_pytest(output_root=root, package="demo")
    assert rep["ran"] is True
    assert rep["passed"] == 0
    assert rep["failed"] == 1
    assert rep["pass_ratio"] == 0.0
    # The failure should be visible in the summary
    assert "FAIL" in rep["pytest_summary"].upper() or rep["failure_excerpts"]


def test_partial_pass_ratio(tmp_path):
    root = _scaffold(tmp_path)
    pkg = root / "src" / "demo"
    (pkg / "ops.py").write_text(
        "def add(a, b): return a + b\n"
        "def sub(a, b): return a + b\n",  # bug — should be a - b
        encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("", encoding="utf-8")
    (tests / "conftest.py").write_text(
        "import sys\nfrom pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))\n",
        encoding="utf-8")
    (tests / "test_ops.py").write_text(
        "from demo.ops import add, sub\n"
        "def test_add(): assert add(2,3) == 5\n"
        "def test_sub(): assert sub(5,3) == 2\n",
        encoding="utf-8")
    rep = run_pytest(output_root=root, package="demo")
    assert rep["passed"] == 1
    assert rep["failed"] == 1
    assert rep["pass_ratio"] == 0.5
