"""Tier verification -- Lane F CS-1 renderer.

Tests for a1_at_functions/cs1_renderer.py.  Pure unit tests: no I/O,
no Receipt files on disk.  Fixtures provide minimal but valid
ForgeReceiptV1 dicts; individual tests override only the field under test.
"""
from __future__ import annotations

import json

import pytest

from atomadic_forge.a1_at_functions.cs1_renderer import (
    CS1_SCHEMA_VERSION,
    render_cs1,
    render_cs1_markdown,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_LEAN4 = {
    "corpora": [
        {
            "name": "aethel-nexus-proofs",
            "repo_url": "https://example.com/aethel",
            "ref_sha": "deadbeefdeadbeefdeadbeef",
            "theorem_count": 29,
            "sorry_count": 0,
            "axiom_count": 0,
        },
        {
            "name": "mhed-toe-codex-v22",
            "repo_url": "https://example.com/mhed",
            "ref_sha": "cafebabecafebabecafebabe",
            "theorem_count": 538,
            "sorry_count": 0,
            "axiom_count": 0,
        },
    ],
    "total_theorems": 567,
    "summary": "567 / 0 sorry",
}

_LINEAGE = {
    "lineage_path": "/v1/forge/lineage/demo/1",
    "parent_receipt_hash": "a" * 64,
    "chain_depth": 3,
}

_SIGSTORE = {
    "rekor_uuid": "abc123",
    "log_index": 42,
    "bundle_path": ".atomadic-forge/bundle.json",
}

_NEXUS_SIG = {
    "signature": "c2lnbmF0dXJl",
    "key_id": "key-001",
    "issuer": "aaaa-nexus.atomadic.tech",
    "issued_at_utc": "2026-04-29T00:00:00Z",
    "verify_endpoint": "/v1/verify/forge-receipt",
}


def _make_receipt(**overrides) -> dict:
    base: dict = {
        "schema_version": "atomadic-forge.receipt/v1",
        "generated_at_utc": "2026-04-29T00:00:00Z",
        "forge_version": "0.2.2",
        "verdict": "PASS",
        "project": {
            "name": "demo",
            "language": "python",
            "languages": {"python": 62},
        },
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
        "wire": {"verdict": "PASS", "violation_count": 0, "auto_fixable": 0},
        "scout": {
            "symbol_count": 14,
            "tier_distribution": {"a1_at_functions": 14},
            "effect_distribution": {"pure": 14},
            "primary_language": "python",
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Schema and required fields
# ---------------------------------------------------------------------------

def test_cs1_schema_version_constant():
    assert CS1_SCHEMA_VERSION == "atomadic-forge.cs1/v1"


def test_render_cs1_returns_correct_schema_version():
    cs1 = render_cs1(_make_receipt())
    assert cs1["schema_version"] == "atomadic-forge.cs1/v1"


def test_render_cs1_has_all_required_top_level_keys():
    cs1 = render_cs1(_make_receipt())
    for key in (
        "schema_version",
        "generated_at_utc",
        "receipt_schema_version",
        "receipt_generated_at_utc",
        "project",
        "receipt_summary",
        "attestation",
        "compliance_claims",
        "regulator_questions",
        "lineage_chain_digest",
        "signatures_status",
    ):
        assert key in cs1, f"missing key: {key!r}"


# ---------------------------------------------------------------------------
# Receipt summary extraction
# ---------------------------------------------------------------------------

def test_receipt_summary_pulls_verdict_and_score():
    cs1 = render_cs1(_make_receipt())
    rs = cs1["receipt_summary"]
    assert rs["verdict"] == "PASS"
    assert rs["certify_score"] == 100.0
    assert rs["wire_verdict"] == "PASS"
    assert rs["wire_violation_count"] == 0
    assert rs["symbol_count"] == 14
    assert rs["project_name"] == "demo"


def test_receipt_summary_fail_path():
    receipt = _make_receipt()
    receipt["verdict"] = "FAIL"
    receipt["wire"] = {"verdict": "FAIL", "violation_count": 3, "auto_fixable": 1}
    receipt["certify"]["score"] = 75.0
    cs1 = render_cs1(receipt)
    rs = cs1["receipt_summary"]
    assert rs["verdict"] == "FAIL"
    assert rs["certify_score"] == 75.0
    assert rs["wire_violation_count"] == 3


# ---------------------------------------------------------------------------
# Lean4 attestation block
# ---------------------------------------------------------------------------

def test_attestation_block_populated_when_lean4_present():
    cs1 = render_cs1(_make_receipt(lean4_attestation=_LEAN4))
    att = cs1["attestation"]
    assert att["total_theorems"] == 567
    assert att["corpora_count"] == 2
    assert att["total_sorry"] == 0
    assert att["summary"] == "567 / 0 sorry"
    names = [c["name"] for c in att["corpora"]]
    assert "aethel-nexus-proofs" in names
    assert "mhed-toe-codex-v22" in names


def test_attestation_block_empty_when_no_lean4():
    cs1 = render_cs1(_make_receipt())
    att = cs1["attestation"]
    assert att["total_theorems"] == 0
    assert att["corpora_count"] == 0
    assert att["corpora"] == []


# ---------------------------------------------------------------------------
# Missing required field
# ---------------------------------------------------------------------------

def test_missing_required_field_raises_value_error():
    bad = _make_receipt()
    del bad["verdict"]
    with pytest.raises(ValueError, match="verdict"):
        render_cs1(bad)


def test_missing_project_raises_value_error():
    bad = _make_receipt()
    del bad["project"]
    with pytest.raises(ValueError, match="project"):
        render_cs1(bad)


# ---------------------------------------------------------------------------
# Lineage digest
# ---------------------------------------------------------------------------

def test_lineage_digest_is_none_when_no_lineage():
    cs1 = render_cs1(_make_receipt())
    assert cs1["lineage_chain_digest"] is None


def test_lineage_digest_is_sha256_hex_when_lineage_present():
    cs1 = render_cs1(_make_receipt(lineage=_LINEAGE))
    digest = cs1["lineage_chain_digest"]
    assert digest is not None
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_lineage_digest_is_deterministic():
    r = _make_receipt(lineage=_LINEAGE)
    d1 = render_cs1(r)["lineage_chain_digest"]
    d2 = render_cs1(r)["lineage_chain_digest"]
    assert d1 == d2


# ---------------------------------------------------------------------------
# Signature status
# ---------------------------------------------------------------------------

def test_signatures_status_unsigned_by_default():
    cs1 = render_cs1(_make_receipt())
    assert cs1["signatures_status"] == "UNSIGNED"


def test_signatures_status_signed_when_both_present():
    sigs = {"sigstore": _SIGSTORE, "aaaa_nexus": _NEXUS_SIG}
    cs1 = render_cs1(_make_receipt(signatures=sigs))
    assert cs1["signatures_status"] == "SIGNED"


def test_signatures_status_partial_when_only_sigstore():
    sigs = {"sigstore": _SIGSTORE}
    cs1 = render_cs1(_make_receipt(signatures=sigs))
    assert cs1["signatures_status"] == "PARTIAL"


# ---------------------------------------------------------------------------
# Compliance claims
# ---------------------------------------------------------------------------

def test_compliance_claims_count():
    cs1 = render_cs1(_make_receipt())
    # 6 EU + 4 SR + 3 FDA + 4 CMMC = 17
    assert len(cs1["compliance_claims"]) == 17


def test_compliance_claims_cover_all_frameworks():
    cs1 = render_cs1(_make_receipt())
    frameworks = {c["framework"] for c in cs1["compliance_claims"]}
    assert frameworks == {"EU AI Act", "SR 11-7", "FDA PCCP", "CMMC-AI"}


def test_eu_ai_act_claims_have_annex_iv_citations():
    cs1 = render_cs1(_make_receipt())
    eu_claims = [c for c in cs1["compliance_claims"] if c["framework"] == "EU AI Act"]
    for claim in eu_claims:
        assert "Annex IV" in claim["citation"], (
            f"EU AI Act claim {claim['ref']!r} missing 'Annex IV' in citation"
        )
        assert "2024/1689" in claim["citation"]


def test_sr_11_7_claims_have_section_citations():
    cs1 = render_cs1(_make_receipt())
    sr_claims = [c for c in cs1["compliance_claims"] if c["framework"] == "SR 11-7"]
    for claim in sr_claims:
        assert "SR Letter 11-7" in claim["citation"], (
            f"SR 11-7 claim {claim['ref']!r} missing 'SR Letter 11-7' in citation"
        )


# ---------------------------------------------------------------------------
# Regulator questions
# ---------------------------------------------------------------------------

def test_regulator_question_count():
    cs1 = render_cs1(_make_receipt())
    assert len(cs1["regulator_questions"]) == 5


def test_regulator_questions_have_required_fields():
    cs1 = render_cs1(_make_receipt())
    for rq in cs1["regulator_questions"]:
        assert "id" in rq
        assert "question" in rq
        assert "answer_fields" in rq
        assert "framework_refs" in rq


def test_regulator_questions_cover_signing():
    cs1 = render_cs1(_make_receipt())
    rq5 = next(rq for rq in cs1["regulator_questions"] if rq["id"] == "RQ-5")
    assert "signatures" in rq5["answer_fields"]


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def test_markdown_contains_schema_version():
    cs1 = render_cs1(_make_receipt())
    md = render_cs1_markdown(cs1)
    assert "atomadic-forge.cs1/v1" in md


def test_markdown_contains_verdict():
    cs1 = render_cs1(_make_receipt())
    md = render_cs1_markdown(cs1)
    assert "PASS" in md


def test_markdown_contains_regulator_questions_section():
    cs1 = render_cs1(_make_receipt())
    md = render_cs1_markdown(cs1)
    assert "Regulator Questions" in md
    assert "RQ-1" in md
    assert "RQ-5" in md


def test_markdown_contains_mapping_doc_references():
    cs1 = render_cs1(_make_receipt())
    md = render_cs1_markdown(cs1)
    assert "EU_AI_ACT_ANNEX_IV.md" in md
    assert "SR_11-7_MAPPING.md" in md
    assert "FDA_PCCP_MAPPING.md" in md
    assert "CMMC_AI_MAPPING.md" in md


def test_markdown_lean4_attestation_shown_when_present():
    cs1 = render_cs1(_make_receipt(lean4_attestation=_LEAN4))
    md = render_cs1_markdown(cs1)
    assert "567" in md
    assert "aethel-nexus-proofs" in md


def test_markdown_unsigned_note():
    cs1 = render_cs1(_make_receipt())
    md = render_cs1_markdown(cs1)
    assert "UNSIGNED" in md


def test_markdown_signed_note_when_both_sigs():
    sigs = {"sigstore": _SIGSTORE, "aaaa_nexus": _NEXUS_SIG}
    cs1 = render_cs1(_make_receipt(signatures=sigs))
    md = render_cs1_markdown(cs1)
    assert "SIGNED" in md


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------

def test_json_roundtrip():
    cs1 = render_cs1(_make_receipt(lean4_attestation=_LEAN4, lineage=_LINEAGE))
    serialized = json.dumps(cs1, default=str)
    restored = json.loads(serialized)
    assert restored["schema_version"] == CS1_SCHEMA_VERSION
    assert restored["receipt_summary"]["verdict"] == "PASS"
    assert restored["lineage_chain_digest"] is not None
    assert len(restored["compliance_claims"]) == 17
