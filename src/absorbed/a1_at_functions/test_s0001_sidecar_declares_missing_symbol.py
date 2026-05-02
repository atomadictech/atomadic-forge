"""Tier verification — Golden Path Lane D W11: sidecar cross-validator.

Pins the seven drift-class detection codes:
  S0000 — source did not parse
  S0001 — sidecar declares a missing symbol
  S0002 — source has an undeclared public symbol
  S0003 — Pure-declared symbol violates purity (IO / Net / Random)
  S0006 — declared tier mismatches detected path tier
"""
from __future__ import annotations

import textwrap

import typer.testing

from atomadic_forge.a1_at_functions.sidecar_parser import parse_sidecar_text
from atomadic_forge.a1_at_functions.sidecar_validator import (
    SCHEMA_VERSION_VALIDATE_V1,
    validate_sidecar,
)
from atomadic_forge.a4_sy_orchestration.cli import app

runner = typer.testing.CliRunner()


def _sidecar(text: str):
    rep = parse_sidecar_text(text)
    assert rep["sidecar"] is not None, rep["errors"]
    return rep["sidecar"]


# ---- happy path --------------------------------------------------------

_GOOD_SOURCE = textwrap.dedent('''
    def hash_password(plain: str) -> str:
        return plain.encode().hex()

    def login(username: str, password: str) -> str:
        return f"sess-{username}"
''').strip()

_GOOD_SIDECAR = textwrap.dedent('''
    schema_version: atomadic-forge.sidecar/v1
    target: auth.py
    symbols:
      - name: hash_password
        effect: Pure
      - name: login
        effect: NetIO
''').strip()


def test_validator_pass():
    sc = _sidecar(_GOOD_SIDECAR)
    rep = validate_sidecar(sc, source_text=_GOOD_SOURCE)
    assert rep["schema_version"] == SCHEMA_VERSION_VALIDATE_V1
    assert rep["verdict"] == "PASS"
    assert all(f["severity"] != "error" for f in rep["findings"])


# ---- drift classes -----------------------------------------------------

def test_s0000_unparseable_source():
    sc = _sidecar(_GOOD_SIDECAR)
    rep = validate_sidecar(sc, source_text="def broken( :\n    pass\n")
    assert rep["verdict"] == "unparseable"
    assert rep["findings"][0]["code"] == "S0000"


def test_s0001_sidecar_declares_missing_symbol():
    sc = _sidecar(textwrap.dedent('''
        schema_version: atomadic-forge.sidecar/v1
        target: auth.py
        symbols:
          - name: ghost
            effect: Pure
    ''').strip())
    rep = validate_sidecar(sc, source_text=_GOOD_SOURCE)
    codes = [f["code"] for f in rep["findings"]]
    assert "S0001" in codes
    assert rep["verdict"] == "FAIL"


def test_s0002_undeclared_public_symbol_warns():
    sc = _sidecar(textwrap.dedent('''
        schema_version: atomadic-forge.sidecar/v1
        target: auth.py
        symbols:
          - name: hash_password
            effect: Pure
    ''').strip())
    rep = validate_sidecar(sc, source_text=_GOOD_SOURCE)
    codes = [(f["code"], f["severity"]) for f in rep["findings"]]
    assert ("S0002", "warn") in codes
    # warn-only must NOT fail the verdict.
    assert rep["verdict"] == "PASS"


def test_s0003_pure_declared_but_does_io():
    src = textwrap.dedent('''
        from pathlib import Path
        def reader(p):
            return Path(p).read_text()
    ''').strip()
    sc = _sidecar(textwrap.dedent('''
        schema_version: atomadic-forge.sidecar/v1
        target: x.py
        symbols:
          - name: reader
            effect: Pure
    ''').strip())
    rep = validate_sidecar(sc, source_text=src)
    codes = [f["code"] for f in rep["findings"]]
    assert "S0003" in codes
    assert rep["verdict"] == "FAIL"


def test_s0003_pure_declared_but_does_net_io():
    src = textwrap.dedent('''
        import requests
        def fetch(u):
            return requests.get(u).json()
    ''').strip()
    sc = _sidecar(textwrap.dedent('''
        schema_version: atomadic-forge.sidecar/v1
        target: x.py
        symbols:
          - name: fetch
            effect: Pure
    ''').strip())
    rep = validate_sidecar(sc, source_text=src)
    assert rep["verdict"] == "FAIL"
    assert any("network" in f["message"] for f in rep["findings"])


def test_s0006_tier_mismatch_warns():
    src = "def helper():\n    return 1\n"
    sc = _sidecar(textwrap.dedent('''
        schema_version: atomadic-forge.sidecar/v1
        target: helper.py
        symbols:
          - name: helper
            effect: Pure
            tier: a3_og_features
    ''').strip())
    rep = validate_sidecar(
        sc, source_text=src,
        source_path="src/pkg/a1_at_functions/helper.py",
    )
    codes = [(f["code"], f["severity"]) for f in rep["findings"]]
    assert ("S0006", "warn") in codes
    # tier mismatch is warn-only -> still PASS.
    assert rep["verdict"] == "PASS"


# ---- CLI ---------------------------------------------------------------

def test_cli_sidecar_parse(tmp_path):
    f = tmp_path / "auth.py.forge"
    f.write_text(_GOOD_SIDECAR, encoding="utf-8")
    result = runner.invoke(app, ["sidecar", "parse", str(f)])
    assert result.exit_code == 0
    assert "Sidecar OK" in result.stdout


def test_cli_sidecar_parse_bad_yaml(tmp_path):
    f = tmp_path / "bad.py.forge"
    f.write_text("not: valid: : yaml :", encoding="utf-8")
    result = runner.invoke(app, ["sidecar", "parse", str(f)])
    assert result.exit_code == 1


def test_cli_sidecar_validate_pass(tmp_path):
    src = tmp_path / "auth.py"
    src.write_text(_GOOD_SOURCE, encoding="utf-8")
    sc = tmp_path / "auth.py.forge"
    sc.write_text(_GOOD_SIDECAR, encoding="utf-8")
    result = runner.invoke(app, ["sidecar", "validate", str(src)])
    assert result.exit_code == 0
    assert "verdict:  PASS" in result.stdout


def test_cli_sidecar_validate_fail(tmp_path):
    src = tmp_path / "auth.py"
    src.write_text(_GOOD_SOURCE, encoding="utf-8")
    sc = tmp_path / "auth.py.forge"
    sc.write_text(textwrap.dedent('''
        schema_version: atomadic-forge.sidecar/v1
        target: auth.py
        symbols:
          - name: ghost_function
            effect: Pure
    ''').strip(), encoding="utf-8")
    result = runner.invoke(app, ["sidecar", "validate", str(src)])
    assert result.exit_code == 1
    assert "S0001" in result.stdout
