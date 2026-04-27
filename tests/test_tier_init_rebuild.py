"""Tests for the tier __init__ rebuilder."""

from pathlib import Path

from atomadic_forge.a1_at_functions.tier_init_rebuild import (
    rebuild_tier_inits, render_tier_init, _public_names_in_module,
)


def _write(p: Path, body: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def test_collects_public_function_names(tmp_path):
    _write(tmp_path / "f.py",
           "def public(): pass\ndef _private(): pass\n"
           "class Pub: pass\nCONST = 1\n")
    names = _public_names_in_module(tmp_path / "f.py")
    assert "public" in names
    assert "Pub" in names
    assert "CONST" in names
    assert "_private" not in names


def test_render_tier_init_emits_imports_and_all():
    body = render_tier_init(
        "a1_at_functions",
        modules={"add": ["add"], "subtract": ["subtract"]},
    )
    assert "from .add import add" in body
    assert "from .subtract import subtract" in body
    assert "__all__ = ['add', 'subtract']" in body
    assert "Auto-managed by atomadic-forge" in body


def test_render_empty_tier_produces_minimal_init():
    body = render_tier_init("a3_og_features", modules={})
    assert body.strip() == '"""Tier a3_og_features — empty."""'


def test_rebuild_tier_inits_writes_re_exports(tmp_path):
    pkg = tmp_path / "src" / "demo"
    a1 = pkg / "a1_at_functions"
    a1.mkdir(parents=True)
    (a1 / "__init__.py").write_text('"""a1_at_functions."""\n', encoding="utf-8")
    (a1 / "add.py").write_text("def add(a, b):\n    return a + b\n",
                                  encoding="utf-8")
    (a1 / "subtract.py").write_text("def subtract(a, b):\n    return a - b\n",
                                      encoding="utf-8")
    written = rebuild_tier_inits(pkg)
    assert any("a1_at_functions/__init__.py" in p for p in written)
    init_text = (a1 / "__init__.py").read_text(encoding="utf-8")
    assert "from .add import add" in init_text
    assert "from .subtract import subtract" in init_text


def test_rebuild_does_not_clobber_user_managed_init(tmp_path):
    pkg = tmp_path / "src" / "demo"
    a1 = pkg / "a1_at_functions"
    a1.mkdir(parents=True)
    (a1 / "__init__.py").write_text(
        "# I am hand-managed\nfrom .magic import secret_export\n",
        encoding="utf-8")
    (a1 / "magic.py").write_text("secret_export = 42\n", encoding="utf-8")
    rebuild_tier_inits(pkg)
    init_text = (a1 / "__init__.py").read_text(encoding="utf-8")
    # Hand-written content preserved.
    assert "I am hand-managed" in init_text


def test_rebuild_idempotent(tmp_path):
    pkg = tmp_path / "src" / "demo"
    a1 = pkg / "a1_at_functions"
    a1.mkdir(parents=True)
    (a1 / "__init__.py").write_text("", encoding="utf-8")
    (a1 / "f.py").write_text("def foo(): pass\n", encoding="utf-8")
    once = rebuild_tier_inits(pkg)
    twice = rebuild_tier_inits(pkg)
    # Same path, same content both times.
    assert list(once.values()) == list(twice.values())
