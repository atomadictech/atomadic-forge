"""Tests for the AAAA-Nexus inference client.

Forge integrates with AAAA-Nexus's ``/v1/inference`` endpoint as a first-
class LLM provider.  Every call:

  * goes through the upstream HELIX anti-hallucination trust gate,
  * is billed at the wrapper's price-per-call (currently ~$0.10),
  * gets a Cloudflare-Worker-AI fallback transparently if the
    AAAA_LLM service binding fails.

These tests cover the client surface without making real network calls.
The single live smoke-call against the public worker is intentionally
skipped by default so CI doesn't bill the operator's account on every
run; opt in with ``FORGE_LIVE_NEXUS=1`` to verify against production.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from io import BytesIO
from unittest.mock import patch

import pytest

from atomadic_forge.a1_at_functions.llm_client import (
    AAAANexusClient, resolve_default_client,
)


# ── construction + configuration ─────────────────────────────────────────

def test_client_default_base_url_and_wrapper():
    c = AAAANexusClient()
    assert c.base_url == "https://aaaa-nexus.atomadictech.workers.dev"
    assert c.wrapper == "helix-standard"
    assert c.name == "aaaa-nexus"


def test_client_base_url_env_override(monkeypatch):
    monkeypatch.setenv("AAAA_NEXUS_URL", "https://staging.example.com/")
    c = AAAANexusClient()
    # Trailing slash stripped.
    assert c.base_url == "https://staging.example.com"


def test_client_wrapper_env_override(monkeypatch):
    monkeypatch.setenv("AAAA_NEXUS_WRAPPER", "bitnet-standard")
    c = AAAANexusClient()
    assert c.wrapper == "bitnet-standard"


def test_client_rejects_unknown_wrapper():
    with pytest.raises(ValueError, match="unknown AAAA-Nexus wrapper"):
        AAAANexusClient(wrapper="not-a-real-wrapper")


def test_client_explicit_kwargs_override_env(monkeypatch):
    monkeypatch.setenv("AAAA_NEXUS_URL", "https://from-env.example")
    monkeypatch.setenv("AAAA_NEXUS_WRAPPER", "helix-stream")
    c = AAAANexusClient(base_url="https://from-arg.example",
                          wrapper="bitnet-standard")
    assert c.base_url == "https://from-arg.example"
    assert c.wrapper == "bitnet-standard"


def test_wrapper_paths_complete():
    """Every advertised wrapper from the live OpenAPI is mapped."""
    expected = {"helix-standard", "helix-stream",
                 "bitnet-standard", "bitnet-stream"}
    assert set(AAAANexusClient.WRAPPER_PATHS) == expected
    assert AAAANexusClient.WRAPPER_PATHS["helix-standard"] == "/v1/inference"
    assert AAAANexusClient.WRAPPER_PATHS["bitnet-standard"] == "/v1/bitnet/inference"


# ── call() shape: missing API key raises, valid key sends correct body ───

def test_call_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("AAAA_NEXUS_API_KEY", raising=False)
    c = AAAANexusClient()
    with pytest.raises(RuntimeError, match="AAAA_NEXUS_API_KEY not set"):
        c.call("anything")


class _FakeResponse:
    """Minimal context-manager stand-in for urllib.request.urlopen."""

    def __init__(self, payload: dict):
        self._buf = BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._buf.getvalue()


def _capture_request(captured: dict):
    """Build a urlopen replacement that records the outgoing Request."""
    def _fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8")) if req.data else None
        captured["headers"] = dict(req.headers)
        return _FakeResponse({
            "choices": [{"message": {"role": "assistant",
                                       "content": "FAKE_RESPONSE"}}],
            "helix": {"anti_hallucination":
                       {"flagged": False, "confidence": 0.99,
                        "trust_floor": 0.95}},
        })
    return _fake_urlopen


def test_call_sends_minimal_body_only(monkeypatch):
    """Body must contain ``messages`` only — Nexus rejects extra fields with 403."""
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "test-key-xxx")
    captured: dict = {}
    monkeypatch.setattr(urllib.request, "urlopen", _capture_request(captured))
    c = AAAANexusClient()
    out = c.call("hello", system="be terse")
    assert out == "FAKE_RESPONSE"
    assert captured["body"].keys() == {"messages"}, (
        f"body must contain ONLY messages — got {list(captured['body'].keys())}"
    )
    msgs = captured["body"]["messages"]
    assert msgs[0] == {"role": "system", "content": "be terse"}
    assert msgs[1] == {"role": "user", "content": "hello"}


def test_call_omits_system_when_empty(monkeypatch):
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "test-key-xxx")
    captured: dict = {}
    monkeypatch.setattr(urllib.request, "urlopen", _capture_request(captured))
    c = AAAANexusClient()
    c.call("just user msg")
    msgs = captured["body"]["messages"]
    assert len(msgs) == 1
    assert msgs[0] == {"role": "user", "content": "just user msg"}


def test_call_uses_correct_endpoint_per_wrapper(monkeypatch):
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "test-key-xxx")
    for wrapper, expected_path in [
        ("helix-standard", "/v1/inference"),
        ("bitnet-standard", "/v1/bitnet/inference"),
    ]:
        captured: dict = {}
        monkeypatch.setattr(urllib.request, "urlopen", _capture_request(captured))
        c = AAAANexusClient(wrapper=wrapper)
        c.call("x")
        assert captured["url"].endswith(expected_path)


def test_call_sends_xapikey_bearer_and_useragent(monkeypatch):
    """The Nexus storefront reads X-API-Key (Bearer falls through to trial).

    The client sends BOTH headers so the same code works against
    operator-tier (X-API-Key matches NONCE_CACHE) AND any future
    Bearer-style endpoint.  Cloudflare WAF also rejects urllib's default
    UA, so the User-Agent must be overridden.
    """
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "secret-token")
    captured: dict = {}
    monkeypatch.setattr(urllib.request, "urlopen", _capture_request(captured))
    c = AAAANexusClient()
    c.call("x")
    # X-API-Key is the load-bearing header for AAAA-Nexus auth.
    xapi = captured["headers"].get("X-api-key", "") or captured["headers"].get("X-API-Key", "")
    assert xapi == "secret-token", (
        f"X-API-Key must equal the raw key (Nexus auth gate); got {xapi!r}"
    )
    # Bearer is also sent for forward-compat with hypothetical Bearer endpoints.
    auth = captured["headers"].get("Authorization", "")
    assert auth == "Bearer secret-token"
    ua = captured["headers"].get("User-agent", "") or captured["headers"].get("User-Agent", "")
    assert "atomadic-forge" in ua
    assert "Python-urllib" not in ua


def test_call_returns_empty_string_when_no_choices(monkeypatch):
    """Defensive: if the upstream returns no choices, return ""."""
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "test-key")

    def _empty(req, timeout=None):
        return _FakeResponse({"choices": []})

    monkeypatch.setattr(urllib.request, "urlopen", _empty)
    c = AAAANexusClient()
    assert c.call("x") == ""


def test_call_warns_when_helix_flags_low_confidence(monkeypatch, capsys):
    """A flagged + low-confidence response should breadcrumb to stderr."""
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "test-key")

    def _flagged(req, timeout=None):
        return _FakeResponse({
            "choices": [{"message": {"role": "assistant", "content": "uncertain"}}],
            "helix": {"anti_hallucination": {
                "flagged": True, "confidence": 0.1, "trust_floor": 0.9,
            }},
        })

    monkeypatch.setattr(urllib.request, "urlopen", _flagged)
    c = AAAANexusClient()
    out = c.call("x")
    err = capsys.readouterr().err
    assert out == "uncertain"     # still returned — soft warning, not block
    assert "anti-hallucination flagged" in err


# ── default-client resolution prefers Nexus when its key is set ──────────

def test_resolve_default_prefers_aaaa_nexus(monkeypatch):
    """Nexus comes first because it bills + trust-gates every call."""
    # Set every key — Nexus should still win.
    monkeypatch.setenv("AAAA_NEXUS_API_KEY", "n")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("OPENAI_API_KEY", "o")
    c = resolve_default_client()
    assert c.name == "aaaa-nexus"


def test_resolve_default_falls_back_to_anthropic(monkeypatch):
    monkeypatch.delenv("AAAA_NEXUS_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FORGE_OLLAMA", raising=False)
    c = resolve_default_client()
    assert c.name == "anthropic"


# ── live smoke (opt-in) ──────────────────────────────────────────────────

@pytest.mark.skipif(
    not os.environ.get("FORGE_LIVE_NEXUS"),
    reason="Skipped by default to avoid billing the operator's Nexus account; "
            "set FORGE_LIVE_NEXUS=1 to opt in.",
)
def test_live_nexus_inference_round_trip():
    """Real call against the production Worker — costs ~$0.10."""
    c = AAAANexusClient()
    out = c.call("reply with the single word OK").strip()
    assert "OK" in out.upper()
