"""Tier a1 — pure Ed25519 local signing for Forge Receipts.

Golden Path Lane G W5. Signs ``canonical_receipt_hash(receipt)`` with a
local Ed25519 private key (PEM); attaches the result to
``receipt['signatures']['local_sign']``.

Soft-fail contract (mirrors the Lane A W2 AAAA-Nexus signer):
  * 'cryptography' not installed  -> receipt unchanged + notes entry, no raise
  * key_path missing / unreadable -> receipt unchanged + notes entry, no raise
  * key is not Ed25519            -> receipt unchanged + notes entry, no raise
  * verify_receipt_local          -> returns (ok, problems), never raises
"""
from __future__ import annotations

import base64
import datetime as _dt
import hashlib
from copy import deepcopy
from pathlib import Path

from ..a0_qk_constants.receipt_schema import (
    ForgeReceiptV1,
    ReceiptLocalSignSignature,
)
from .lineage_chain import canonical_receipt_hash


def sign_receipt_local(
    receipt: ForgeReceiptV1,
    *,
    key_path: Path | str,
) -> ForgeReceiptV1:
    """Return a copy of ``receipt`` with ``signatures.local_sign`` populated.

    Reads an Ed25519 private key from ``key_path`` (PEM, unencrypted),
    signs ``canonical_receipt_hash(receipt)``, and attaches the block.
    Soft-fails silently on any error.
    """
    out = deepcopy(receipt)

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # noqa: PLC0415
            Ed25519PrivateKey,
        )
        from cryptography.hazmat.primitives.serialization import (  # noqa: PLC0415
            Encoding,
            PublicFormat,
            load_pem_private_key,
        )
    except ImportError:
        _note(out, "local_sign skipped: 'cryptography' package not installed")
        return out

    key_path = Path(key_path)
    try:
        pem_bytes = key_path.read_bytes()
        private_key = load_pem_private_key(pem_bytes, password=None)
        if not isinstance(private_key, Ed25519PrivateKey):
            _note(out, f"local_sign skipped: {key_path.name} is not an Ed25519 key")
            return out
    except Exception as exc:  # noqa: BLE001
        _note(out, f"local_sign skipped: cannot load {key_path.name}: {type(exc).__name__}")
        return out

    receipt_hash_hex = canonical_receipt_hash(out)
    hash_bytes = bytes.fromhex(receipt_hash_hex)

    try:
        sig_bytes = private_key.sign(hash_bytes)
    except Exception as exc:  # noqa: BLE001
        _note(out, f"local_sign skipped: sign() raised {type(exc).__name__}")
        return out

    pub_key = private_key.public_key()
    pub_raw = pub_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    key_id = hashlib.sha256(pub_raw).hexdigest()[:16]
    signed_at = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    local_sig: ReceiptLocalSignSignature = {
        "alg": "Ed25519",
        "signature": base64.b64encode(sig_bytes).decode("ascii"),
        "public_key": base64.b64encode(pub_raw).decode("ascii"),
        "key_id": key_id,
        "signed_at_utc": signed_at,
    }
    sigs = dict(out.get("signatures") or {})
    sigs["local_sign"] = local_sig  # type: ignore[typeddict-item]
    out["signatures"] = sigs  # type: ignore[typeddict-item]
    return out


def verify_receipt_local(receipt: ForgeReceiptV1) -> tuple[bool, list[str]]:
    """Verify the ``signatures.local_sign`` block in a Receipt.

    Returns ``(True, [])`` when valid. Returns ``(False, [problem...])``
    on any failure. Never raises.
    """
    sigs = receipt.get("signatures") or {}
    local_sig = (sigs or {}).get("local_sign")  # type: ignore[union-attr]
    if local_sig is None:
        return False, ["no local_sign block in receipt.signatures"]

    try:
        from cryptography.exceptions import InvalidSignature  # noqa: PLC0415
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # noqa: PLC0415
            Ed25519PublicKey,
        )
    except ImportError:
        return False, ["'cryptography' package not installed — cannot verify"]

    try:
        sig_bytes = base64.b64decode(local_sig["signature"])
        pub_raw = base64.b64decode(local_sig["public_key"])
    except Exception as exc:  # noqa: BLE001
        return False, [f"base64 decode failed: {exc}"]

    receipt_hash_hex = canonical_receipt_hash(receipt)
    hash_bytes = bytes.fromhex(receipt_hash_hex)

    try:
        pub_key = Ed25519PublicKey.from_public_bytes(pub_raw)
        pub_key.verify(sig_bytes, hash_bytes)
    except InvalidSignature:
        return False, ["Ed25519 signature verification failed"]
    except Exception as exc:  # noqa: BLE001
        return False, [f"verification error: {type(exc).__name__}: {exc}"]

    return True, []


def _note(receipt: ForgeReceiptV1, message: str) -> None:
    notes = list(receipt.get("notes") or [])
    notes.append(message)
    receipt["notes"] = notes  # type: ignore[typeddict-item]
