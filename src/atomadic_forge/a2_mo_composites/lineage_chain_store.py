"""Tier a2 — append-only lineage chain store.

Persists the local Vanguard-style lineage chain at
``.atomadic-forge/lineage_chain.jsonl``. One JSON line per Receipt;
each line records:

    {
      "ts_utc":              "2026-04-29T05:30:00Z",
      "hash":                "<receipt content hash>",
      "parent_receipt_hash": "<prior link hash, or null for head>",
      "chain_depth":         <int>,
      "verdict":             "PASS" | "FAIL" | "REFINE" | "QUARANTINE",
      "schema_version":      "<receipt schema_version>",
      "lineage_path":        "<local:// URI>",
    }

Reading the tip of the chain returns ``(parent_hash, depth)`` for the
next link to consume. The chain log is append-only — corrupt lines
are skipped silently so a malformed write never breaks subsequent
reads.

Lane A W4 ships the LOCAL store today; the AAAA-Nexus
``/v1/forge/lineage`` POST publisher slots in here once the endpoint
is live, with the same soft-fail contract as Lane A W2's
``ReceiptSigner``.
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from ..a0_qk_constants.receipt_schema import ForgeReceiptV1
from ..a1_at_functions.lineage_chain import (
    canonical_receipt_hash,
    link_to_parent,
)


_DIRNAME = ".atomadic-forge"
_FILENAME = "lineage_chain.jsonl"


class LineageChainStore:
    """Append-only local Vanguard ledger for one project."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root).resolve()
        self.dir = self.project_root / _DIRNAME
        self.path = self.dir / _FILENAME

    # ---- read paths ----------------------------------------------------

    def read_tip(self) -> tuple[str | None, int]:
        """Return ``(parent_hash, depth_of_tip)``.

        For the chain head (no prior receipts) the tuple is
        ``(None, 0)``; the next link should be at depth=1.
        """
        if not self.path.exists():
            return None, 0
        last: dict | None = None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                last = entry
        if last is None:
            return None, 0
        return last.get("hash"), int(last.get("chain_depth", 0))

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        out: list[dict] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                out.append(entry)
        return out

    # ---- write path ----------------------------------------------------

    def link_and_append(self, receipt: ForgeReceiptV1) -> ForgeReceiptV1:
        """Compute the chain link for ``receipt``, append, return the
        Receipt with its lineage block populated.

        Always writes — append-only. Caller decides whether to also
        re-emit the Receipt JSON (typically yes; the chain entry and
        the on-disk Receipt should both reflect the same lineage).
        """
        parent_hash, parent_depth = self.read_tip()
        linked = link_to_parent(
            receipt,
            parent_receipt_hash=parent_hash,
            chain_depth=parent_depth + 1,
        )
        own_hash = canonical_receipt_hash(linked)
        entry = {
            "ts_utc": _dt.datetime.now(_dt.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "hash": own_hash,
            "parent_receipt_hash": parent_hash,
            "chain_depth": parent_depth + 1,
            "verdict": linked.get("verdict"),
            "schema_version": linked.get("schema_version"),
            "lineage_path": (linked.get("lineage") or {}).get("lineage_path"),
        }
        self.dir.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return linked
