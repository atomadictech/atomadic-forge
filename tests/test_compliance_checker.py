"""Tier verification -- Lane F W2 compliance checker."""
from __future__ import annotations
import json, copy
import pytest
from atomadic_forge.a1_at_functions.compliance_checker import (
    COMPLIANCE_FRAMEWORK_KEYS,
    check_compliance,
    check_compliance_framework,
    _VALID_STATUSES,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_LEAN4 = {
    "corpora": [
        {"name": "aethel-nexus-proofs", "sorry_count": 0, "theorem_count": 29},
        {"name": "mhed-toe-codex-v22",  "sorry_count": 0, "theorem_count": 538},
    ],
    "total_theorems": 567,
}
_LINEAGE_3 = {"chain_depth": 3, "parent_receipt_hash": "a" * 64}
_LINEAGE_1 = {"chain_depth": 1, "parent_receipt_hash": None}
_SIGS = {"sigstore": {"rekor_uuid": "abc123"}, "aaaa_nexus": None, "local_sign": None}


def _r(**ov) -> dict:
    """Minimal PASS receipt, override any field."""
    base = {
        "schema_version": "atomadic-forge.receipt/v1",
        "forge_version": "0.2.2",
        "verdict": "PASS",
        "project": {"name": "my-project", "language": "python"},
        "certify": {
            "score": 100.0,
            "axes": {
                "documentation_complete": True,
                "tests_present": True,
                "tier_layout_present": True,
                "no_upward_imports": True,
            },
            "issues": [],
        },
        "wire":   {"verdict": "PASS", "violation_count": 0, "auto_fixable": 0},
        "scout":  {"symbol_count": 50, "tier_distribution": {}, "effect_distribution": {}},
        "lean4_attestation": _LEAN4,
        "lineage": _LINEAGE_3,
        "signatures": _SIGS,
        "compliance_mappings": {},
    }
    base.update(ov)
    return base


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------

def test_framework_keys_length():
    assert len(COMPLIANCE_FRAMEWORK_KEYS) == 4


def test_framework_keys_contents():
    assert set(COMPLIANCE_FRAMEWORK_KEYS) == {"eu_ai_act", "sr_11_7", "fda_pccp", "cmmc_ai"}


def test_check_compliance_returns_all_keys():
    result = check_compliance(_r())
    assert set(result.keys()) == set(COMPLIANCE_FRAMEWORK_KEYS)


def test_valid_statuses_set():
    assert _VALID_STATUSES == {"PASS", "PARTIAL", "FAIL", "NOT_ASSESSED"}


def test_all_statuses_valid():
    result = check_compliance(_r())
    for v in result.values():
        assert v in _VALID_STATUSES, f"unexpected status {v!r}"


# ---------------------------------------------------------------------------
# Empty / None receipt
# ---------------------------------------------------------------------------

def test_empty_dict_all_not_assessed():
    assert check_compliance({}) == {k: "NOT_ASSESSED" for k in COMPLIANCE_FRAMEWORK_KEYS}


def test_none_receipt_all_not_assessed():
    assert check_compliance(None) == {k: "NOT_ASSESSED" for k in COMPLIANCE_FRAMEWORK_KEYS}


# ---------------------------------------------------------------------------
# Full PASS receipt
# ---------------------------------------------------------------------------

def test_full_pass_receipt_eu_ai_act():
    assert check_compliance(_r())["eu_ai_act"] == "PASS"


def test_full_pass_receipt_sr_11_7():
    assert check_compliance(_r())["sr_11_7"] == "PASS"


def test_full_pass_receipt_fda_pccp():
    assert check_compliance(_r())["fda_pccp"] == "PASS"


def test_full_pass_receipt_cmmc_ai():
    assert check_compliance(_r())["cmmc_ai"] == "PASS"


# ---------------------------------------------------------------------------
# Wire FAIL propagation
# ---------------------------------------------------------------------------

def test_wire_fail_eu_ai_act():
    r = _r(wire={"verdict": "FAIL", "violation_count": 3, "auto_fixable": 0})
    assert check_compliance(r)["eu_ai_act"] == "FAIL"


def test_wire_fail_sr_11_7():
    r = _r(wire={"verdict": "FAIL", "violation_count": 1, "auto_fixable": 0})
    assert check_compliance(r)["sr_11_7"] == "FAIL"


def test_wire_fail_cmmc_ai():
    r = _r(wire={"verdict": "FAIL", "violation_count": 2, "auto_fixable": 0})
    assert check_compliance(r)["cmmc_ai"] == "FAIL"


def test_wire_fail_does_not_affect_fda_pccp():
    # FDA PCCP does not check wire directly
    r = _r(wire={"verdict": "FAIL", "violation_count": 1, "auto_fixable": 0})
    result = check_compliance(r)["fda_pccp"]
    assert result in _VALID_STATUSES


# ---------------------------------------------------------------------------
# Low score propagation
# ---------------------------------------------------------------------------

def test_low_score_eu_ai_act_fail():
    r = _r(certify={"score": 50.0, "axes": {
        "documentation_complete": True, "tests_present": True,
        "tier_layout_present": True, "no_upward_imports": True}, "issues": []})
    assert check_compliance(r)["eu_ai_act"] == "FAIL"


def test_low_score_sr_11_7_fail():
    r = _r(certify={"score": 65.0, "axes": {
        "documentation_complete": True, "tests_present": True,
        "tier_layout_present": True, "no_upward_imports": True}, "issues": []})
    assert check_compliance(r)["sr_11_7"] == "FAIL"


def test_low_score_fda_pccp_partial():
    # score < 80 but >= 0 with chain_depth >= 1 → PARTIAL
    r = _r(certify={"score": 75.0, "axes": {
        "documentation_complete": True, "tests_present": True,
        "tier_layout_present": True, "no_upward_imports": True}, "issues": []})
    assert check_compliance(r)["fda_pccp"] == "PARTIAL"


# ---------------------------------------------------------------------------
# Missing lean4 → PARTIAL (not FAIL)
# ---------------------------------------------------------------------------

def test_no_lean4_eu_ai_act_partial():
    r = _r(lean4_attestation={})
    assert check_compliance(r)["eu_ai_act"] == "PARTIAL"


def test_lean4_with_sorry_eu_ai_act_partial():
    r = _r(lean4_attestation={"corpora": [
        {"name": "bad", "sorry_count": 3, "theorem_count": 10}
    ]})
    assert check_compliance(r)["eu_ai_act"] == "PARTIAL"


# ---------------------------------------------------------------------------
# Lineage
# ---------------------------------------------------------------------------

def test_no_lineage_fda_pccp_fail():
    r = _r(lineage={})
    assert check_compliance(r)["fda_pccp"] == "FAIL"


def test_lineage_depth_1_sr_11_7_partial():
    r = _r(lineage=_LINEAGE_1)
    assert check_compliance(r)["sr_11_7"] == "PARTIAL"


# ---------------------------------------------------------------------------
# Missing project fields
# ---------------------------------------------------------------------------

def test_missing_project_name_eu_ai_act_not_assessed():
    r = _r(project={"language": "python"})
    assert check_compliance(r)["eu_ai_act"] == "NOT_ASSESSED"


def test_missing_tier_layout_sr_11_7_not_assessed():
    r = _r(certify={"score": 100.0, "axes": {
        "documentation_complete": True, "tests_present": True,
        "tier_layout_present": False, "no_upward_imports": True}, "issues": []})
    assert check_compliance(r)["sr_11_7"] == "NOT_ASSESSED"


def test_missing_schema_version_fda_pccp_not_assessed():
    r = _r()
    del r["schema_version"]
    assert check_compliance(r)["fda_pccp"] == "NOT_ASSESSED"


# ---------------------------------------------------------------------------
# check_compliance_framework
# ---------------------------------------------------------------------------

def test_single_framework_eu_ai_act():
    assert check_compliance_framework(_r(), "eu_ai_act") == "PASS"


def test_single_framework_unknown_key():
    assert check_compliance_framework(_r(), "gdpr_2025") == "NOT_ASSESSED"


def test_single_framework_cmmc_ai_partial_no_sigs():
    r = _r(signatures={"sigstore": None, "aaaa_nexus": None, "local_sign": None})
    assert check_compliance_framework(r, "cmmc_ai") == "PARTIAL"


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------

def test_json_roundtrip():
    result = check_compliance(_r())
    dumped = json.dumps(result)
    loaded = json.loads(dumped)
    assert loaded == result
