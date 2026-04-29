"""Tier verification — Golden Path Lane A W1: card_renderer.

Snapshot-style tests of render_receipt_card. The viral-demo footage
(Lane E W2) screen-grabs this exact output, so the structural shape
needs to be stable across releases.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from atomadic_forge.a1_at_functions.card_renderer import render_receipt_card
from atomadic_forge.a1_at_functions.receipt_emitter import build_receipt


_CERTIFY_PASS = {
    "score": 100.0,
    "documentation_complete": True,
    "tests_present": True,
    "tier_layout_present": True,
    "no_upward_imports": True,
    "issues": [],
}

_WIRE_PASS = {
    "verdict": "PASS", "violation_count": 0, "auto_fixable": 0,
    "violations": [],
}

_SCOUT = {
    "symbol_count": 14,
    "tier_distribution": {"a1_at_functions": 14},
    "effect_distribution": {"pure": 14, "state": 0, "io": 0},
    "primary_language": "python",
}


def _receipt(**overrides):
    return build_receipt(
        certify_result=overrides.pop("certify", _CERTIFY_PASS),
        wire_report=overrides.pop("wire", _WIRE_PASS),
        scout_report=overrides.pop("scout", _SCOUT),
        project_name=overrides.pop("project_name", "demo"),
        project_root=overrides.pop("project_root", Path("/tmp/demo")),
        forge_version=overrides.pop("forge_version", "0.2.2"),
        compute_artifact_hashes=False,
        **overrides,
    )


# ---- shape invariants ---------------------------------------------------

def test_card_default_width_60():
    out = render_receipt_card(_receipt())
    for line in out.splitlines():
        # Box-drawing chars are single columns visually, so len == width.
        assert len(line) == 60, f"line wrong width: {len(line)} → {line!r}"


def test_card_explicit_width_80():
    out = render_receipt_card(_receipt(), width=80)
    for line in out.splitlines():
        assert len(line) == 80


def test_card_too_narrow_raises():
    with pytest.raises(ValueError):
        render_receipt_card(_receipt(), width=10)


def test_card_top_and_bottom_borders():
    out = render_receipt_card(_receipt())
    lines = out.splitlines()
    assert lines[0].startswith("╔") and lines[0].endswith("╗")
    assert lines[-1].startswith("╚") and lines[-1].endswith("╝")


def test_card_includes_schema_version_in_title_row():
    out = render_receipt_card(_receipt())
    assert "Atomadic Forge Receipt" in out
    assert "atomadic-forge.receipt/v1" in out


# ---- verdict variants ---------------------------------------------------

def test_card_pass_uses_check_glyph():
    out = render_receipt_card(_receipt())
    assert "✓ PASS" in out


def test_card_fail_uses_cross_glyph():
    out = render_receipt_card(_receipt(
        certify=dict(_CERTIFY_PASS, score=50.0,
                      documentation_complete=False),
    ))
    assert "✗ FAIL" in out


def test_card_refine_uses_arrow_glyph():
    out = render_receipt_card(_receipt(verdict_override="REFINE"))
    assert "↻ REFINE" in out


def test_card_quarantine_uses_pause_glyph():
    out = render_receipt_card(_receipt(verdict_override="QUARANTINE"))
    assert "⏸ QUARANTINE" in out


# ---- content rows -------------------------------------------------------

def test_card_certify_score_visible():
    out = render_receipt_card(_receipt())
    assert "100.0 / 100" in out


def test_card_certify_axis_glyphs_visible():
    out = render_receipt_card(_receipt(
        certify=dict(_CERTIFY_PASS, no_upward_imports=False),
    ))
    assert "wire ✗" in out
    assert "docs ✓" in out


def test_card_wire_summary_pluralizes():
    one_violation = render_receipt_card(_receipt(
        wire=dict(_WIRE_PASS, verdict="FAIL", violation_count=1),
    ))
    assert "1 violation)" in one_violation
    assert "violations)" not in one_violation
    multi = render_receipt_card(_receipt(
        wire=dict(_WIRE_PASS, verdict="FAIL", violation_count=5),
    ))
    assert "5 violations)" in multi


def test_card_wire_auto_fixable_visible():
    out = render_receipt_card(_receipt(
        wire=dict(_WIRE_PASS, verdict="FAIL",
                   violation_count=3, auto_fixable=2),
    ))
    assert "3 viol, 2 auto-fix" in out


def test_card_scout_symbol_count():
    out = render_receipt_card(_receipt())
    assert "14 symbols" in out
    out_one = render_receipt_card(_receipt(scout=dict(_SCOUT, symbol_count=1)))
    assert "1 symbol  " in out_one  # singular


# ---- attestation + signature rows --------------------------------------

def test_card_unattested_says_no_attestation():
    out = render_receipt_card(_receipt())
    assert "no attestation" in out


def test_card_attestation_summary():
    att = {"corpora": [
        {"name": "aethel-nexus-proofs", "repo_url": "u", "ref_sha": "s",
         "theorem_count": 29, "sorry_count": 0, "axiom_count": 0},
        {"name": "mhed-toe-codex-v22", "repo_url": "u", "ref_sha": "s",
         "theorem_count": 538, "sorry_count": 0, "axiom_count": 0},
    ], "total_theorems": 567, "summary": "567 / 0 sorry"}
    out = render_receipt_card(_receipt(lean4_attestation=att))
    assert "567 theorems" in out
    assert "2 corpuses" in out  # plural form
    assert "0 sorry" in out


def test_card_unsigned_state_visible():
    out = render_receipt_card(_receipt())
    assert "UNSIGNED" in out


def test_card_signed_state_when_both_signatures():
    sigs = {
        "sigstore": {"rekor_uuid": "x", "log_index": 1, "bundle_path": "p"},
        "aaaa_nexus": {"signature": "s", "key_id": "k", "issuer": "i",
                        "issued_at_utc": "t", "verify_endpoint": "/v"},
    }
    out = render_receipt_card(_receipt(signatures=sigs))
    assert "SIGNED" in out
    assert "Sigstore + AAAA-Nexus" in out


# ---- VCS / project line -------------------------------------------------

def test_card_includes_vcs_branch_and_short_sha():
    vcs = {"head_sha": "abcdef1234567890" * 2, "short_sha": "abcdef1",
           "branch": "main", "remote_url": "u", "dirty": False}
    out = render_receipt_card(_receipt(vcs=vcs))
    assert "main@abcdef1" in out


def test_card_no_vcs_means_no_branch_suffix():
    out = render_receipt_card(_receipt())
    assert "@" not in [
        l for l in out.splitlines() if l.startswith("│ demo ")
    ][0].replace("│", "")
