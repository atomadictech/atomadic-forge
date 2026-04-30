"""Tier a1 — pure helpers for the Forge subscription gate.

Golden Path Lane C W5 deliverable. Stateless helpers that read from
inputs and return values — no I/O, no env access of their own, no
filesystem touches. The HTTP round trips and the in-memory cache live
in ``a2_mo_composites/forge_auth_client.py``; the MCP gate that calls
both lives in ``a3_og_features/mcp_server.py``.

The split mirrors the a1↔a2 contract used by the receipt signer: a1
shapes the request body and parses the response into a ``VerifyResult``
TypedDict; a2 owns the network call, the cache, and the offline-grace
clock. That way the parser is trivially unit-testable without monkey-
patching urllib.

What lives here:
  * ``read_api_key_from_env``   — pull FORGE_API_KEY out of an env dict
                                   (passed in, not read from os.environ)
  * ``is_valid_api_key_shape``  — cheap fk_live_-prefix check
  * ``build_verify_request``    — body for the verify POST
  * ``parse_verify_response``   — JSON dict → VerifyResult, strict
  * ``build_usage_log_request`` — body for the usage-log POST
  * ``hash_project_path``       — SHA-256 of resolved abspath, so the
                                   telemetry stream sees ``a3f81b...``
                                   instead of ``C:/Users/<name>/...``
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..a0_qk_constants.auth_constants import (
    API_KEY_ENV,
    API_KEY_PREFIX,
    VerifyResult,
)


def read_api_key_from_env(env: dict[str, str]) -> str | None:
    """Return the FORGE_API_KEY value from ``env`` if it's plausibly real.

    Pure: takes an env dict (caller passes ``os.environ`` or a test
    fixture), strips whitespace, and returns the key only when it
    starts with the ``fk_live_`` prefix. Missing or wrong-shape keys
    return ``None`` — so the caller can distinguish "no key configured"
    from "key was set to a non-empty but invalid string". Both cases
    fail the gate, but the caller may want to print different hints.
    """
    raw = env.get(API_KEY_ENV)
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    if not stripped.startswith(API_KEY_PREFIX):
        return None
    return stripped


def is_valid_api_key_shape(key: str) -> bool:
    """Return True when ``key`` looks like a real Forge live key.

    Validates the ``fk_live_`` prefix AND requires at least one
    character after it (so ``fk_live_`` alone is rejected). This is
    the cheap pre-check the a2 client runs before the network round
    trip; the verify endpoint owns the authoritative decision.
    """
    if not isinstance(key, str):
        return False
    stripped = key.strip()
    if not stripped.startswith(API_KEY_PREFIX):
        return False
    if len(stripped) <= len(API_KEY_PREFIX):
        return False
    return True


def build_verify_request(api_key: str) -> dict[str, str]:
    """Return the JSON body for a verify POST.

    Pure: just shapes the dict. Encoding to bytes happens in a2 right
    before the urllib call, which lets a2 control content-type headers.
    """
    return {"api_key": api_key}


def parse_verify_response(body: dict[str, Any]) -> VerifyResult:
    """Convert the verify endpoint's JSON body into a strict VerifyResult.

    The remote shape we accept (Lane C W5 v1):

        {
          "ok": true,
          "email": "user@example.com",
          "plan": "pro",
          "reason": ""
        }

    Anything missing falls back to safe defaults (ok=False, empty
    strings). ``cached`` and ``degraded`` are NOT set here — those are
    a2's concern (the client knows whether it's serving a cached or
    degraded result; the parser doesn't).
    """
    if not isinstance(body, dict):
        return VerifyResult(  # type: ignore[typeddict-item]
            ok=False, email="", plan="",
            reason="non-object response from verify endpoint",
        )
    ok_raw = body.get("ok", False)
    ok = bool(ok_raw) if isinstance(ok_raw, bool | int) else False
    email = body.get("email") or ""
    plan = body.get("plan") or ""
    reason = body.get("reason") or ("" if ok else "verify endpoint returned ok=False")
    out: VerifyResult = {  # type: ignore[typeddict-item]
        "ok": ok,
        "email": str(email),
        "plan": str(plan),
        "reason": str(reason),
    }
    return out


def build_usage_log_request(
    api_key: str, tool: str, project_hash: str,
) -> dict[str, str]:
    """Return the JSON body for one usage-log POST.

    The body intentionally never includes the raw project path — the
    caller is expected to pass ``hash_project_path(...)`` so the
    telemetry stream stores opaque hashes, not local FS layouts.
    """
    return {
        "api_key": api_key,
        "tool": tool,
        "project_hash": project_hash,
    }


def hash_project_path(path: str | Path) -> str:
    """Return the SHA-256 hex digest of the resolved absolute path.

    Stable across runs on the same machine, but reveals nothing about
    the user's directory layout to the telemetry endpoint. Unicode
    paths are encoded as UTF-8 before hashing.
    """
    resolved = str(Path(path).resolve())
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()


__all__ = [
    "build_usage_log_request",
    "build_verify_request",
    "hash_project_path",
    "is_valid_api_key_shape",
    "parse_verify_response",
    "read_api_key_from_env",
]
