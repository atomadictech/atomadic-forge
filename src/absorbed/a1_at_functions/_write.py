"""Test commandsmith discover + render + import-repair."""
from __future__ import annotations

from pathlib import Path

from atomadic_forge.a1_at_functions.commandsmith_discover import discover_command_modules
from atomadic_forge.a1_at_functions.commandsmith_render import (
    render_registry_module,
    render_wrapper_module,
)
from atomadic_forge.a1_at_functions.import_repair import (
    KNOWN_SOURCE_ROOTS,
    _split_source_stem,
    build_name_to_file_map,
    rewrite_imports,
)


def _write(p: Path, body: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def test_discover_picks_up_typer_app(tmp_path):
    _write(tmp_path / "pkg" / "commands" / "scout.py",
           '"""Scout help line."""\n'
           "import typer\n"
           "app = typer.Typer()\n")
    _write(tmp_path / "pkg" / "commands" / "__init__.py", "")
    _write(tmp_path / "pkg" / "__init__.py", "")
    cards = discover_command_modules(tmp_path / "pkg", package="pkg")
    assert any(c["name"] == "scout" and c["surface"] == "typer_app" for c in cards)


def test_discover_picks_up_register_fn(tmp_path):
    _write(tmp_path / "pkg" / "commands" / "agent.py",
           "import typer\n"
           "def register(app):\n    app.command()\n")
    _write(tmp_path / "pkg" / "commands" / "__init__.py", "")
    _write(tmp_path / "pkg" / "__init__.py", "")
    cards = discover_command_modules(tmp_path / "pkg", package="pkg")
    surfaces = {c["name"]: c["surface"] for c in cards}
    assert surfaces.get("agent") == "register_fn"


def test_render_registry_emits_valid_python(tmp_path):
    """Generated registry module must compile."""
    cards = [
        {"name": "alpha", "module": "pkg.commands.alpha", "surface": "typer_app",
         "help_text": "alpha help", "hidden": False, "sub_commands": [],
         "source_root": "atomadic_forge_seed"},
        {"name": "beta", "module": "pkg.commands.beta", "surface": "register_fn",
         "help_text": "beta help", "hidden": False, "sub_commands": [],
         "source_root": "atomadic_forge_seed"},
    ]
    src = render_registry_module(cards)  # type: ignore[arg-type]
    import ast
    ast.parse(src)


def test_render_wrapper_emits_valid_python():
    src = render_wrapper_module(
        target_module="atomadic.cherry_picker",
        target_class="CherryPicker",
        command_name="atomadic-cherry",
        sub_commands=[
            {"name": "scan_repo", "parameters": [], "return_type": "list",
             "docstring": "Walk every file"},
        ],
        help_text="atomadic-v2 cherry",
        init_params=["repo_path: Path"],
        auto_scan="scan_repo",
    )
    import ast
    ast.parse(src)
    assert "scan_repo" in src
    assert "CherryPicker(repo_path)" in src


def test_split_source_stem_handles_known_roots():
    """Greedy regex bug regression test: ``a1_source_atomadic_v2_infer_tier``
    must split as (atomadic_v2, infer_tier), not (atomadic_v2_infer, tier)."""
    parsed = _split_source_stem("a1_source_atomadic_v2_infer_tier", KNOWN_SOURCE_ROOTS)
    assert parsed == ("atomadic_v2", "infer_tier")


def test_rewrite_imports_redirects_flat_module(tmp_path):
    """Old-style ``from kg import infer_tier`` rewrites to sibling reference."""
    pkg = tmp_path / "pkg"
    a1 = pkg / "a1_at_functions"
    a1.mkdir(parents=True)
    (a1 / "a1_source_atomadic_v2_infer_tier.py").write_text(
        "def infer_tier(): pass\n", encoding="utf-8")
    (a1 / "a1_source_atomadic_v2_consumer.py").write_text(
        "from kg import infer_tier\n", encoding="utf-8")
    n2f = build_name_to_file_map(a1)
    rewritten = rewrite_imports(
        "from kg import infer_tier\n",
        symbol_map={},  # head ``kg`` is unknown → fall back to per-name
        stdlib_safelist=("typing", "json"),
        name_to_file=n2f,
    )
    assert "from .a1_source_atomadic_v2_infer_tier import infer_tier" in rewritten
