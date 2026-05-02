"""Tier a2 — Receipt signing client.

Golden Path Lane A W2. Calls AAAA-Nexus ``/v1/verify/forge-receipt`` to
obtain Sigstore Rekor metadata + AAAA-Nexus signature, mutates the
Receipt in place, and returns it.

Stateful by design: holds base URL + auth env name + last-known
endpoint health (so a single CLI session probing once doesn't probe
again on every Receipt). Fits a2 cleanly (composes a1 emitter output
+ a0 schema constants + std-lib I/O); never imports a3+.

Graceful-degradation contract:
  * If ``AAAA_NEXUS_API_KEY`` is unset → return the Receipt unchanged
    with a ``notes`` entry explaining why. No exception.
  * If the endpoint returns 4xx (trial-tier rate limit, key invalid,
    feature not yet shipped) → same: return unsigned with a note.
  * Network / DNS / timeout error → same: return unsigned with a note
    that includes the underlying error class.
  * 5xx → caller's choice: ``strict=True`` raises ``RuntimeError``;
    ``strict=False`` (default) returns unsigned + note.

Why the soft-fail default: per the Golden Path, "unsigned Receipts
are valid. The signature fields default to None." A local-development
``forge certify --sign`` invocation should never crash because the
prod endpoint is having a bad day. CI gates that REQUIRE a signature
should pass ``--sign --require-signed`` (Lane G future work).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from copy import deepcopy
from typing import Any

from ..a0_qk_constants.receipt_schema import (
    ForgeReceiptV1,
    ReceiptAAAANexusSignature,
    ReceiptSigstoreSignature,
)


class ReceiptSigner:
    """Stateful signer that wraps the AAAA-Nexus verify endpoint."""

    DEFAULT_BASE_URL = "https://aaaa-nexus.atomadictech.workers.dev"
    DEFAULT_PATH = "/v1/verify/forge-receipt"
    DEFAULT_TIMEOUT_SECONDS = 30
    USER_AGENT = "atomadic-forge/0.2 (ReceiptSigner)"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key_env: str = "AAAA_NEXUS_API_KEY",
        path: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("AAAA_NEXUS_URL")
            or self.DEFAULT_BASE_URL
        ).rstrip("/")
        self.api_key_env = api_key_env
        self.path = path or self.DEFAULT_PATH
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else self.DEFAULT_TIMEOUT_SECONDS
        )
        # Soft cache of last-known reachability so a session that
        # probed once and got 404 doesn't re-probe on every receipt.
        self._endpoint_known_unavailable = False

    # ---- public surface ------------------------------------------------

    def sign(
        self,
        receipt: ForgeReceiptV1,
        *,
        strict: bool = False,
    ) -> ForgeReceiptV1:
        """Return a new Receipt with the ``signatures`` block populated.

        The input Receipt is not mutated. The output is a deep copy
        with ``signatures.sigstore`` and ``signatures.aaaa_nexus``
        either populated (success) or left at None with a ``notes``
        entry (soft-fail).
        """
        out = deepcopy(receipt)
        api_key = os.environ.get(self.api_key_env, "")
        if not api_key:
            self._note(out, f"{self.api_key_env} not set — receipt left unsigned")
            return out
        if self._endpoint_known_unavailable:
            self._note(out, "AAAA-Nexus signing endpoint unavailable this session")
            return out
        try:
            response = self._post_for_signature(receipt, api_key)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError,
                ValueError) as exc:
            return self._handle_request_failure(out, exc, strict=strict)
        self._apply_signature(out, response)
        return out

    # ---- request helpers ----------------------------------------------

    def _post_for_signature(
        self,
        receipt: ForgeReceiptV1,
        api_key: str,
    ) -> dict[str, Any]:
        body = json.dumps({"receipt": receipt}, default=str).encode("utf-8")
        endpoint = self.base_url + self.path
        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "X-API-Key": api_key,
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": self.USER_AGENT,
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            payload = resp.read()
        decoded = json.loads(payload.decode("utf-8") or "{}")
        if not isinstance(decoded, dict):
            raise ValueError("AAAA-Nexus returned non-object body")
        return decoded

    def _apply_signature(
        self,
        receipt: ForgeReceiptV1,
        response: dict[str, Any],
    ) -> None:
        sigstore = response.get("sigstore")
        nexus = response.get("aaaa_nexus") or response.get("aaaa-nexus")
        sigs = receipt.get("signatures") or {}
        if isinstance(sigstore, dict):
            sigs["sigstore"] = ReceiptSigstoreSignature(  # type: ignore[typeddict-item]
                rekor_uuid=str(sigstore.get("rekor_uuid", "")),
                log_index=int(sigstore.get("log_index", 0)),
                bundle_path=str(sigstore.get("bundle_path", "")),
            )
        else:
            sigs["sigstore"] = None  # type: ignore[typeddict-item]
        if isinstance(nexus, dict):
            sigs["aaaa_nexus"] = ReceiptAAAANexusSignature(  # type: ignore[typeddict-item]
                signature=str(nexus.get("signature", "")),
                key_id=str(nexus.get("key_id", "")),
                issuer=str(nexus.get("issuer", "")),
                issued_at_utc=str(nexus.get("issued_at_utc", "")),
                verify_endpoint=str(nexus.get("verify_endpoint", self.path)),
            )
        else:
            sigs["aaaa_nexus"] = None  # type: ignore[typeddict-item]
        receipt["signatures"] = sigs  # type: ignore[typeddict-item]

    # ---- failure handling ---------------------------------------------

    def _handle_request_failure(
        self,
        receipt: ForgeReceiptV1,
        exc: BaseException,
        *,
        strict: bool,
    ) -> ForgeReceiptV1:
        # 4xx: known bad request / auth / not-yet-shipped — never retry,
        # mark endpoint unavailable for the session so subsequent calls
        # in this run skip the round trip.
        if isinstance(exc, urllib.error.HTTPError):
            if 400 <= exc.code < 500:
                self._endpoint_known_unavailable = True
                self._note(
                    receipt,
                    f"AAAA-Nexus signing returned HTTP {exc.code}; "
                    "receipt left unsigned",
                )
                return receipt
            if strict:
                raise RuntimeError(
                    f"AAAA-Nexus signing failed with HTTP {exc.code}: {exc}"
                ) from exc
            self._note(
                receipt,
                f"AAAA-Nexus signing failed with HTTP {exc.code}; "
                "soft-fail, receipt left unsigned",
            )
            return receipt
        if strict:
            raise RuntimeError(
                f"AAAA-Nexus signing transport error: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        self._note(
            receipt,
            f"AAAA-Nexus signing transport error "
            f"({type(exc).__name__}); receipt left unsigned",
        )
        return receipt

    # ---- helpers -------------------------------------------------------

    @staticmethod
    def _note(receipt: ForgeReceiptV1, message: str) -> None:
        notes = list(receipt.get("notes") or [])
        notes.append(message)
        receipt["notes"] = notes  # type: ignore[typeddict-item]


def sign_receipt(
    receipt: ForgeReceiptV1,
    *,
    base_url: str | None = None,
    api_key_env: str = "AAAA_NEXUS_API_KEY",
    strict: bool = False,
) -> ForgeReceiptV1:
    """Module-level convenience: instantiate a signer and call ``sign``.

    For one-shot CLI calls. Long-running processes should construct a
    ``ReceiptSigner`` once and reuse it (the endpoint-availability
    cache is per-instance).
    """
    return ReceiptSigner(
        base_url=base_url,
        api_key_env=api_key_env,
    ).sign(receipt, strict=strict)
