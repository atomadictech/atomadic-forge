"""Tier verification — Golden Path Lane A W2: receipt_signer.

Covers the signer's graceful-degradation contract end to end:
  * AAAA_NEXUS_API_KEY unset       → unsigned + note
  * 4xx from endpoint              → unsigned + note + endpoint cached unavailable
  * 5xx soft-fail (default)        → unsigned + note
  * 5xx strict mode                → RuntimeError
  * Transport error (URLError)     → unsigned + note (default)
  * 200 with full payload          → both sigstore + aaaa_nexus populated
  * 200 with partial payload       → just the present block populated
  * input receipt is not mutated   → caller's copy stays clean

No network: every test patches urllib.request.urlopen with a stub
that returns a chosen response or raises a chosen error. The
production code path is exactly the same.
"""
from __future__ import annotations

import io
import json
import os
import urllib.error
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from atomadic_forge.a0_qk_constants.receipt_schema import ForgeReceiptV1
from atomadic_forge.a1_at_functions.receipt_emitter import build_receipt
from atomadic_forge.a2_mo_composites.receipt_signer import (
    ReceiptSigner,
    sign_receipt,
)


def _sample_receipt() -> ForgeReceiptV1:
    return build_receipt(
        certify_result={
            "score": 100.0,
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


class _FakeResponse:
    """Stub urllib HTTPResponse-shaped object."""
    def __init__(self, payload: bytes, status: int = 200):
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


# ---- soft-fail paths ----------------------------------------------------

def test_no_api_key_returns_unsigned_with_note(monkeypatch):
    monkeypatch.delenv("AAAA_NEXUS_API_KEY", raising=False)
    r = _sample_receipt()
    signed = ReceiptSigner().sign(r)
    assert signed["signatures"]["sigstore"] is None
    assert signed["signatures"]["aaaa_nexus"] is None
    assert any("AAAA_NEXUS_API_KEY not set" in n for n in signed["notes"])
    # Original is untouched.
    assert r["notes"] == []


def test_http_404_returns_unsigned_and_caches_unavailability(monkeypatch):
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "test-key")
    err = urllib.error.HTTPError(
        url="x", code=404, msg="Not Found", hdrs=None, fp=None,  # type: ignore[arg-type]
    )
    signer = ReceiptSigner()
    with patch("urllib.request.urlopen", side_effect=err):
        signed = signer.sign(_sample_receipt())
    assert signed["signatures"]["sigstore"] is None
    assert any("HTTP 404" in n for n in signed["notes"])
    # Subsequent call short-circuits without re-probing — patch with a
    # raising stub and confirm we don't reach it (because cached).
    with patch("urllib.request.urlopen",
                side_effect=AssertionError("should not be called")):
        again = signer.sign(_sample_receipt())
    assert any("unavailable this session" in n for n in again["notes"])


def test_http_500_soft_fails_by_default(monkeypatch):
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "test-key")
    err = urllib.error.HTTPError(
        url="x", code=500, msg="boom", hdrs=None, fp=None,  # type: ignore[arg-type]
    )
    with patch("urllib.request.urlopen", side_effect=err):
        signed = ReceiptSigner().sign(_sample_receipt())
    assert signed["signatures"]["sigstore"] is None
    assert any("HTTP 500" in n for n in signed["notes"])


def test_http_500_strict_raises(monkeypatch):
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "test-key")
    err = urllib.error.HTTPError(
        url="x", code=500, msg="boom", hdrs=None, fp=None,  # type: ignore[arg-type]
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(RuntimeError, match="HTTP 500"):
            ReceiptSigner().sign(_sample_receipt(), strict=True)


def test_url_error_soft_fails_with_transport_note(monkeypatch):
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "test-key")
    err = urllib.error.URLError("name resolution")
    with patch("urllib.request.urlopen", side_effect=err):
        signed = ReceiptSigner().sign(_sample_receipt())
    assert any("transport error" in n for n in signed["notes"])


def test_url_error_strict_raises(monkeypatch):
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "test-key")
    err = urllib.error.URLError("dns")
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(RuntimeError, match="transport error"):
            ReceiptSigner().sign(_sample_receipt(), strict=True)


# ---- happy paths --------------------------------------------------------

def test_full_payload_populates_both_signature_blocks(monkeypatch):
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "test-key")
    body = json.dumps({
        "sigstore": {
            "rekor_uuid": "abc-123",
            "log_index": 42,
            "bundle_path": ".atomadic-forge/receipt.bundle.json",
        },
        "aaaa_nexus": {
            "signature": "BASE64SIG==",
            "key_id": "atomadic-forge-prod-v1",
            "issuer": "aaaa-nexus.atomadic.tech",
            "issued_at_utc": "2026-04-29T05:30:00Z",
            "verify_endpoint": "/v1/verify/forge-receipt",
        },
    }).encode("utf-8")
    fake = _FakeResponse(body, status=200)
    with patch("urllib.request.urlopen", return_value=fake):
        signed = ReceiptSigner().sign(_sample_receipt())
    sg = signed["signatures"]["sigstore"]
    nx = signed["signatures"]["aaaa_nexus"]
    assert sg is not None and nx is not None
    assert sg["rekor_uuid"] == "abc-123"
    assert sg["log_index"] == 42
    assert nx["signature"] == "BASE64SIG=="
    assert nx["key_id"] == "atomadic-forge-prod-v1"
    # No soft-fail notes when signing succeeds.
    assert all("unsigned" not in n for n in signed["notes"])


def test_partial_payload_only_sigstore(monkeypatch):
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "test-key")
    body = json.dumps({
        "sigstore": {"rekor_uuid": "x", "log_index": 1, "bundle_path": "p"},
    }).encode("utf-8")
    fake = _FakeResponse(body, status=200)
    with patch("urllib.request.urlopen", return_value=fake):
        signed = ReceiptSigner().sign(_sample_receipt())
    assert signed["signatures"]["sigstore"]["rekor_uuid"] == "x"
    assert signed["signatures"]["aaaa_nexus"] is None


def test_input_receipt_is_not_mutated(monkeypatch):
    monkeypatch.delenv("AAAA_NEXUS_API_KEY", raising=False)
    receipt = _sample_receipt()
    snapshot = deepcopy(receipt)
    _ = ReceiptSigner().sign(receipt)
    # The signer should never modify the caller's input.
    assert receipt == snapshot


def test_module_level_helper_dispatches(monkeypatch):
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "test-key")
    body = json.dumps({"sigstore": None, "aaaa_nexus": None}).encode("utf-8")
    with patch("urllib.request.urlopen", return_value=_FakeResponse(body)):
        signed = sign_receipt(_sample_receipt())
    # Endpoint reached but returned no signatures — receipt remains
    # unsigned, no soft-fail notes (this is a 'success' empty payload).
    assert signed["signatures"]["sigstore"] is None
    assert signed["signatures"]["aaaa_nexus"] is None


# ---- non-JSON / empty body ---------------------------------------------

def test_non_object_response_treated_as_failure(monkeypatch):
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "test-key")
    fake = _FakeResponse(b"[1, 2, 3]")
    with patch("urllib.request.urlopen", return_value=fake):
        signed = ReceiptSigner().sign(_sample_receipt())
    # Soft-fail note for ValueError (non-object body).
    assert signed["signatures"]["sigstore"] is None
    assert any("transport error" in n for n in signed["notes"])
