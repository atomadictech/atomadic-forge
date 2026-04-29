"""Tier verification — Golden Path Lane A W5: F-code registry.

Pins the F-code registry's published contract. Adding a code is
additive; renaming or renumbering one is a major schema bump and
must update every test in this file.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import typer.testing

from atomadic_forge.a0_qk_constants.error_codes import (
    F_CODE_REGISTRY,
    all_auto_fixable_fcodes,
    fcode_for_certify_axis,
    fcode_for_tier_violation,
    get_fcode,
)
from atomadic_forge.a1_at_functions.wire_check import scan_violations
from atomadic_forge.a4_sy_orchestration.cli import app

runner = typer.testing.CliRunner()


_FCODE_REGEX = re.compile(r"^F\d{4}$")


# ---- registry shape -----------------------------------------------------

def test_every_code_matches_fixed_format():
    for code in F_CODE_REGISTRY:
        assert _FCODE_REGEX.match(code), f"bad shape: {code!r}"


def test_every_entry_is_self_consistent():
    for code, entry in F_CODE_REGISTRY.items():
        assert entry["code"] == code
        assert entry["name"]
        assert entry["severity"] in {"info", "warn", "error"}
        assert entry["title"]
        assert isinstance(entry["auto_fixable"], bool)
        assert entry["doc_anchor"]


def test_codes_are_unique():
    assert len(F_CODE_REGISTRY) == len(set(F_CODE_REGISTRY.keys()))


def test_names_are_unique():
    names = [e["name"] for e in F_CODE_REGISTRY.values()]
    assert len(names) == len(set(names)), (
        "F-code names must be unique — repeated slugs cause grep ambiguity"
    )


# ---- canonical mapping pinned -------------------------------------------

def test_w5_seed_codes_pinned():
    """The seed set is fixed; adding entries here is additive but
    renaming or renumbering is a breaking change. Updated for Lane D
    W11 (F0100..F0106 sidecar codes)."""
    pinned = {
        # W5 wire / certify seed
        "F0040": "a0-cannot-import-anything",
        "F0041": "a1-imports-a2",
        "F0042": "a1-imports-a3",
        "F0043": "a1-imports-a4",
        "F0044": "a2-imports-a3",
        "F0045": "a2-imports-a4",
        "F0046": "a3-imports-a4",
        "F0049": "unknown-tier-violation",
        "F0050": "documentation-missing",
        "F0051": "tests-missing",
        "F0052": "tier-layout-incomplete",
        "F0053": "upward-imports-present",
        # Lane D W11 sidecar drift
        "F0100": "sidecar-source-unparseable",
        "F0101": "sidecar-declares-missing-symbol",
        "F0102": "sidecar-coverage-incomplete",
        "F0103": "sidecar-pure-violates-purity",
        "F0106": "sidecar-tier-mismatch",
    }
    for code, name in pinned.items():
        entry = F_CODE_REGISTRY.get(code)
        assert entry is not None, f"{code} missing from registry"
        assert entry["name"] == name, (
            f"{code} renamed: registry={entry['name']!r} expected={name!r}"
        )


def test_sidecar_s_to_f_mapping():
    from atomadic_forge.a0_qk_constants.error_codes import SIDECAR_S_TO_F
    assert SIDECAR_S_TO_F["S0001"] == "F0101"
    assert SIDECAR_S_TO_F["S0003"] == "F0103"
    # Every S-code mapping points at a registered F-code.
    for s, f in SIDECAR_S_TO_F.items():
        assert f in F_CODE_REGISTRY, (
            f"{s} maps to {f} but {f} is not registered"
        )


def test_sidecar_validator_attaches_fcode():
    """The validator promotes S-codes to f_code on each finding."""
    from atomadic_forge.a1_at_functions.sidecar_parser import parse_sidecar_text
    from atomadic_forge.a1_at_functions.sidecar_validator import validate_sidecar
    parse = parse_sidecar_text(
        "schema_version: atomadic-forge.sidecar/v1\n"
        "target: x.py\n"
        "symbols:\n"
        "  - name: ghost\n"
        "    effect: Pure\n"
    )
    rep = validate_sidecar(parse["sidecar"], source_text="def real(): pass\n")
    s001_findings = [f for f in rep["findings"] if f["code"] == "S0001"]
    assert s001_findings
    assert s001_findings[0]["f_code"] == "F0101"


# ---- lookup helpers -----------------------------------------------------

def test_fcode_for_tier_violation_canonical_pairs():
    assert fcode_for_tier_violation("a1_at_functions", "a2_mo_composites") == "F0041"
    assert fcode_for_tier_violation("a1_at_functions", "a3_og_features") == "F0042"
    assert fcode_for_tier_violation("a1_at_functions", "a4_sy_orchestration") == "F0043"
    assert fcode_for_tier_violation("a2_mo_composites", "a3_og_features") == "F0044"
    assert fcode_for_tier_violation("a2_mo_composites", "a4_sy_orchestration") == "F0045"
    assert fcode_for_tier_violation("a3_og_features", "a4_sy_orchestration") == "F0046"


def test_fcode_for_tier_violation_a0_is_special():
    """a0 may not import anything — F0040 covers any from_tier=a0 pair."""
    assert fcode_for_tier_violation("a0_qk_constants", "a1_at_functions") == "F0040"
    assert fcode_for_tier_violation("a0_qk_constants", "a4_sy_orchestration") == "F0040"


def test_fcode_for_tier_violation_unknown_falls_back_to_F0049():
    assert fcode_for_tier_violation("custom_tier", "a3_og_features") == "F0049"


def test_fcode_for_certify_axis():
    assert fcode_for_certify_axis("documentation_complete") == "F0050"
    assert fcode_for_certify_axis("tests_present") == "F0051"
    assert fcode_for_certify_axis("tier_layout_present") == "F0052"
    assert fcode_for_certify_axis("no_upward_imports") == "F0053"
    assert fcode_for_certify_axis("nonsense_axis") == ""


def test_get_fcode_returns_none_for_unregistered():
    assert get_fcode("F0042") is not None
    assert get_fcode("F9999") is None


def test_all_auto_fixable_fcodes_sorted_subset():
    fixable = all_auto_fixable_fcodes()
    assert "F0042" in fixable      # a1-imports-a3 is fixable
    assert "F0040" not in fixable  # a0 violations need human review
    assert "F0049" not in fixable  # unknown shape needs review
    assert list(fixable) == sorted(fixable), "must be sorted for stable iteration"


# ---- wire_check integration --------------------------------------------

def test_wire_violations_carry_fcode_python(tmp_path):
    pkg = tmp_path / "pkg"
    a1 = pkg / "a1_at_functions"
    a2 = pkg / "a2_mo_composites"
    a1.mkdir(parents=True); a2.mkdir(parents=True)
    (a2 / "store.py").write_text(
        '"""a2 store."""\nclass Store:\n    pass\n', encoding="utf-8")
    (a1 / "h.py").write_text(
        "from ..a2_mo_composites.store import Store\n", encoding="utf-8")
    report = scan_violations(pkg)
    assert report["violation_count"] >= 1
    v = report["violations"][0]
    assert v["f_code"] == "F0041"
    assert v["language"] == "python"


def test_wire_violations_carry_fcode_a3_to_a4(tmp_path):
    pkg = tmp_path / "pkg"
    a3 = pkg / "a3_og_features"
    a4 = pkg / "a4_sy_orchestration"
    a3.mkdir(parents=True); a4.mkdir(parents=True)
    (a4 / "cli.py").write_text(
        '"""a4."""\ndef main():\n    pass\n', encoding="utf-8")
    (a3 / "feat.py").write_text(
        "from ..a4_sy_orchestration.cli import main\n", encoding="utf-8")
    report = scan_violations(pkg)
    fcodes = {v["f_code"] for v in report["violations"]}
    assert "F0046" in fcodes


# ---- CLI: F-code prefix in human output --------------------------------

def test_cli_wire_human_output_prefixes_with_fcode(tmp_path):
    pkg = tmp_path / "pkg"
    a1 = pkg / "a1_at_functions"
    a2 = pkg / "a2_mo_composites"
    a1.mkdir(parents=True); a2.mkdir(parents=True)
    (a2 / "store.py").write_text(
        '"""a2."""\nclass Store:\n    pass\n', encoding="utf-8")
    (a1 / "h.py").write_text(
        "from ..a2_mo_composites.store import Store\n", encoding="utf-8")
    result = runner.invoke(app, ["wire", str(pkg)])
    assert result.exit_code == 0
    assert "[F0041]" in result.stdout


def test_cli_wire_json_carries_fcode(tmp_path):
    pkg = tmp_path / "pkg"
    a1 = pkg / "a1_at_functions"
    a3 = pkg / "a3_og_features"
    a1.mkdir(parents=True); a3.mkdir(parents=True)
    (a3 / "feat.py").write_text(
        '"""a3."""\nclass F:\n    pass\n', encoding="utf-8")
    (a1 / "h.py").write_text(
        "from ..a3_og_features.feat import F\n", encoding="utf-8")
    result = runner.invoke(app, ["wire", str(pkg), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert any(v["f_code"] == "F0042" for v in data["violations"])


# ---- a0 tier discipline -------------------------------------------------

def test_error_codes_module_imports_only_typing():
    """a0 invariant: error_codes.py holds only data + lookups; imports
    only __future__ and typing."""
    src = (
        Path(__file__).resolve().parents[1]
        / "src" / "atomadic_forge" / "a0_qk_constants" / "error_codes.py"
    ).read_text(encoding="utf-8")
    imports = [ln.strip() for ln in src.splitlines()
               if ln.startswith(("import ", "from "))]
    for ln in imports:
        assert ln.startswith(("from __future__", "from typing")), (
            f"a0/error_codes.py imports outside __future__ / typing: {ln!r}"
        )
