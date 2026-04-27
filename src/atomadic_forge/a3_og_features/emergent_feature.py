"""Tier a3 — Emergent Behaviors Scan feature.

Glues the a1 harvester / composer / ranker / synthesiser into one pipeline.
The a4 CLI surface (``commands/emergent.py``) is the only thing that
should depend on this module.
"""

from __future__ import annotations

import collections
import datetime as _dt
import json
from pathlib import Path
from typing import Iterable

from ..a0_qk_constants.emergent_types import (
    EmergentCandidateCard,
    EmergentScanReport,
    SymbolSignatureCard,
)
from ..a1_at_functions.emergent_compose import find_chains
from ..a1_at_functions.emergent_rank import rank_chains
from ..a1_at_functions.emergent_signature_extract import harvest_signatures
from ..a1_at_functions.emergent_synthesize import render_emergent_feature


class EmergentScan:
    """Scan a tier-organized package for emergent feature candidates."""

    def __init__(self, *, src_root: Path, package: str = "atomadic_forge") -> None:
        self.src_root = Path(src_root)
        self.package = package
        self._catalog: list[SymbolSignatureCard] | None = None
        self._chains_count: int = 0

    @property
    def catalog(self) -> list[SymbolSignatureCard]:
        if self._catalog is None:
            self._catalog = harvest_signatures(self.src_root, self.package)
        return self._catalog

    def scan(
        self,
        *,
        max_depth: int = 3,
        top_n: int = 25,
        require_pure: bool = False,
        domain_jump_required: bool = True,
        max_chains: int = 5_000,
    ) -> EmergentScanReport:
        catalog = self.catalog
        chains = find_chains(
            catalog,
            max_depth=max_depth,
            max_chains=max_chains,
            require_pure=require_pure,
            domain_jump_required=domain_jump_required,
        )
        self._chains_count = len(chains)
        candidates = rank_chains(chains, catalog=catalog, top_n=top_n)

        domain_inv: collections.Counter[str] = collections.Counter(
            c["domain"] for c in catalog
        )
        tier_inv: collections.Counter[str] = collections.Counter(
            c["tier"] for c in catalog
        )

        return EmergentScanReport(
            schema_version="atomadic-forge.emergent.scan/v1",
            generated_at_utc=_dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            catalog_size=len(catalog),
            chain_count_considered=len(chains),
            candidates=candidates,
            domain_inventory=dict(domain_inv),
            tier_inventory=dict(tier_inv),
        )

    def synthesize(self, candidate_id: str, report: EmergentScanReport,
                   *, out_dir: Path | None = None) -> Path:
        """Materialize a candidate as a new ``a3_og_features/<name>.py``."""
        match = next((c for c in report["candidates"] if c["candidate_id"] == candidate_id),
                     None)
        if match is None:
            raise KeyError(f"candidate {candidate_id} not found in report")
        out_dir = out_dir or (self.src_root / self.package / "a3_og_features")
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = match["name"].replace("-", "_") + "_emergent.py"
        target = out_dir / slug
        target.write_text(render_emergent_feature(match), encoding="utf-8")
        return target

    @staticmethod
    def save_report(report: EmergentScanReport, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        return target
