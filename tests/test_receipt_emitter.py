"""Tier verification — Golden Path Lane A W1: receipt_emitter.

Pure-function coverage of build_receipt + receipt_to_json. Round-trips
the docs/RECEIPT.md worked example through the schema TypedDict.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from atomadic_forge.a0_qk_constants.receipt_schema import (
    REQUIRED_RECEIPT_V1_FIELDS,
    SCHEMA_VERSION_V1,
    VALID_VERDICTS,
)
from atomadic_forge.a1_at_functions.receipt_emitter import (
    build_receipt,
    receipt_to_json,
)

_CERTIFY_PASS = {
    "schema_version": "atomadic-forge.certify/v1",
    "score": 100.0,
    "documentation_complete": True,
    "tests_present": True,
    "tier_layout_present": True,
    "no_upward_imports": True,
    "issues": [],
}

_WIRE_PASS = {
    "schema_version": "atomadic-forge.wire/v1",
    "verdict": "PASS",
    "violation_count": 0,
    "auto_fixable": 0,
    "violations": [],
}

_SCOUT = {
    "schema_version": "atomadic-forge.scout/v1",
    "symbol_count": 14,
    "tier_distribution": {"a1_at_functions": 14},
    "effect_distribution": {"pure": 14, "state": 0, "io": 0},
    "primary_language": "python",
    "language_distribution": {"python": 2, "javascript": 0, "typescript": 0},
}


def _build(*, certify=None, wire=None, scout=None, **overrides):
    return build_receipt(
        certify_result=certify or _CERTIFY_PASS,
        wire_report=wire or _WIRE_PASS,
        scout_report=scout or _SCOUT,
        project_name=overrides.pop("project_name", "demo"),
        project_root=overrides.pop("project_root", Path("/tmp/demo")),
        forge_version=overrides.pop("forge_version", "0.2.2-test"),
        compute_artifact_hashes=overrides.pop("compute_artifact_hashes", False),
        **overrides,
    )


# ---- required-field plumbing -------------------------------------------

def test_build_receipt_populates_required_v1_fields():
    r = _build()
    for field in REQUIRED_RECEIPT_V1_FIELDS:
        assert field in r, f"required field {field!r} missing"


def test_build_receipt_schema_version_v1():
    r = _build()
    assert r["schema_version"] == SCHEMA_VERSION_V1


def test_build_receipt_generated_at_utc_format():
    import re
    r = _build()
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
                    r["generated_at_utc"])


# ---- verdict-decision contract -----------------------------------------

def test_verdict_pass_when_wire_pass_and_score_meets_threshold():
    r = _build(certify=dict(_CERTIFY_PASS, score=100.0))
    assert r["verdict"] == "PASS"


def test_verdict_fail_when_wire_fails():
    r = _build(wire=dict(_WIRE_PASS, verdict="FAIL", violation_count=3))
    assert r["verdict"] == "FAIL"


def test_verdict_fail_when_score_below_threshold():
    r = _build(certify=dict(_CERTIFY_PASS, score=72.0))
    # Default threshold = 100.0
    assert r["verdict"] == "FAIL"


def test_custom_threshold_changes_verdict():
    r = _build(
        certify=dict(_CERTIFY_PASS, score=72.0),
        certify_threshold=70.0,
    )
    assert r["verdict"] == "PASS"


def test_verdict_override_refine():
    r = _build(verdict_override="REFINE")
    assert r["verdict"] == "REFINE"


def test_verdict_override_quarantine():
    r = _build(verdict_override="QUARANTINE")
    assert r["verdict"] == "QUARANTINE"


def test_verdict_override_invalid_raises():
    with pytest.raises(ValueError):
        _build(verdict_override="MAYBE")


# ---- shape tests --------------------------------------------------------

def test_certify_axes_block_populated():
    r = _build()
    axes = r["certify"]["axes"]
    assert axes["documentation_complete"] is True
    assert axes["tests_present"] is True
    assert axes["tier_layout_present"] is True
    assert axes["no_upward_imports"] is True


def test_wire_block_carries_counts():
    r = _build(wire=dict(_WIRE_PASS, verdict="FAIL",
                          violation_count=5, auto_fixable=2))
    assert r["wire"]["verdict"] == "FAIL"
    assert r["wire"]["violation_count"] == 5
    assert r["wire"]["auto_fixable"] == 2


def test_scout_block_passes_through_distributions():
    r = _build()
    assert r["scout"]["primary_language"] == "python"
    assert r["scout"]["tier_distribution"] == {"a1_at_functions": 14}


def test_optional_blocks_default_to_empty_or_none():
    r = _build()
    assert r["assimilate_digest"] is None
    assert r["artifacts"] == []
    assert r["signatures"]["sigstore"] is None
    assert r["signatures"]["aaaa_nexus"] is None
    assert r["lean4_attestation"] == {}
    assert r["lineage"] == {}
    assert r["compliance_mappings"] == {}
    assert r["notes"] == []
    assert r["extra"] == {}


def test_optional_blocks_pass_through(tmp_path):
    sig = {"sigstore": {"rekor_uuid": "abc", "log_index": 1,
                         "bundle_path": "x"},
           "aaaa_nexus": None}
    att = {"corpora": [{"name": "aethel-nexus-proofs", "repo_url": "u",
                         "ref_sha": "s", "theorem_count": 29,
                         "sorry_count": 0, "axiom_count": 0}],
           "total_theorems": 29, "summary": "29 / 0 sorry / 0 axioms"}
    lin = {"lineage_path": "vanguard://x/y", "parent_receipt_hash": None,
           "chain_depth": 1}
    r = _build(
        signatures=sig, lean4_attestation=att, lineage=lin,
        notes=["one note"], compliance_mappings={"eu_ai_act": "pending"},
    )
    assert r["signatures"]["sigstore"]["rekor_uuid"] == "abc"
    assert r["lean4_attestation"]["total_theorems"] == 29
    assert r["lineage"]["lineage_path"] == "vanguard://x/y"
    assert r["notes"] == ["one note"]
    assert r["compliance_mappings"] == {"eu_ai_act": "pending"}


# ---- artifact gathering -------------------------------------------------

def test_artifacts_picked_up_from_atomadic_forge_dir(tmp_path):
    d = tmp_path / ".atomadic-forge"
    d.mkdir()
    (d / "scout.json").write_text('{"x":1}', encoding="utf-8")
    (d / "wire.json").write_text('{"y":2}', encoding="utf-8")
    r = _build(project_root=tmp_path, compute_artifact_hashes=True)
    by_name = {a["name"]: a for a in r["artifacts"]}
    assert "scout" in by_name and "wire" in by_name
    # SHA-256 hex digest length = 64 chars
    assert len(by_name["scout"]["sha256"]) == 64
    assert len(by_name["wire"]["sha256"]) == 64


def test_artifacts_respect_compute_hashes_false(tmp_path):
    d = tmp_path / ".atomadic-forge"
    d.mkdir()
    (d / "scout.json").write_text("{}", encoding="utf-8")
    r = _build(project_root=tmp_path, compute_artifact_hashes=False)
    assert r["artifacts"][0]["sha256"] is None


# ---- JSON round-trip ----------------------------------------------------

def test_receipt_to_json_roundtrips():
    r = _build()
    text = receipt_to_json(r)
    decoded = json.loads(text)
    assert decoded["schema_version"] == SCHEMA_VERSION_V1
    assert decoded["verdict"] in VALID_VERDICTS
    for f in REQUIRED_RECEIPT_V1_FIELDS:
        assert f in decoded


def test_receipt_to_json_indent_is_stable():
    r = _build()
    assert "\n  " in receipt_to_json(r, indent=2)
    assert "\n    " in receipt_to_json(r, indent=4)
