"""Tier a1 — pure Vanguard-style lineage chain primitives.

Golden Path Lane A W4 deliverable. Until AAAA-Nexus
``/v1/forge/lineage`` ships, every Receipt still gets a real
``lineage`` block via a local content-addressed chain:

  receipt_hash := SHA-256(canonical_json(receipt minus mutable fields))
  link_n.parent_receipt_hash = receipt_hash(receipt_{n-1})
  link_n.chain_depth         = link_{n-1}.chain_depth + 1
  link_n.lineage_path        = 'local://lineage-chain/<receipt_hash>'

Mutable fields excluded from the canonical hash:
  signatures   — added by Lane A W2 signer (would change the hash if
                 we hashed AFTER signing)
  lineage      — circular: hashing the lineage block would require
                 the hash to depend on itself
  notes        — soft-fail strings appended over time
  generated_at_utc — timestamp drift between emit and sign

Once Vanguard ships, ``a2_mo_composites.lineage_chain_store`` will
also POST each link to ``/v1/forge/lineage`` with the same soft-fail
contract as W2 signer; the LOCAL chain remains the source of truth.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from ..a0_qk_constants.receipt_schema import ForgeReceiptV1, ReceiptLineage

_HASH_EXCLUDE_FIELDS: frozenset[str] = frozenset({
    "signatures",
    "lineage",
    "notes",
    "generated_at_utc",
})

_LOCAL_LINEAGE_PREFIX: str = "local://lineage-chain/"


def canonical_receipt_hash(receipt: ForgeReceiptV1) -> str:
    """SHA-256 hex digest of the receipt's structural content.

    Excludes the four mutable fields enumerated in
    ``_HASH_EXCLUDE_FIELDS`` so signing / re-emitting / re-noting a
    receipt does not change its identity. Two receipts with the same
    project + verdict + certify + wire + scout content yield the same
    hash regardless of sign state.
    """
    stripped: dict[str, Any] = {
        k: v for k, v in receipt.items()
        if k not in _HASH_EXCLUDE_FIELDS
    }
    canonical = json.dumps(stripped, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def link_to_parent(
    receipt: ForgeReceiptV1,
    *,
    parent_receipt_hash: str | None,
    chain_depth: int,
    lineage_path: str | None = None,
) -> ForgeReceiptV1:
    """Return a deep-copy of ``receipt`` with the lineage block populated.

    ``parent_receipt_hash``: SHA-256 hex digest of the immediately
                             prior link's receipt (None for chain head).
    ``chain_depth``:        1 for the chain head; n+1 for each link.
    ``lineage_path``:       optional override; defaults to a local URI
                             of the form ``local://lineage-chain/<hash>``.

    Pure: input is not mutated.
    """
    if chain_depth < 1:
        raise ValueError("chain_depth must be >= 1")
    out = deepcopy(receipt)
    own_hash = canonical_receipt_hash(out)
    path = lineage_path or f"{_LOCAL_LINEAGE_PREFIX}{own_hash}"
    out["lineage"] = ReceiptLineage(
        lineage_path=path,
        parent_receipt_hash=parent_receipt_hash,
        chain_depth=chain_depth,
    )
    return out


def is_local_lineage(lineage_path: str | None) -> bool:
    """True when the lineage_path is a local-chain pointer.

    Useful for downstream tools (CS-1 PDF, Lane B Studio) to render a
    'local-only' badge until the AAAA-Nexus Vanguard wire-up ships.
    """
    return bool(lineage_path) and str(lineage_path).startswith(_LOCAL_LINEAGE_PREFIX)


def verify_chain_link(
    child: ForgeReceiptV1,
    parent: ForgeReceiptV1 | None,
) -> tuple[bool, list[str]]:
    """Verify that ``child`` is a valid successor of ``parent``.

    Returns (ok, problems). ``ok`` is True when:
      * child.lineage.parent_receipt_hash == hash(parent)  (or both None)
      * child.lineage.chain_depth == parent.lineage.chain_depth + 1  (or 1)

    Pure check; no I/O. Used by the chain store and by anyone who
    wants to audit a saved chain offline.
    """
    problems: list[str] = []
    lineage = child.get("lineage") or {}
    if not lineage:
        problems.append("child receipt has no lineage block")
        return False, problems
    declared_parent = lineage.get("parent_receipt_hash")
    declared_depth = lineage.get("chain_depth")

    if parent is None:
        if declared_parent is not None:
            problems.append(
                "chain head must have parent_receipt_hash=None; "
                f"got {declared_parent!r}"
            )
        if declared_depth != 1:
            problems.append(
                f"chain head must have chain_depth=1; got {declared_depth!r}"
            )
    else:
        expected_parent_hash = canonical_receipt_hash(parent)
        if declared_parent != expected_parent_hash:
            problems.append(
                f"parent_receipt_hash mismatch: declared={declared_parent!r} "
                f"expected={expected_parent_hash!r}"
            )
        parent_lineage = parent.get("lineage") or {}
        parent_depth = int(parent_lineage.get("chain_depth", 0))
        if declared_depth != parent_depth + 1:
            problems.append(
                f"chain_depth not monotonic: declared={declared_depth!r} "
                f"parent_depth={parent_depth!r}"
            )
    return (not problems), problems
