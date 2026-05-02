"""Tier a2 — Forge subscription verify client (stateful).

Golden Path Lane C W5 deliverable. Wraps the
``https://forge-auth.atomadic.tech`` verify and usage-log endpoints,
adds a 5-minute in-memory verify cache, and implements the 24h
offline-grace contract — if the verify endpoint becomes unreachable
AFTER a recent successful verify, the client keeps returning
``ok=True, degraded=True`` for up to ``OFFLINE_GRACE_SECONDS``. Past
that window, the gate slams shut.

Design mirrors ``ReceiptSigner`` (sister a2 file): stateful by
construction, soft-fails by default, never throws on network or HTTP
error. The MCP gate at a3 calls this on every ``tools/call`` and
trusts the result blindly — so it has to be defensive here.

Test seam: the ``urlopen`` callable is injectable via the constructor
so unit tests don't monkeypatch ``urllib.request`` globally. Pass any
callable with the same shape as ``urllib.request.urlopen``.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from ..a0_qk_constants.auth_constants import (
    AUTH_URL_ENV,
    DEFAULT_AUTH_ENDPOINT,
    DEFAULT_USAGE_ENDPOINT,
    OFFLINE_GRACE_SECONDS,
    USAGE_URL_ENV,
    VERIFY_CACHE_TTL_SECONDS,
    UsageLogResult,
    VerifyResult,
)
from ..a1_at_functions.forge_auth import (
    build_usage_log_request,
    build_verify_request,
    is_valid_api_key_shape,
    parse_verify_response,
)


# Type alias for the urlopen seam — accepts a Request and returns an
# object with .read() (and ideally context-manager protocol).
UrlOpen = Callable[..., Any]


class ForgeAuthClient:
    """Verify Forge subscription keys + log MCP tool usage."""

    DEFAULT_TIMEOUT_SECONDS = 10
    USER_AGENT = "atomadic-forge/0.3 (ForgeAuthClient)"

    def __init__(
        self,
        *,
        auth_endpoint: str | None = None,
        usage_endpoint: str | None = None,
        timeout_seconds: int | None = None,
        urlopen: UrlOpen | None = None,
        clock: Callable[[], float] | None = None,
        cache_ttl_seconds: int = VERIFY_CACHE_TTL_SECONDS,
        offline_grace_seconds: int = OFFLINE_GRACE_SECONDS,
    ) -> None:
        self.auth_endpoint = (
            auth_endpoint
            or os.environ.get(AUTH_URL_ENV)
            or DEFAULT_AUTH_ENDPOINT
        ).strip()
        self.usage_endpoint = (
            usage_endpoint
            or os.environ.get(USAGE_URL_ENV)
            or DEFAULT_USAGE_ENDPOINT
        ).strip()
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else self.DEFAULT_TIMEOUT_SECONDS
        )
        self._urlopen: UrlOpen = urlopen or urllib.request.urlopen
        self._clock: Callable[[], float] = clock or time.time
        self._cache_ttl = cache_ttl_seconds
        self._grace = offline_grace_seconds
        # cache keyed by api_key — value is a (verify_result, checked_at)
        # tuple. We keep last-known-good separately from the TTL cache so
        # that an expired-but-still-in-grace key can be served as
        # degraded after a network failure.
        self._cache: dict[str, tuple[VerifyResult, float]] = {}
        self._last_good: dict[str, tuple[VerifyResult, float]] = {}

    # ---- public surface ------------------------------------------------

    def verify(self, api_key: str) -> VerifyResult:
        """Return the gate decision for ``api_key``.

        Behaviour matrix:
          * empty / wrong-shape key            → ok=False, fast-path
          * fresh cache hit (<TTL)             → cached=True, served
          * cache miss + endpoint OK           → fresh result, cached
          * cache miss + endpoint unreachable
              AND last_good within grace       → ok=True, degraded=True
              else                             → ok=False, reason=...
          * 4xx / explicit ok=False            → ok=False, no grace
        """
        if not is_valid_api_key_shape(api_key):
            return VerifyResult(  # type: ignore[typeddict-item]
                ok=False, email="", plan="",
                reason="api key missing or wrong shape (must start with fk_live_)",
                cached=False, degraded=False,
                checked_at=self._clock(),
            )
        cached = self._cache_lookup(api_key)
        if cached is not None:
            return cached
        try:
            payload = self._post_verify(api_key)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError,
                ValueError, TimeoutError) as exc:
            return self._handle_verify_failure(api_key, exc)
        result = parse_verify_response(payload)
        now = self._clock()
        result_full: VerifyResult = {  # type: ignore[typeddict-item]
            **result,
            "cached": False,
            "degraded": False,
            "checked_at": now,
        }
        self._cache[api_key] = (result_full, now)
        if result_full.get("ok"):
            self._last_good[api_key] = (result_full, now)
        return result_full

    def log_usage(
        self, api_key: str, tool: str, project_hash: str,
    ) -> UsageLogResult:
        """Fire-and-forget: POST a usage record. Never raises.

        Returns ``UsageLogResult`` for tests / observability. Production
        callers should call this and ignore the result. Any exception
        from the transport (network, HTTP, encoding) is swallowed.
        """
        if not is_valid_api_key_shape(api_key):
            return UsageLogResult(sent=False, reason="invalid key shape")  # type: ignore[typeddict-item]
        try:
            body = json.dumps(
                build_usage_log_request(api_key, tool, project_hash)
            ).encode("utf-8")
            req = urllib.request.Request(
                self.usage_endpoint,
                data=body,
                headers=self._headers(api_key),
                method="POST",
            )
            with self._urlopen(req, timeout=self.timeout_seconds) as resp:
                _ = resp.read()
            return UsageLogResult(sent=True, reason="")  # type: ignore[typeddict-item]
        except Exception as exc:  # noqa: BLE001 — fire-and-forget by contract
            return UsageLogResult(  # type: ignore[typeddict-item]
                sent=False, reason=f"{type(exc).__name__}: {exc}",
            )

    # ---- internals -----------------------------------------------------

    def _cache_lookup(self, api_key: str) -> VerifyResult | None:
        entry = self._cache.get(api_key)
        if entry is None:
            return None
        result, checked_at = entry
        if (self._clock() - checked_at) > self._cache_ttl:
            return None
        # Mark as cached without mutating the stored copy.
        out: VerifyResult = {**result, "cached": True}  # type: ignore[typeddict-item]
        return out

    def _post_verify(self, api_key: str) -> dict[str, Any]:
        body = json.dumps(build_verify_request(api_key)).encode("utf-8")
        req = urllib.request.Request(
            self.auth_endpoint,
            data=body,
            headers=self._headers(api_key),
            method="POST",
        )
        with self._urlopen(req, timeout=self.timeout_seconds) as resp:
            payload = resp.read()
        decoded = json.loads((payload or b"{}").decode("utf-8") or "{}")
        if not isinstance(decoded, dict):
            raise ValueError("verify endpoint returned non-object body")
        return decoded

    def _handle_verify_failure(
        self, api_key: str, exc: BaseException,
    ) -> VerifyResult:
        """Apply the offline-grace contract.

        4xx is a hard reject — the server explicitly told us the key is
        bad. Other failures (5xx, network, DNS, timeout) are eligible
        for grace if there's a recent last-known-good for this key.
        """
        if isinstance(exc, urllib.error.HTTPError) and 400 <= exc.code < 500:
            now = self._clock()
            result: VerifyResult = {  # type: ignore[typeddict-item]
                "ok": False, "email": "", "plan": "",
                "reason": f"verify endpoint rejected key (HTTP {exc.code})",
                "cached": False, "degraded": False,
                "checked_at": now,
            }
            # Cache the rejection for the TTL so we don't hammer the
            # endpoint with a known-bad key on every tools/call.
            self._cache[api_key] = (result, now)
            return result
        last = self._last_good.get(api_key)
        now = self._clock()
        if last is not None and (now - last[1]) <= self._grace:
            base = last[0]
            return {  # type: ignore[typeddict-item]
                **base,
                "cached": False,
                "degraded": True,
                "reason": (
                    f"verify endpoint unreachable ({type(exc).__name__});"
                    f" serving last-known-good within "
                    f"{self._grace}s grace window"
                ),
                "checked_at": now,
            }
        return {  # type: ignore[typeddict-item]
            "ok": False, "email": "", "plan": "",
            "reason": (
                f"verify endpoint unreachable ({type(exc).__name__})"
                " and no last-known-good within grace window"
            ),
            "cached": False, "degraded": False,
            "checked_at": now,
        }

    def _headers(self, api_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.USER_AGENT,
        }


__all__ = ["ForgeAuthClient"]
