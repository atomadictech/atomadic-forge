"""Tests for deterministic generated-package quality phases."""

from __future__ import annotations

import ast
import json

from atomadic_forge.a1_at_functions.generation_quality import (
    add_missing_docstrings,
    apply_docs_phase,
    apply_docstring_phase,
    apply_test_phase,
)
from atomadic_forge.a1_at_functions.llm_client import StubLLMClient
from atomadic_forge.a3_og_features.forge_loop import run_iterate


def test_add_missing_docstrings_for_module_function_class_and_method():
    source = (
        "def add(a, b):\n"
        "    return a + b\n"
        "\n"
        "class Counter:\n"
        "    def bump(self):\n"
        "        return 1\n"
    )
    updated = add_missing_docstrings(source, rel_path="a1_at_functions/math_ops.py")
    tree = ast.parse(updated)
    assert ast.get_docstring(tree)
    fn = tree.body[1]
    cls = tree.body[2]
    assert isinstance(fn, ast.FunctionDef)
    assert isinstance(cls, ast.ClassDef)
    assert ast.get_docstring(fn)
    assert ast.get_docstring(cls)
    assert ast.get_docstring(cls.body[1])


def test_quality_phases_write_docs_tests_and_docstrings(tmp_path):
    output = tmp_path / "out"
    pkg = output / "src" / "demo"
    mod = pkg / "a1_at_functions" / "math_ops.py"
    mod.parent.mkdir(parents=True)
    mod.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    docstrings = apply_docstring_phase(pkg)
    docs = apply_docs_phase(
        output_root=output,
        package_root=pkg,
        package="demo",
        intent="Build math helpers",
    )
    tests = apply_test_phase(output_root=output, package_root=pkg, package="demo")

    assert docstrings["files_changed"] == ["a1_at_functions/math_ops.py"]
    assert (output / "docs" / "API.md").exists()
    assert (output / "docs" / "TESTING.md").exists()
    assert docs["files_written"] == ["docs/API.md", "docs/TESTING.md"]
    assert tests["files_written"] == ["tests/test_generated_smoke.py"]
    assert "demo.a1_at_functions.math_ops" in (
        output / "tests" / "test_generated_smoke.py"
    ).read_text(encoding="utf-8")
    assert "\nimport importlib\n\nimport demo as generated_package\n" in (
        output / "tests" / "test_generated_smoke.py"
    ).read_text(encoding="utf-8")


def test_iterate_runs_quality_phases_after_llm_emit(tmp_path):
    output = tmp_path / "out"
    emitted = json.dumps([
        {
            "path": "src/qualitydemo/a1_at_functions/math_ops.py",
            "content": "def add(a, b):\n    return a + b\n",
        },
    ])
    report = run_iterate(
        "Build math helpers",
        output=output,
        package="qualitydemo",
        llm=StubLLMClient(canned=[emitted]),
        max_iterations=0,
        target_score=200.0,
    )

    source = (
        output / "src" / "qualitydemo" / "a1_at_functions" / "math_ops.py"
    ).read_text(encoding="utf-8")
    assert '"""Pure functions for math ops."""' in source
    assert (output / "docs" / "API.md").exists()
    assert (output / "tests" / "test_generated_smoke.py").exists()
    assert (output / ".atomadic-forge" / "quality.json").exists()
    assert [p["phase"] for p in report["quality_phases"]] == [
        "docstrings", "docs", "tests",
    ]
    assert report["final_certify"]["score"] >= 90
