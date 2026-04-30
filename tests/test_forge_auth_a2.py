"""Tests for Tier a2 — ``ForgeAuthClient`` (stateful verify + usage).

Golden Path Lane C W5 — exercises the cache, the offline-grace
window, the soft-fail-on-network-error contract, and the
fire-and-forget usage logger. We inject a fake ``urlopen`` so no real
HTTP traffic happens, and we inject a fake clock so we can push past
the cache TTL and grace boundary deterministically.
"""

from __future__ import annotations

import json
import urllib.error
from io import BytesIO
from typing import Any

import pytest

from atomadic_forge.a0_qk_constants.auth_constants import (
    OFFLINE_GRACE_SECONDS,
    VERIFY_CACHE_TTL_SECONDS,
)
from atomadic_forge.a2_mo_composites.forge_auth_client import ForgeAuthClient


# ---- fake urlopen helpers --------------------------------------------

class _FakeResponse:
    """Minimal context-manager stand-in for urllib.request.urlopen."""

    def __init__(self, payload: dict[str, Any] | bytes):
        if isinstance(payload, bytes):
            self._buf = BytesIO(payload)
        else:
            self._buf = BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: Any) -> bool:
        return False

    def read(self) -> bytes:
        return self._buf.getvalue()


def _ok_urlopen(payload: dict[str, Any]):
    """Return a fake urlopen that always returns ``payload``."""
    captured: list[dict[str, Any]] = []

    def _fn(req, timeout=None):  # noqa: ANN001
        captured.append({
            "url": req.full_url,
            "headers": dict(req.headers),
            "body": json.loads(req.data.decode("utf-8")) if req.data else None,
        })
        return _FakeResponse(payload)

    _fn.captured = captured  # type: ignore[attr-defined]
    return _fn


def _raising_urlopen(exc: BaseException):
    """Return a fake urlopen that always raises ``exc``."""

    def _fn(req, timeout=None):  # noqa: ANN001
        raise exc

    return _fn


class _Clock:
    """Manual clock for cache / grace tests."""

    def __init__(self, t: float = 1_000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


# ---- shape rejection -------------------------------------------------

def test_verify_rejects_invalid_shape_without_calling_endpoint():
    calls = []

    def _spy(req, timeout=None):  # noqa: ANN001
        calls.append(req)
        return _FakeResponse({"ok": True})

    c = ForgeAuthClient(urlopen=_spy)
    out = c.verify("")
    assert out["ok"] is False
    assert calls == []  # never reached the network


def test_verify_rejects_wrong_prefix():
    c = ForgeAuthClient(urlopen=_ok_urlopen({"ok": True}))
    out = c.verify("sk_live_abc")
    assert out["ok"] is False


# ---- success path ----------------------------------------------------

def test_verify_success_populates_email_plan_and_caches():
    fake = _ok_urlopen({
        "ok": True, "email": "u@example.com", "plan": "pro", "reason": "",
    })
    clock = _Clock()
    c = ForgeAuthClient(urlopen=fake, clock=clock)
    out = c.verify("fk_live_abc")
    assert out["ok"] is True
    assert out["email"] == "u@example.com"
    assert out["plan"] == "pro"
    assert out["cached"] is False
    # Second call should hit the cache (no second URL call).
    out2 = c.verify("fk_live_abc")
    assert out2["ok"] is True
    assert out2["cached"] is True
    assert len(fake.captured) == 1  # type: ignore[attr-defined]


def test_verify_cache_expires_after_ttl():
    fake = _ok_urlopen({"ok": True, "email": "u@x", "plan": "pro"})
    clock = _Clock()
    c = ForgeAuthClient(urlopen=fake, clock=clock)
    c.verify("fk_live_abc")
    clock.advance(VERIFY_CACHE_TTL_SECONDS + 1)
    c.verify("fk_live_abc")
    assert len(fake.captured) == 2  # type: ignore[attr-defined]


def test_verify_sends_correct_endpoint_and_headers():
    fake = _ok_urlopen({"ok": True, "email": "u@x", "plan": "free"})
    c = ForgeAuthClient(urlopen=fake)
    c.verify("fk_live_xyz")
    rec = fake.captured[0]  # type: ignore[attr-defined]
    assert "forge-auth.atomadic.tech" in rec["url"]
    assert "/v1/forge/auth/verify" in rec["url"]
    assert rec["body"] == {"api_key": "fk_live_xyz"}
    headers = {k.lower(): v for k, v in rec["headers"].items()}
    assert headers.get("authorization") == "Bearer fk_live_xyz"
    assert headers.get("x-api-key") == "fk_live_xyz"


def test_verify_custom_endpoint_overrides_default():
    fake = _ok_urlopen({"ok": True, "email": "u@x", "plan": "pro"})
    c = ForgeAuthClient(
        auth_endpoint="https://staging.example.com/verify",
        urlopen=fake,
    )
    c.verify("fk_live_abc")
    assert "staging.example.com" in fake.captured[0]["url"]  # type: ignore[attr-defined]


# ---- 401 / 4xx hard-reject path --------------------------------------

def test_verify_4xx_returns_ok_false_no_grace():
    err = urllib.error.HTTPError(
        url="https://forge-auth.atomadic.tech/v1/forge/auth/verify",
        code=401, msg="Unauthorized", hdrs=None, fp=None,
    )
    c = ForgeAuthClient(urlopen=_raising_urlopen(err))
    out = c.verify("fk_live_revoked")
    assert out["ok"] is False
    assert out["degraded"] is False
    assert "401" in out["reason"]


def test_verify_4xx_caches_rejection():
    """Don't hammer the endpoint with a known-bad key on every call."""
    calls = {"n": 0}

    def _fn(req, timeout=None):  # noqa: ANN001
        calls["n"] += 1
        raise urllib.error.HTTPError(
            url="x", code=401, msg="Unauthorized", hdrs=None, fp=None,
        )

    c = ForgeAuthClient(urlopen=_fn)
    c.verify("fk_live_revoked")
    c.verify("fk_live_revoked")
    assert calls["n"] == 1  # second call served from cache


# ---- offline grace path ----------------------------------------------

def test_network_error_within_grace_returns_degraded_ok():
    """First call succeeds; second call (network error within grace) is
    served as degraded=true, ok=true."""
    payload = {"ok": True, "email": "u@x", "plan": "pro"}
    seq = [_FakeResponse(payload)]

    def _flaky(req, timeout=None):  # noqa: ANN001
        if seq:
            return seq.pop(0)
        raise urllib.error.URLError("connection refused")

    clock = _Clock()
    c = ForgeAuthClient(urlopen=_flaky, clock=clock)
    first = c.verify("fk_live_abc")
    assert first["ok"] is True

    # Push past TTL so the cache misses, but stay within grace.
    clock.advance(VERIFY_CACHE_TTL_SECONDS + 10)
    out = c.verify("fk_live_abc")
    assert out["ok"] is True
    assert out["degraded"] is True
    assert "unreachable" in out["reason"]


def test_network_error_outside_grace_returns_ok_false():
    payload = {"ok": True, "email": "u@x", "plan": "pro"}
    seq = [_FakeResponse(payload)]

    def _flaky(req, timeout=None):  # noqa: ANN001
        if seq:
            return seq.pop(0)
        raise urllib.error.URLError("connection refused")

    clock = _Clock()
    c = ForgeAuthClient(urlopen=_flaky, clock=clock)
    c.verify("fk_live_abc")
    # Past the grace window.
    clock.advance(OFFLINE_GRACE_SECONDS + 1)
    out = c.verify("fk_live_abc")
    assert out["ok"] is False
    assert out["degraded"] is False


def test_network_error_with_no_prior_good_returns_ok_false():
    c = ForgeAuthClient(
        urlopen=_raising_urlopen(urllib.error.URLError("no route")),
    )
    out = c.verify("fk_live_first_time")
    assert out["ok"] is False
    assert out["degraded"] is False
    assert "no last-known-good" in out["reason"]


def test_5xx_within_grace_serves_degraded():
    """5xx is not a hard-reject — same grace path as a transport error."""
    payload = {"ok": True, "email": "u@x", "plan": "pro"}
    seq: list[Any] = [_FakeResponse(payload)]

    def _flaky(req, timeout=None):  # noqa: ANN001
        if seq:
            return seq.pop(0)
        raise urllib.error.HTTPError(
            url="x", code=503, msg="Service Unavailable", hdrs=None, fp=None,
        )

    clock = _Clock()
    c = ForgeAuthClient(urlopen=_flaky, clock=clock)
    c.verify("fk_live_abc")
    clock.advance(VERIFY_CACHE_TTL_SECONDS + 1)
    out = c.verify("fk_live_abc")
    assert out["ok"] is True
    assert out["degraded"] is True


def test_non_object_body_treated_as_failure_then_grace_kicks_in_next_time():
    """A malformed body raises ValueError inside the client; first call
    has no last-known-good so it returns ok=False."""
    bad = _FakeResponse(b"not-json")

    def _fn(req, timeout=None):  # noqa: ANN001
        return bad

    c = ForgeAuthClient(urlopen=_fn)
    out = c.verify("fk_live_abc")
    assert out["ok"] is False


# ---- usage log -------------------------------------------------------

def test_log_usage_sends_when_endpoint_ok():
    fake = _ok_urlopen({"sent": True})
    c = ForgeAuthClient(urlopen=fake)
    out = c.log_usage("fk_live_abc", "wire", "deadbeef")
    assert out["sent"] is True
    rec = fake.captured[0]  # type: ignore[attr-defined]
    assert "/v1/forge/usage/log" in rec["url"]
    assert rec["body"]["tool"] == "wire"
    assert rec["body"]["project_hash"] == "deadbeef"


def test_log_usage_swallows_network_errors():
    """Fire-and-forget — usage logging MUST NEVER raise."""
    c = ForgeAuthClient(
        urlopen=_raising_urlopen(urllib.error.URLError("offline")),
    )
    out = c.log_usage("fk_live_abc", "wire", "deadbeef")
    assert out["sent"] is False
    assert "URLError" in out["reason"]


def test_log_usage_swallows_arbitrary_exceptions():
    def _boom(req, timeout=None):  # noqa: ANN001
        raise RuntimeError("kaboom")

    c = ForgeAuthClient(urlopen=_boom)
    out = c.log_usage("fk_live_abc", "wire", "deadbeef")
    assert out["sent"] is False
    assert "kaboom" in out["reason"]


def test_log_usage_rejects_invalid_key_shape_without_calling_endpoint():
    calls = []

    def _spy(req, timeout=None):  # noqa: ANN001
        calls.append(req)
        return _FakeResponse({"sent": True})

    c = ForgeAuthClient(urlopen=_spy)
    out = c.log_usage("not-a-real-key", "wire", "deadbeef")
    assert out["sent"] is False
    assert calls == []


def test_log_usage_does_not_raise_on_string_body_decode_failure(monkeypatch):
    """Even pathological encoding bugs must be swallowed."""

    def _bad_dumps(*a, **k):  # noqa: ANN001, ANN003
        raise TypeError("non-serializable")

    monkeypatch.setattr(
        "atomadic_forge.a2_mo_composites.forge_auth_client.json.dumps",
        _bad_dumps,
    )
    c = ForgeAuthClient(urlopen=_ok_urlopen({"sent": True}))
    out = c.log_usage("fk_live_abc", "wire", "deadbeef")
    assert out["sent"] is False


# ---- sanity / smoke --------------------------------------------------

def test_constructor_uses_default_endpoints():
    c = ForgeAuthClient()
    assert c.auth_endpoint.startswith("https://forge-auth.atomadic.tech")
    assert c.usage_endpoint.startswith("https://forge-auth.atomadic.tech")


def test_verify_does_not_mutate_cached_dict_when_returning_cached():
    fake = _ok_urlopen({"ok": True, "email": "u@x", "plan": "pro"})
    c = ForgeAuthClient(urlopen=fake)
    first = c.verify("fk_live_abc")
    second = c.verify("fk_live_abc")
    # First call's dict shouldn't have been mutated to cached=True.
    assert first["cached"] is False
    assert second["cached"] is True


@pytest.mark.parametrize("code", [400, 401, 402, 403, 404])
def test_all_4xx_codes_treated_as_hard_reject(code):
    err = urllib.error.HTTPError(
        url="x", code=code, msg="Err", hdrs=None, fp=None,
    )
    c = ForgeAuthClient(urlopen=_raising_urlopen(err))
    out = c.verify("fk_live_abc")
    assert out["ok"] is False
    assert out["degraded"] is False
