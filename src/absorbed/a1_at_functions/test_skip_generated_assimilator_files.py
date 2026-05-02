"""Test the signature harvester (tier-mode + flat-mode)."""
from __future__ import annotations

from pathlib import Path

from atomadic_forge.a1_at_functions.emergent_signature_extract import harvest_signatures


def _write(p: Path, body: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def test_tier_mode_harvests_only_tier_dirs(tmp_path):
    pkg = tmp_path / "pkg"
    _write(pkg / "a1_at_functions" / "helpers.py",
           "def add(x: int, y: int) -> int:\n    return x + y\n")
    _write(pkg / "a1_at_functions" / "__init__.py", "")
    _write(pkg / "a2_mo_composites" / "store.py",
           "class Store:\n"
           "    def get(self, key: str) -> str:\n"
           "        return key\n")
    _write(pkg / "a2_mo_composites" / "__init__.py", "")
    _write(pkg / "noise.py", "def junk(): pass\n")  # outside any tier
    cards = harvest_signatures(tmp_path, package="pkg")
    names = {c["name"] for c in cards}
    assert "add" in names
    assert "Store.get" in names
    # ``junk`` lives outside a tier and must be skipped in tier mode.
    assert "junk" not in names


def test_flat_mode_harvests_any_repo(tmp_path):
    """No tier folders → flat-mode kicks in and walks every .py."""
    _write(tmp_path / "src" / "calc.py",
           "def add(a: int, b: int) -> int:\n    return a + b\n")
    _write(tmp_path / "src" / "io_runner.py",
           "def main() -> None:\n    print('hi')\n")
    cards = harvest_signatures(tmp_path / "src", package="anything")
    names = {c["name"] for c in cards}
    assert "add" in names
    assert "main" in names


def test_skip_generated_assimilator_files(tmp_path):
    pkg = tmp_path / "pkg"
    _write(pkg / "a1_at_functions" / "a1_source_atomadic_v2_foo.py",
           "def foo(): pass\n")
    _write(pkg / "a1_at_functions" / "real.py",
           "def real(x: int) -> int:\n    return x\n")
    _write(pkg / "a1_at_functions" / "__init__.py", "")
    cards = harvest_signatures(tmp_path, package="pkg")
    names = {c["name"] for c in cards}
    assert "real" in names
    assert "foo" not in names  # generated stem skipped
