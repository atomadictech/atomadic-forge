"""Tier verification — Golden Path Lane A W4: lineage chain stub.

Pure-function coverage of canonical_receipt_hash + link_to_parent +
verify_chain_link, plus integration coverage of LineageChainStore
(append-only persistence to .atomadic-forge/lineage_chain.jsonl).
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from atomadic_forge.a1_at_functions.lineage_chain import (
    canonical_receipt_hash,
    is_local_lineage,
    link_to_parent,
    verify_chain_link,
)
from atomadic_forge.a1_at_functions.receipt_emitter import build_receipt
from atomadic_forge.a2_mo_composites.lineage_chain_store import (
    LineageChainStore,
)


def _sample(score: float = 100.0):
    return build_receipt(
        certify_result={
            "score": score,
            "documentation_complete": True,
            "tests_present": True,
            "tier_layout_present": True,
            "no_upward_imports": True,
            "issues": [],
        },
        wire_report={"verdict": "PASS", "violation_count": 0,
                      "auto_fixable": 0, "violations": []},
        scout_report={
            "symbol_count": 1,
            "tier_distribution": {"a1_at_functions": 1},
            "effect_distribution": {"pure": 1, "state": 0, "io": 0},
            "primary_language": "python",
        },
        project_name="demo",
        project_root=Path("/tmp/demo"),
        forge_version="0.2.2-test",
        compute_artifact_hashes=False,
    )


# ---- canonical hash ----------------------------------------------------

def test_canonical_hash_deterministic():
    a = _sample()
    b = _sample()
    # generated_at_utc is excluded from the hash, so two receipts with
    # identical structural content hash to the same value.
    assert canonical_receipt_hash(a) == canonical_receipt_hash(b)


def test_canonical_hash_excludes_signatures():
    """Signing must not change the receipt's identity hash."""
    a = _sample()
    signed = deepcopy(a)
    signed["signatures"] = {
        "sigstore": {"rekor_uuid": "x", "log_index": 1, "bundle_path": "p"},
        "aaaa_nexus": {"signature": "s", "key_id": "k", "issuer": "i",
                        "issued_at_utc": "t", "verify_endpoint": "/v"},
    }
    assert canonical_receipt_hash(a) == canonical_receipt_hash(signed)


def test_canonical_hash_excludes_lineage():
    """Hashing the lineage block would require the hash to depend on
    its own value — the canonical hash strips it."""
    a = _sample()
    linked = link_to_parent(a, parent_receipt_hash=None, chain_depth=1)
    assert canonical_receipt_hash(a) == canonical_receipt_hash(linked)


def test_canonical_hash_excludes_notes():
    a = _sample()
    noted = deepcopy(a)
    noted["notes"] = ["AAAA_NEXUS_API_KEY not set — receipt left unsigned"]
    assert canonical_receipt_hash(a) == canonical_receipt_hash(noted)


def test_canonical_hash_changes_with_score():
    a = _sample(score=100.0)
    b = _sample(score=50.0)
    assert canonical_receipt_hash(a) != canonical_receipt_hash(b)


# ---- link_to_parent ----------------------------------------------------

def test_link_head_has_no_parent_and_depth_one():
    receipt = _sample()
    linked = link_to_parent(receipt, parent_receipt_hash=None, chain_depth=1)
    lin = linked["lineage"]
    assert lin["parent_receipt_hash"] is None
    assert lin["chain_depth"] == 1
    assert is_local_lineage(lin["lineage_path"])


def test_link_includes_hash_in_local_path():
    receipt = _sample()
    linked = link_to_parent(receipt, parent_receipt_hash=None, chain_depth=1)
    h = canonical_receipt_hash(linked)
    assert linked["lineage"]["lineage_path"] == f"local://lineage-chain/{h}"


def test_link_depth_must_be_positive():
    with pytest.raises(ValueError):
        link_to_parent(_sample(), parent_receipt_hash=None, chain_depth=0)


def test_link_does_not_mutate_input():
    receipt = _sample()
    snapshot = deepcopy(receipt)
    _ = link_to_parent(receipt, parent_receipt_hash=None, chain_depth=1)
    assert receipt == snapshot


def test_link_explicit_lineage_path_override():
    linked = link_to_parent(
        _sample(),
        parent_receipt_hash=None,
        chain_depth=1,
        lineage_path="vanguard://forge/2026/04/29/abc",
    )
    assert linked["lineage"]["lineage_path"] == "vanguard://forge/2026/04/29/abc"
    assert not is_local_lineage(linked["lineage"]["lineage_path"])


# ---- verify_chain_link --------------------------------------------------

def test_verify_chain_head_ok():
    head = link_to_parent(_sample(), parent_receipt_hash=None, chain_depth=1)
    ok, problems = verify_chain_link(head, parent=None)
    assert ok and not problems


def test_verify_chain_head_with_bogus_parent_fails():
    head = link_to_parent(_sample(), parent_receipt_hash="abc", chain_depth=1)
    ok, problems = verify_chain_link(head, parent=None)
    assert not ok
    assert any("parent_receipt_hash=None" in p for p in problems)


def test_verify_successor_ok():
    parent = link_to_parent(_sample(), parent_receipt_hash=None, chain_depth=1)
    parent_hash = canonical_receipt_hash(parent)
    child_raw = _sample(score=80.0)
    child = link_to_parent(
        child_raw, parent_receipt_hash=parent_hash, chain_depth=2)
    ok, problems = verify_chain_link(child, parent=parent)
    assert ok and not problems


def test_verify_successor_bad_parent_hash():
    parent = link_to_parent(_sample(), parent_receipt_hash=None, chain_depth=1)
    child_raw = _sample(score=80.0)
    child = link_to_parent(
        child_raw, parent_receipt_hash="wrong-hash", chain_depth=2)
    ok, problems = verify_chain_link(child, parent=parent)
    assert not ok
    assert any("parent_receipt_hash mismatch" in p for p in problems)


def test_verify_successor_bad_depth():
    parent = link_to_parent(_sample(), parent_receipt_hash=None, chain_depth=1)
    parent_hash = canonical_receipt_hash(parent)
    child_raw = _sample(score=80.0)
    child = link_to_parent(
        child_raw, parent_receipt_hash=parent_hash, chain_depth=5)
    ok, problems = verify_chain_link(child, parent=parent)
    assert not ok
    assert any("chain_depth not monotonic" in p for p in problems)


def test_verify_no_lineage_block():
    raw = _sample()
    ok, problems = verify_chain_link(raw, parent=None)
    assert not ok
    assert any("no lineage block" in p for p in problems)


# ---- LineageChainStore -------------------------------------------------

def test_store_empty_tip_is_none(tmp_path):
    store = LineageChainStore(tmp_path)
    assert store.read_tip() == (None, 0)
    assert store.read_all() == []


def test_store_first_link_is_head(tmp_path):
    store = LineageChainStore(tmp_path)
    linked = store.link_and_append(_sample())
    assert linked["lineage"]["chain_depth"] == 1
    assert linked["lineage"]["parent_receipt_hash"] is None
    entries = store.read_all()
    assert len(entries) == 1
    assert entries[0]["chain_depth"] == 1
    assert entries[0]["parent_receipt_hash"] is None
    assert entries[0]["verdict"] == "PASS"


def test_store_second_link_chains_to_first(tmp_path):
    store = LineageChainStore(tmp_path)
    a = store.link_and_append(_sample(score=100.0))
    b = store.link_and_append(_sample(score=80.0))
    assert b["lineage"]["chain_depth"] == 2
    assert b["lineage"]["parent_receipt_hash"] == canonical_receipt_hash(a)
    # File now has two lines.
    log = (tmp_path / ".atomadic-forge" / "lineage_chain.jsonl")
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_store_skips_corrupt_lines(tmp_path):
    d = tmp_path / ".atomadic-forge"
    d.mkdir()
    (d / "lineage_chain.jsonl").write_text(
        json.dumps({"hash": "h1", "chain_depth": 1,
                    "parent_receipt_hash": None,
                    "verdict": "PASS",
                    "schema_version": "atomadic-forge.receipt/v1",
                    "lineage_path": "x", "ts_utc": "t"}) + "\n"
        + "this-is-not-json\n"
        + json.dumps({"hash": "h2", "chain_depth": 2,
                      "parent_receipt_hash": "h1",
                      "verdict": "PASS",
                      "schema_version": "atomadic-forge.receipt/v1",
                      "lineage_path": "y", "ts_utc": "t"}) + "\n",
        encoding="utf-8",
    )
    store = LineageChainStore(tmp_path)
    parent_hash, depth = store.read_tip()
    assert parent_hash == "h2"
    assert depth == 2
    assert len(store.read_all()) == 2


def test_store_ten_link_chain_monotonic(tmp_path):
    """Append 10 receipts and confirm depth grows 1..10 monotonically."""
    store = LineageChainStore(tmp_path)
    for i in range(10):
        store.link_and_append(_sample(score=100.0 - i))
    entries = store.read_all()
    assert len(entries) == 10
    assert [e["chain_depth"] for e in entries] == list(range(1, 11))
    # Each link points to the prior link's hash.
    for i in range(1, 10):
        assert entries[i]["parent_receipt_hash"] == entries[i - 1]["hash"]
