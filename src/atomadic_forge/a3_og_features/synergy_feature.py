"""Tier a3 — Synergy Scan feature.

One pipeline that wires the a1 surface-extractor + detector + renderer:

    SynergyScan(repo).scan() → SynergyScanReport
    SynergyScan(repo).implement(candidate_id) → wrote commands/<name>.py
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from ..a0_qk_constants.synergy_types import (
    SynergyScanReport,
)
from ..a1_at_functions.synergy_detect import detect_synergies
from ..a1_at_functions.synergy_render import render_synergy_adapter
from ..a1_at_functions.synergy_surface_extract import harvest_feature_surfaces


class SynergyScan:
    """Find feature-level synergies across an ASS-ADE-style package."""

    def __init__(self, *, src_root: Path, package: str = "atomadic_forge") -> None:
        self.src_root = Path(src_root)
        self.package = package
        self._features = None  # cached

    @property
    def features(self) -> list:
        if self._features is None:
            self._features = harvest_feature_surfaces(self.src_root, self.package)
        return self._features

    def scan(self, *, top_n: int = 25) -> SynergyScanReport:
        candidates = detect_synergies(self.features)[:top_n]
        return SynergyScanReport(
            schema_version="atomadic-forge.synergy.scan/v1",
            generated_at_utc=_dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            feature_count=len(self.features),
            candidate_count=len(candidates),
            candidates=candidates,
        )

    def implement(self, candidate_id: str, report: SynergyScanReport,
                  *, out_dir: Path | None = None) -> Path:
        match = next((c for c in report["candidates"]
                      if c["candidate_id"] == candidate_id), None)
        if match is None:
            raise KeyError(f"candidate {candidate_id} not in report")
        target_dir = out_dir or (self.src_root / self.package / "commands")
        target_dir.mkdir(parents=True, exist_ok=True)
        slug = match["proposed_adapter_name"].replace("-", "_") + ".py"
        target = target_dir / slug
        target.write_text(render_synergy_adapter(match), encoding="utf-8")
        return target

    @staticmethod
    def save_report(report: SynergyScanReport, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, default=str),
                          encoding="utf-8")
        return target
