"""Tier verification — Golden Path Lane D W8: .forge sidecar parser.

Pins the v1 spec contract:
  * required-fields shape
  * effect-kind enum
  * forward-compat (unknown fields preserved in 'extra')
  * graceful errors (no Python tracebacks for malformed YAML)
  * find_sidecar_for path convention
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from atomadic_forge.a0_qk_constants.sidecar_schema import (
    REQUIRED_SIDECAR_FIELDS,
    REQUIRED_SYMBOL_FIELDS,
    SCHEMA_VERSION_SIDECAR_V1,
    VALID_EFFECTS,
)
from atomadic_forge.a1_at_functions.sidecar_parser import (
    find_sidecar_for,
    parse_sidecar_file,
    parse_sidecar_text,
)


# ---- a0 schema constants ----------------------------------------------

def test_schema_version_pinned():
    assert SCHEMA_VERSION_SIDECAR_V1 == "atomadic-forge.sidecar/v1"


def test_required_fields_pinned():
    assert set(REQUIRED_SIDECAR_FIELDS) == {
        "schema_version", "target", "symbols",
    }
    assert set(REQUIRED_SYMBOL_FIELDS) == {"name", "effect"}


def test_valid_effects_pinned():
    assert set(VALID_EFFECTS) == {
        "Pure", "IO", "NetIO", "KeyedCache",
        "Logging", "Random", "Mutation",
    }


# ---- happy path --------------------------------------------------------

_GOOD_SIDECAR = textwrap.dedent('''
    schema_version: atomadic-forge.sidecar/v1
    target: users/auth.py

    symbols:
      - name: login
        effect: NetIO
        tier: a3_og_features
        compose_with:
          - users.session.SessionStore.put
        proves:
          - "lemma:login_emits_session"

      - name: hash_password
        effect: Pure
        tier: a1_at_functions
''').strip()


def test_parse_good_sidecar_text():
    rep = parse_sidecar_text(_GOOD_SIDECAR)
    assert rep["errors"] == []
    sc = rep["sidecar"]
    assert sc is not None
    assert sc["schema_version"] == SCHEMA_VERSION_SIDECAR_V1
    assert sc["target"] == "users/auth.py"
    assert len(sc["symbols"]) == 2
    s0 = sc["symbols"][0]
    assert s0["name"] == "login"
    assert s0["effect"] == "NetIO"
    assert s0["compose_with"] == ["users.session.SessionStore.put"]
    assert "lemma:login_emits_session" in s0["proves"]


def test_parse_sidecar_file(tmp_path):
    f = tmp_path / "auth.py.forge"
    f.write_text(_GOOD_SIDECAR, encoding="utf-8")
    rep = parse_sidecar_file(f)
    assert rep["errors"] == []
    assert rep["sidecar"] is not None


def test_find_sidecar_for_python():
    p = find_sidecar_for(Path("src/pkg/users/auth.py"))
    assert str(p).endswith("auth.py.forge")


def test_find_sidecar_for_typescript():
    p = find_sidecar_for(Path("src/pkg/users/auth.ts"))
    assert str(p).endswith("auth.ts.forge")


# ---- error paths -------------------------------------------------------

def test_parse_yaml_error_returns_error_not_raise():
    rep = parse_sidecar_text("not: valid: yaml: : :")
    assert rep["sidecar"] is None
    assert any("YAML parse error" in e for e in rep["errors"])


def test_parse_missing_required_fields():
    rep = parse_sidecar_text("schema_version: atomadic-forge.sidecar/v1")
    assert rep["sidecar"] is None
    assert any("missing required" in e for e in rep["errors"])


def test_parse_non_mapping_top_level():
    rep = parse_sidecar_text("- not\n- a\n- mapping\n")
    assert rep["sidecar"] is None
    assert any("must be a mapping" in e for e in rep["errors"])


def test_parse_missing_file_returns_error():
    rep = parse_sidecar_file(Path("/definitely/does/not/exist.forge"))
    assert rep["sidecar"] is None
    assert any("not found" in e for e in rep["errors"])


def test_parse_symbol_missing_name_or_effect():
    sc = textwrap.dedent('''
        schema_version: atomadic-forge.sidecar/v1
        target: users/auth.py
        symbols:
          - name: x
            # missing effect
    ''').strip()
    rep = parse_sidecar_text(sc)
    assert any("symbols[0] missing required 'effect'" in e
               for e in rep["errors"])


# ---- forward-compat ----------------------------------------------------

def test_parse_unknown_top_level_field_preserved_in_extra():
    sc = textwrap.dedent('''
        schema_version: atomadic-forge.sidecar/v1
        target: users/auth.py
        symbols: []
        future_field: hello
    ''').strip()
    rep = parse_sidecar_text(sc)
    assert rep["sidecar"]["extra"] == {"future_field": "hello"}


def test_parse_unknown_effect_warns_but_succeeds():
    sc = textwrap.dedent('''
        schema_version: atomadic-forge.sidecar/v1
        target: users/auth.py
        symbols:
          - name: login
            effect: SuperFutureEffect
    ''').strip()
    rep = parse_sidecar_text(sc)
    assert rep["sidecar"] is not None
    assert any("not in VALID_EFFECTS" in w for w in rep["warnings"])
    assert rep["sidecar"]["symbols"][0]["effect"] == "SuperFutureEffect"


def test_parse_wrong_schema_version_warns():
    sc = textwrap.dedent('''
        schema_version: atomadic-forge.sidecar/v999
        target: users/auth.py
        symbols: []
    ''').strip()
    rep = parse_sidecar_text(sc)
    assert any("expected" in w for w in rep["warnings"])


# ---- a0 tier discipline -----------------------------------------------

def test_sidecar_schema_module_imports_only_typing():
    src = (Path(__file__).resolve().parents[1]
           / "src" / "atomadic_forge" / "a0_qk_constants"
           / "sidecar_schema.py").read_text(encoding="utf-8")
    imports = [ln.strip() for ln in src.splitlines()
               if ln.startswith(("import ", "from "))]
    for ln in imports:
        assert ln.startswith(("from __future__", "from typing")), (
            f"a0/sidecar_schema.py imports outside __future__/typing: {ln!r}"
        )
