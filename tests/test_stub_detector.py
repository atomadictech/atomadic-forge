"""Tests for the stub-body detector + certify integration."""

from pathlib import Path

from atomadic_forge.a1_at_functions.certify_checks import certify
from atomadic_forge.a1_at_functions.stub_detector import (
    detect_stubs, detect_stubs_in_file, stub_penalty,
)


def _write(p: Path, body: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def test_detects_pass_only_function(tmp_path):
    _write(tmp_path / "f.py", "def foo():\n    pass\n")
    findings = detect_stubs_in_file(tmp_path / "f.py", repo_root=tmp_path)
    assert any(f["kind"] == "pass_only" and f["qualname"] == "foo"
               for f in findings)


def test_detects_not_implemented(tmp_path):
    _write(tmp_path / "f.py",
           "def bar():\n    raise NotImplementedError()\n")
    findings = detect_stubs_in_file(tmp_path / "f.py", repo_root=tmp_path)
    assert any(f["kind"] == "not_implemented" for f in findings)


def test_detects_todo_marker(tmp_path):
    _write(tmp_path / "f.py",
           'def baz(x):\n    # TODO: implement\n    return x\n')
    findings = detect_stubs_in_file(tmp_path / "f.py", repo_root=tmp_path)
    assert any(f["kind"] == "todo_marker" for f in findings)


def test_detects_implement_me_comment(tmp_path):
    """Regression: codellama emitted `# Implement me!` literally."""
    _write(tmp_path / "f.py",
           "def slug():\n    # Implement me!\n    pass\n")
    findings = detect_stubs_in_file(tmp_path / "f.py", repo_root=tmp_path)
    kinds = {f["kind"] for f in findings}
    assert kinds & {"pass_only", "todo_marker"}


def test_does_not_flag_real_function(tmp_path):
    _write(tmp_path / "f.py",
           '"""real."""\ndef add(a, b):\n    """sum."""\n    return a + b\n')
    findings = detect_stubs_in_file(tmp_path / "f.py", repo_root=tmp_path)
    assert findings == []


def test_does_not_flag_private_pass(tmp_path):
    """A private `_helper` legitimately passing should not count."""
    _write(tmp_path / "f.py",
           "def _abstract():\n    pass\n")
    findings = detect_stubs_in_file(tmp_path / "f.py", repo_root=tmp_path)
    assert findings == []


def test_stub_penalty_capped(tmp_path):
    findings = [{"file": "x", "qualname": "f", "lineno": 1,
                  "kind": "pass_only", "excerpt": ""} for _ in range(20)]
    assert stub_penalty(findings) == 40  # cap


def test_certify_deducts_for_stubs(tmp_path):
    pkg = tmp_path / "src" / "demo"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    for tier in ("a0_qk_constants", "a1_at_functions", "a2_mo_composites",
                 "a3_og_features", "a4_sy_orchestration"):
        d = pkg / tier
        d.mkdir()
        (d / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a1_at_functions" / "stubby.py").write_text(
        "def needs_work():\n    pass\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text(
        "import demo\ndef test_one():\n    assert demo is not None\n",
        encoding="utf-8")
    result = certify(tmp_path, project="demo", package="demo")
    # New score weights:
    #   structural: docs(10)+layout(10)+wire(10)+tests-present(5) = 35
    #   runtime: import(25)
    #   behavioral: pass-ratio(1.0) * 30 = 30
    #   stub penalty: -8 (one stub)
    # Total: 35 + 25 + 30 - 8 = 82.
    assert result["score"] == 82
    assert result["no_stub_bodies"] is False
    assert result["package_importable"] is True
    assert any("Stub bodies detected" in i for i in result["issues"])


def test_certify_score_pristine_with_no_stubs(tmp_path):
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
    result = certify(tmp_path, project="demo", package="demo")
    # 35 (structural) + 25 (runtime) + 30 (1/1 pass) = 90 — losing 10pts
    # because tests-present is now 5pt and behavioral is 30pt.  No, wait:
    # docs(10) + layout(10) + wire(10) + tests(5) = 35; import(25); behav(30) = 90.
    # Hmm that's 90 not 100.  Let me re-do: structural max 35, runtime 25, behav 30 = 90 max.
    # We removed 10 points from the structural side and added them to behavioral.
    assert result["score"] == 90
    assert result["test_pass_ratio"] == 1.0
    assert result["no_stub_bodies"] is True
    assert result["package_importable"] is True


def test_certify_penalises_unimportable_package(tmp_path):
    """Wire-clean tier tree but a syntax error → loses runtime AND behavioral points."""
    pkg = tmp_path / "src" / "demo"
    pkg.mkdir(parents=True)
    for tier in ("a0_qk_constants", "a1_at_functions", "a2_mo_composites",
                 "a3_og_features", "a4_sy_orchestration"):
        d = pkg / tier
        d.mkdir()
        (d / "__init__.py").write_text("", encoding="utf-8")
    # __init__.py triggers a syntax error during `python -c "import demo"`.
    (pkg / "__init__.py").write_text("def broken(\n    return\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text(
        "def test_one():\n    assert True\n", encoding="utf-8")
    result = certify(tmp_path, project="demo", package="demo")
    assert result["package_importable"] is False
    # structural 35 + runtime 0 + behavioral 0 (tests can't run if package
    # doesn't import — the runner is gated on importable) = 35.
    assert result["score"] == 35
    assert any("fails to import" in i for i in result["issues"])
