"""Tests for ``forge iterate`` / ``forge evolve`` in JavaScript mode.

These tests use a deterministic ``StubLLMClient`` with canned JSON
responses — no real LLM tokens are spent.  They verify:

* ``--language javascript`` produces a JS-shaped scaffold under
  ``output/<package>/aN_*/`` (no ``src/`` wrapper, no ``pyproject.toml``,
  no ``__init__.py``).
* The JS scaffold writes a minimal ``package.json`` with
  ``"type": "module"`` so ES6 imports resolve at runtime.
* ``_safe_path`` accepts ``.js`` and rejects ``.py`` when language is
  ``javascript`` (and vice-versa).
* The system prompt switches to the JS variant — no ``pyproject``,
  no Python module-docstring instructions, the example uses
  ``export``/``import`` ES syntax.
* Back-compat: existing Python tests still work unchanged because the
  default language is still ``"python"``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from atomadic_forge.a0_qk_constants.gen_language import (
    ALLOWED_FILE_EXTS, DEFAULT_LANGUAGE, LANGUAGES,
    PKG_ROOT_TEMPLATE, normalize_language, pkg_root_for,
)
from atomadic_forge.a1_at_functions.forge_feedback import (
    pack_initial_intent, system_prompt,
)
from atomadic_forge.a1_at_functions.llm_client import StubLLMClient
from atomadic_forge.a1_at_functions.scaffold_js import (
    render_js_readme, render_package_json,
)
from atomadic_forge.a3_og_features.forge_evolve import run_evolve
from atomadic_forge.a3_og_features.forge_loop import (
    _safe_path, _scaffold_package, run_iterate,
)


# ── gen_language constants ───────────────────────────────────────────────

def test_default_language_is_python():
    assert DEFAULT_LANGUAGE == "python"


def test_languages_tuple_contains_three():
    assert set(LANGUAGES) == {"python", "javascript", "typescript"}


def test_pkg_root_template_python_uses_src():
    assert PKG_ROOT_TEMPLATE["python"] == "src/{package}"


def test_pkg_root_template_javascript_no_src():
    assert PKG_ROOT_TEMPLATE["javascript"] == "{package}"


def test_pkg_root_template_typescript_no_src():
    assert PKG_ROOT_TEMPLATE["typescript"] == "{package}"


def test_pkg_root_for_python_inserts_src():
    assert pkg_root_for("python", "myapp") == "src/myapp"


def test_pkg_root_for_javascript_no_src():
    assert pkg_root_for("javascript", "myapp") == "myapp"


def test_allowed_exts_python_excludes_js():
    assert ".py" in ALLOWED_FILE_EXTS["python"]
    assert ".js" not in ALLOWED_FILE_EXTS["python"]


def test_allowed_exts_javascript_excludes_py():
    assert ".js" in ALLOWED_FILE_EXTS["javascript"]
    assert ".mjs" in ALLOWED_FILE_EXTS["javascript"]
    assert ".cjs" in ALLOWED_FILE_EXTS["javascript"]
    assert ".py" not in ALLOWED_FILE_EXTS["javascript"]


def test_allowed_exts_typescript_includes_ts():
    assert ".ts" in ALLOWED_FILE_EXTS["typescript"]
    assert ".tsx" in ALLOWED_FILE_EXTS["typescript"]
    assert ".py" not in ALLOWED_FILE_EXTS["typescript"]


def test_normalize_language_aliases():
    assert normalize_language("py") == "python"
    assert normalize_language("PYTHON") == "python"
    assert normalize_language("js") == "javascript"
    assert normalize_language("Node") == "javascript"
    assert normalize_language("ts") == "typescript"
    assert normalize_language(None) == "python"


def test_normalize_language_rejects_unknown():
    with pytest.raises(ValueError, match="unknown language"):
        normalize_language("rust")


# ── _safe_path is language-aware ─────────────────────────────────────────

def test_safe_path_python_accepts_py_rejects_js():
    assert _safe_path("src/x/a1_at_functions/foo.py", language="python")
    assert not _safe_path("src/x/a1_at_functions/foo.js", language="python")


def test_safe_path_javascript_accepts_js_rejects_py():
    assert _safe_path("x/a1_at_functions/foo.js", language="javascript")
    assert _safe_path("x/a1_at_functions/foo.mjs", language="javascript")
    assert not _safe_path("x/a1_at_functions/foo.py", language="javascript")


def test_safe_path_typescript_accepts_ts():
    assert _safe_path("x/a1_at_functions/foo.ts", language="typescript")
    assert _safe_path("x/a1_at_functions/foo.tsx", language="typescript")


def test_safe_path_md_allowed_in_all_languages():
    assert _safe_path("README.md", language="python")
    assert _safe_path("README.md", language="javascript")
    assert _safe_path("README.md", language="typescript")


def test_safe_path_traversal_rejected_for_js():
    assert not _safe_path("../escape/foo.js", language="javascript")
    assert not _safe_path("a1_at_functions/<pkg>/foo.js", language="javascript")


# ── scaffold_js helpers are pure ─────────────────────────────────────────

def test_render_package_json_has_type_module():
    pj = json.loads(render_package_json(package="counter",
                                          description="counts things"))
    assert pj["name"] == "counter"
    assert pj["type"] == "module"
    assert pj["private"] is True
    assert pj["version"] == "0.0.1"


def test_render_js_readme_mentions_tier_layout():
    body = render_js_readme(package="ctr", intent="counter feature",
                              language="javascript")
    assert "ctr" in body
    assert "a0_qk_constants" in body
    assert "a4_sy_orchestration" in body
    assert "JavaScript" in body


def test_render_js_readme_typescript_label():
    body = render_js_readme(package="ctr", intent="x", language="typescript")
    assert "TypeScript" in body


# ── _scaffold_package: JS-shape produces correct files ───────────────────

def test_scaffold_package_javascript_no_src_no_init(tmp_path: Path):
    """JS scaffold puts the package at output/<pkg>/, NOT output/src/<pkg>/."""
    pkg_root = _scaffold_package(tmp_path, "ctr", intent="counter",
                                   language="javascript")
    # Package directory at output root, not under src/
    assert pkg_root == (tmp_path / "ctr").resolve() or pkg_root == tmp_path / "ctr"
    assert (tmp_path / "ctr").is_dir()
    assert not (tmp_path / "src").exists()
    # No Python __init__.py anywhere
    assert not (tmp_path / "ctr" / "__init__.py").exists()
    for tier in ("a0_qk_constants", "a1_at_functions", "a2_mo_composites",
                 "a3_og_features", "a4_sy_orchestration"):
        assert (tmp_path / "ctr" / tier).is_dir()
        assert not (tmp_path / "ctr" / tier / "__init__.py").exists()


def test_scaffold_package_javascript_writes_package_json(tmp_path: Path):
    _scaffold_package(tmp_path, "ctr", intent="counter feature",
                       language="javascript")
    pj_path = tmp_path / "package.json"
    assert pj_path.is_file()
    pj = json.loads(pj_path.read_text(encoding="utf-8"))
    assert pj["name"] == "ctr"
    assert pj["type"] == "module"


def test_scaffold_package_javascript_no_pyproject_no_tests_dir(tmp_path: Path):
    _scaffold_package(tmp_path, "ctr", intent="x", language="javascript")
    assert not (tmp_path / "pyproject.toml").exists()
    assert not (tmp_path / "tests").exists()


def test_scaffold_package_javascript_writes_js_readme(tmp_path: Path):
    _scaffold_package(tmp_path, "ctr", intent="x", language="javascript")
    body = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "JavaScript" in body
    assert "a4_sy_orchestration" in body


def test_scaffold_package_python_unchanged(tmp_path: Path):
    """Python default still produces the original layout — no regression."""
    pkg_root = _scaffold_package(tmp_path, "py_pkg", intent="x")
    assert pkg_root == tmp_path / "src" / "py_pkg"
    assert (tmp_path / "src" / "py_pkg" / "a1_at_functions" / "__init__.py").exists()
    assert (tmp_path / "pyproject.toml").exists()
    assert (tmp_path / "tests" / "conftest.py").exists()
    # No package.json contamination on Python path
    assert not (tmp_path / "package.json").exists()


# ── system_prompt switches per language ─────────────────────────────────

def test_system_prompt_python_default_mentions_pyproject():
    sp = system_prompt()  # default language
    assert "pyproject.toml" in sp
    assert "__init__.py" in sp


def test_system_prompt_javascript_no_pyproject_yes_esmodule():
    sp = system_prompt(language="javascript")
    # The JS prompt should NOT instruct emitting pyproject or Python tests.
    assert "pyproject" not in sp
    assert "PEP-621" not in sp
    assert "console_script" not in sp
    assert "tests/`` directory with ``conftest.py``" not in sp
    # It SHOULD describe the JS scaffold the LLM gets for free.
    assert "package.json" in sp
    assert 'type": "module"' in sp or "ES module" in sp or "ES6" in sp
    # JS-specific syntax instructions for the LLM's emit.
    assert "import" in sp
    assert "export" in sp


def test_system_prompt_typescript_uses_js_variant():
    """TypeScript reuses the JS prompt today (tsconfig polish is roadmap)."""
    sp_ts = system_prompt(language="typescript")
    sp_js = system_prompt(language="javascript")
    assert sp_ts == sp_js


def test_pack_initial_intent_javascript_no_src_prefix():
    msg = pack_initial_intent("make a counter", package="ctr",
                                language="javascript")
    # JS path doesn't have src/ prefix
    assert "`ctr/`" in msg
    assert "`src/ctr/`" not in msg


def test_pack_initial_intent_python_default_keeps_src():
    msg = pack_initial_intent("make a calc", package="calc")
    assert "`src/calc/`" in msg


# ── End-to-end JS iterate with stub LLM ─────────────────────────────────

def test_iterate_javascript_stub_writes_js_files(tmp_path: Path):
    """The full loop runs end-to-end in JS mode with a stub LLM."""
    canned = [
        json.dumps([
            {"path": "ctr/a1_at_functions/increment.js",
             "content": "// Tier a1 — increment.\n"
                        "export function increment(n) { return n + 1; }\n"},
            {"path": "ctr/a4_sy_orchestration/worker.js",
             "content": "// Tier a4 — Worker entry.\n"
                        "import { increment } from "
                        "\"../a1_at_functions/increment.js\";\n"
                        "export default {\n"
                        "  async fetch(req) {\n"
                        "    return new Response(String(increment(0)));\n"
                        "  }\n"
                        "};\n"},
        ]),
        "[]",
    ]
    llm = StubLLMClient(canned=canned)
    output = tmp_path / "out"
    output.mkdir()
    report = run_iterate(
        "counter Worker",
        output=output,
        package="ctr",
        llm=llm,
        max_iterations=2,
        target_score=0.0,
        language="javascript",
    )
    assert report["applied"] is True
    assert report["language"] == "javascript"
    # JS files written, NO src/ prefix
    assert (output / "ctr" / "a1_at_functions" / "increment.js").is_file()
    assert (output / "ctr" / "a4_sy_orchestration" / "worker.js").is_file()
    assert not (output / "src").exists()
    # Scaffolded package.json present, no pyproject.toml
    assert (output / "package.json").is_file()
    assert not (output / "pyproject.toml").exists()


def test_iterate_javascript_drops_python_emits(tmp_path: Path):
    """If the LLM mistakenly emits a .py file in JS mode, _safe_path drops it."""
    canned = [
        json.dumps([
            # Valid JS — should be written
            {"path": "ctr/a1_at_functions/inc.js",
             "content": "export function inc(n) { return n + 1; }\n"},
            # Wrong language — should be silently dropped
            {"path": "ctr/a1_at_functions/inc.py",
             "content": "def inc(n): return n + 1\n"},
        ]),
        "[]",
    ]
    llm = StubLLMClient(canned=canned)
    output = tmp_path / "out"
    output.mkdir()
    run_iterate(
        "counter",
        output=output,
        package="ctr",
        llm=llm,
        max_iterations=2,
        target_score=0.0,
        language="javascript",
    )
    assert (output / "ctr" / "a1_at_functions" / "inc.js").is_file()
    assert not (output / "ctr" / "a1_at_functions" / "inc.py").exists()


def test_evolve_javascript_two_rounds_with_stub(tmp_path: Path):
    """Recursive evolve in JS mode completes without error."""
    canned = (
        # Round 0
        [json.dumps([
            {"path": "ev/a1_at_functions/seed.js",
             "content": "// Tier a1.\nexport function seed(x) { return x * 2; }\n"},
        ]), "[]"]
        # Round 1
        + [json.dumps([
            {"path": "ev/a2_mo_composites/store.js",
             "content": "// Tier a2.\nexport class Store {\n"
                        "  constructor() { this.data = {}; }\n"
                        "  put(k, v) { this.data[k] = v; }\n"
                        "}\n"},
        ]), "[]"]
    )
    llm = StubLLMClient(canned=canned)
    report = run_evolve(
        "grow",
        output=tmp_path / "out",
        package="ev",
        llm=llm,
        rounds=2,
        iterations_per_round=2,
        target_score=0.0,
        language="javascript",
    )
    assert report["language"] == "javascript"
    assert report["rounds_completed"] >= 1
    assert (tmp_path / "out" / "ev" / "a1_at_functions" / "seed.js").is_file()


def test_iterate_preflight_javascript(tmp_path: Path):
    """--no-apply path returns the JS prompt without scaffolding files."""
    llm = StubLLMClient()
    report = run_iterate(
        "anything",
        output=tmp_path / "out",
        package="preview",
        llm=llm,
        apply=False,
        language="javascript",
    )
    assert report["applied"] is False
    assert report["language"] == "javascript"
    assert "package.json" in report["system_prompt"]
    assert "pyproject" not in report["system_prompt"]
    assert "`preview/`" in report["first_prompt"]
    assert "`src/preview/`" not in report["first_prompt"]
    assert llm.calls == 0
