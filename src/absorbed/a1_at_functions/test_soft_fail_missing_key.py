"""Tests for a1/local_signer.py — Ed25519 local Receipt signing.

Covers:
  - soft-fail when 'cryptography' is absent (import patched)
  - soft-fail when key_path does not exist
  - soft-fail when key_path is not an Ed25519 key
  - round-trip sign + verify with a generated Ed25519 key
  - verify returns (False, problems) when signature is tampered
  - verify returns (False, problems) when local_sign block is absent
  - sign does not mutate the input receipt
"""
from __future__ import annotations

import base64
import builtins
import sys
from pathlib import Path

import pytest

from atomadic_forge.a1_at_functions.local_signer import (
    sign_receipt_local,
    verify_receipt_local,
)

# ── helpers ───────────────────────────────────────────────────────────────

def _minimal_receipt() -> dict:
    return {
        "schema_version": "atomadic-forge.receipt/v1",
        "generated_at_utc": "2026-04-29T00:00:00Z",
        "forge_version": "0.3.0",
        "verdict": "PASS",
        "project": {"name": "test-project", "root": "/tmp/test"},
        "certify": {"score": 100.0, "axes": {}, "issues": []},
        "wire": {"verdict": "PASS", "violation_count": 0, "auto_fixable": 0},
        "scout": {
            "symbol_count": 1,
            "tier_distribution": {},
            "effect_distribution": {},
            "primary_language": "python",
        },
        "signatures": {"sigstore": None, "aaaa_nexus": None},
        "notes": [],
    }


def _gen_ed25519_pem(tmp_path: Path) -> Path:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            NoEncryption,
            PrivateFormat,
        )
    except ImportError:
        pytest.skip("cryptography not installed")

    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    key_file = tmp_path / "test-ed25519.pem"
    key_file.write_bytes(pem)
    return key_file


# ── soft-fail: cryptography absent ────────────────────────────────────────

def test_soft_fail_no_cryptography(tmp_path, monkeypatch):
    original_import = builtins.__import__

    def _blocked(name, *args, **kwargs):
        if name.startswith("cryptography"):
            raise ImportError("cryptography blocked for test")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked)
    blocked = [k for k in sys.modules if k.startswith("cryptography")]
    for k in blocked:
        monkeypatch.delitem(sys.modules, k)

    receipt = _minimal_receipt()
    result = sign_receipt_local(receipt, key_path=tmp_path / "nonexistent.pem")
    notes = result.get("notes") or []
    assert any("cryptography" in n for n in notes), f"Expected soft-fail note: {notes}"
    assert result.get("signatures", {}).get("local_sign") is None


# ── soft-fail: key file absent ────────────────────────────────────────────

def test_soft_fail_missing_key(tmp_path):
    pytest.importorskip("cryptography")
    receipt = _minimal_receipt()
    result = sign_receipt_local(receipt, key_path=tmp_path / "no-such-key.pem")
    notes = result.get("notes") or []
    assert any("local_sign skipped" in n for n in notes)
    assert result.get("signatures", {}).get("local_sign") is None


# ── soft-fail: wrong key type ─────────────────────────────────────────────

def test_soft_fail_non_ed25519_key(tmp_path):
    pytest.importorskip("cryptography")
    try:
        from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            NoEncryption,
            PrivateFormat,
        )
    except ImportError:
        pytest.skip("cryptography not available")

    rsa_key = generate_private_key(65537, 2048)
    pem = rsa_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    key_file = tmp_path / "rsa.pem"
    key_file.write_bytes(pem)

    receipt = _minimal_receipt()
    result = sign_receipt_local(receipt, key_path=key_file)
    notes = result.get("notes") or []
    assert any("local_sign skipped" in n for n in notes)
    assert result.get("signatures", {}).get("local_sign") is None


# ── happy path: round-trip sign + verify ─────────────────────────────────

def test_sign_and_verify_roundtrip(tmp_path):
    key_file = _gen_ed25519_pem(tmp_path)
    receipt = _minimal_receipt()
    signed = sign_receipt_local(receipt, key_path=key_file)

    local_sig = (signed.get("signatures") or {}).get("local_sign")
    assert local_sig is not None
    assert local_sig["alg"] == "Ed25519"
    assert local_sig["signature"]
    assert local_sig["public_key"]
    assert len(local_sig["key_id"]) == 16
    assert local_sig["signed_at_utc"].endswith("Z")

    ok, problems = verify_receipt_local(signed)
    assert ok is True, f"verification failed: {problems}"
    assert problems == []


# ── verify: no local_sign block ───────────────────────────────────────────

def test_verify_no_local_sign_block():
    receipt = _minimal_receipt()
    ok, problems = verify_receipt_local(receipt)
    assert ok is False
    assert any("no local_sign" in p for p in problems)


# ── verify: tampered signature ────────────────────────────────────────────

def test_verify_tampered_signature(tmp_path):
    key_file = _gen_ed25519_pem(tmp_path)
    receipt = _minimal_receipt()
    signed = sign_receipt_local(receipt, key_path=key_file)

    sigs = dict(signed["signatures"])
    local_sig = dict(sigs["local_sign"])
    raw = bytearray(base64.b64decode(local_sig["signature"]))
    raw[0] ^= 0xFF
    local_sig["signature"] = base64.b64encode(bytes(raw)).decode("ascii")
    sigs["local_sign"] = local_sig
    signed["signatures"] = sigs

    ok, problems = verify_receipt_local(signed)
    assert ok is False
    assert problems


# ── input not mutated ─────────────────────────────────────────────────────

def test_sign_does_not_mutate_input(tmp_path):
    key_file = _gen_ed25519_pem(tmp_path)
    receipt = _minimal_receipt()
    original_notes = list(receipt.get("notes") or [])
    original_sigs = dict(receipt.get("signatures") or {})

    sign_receipt_local(receipt, key_path=key_file)

    assert (receipt.get("notes") or []) == original_notes
    assert receipt.get("signatures") == original_sigs
