"""Tests for IGNORED_DIRS, file_class_for_path, and the docs/layout
checks treating markdown + asset + config files correctly.

Atomadic's repo has cognition/guides/*.md, .claude/, .github/, and a
mix of JS source.  Forge must:
  * never recurse into IGNORED_DIRS (.claude, .github, node_modules,
    __pycache__, .wrangler, etc.),
  * count .md files as documentation (not untiered code),
  * count .html / .css / .json as assets/configs (not untiered code),
  * recognise nested guides/ directories (cognition/guides/INDEX.md)
    for the docs signal.
"""

from __future__ import annotations

from pathlib import Path

from atomadic_forge.a0_qk_constants.lang_extensions import (
    ALL_SOURCE_EXTS,
    ASSET_EXTS,
    CONFIG_EXTS,
    DOC_EXTS,
    IGNORED_DIRS,
    file_class_for_path,
    is_ignored_segment,
    path_parts_contain_ignored_dir,
)
from atomadic_forge.a1_at_functions.certify_checks import (
    check_documentation,
    check_tests_present,
    check_tier_layout,
    count_untiered_source_files,
)
from atomadic_forge.a1_at_functions.scout_walk import (
    _file_class_counts,
    _under_skip_dir,
    harvest_repo,
)

# ── lang_extensions ────────────────────────────────────────────────────

def test_doc_extensions_includes_md():
    assert ".md" in DOC_EXTS
    assert ".rst" in DOC_EXTS
    assert ".mdx" in DOC_EXTS


def test_asset_extensions_includes_html():
    assert ".html" in ASSET_EXTS
    assert ".css" in ASSET_EXTS
    assert ".png" in ASSET_EXTS


def test_config_extensions_includes_json_yaml_toml():
    for ext in (".json", ".yaml", ".yml", ".toml"):
        assert ext in CONFIG_EXTS


def test_source_doc_asset_config_disjoint():
    # No extension should be in two buckets at once.
    assert not (ALL_SOURCE_EXTS & DOC_EXTS)
    assert not (ALL_SOURCE_EXTS & ASSET_EXTS)
    assert not (ALL_SOURCE_EXTS & CONFIG_EXTS)
    assert not (DOC_EXTS & ASSET_EXTS)
    assert not (DOC_EXTS & CONFIG_EXTS)


def test_ignored_dirs_includes_common_tooling():
    for d in (".claude", ".github", "node_modules", "__pycache__",
              ".wrangler", "dist", "build", ".venv"):
        assert d in IGNORED_DIRS, f"{d} should be in IGNORED_DIRS"


def test_pytest_basetemp_prefix_is_ignored_without_enumerating_every_name():
    assert path_parts_contain_ignored_dir((".pytest_tmp_run", "tests", "test_x.py"))
    assert path_parts_contain_ignored_dir(("nested", ".pytest_tmp_focus", "src"))
    assert is_ignored_segment(".pytest_tmp_focus")


def test_file_class_for_path_source():
    assert file_class_for_path("src/x/foo.py") == "source"
    assert file_class_for_path("cognition/cognition_worker.js") == "source"
    assert file_class_for_path("app/page.tsx") == "source"


def test_file_class_for_path_documentation():
    assert file_class_for_path("README.md") == "documentation"
    assert file_class_for_path("docs/ARCHITECTURE.md") == "documentation"
    assert file_class_for_path("cognition/guides/INDEX.md") == "documentation"
    assert file_class_for_path("notes.rst") == "documentation"


def test_file_class_for_path_asset():
    assert file_class_for_path("public/logo.png") == "asset"
    assert file_class_for_path("chat/index.html") == "asset"
    assert file_class_for_path("hello/style.css") == "asset"


def test_file_class_for_path_config():
    assert file_class_for_path("pyproject.toml") == "config"
    assert file_class_for_path("package.json") == "config"
    assert file_class_for_path(".gitignore") == "config"


# ── scout_walk._under_skip_dir ─────────────────────────────────────────

def test_under_skip_dir_catches_dot_github():
    assert _under_skip_dir((".github", "workflows", "ci.yml"))


def test_under_skip_dir_catches_node_modules_anywhere():
    assert _under_skip_dir(("any", "depth", "node_modules", "lodash"))


def test_under_skip_dir_does_not_match_arbitrary_dotfile():
    # Leading dot alone shouldn't kill traversal — only explicit ignores.
    # E.g. a hypothetical app folder ".storybook" isn't on the list,
    # so it should NOT be skipped (until/unless someone adds it).
    assert _under_skip_dir((".storybook",)) is False


# ── _file_class_counts on a synthetic tree ─────────────────────────────

def test_file_class_counts_classifies_correctly(tmp_path: Path):
    # source
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.py").write_text("x = 1\n")
    (tmp_path / "src" / "bar.js").write_text("export const x = 1;\n")
    # documentation
    (tmp_path / "README.md").write_text("# project\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ARCH.md").write_text("# arch\n")
    # asset
    (tmp_path / "logo.png").write_bytes(b"\x89PNG")
    (tmp_path / "page.html").write_text("<html></html>\n")
    # config
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    # ignored — should not be counted
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "workflows.yml").write_text("name: x\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.js").write_text("var x;\n")

    counts = _file_class_counts(tmp_path)
    assert counts["source"] == 2,         f"expected 2 source, got {counts}"
    assert counts["documentation"] == 2,  f"expected 2 doc, got {counts}"
    assert counts["asset"] == 2,          f"expected 2 asset, got {counts}"
    assert counts["config"] == 1,         f"expected 1 config, got {counts}"


# ── check_documentation recognises nested guides/ ──────────────────────

def test_check_documentation_finds_nested_guides_md(tmp_path: Path):
    # No README, no docs/ — only nested guides/ markdown
    (tmp_path / "cognition").mkdir()
    (tmp_path / "cognition" / "guides").mkdir()
    (tmp_path / "cognition" / "guides" / "INDEX.md").write_text("# index\n")
    (tmp_path / "cognition" / "guides" / "CHAT.md").write_text("# chat\n")
    ok, detail = check_documentation(tmp_path)
    assert ok is True, f"nested guides/ should pass docs check: {detail}"
    assert detail["docs_md_count"] >= 2


def test_check_documentation_root_readme_passes(tmp_path: Path):
    (tmp_path / "README.md").write_text("# project\n")
    ok, _ = check_documentation(tmp_path)
    assert ok is True


def test_check_documentation_no_docs_fails(tmp_path: Path):
    # Empty repo with only a source file
    (tmp_path / "main.py").write_text("x=1\n")
    ok, detail = check_documentation(tmp_path)
    assert ok is False
    assert detail["readme"] is False
    assert detail["docs_md_count"] == 0


def test_certify_doc_test_layout_signals_ignore_pytest_basetemp(tmp_path: Path):
    scratch = tmp_path / ".pytest_tmp_run"
    (scratch / "docs").mkdir(parents=True)
    (scratch / "docs" / "A.md").write_text("# a\n", encoding="utf-8")
    (scratch / "docs" / "B.md").write_text("# b\n", encoding="utf-8")
    (scratch / "tests").mkdir()
    (scratch / "tests" / "test_fake.py").write_text("def test_fake(): pass\n", encoding="utf-8")
    for tier in ("a0_qk_constants", "a1_at_functions", "a4_sy_orchestration"):
        (scratch / "src" / "fake" / tier).mkdir(parents=True)
    (scratch / "src" / "fake" / "a1_at_functions" / "fake.py").write_text(
        "def fake(): return 1\n", encoding="utf-8")

    docs_ok, docs_detail = check_documentation(tmp_path)
    tests_ok, tests_detail = check_tests_present(tmp_path)
    layout_ok, layout_detail = check_tier_layout(tmp_path)
    untiered = count_untiered_source_files(tmp_path)

    assert docs_ok is False
    assert docs_detail["docs_md_count"] == 0
    assert tests_ok is False
    assert tests_detail["test_files_found"] == 0
    assert layout_ok is False
    assert layout_detail["tiers_present"] == []
    assert untiered["untiered_source_count"] == 0


# ── count_untiered_source_files: markdown does NOT count as untiered ───

def test_untiered_count_excludes_docs_assets_config(tmp_path: Path):
    # Source NOT under any tier dir
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.py").write_text("x=1\n")
    # Docs all over the place — these should NOT show up as untiered source
    (tmp_path / "README.md").write_text("# x\n")
    (tmp_path / "guides").mkdir()
    (tmp_path / "guides" / "WORK.md").write_text("# work\n")
    # An asset
    (tmp_path / "page.html").write_text("<html></html>\n")
    # An ignored dir with a JS file
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "ci.yml").write_text("name: x\n")
    (tmp_path / ".github" / "ci-helper.js").write_text("export const x = 1;\n")

    info = count_untiered_source_files(tmp_path)
    # foo.py is untiered (1).  Markdown / HTML / .github files don't
    # show up.  CI helper inside .github is ignored.
    assert info["untiered_source_count"] == 1
    assert info["tiered_source_count"] == 0
    assert info["untiered_samples"] == ["src/foo.py"]


def test_untiered_count_credits_tier_dir_files(tmp_path: Path):
    (tmp_path / "src" / "pkg" / "a1_at_functions").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "a1_at_functions" / "helper.py").write_text("def f(): return 1\n")
    (tmp_path / "src" / "pkg" / "a4_sy_orchestration").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "a4_sy_orchestration" / "cli.py").write_text("def main(): pass\n")
    info = count_untiered_source_files(tmp_path)
    assert info["tiered_source_count"] == 2
    assert info["untiered_source_count"] == 0


# ── harvest_repo includes file_class_counts in its output ──────────────

def test_harvest_repo_exposes_file_class_counts(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.py").write_text("x=1\n")
    (tmp_path / "README.md").write_text("# r\n")
    (tmp_path / "page.html").write_text("<html></html>\n")
    out = harvest_repo(tmp_path)
    assert "file_class_counts" in out
    fc = out["file_class_counts"]
    assert fc["source"] == 1
    assert fc["documentation"] == 1
    assert fc["asset"] == 1


def test_harvest_repo_skips_ignored_dirs(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.py").write_text("def real(): return 1\n")
    # Junk in ignored dirs should be invisible
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.js").write_text(
        "export function junk() { return 99; }\n")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "agent.js").write_text(
        "export const NEVER = 1;\n")
    out = harvest_repo(tmp_path)
    # Only the real source file's symbols should appear.
    files_seen = {s["file"] for s in out["symbols"]}
    assert "src/foo.py" in files_seen
    assert all("node_modules" not in f for f in files_seen)
    assert all(".claude" not in f for f in files_seen)
