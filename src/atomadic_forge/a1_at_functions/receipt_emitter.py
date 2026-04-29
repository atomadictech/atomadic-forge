"""Tier a1 — pure CertifyResult+WireReport+ScoutReport → Receipt v1.

Golden Path Lane A W1 (paired with ``card_renderer.py``).

Pure: no I/O. Takes already-computed report dicts (the same ones
``forge certify`` and ``forge wire`` already produce) plus a few
context strings, returns a ``ForgeReceiptV1`` dict ready to be
``json.dumps``-ed and either signed (Lane A W2 ``receipt_signer``)
or shipped as-is for local development.

The emitter never decides whether a Receipt should be signed. That's
a policy call the CLI layer makes. Same for lineage — Vanguard's
``/v1/forge/lineage`` lookup happens at a2; the emitter accepts a
pre-resolved ``lineage`` dict if the caller has one.

Verdict-decision contract (matches ``docs/RECEIPT.md`` §"How verdict
is decided"):

  verdict = PASS         when wire.verdict == 'PASS'
                         AND certify.score >= certify_threshold
  verdict = FAIL         when wire.verdict == 'FAIL'
                         OR  certify.score <  certify_threshold
  verdict = REFINE       when caller passed an explicit
                         override='REFINE' (iterate stagnation case)
  verdict = QUARANTINE   when caller passed an explicit
                         override='QUARANTINE' (hysteresis ratchet
                         > 0.5; reserved for Lane E)

The emitter never invents REFINE / QUARANTINE on its own.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
from pathlib import Path
from typing import Any

from ..a0_qk_constants.receipt_schema import (
    REQUIRED_RECEIPT_V1_FIELDS,
    SCHEMA_VERSION_V1,
    VALID_VERDICTS,
    ForgeReceiptV1,
    ReceiptArtifact,
    ReceiptCertify,
    ReceiptCertifyAxes,
    ReceiptLean4Attestation,
    ReceiptLineage,
    ReceiptProject,
    ReceiptScout,
    ReceiptSignatures,
    ReceiptWire,
)


_DEFAULT_THRESHOLD = 100.0
_ARTIFACT_FILES = ("scout", "cherry", "wire", "certify", "assimilate")


def _now_utc_iso() -> str:
    """Return the current UTC instant as YYYY-MM-DDTHH:MM:SSZ."""
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _decide_verdict(
    *,
    wire_verdict: str,
    certify_score: float,
    threshold: float,
    override: str | None,
) -> str:
    """See module docstring's verdict-decision contract."""
    if override is not None:
        if override not in VALID_VERDICTS:
            raise ValueError(
                f"verdict override {override!r} not in {VALID_VERDICTS}"
            )
        return override
    if wire_verdict == "PASS" and certify_score >= threshold:
        return "PASS"
    return "FAIL"


def _hash_file(path: Path) -> str | None:
    """Return the SHA-256 hex digest of a file, or None on read failure.

    Pure-ish: deterministic given file contents. The 'I/O' here is a
    bounded read of a known artifact path the caller controls; no
    network. Keeps the emitter callable in cheap-mode (caller passes
    ``compute_artifact_hashes=False`` and we skip).
    """
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _gather_artifacts(
    project_root: Path,
    *,
    compute_hashes: bool,
) -> list[ReceiptArtifact]:
    """Build the artifacts pointer list from ``.atomadic-forge/`` files."""
    base = project_root / ".atomadic-forge"
    if not base.is_dir():
        return []
    out: list[ReceiptArtifact] = []
    for name in _ARTIFACT_FILES:
        target = base / f"{name}.json"
        if not target.exists():
            continue
        sha = _hash_file(target) if compute_hashes else None
        out.append(ReceiptArtifact(
            name=name,
            path=str(target.relative_to(project_root).as_posix()),
            sha256=sha,
        ))
    return out


def _project_block(
    *,
    name: str,
    root: Path,
    package: str | None,
    primary_language: str,
    languages: dict[str, int],
    vcs: dict[str, Any] | None,
) -> ReceiptProject:
    block: ReceiptProject = ReceiptProject(
        name=name,
        root=str(root),
        package=package,
        language=primary_language,
        languages=dict(languages),
    )
    if vcs is not None:
        block["vcs"] = vcs  # type: ignore[typeddict-item]
    return block


def _certify_block(certify_result: dict) -> ReceiptCertify:
    axes = ReceiptCertifyAxes(
        documentation_complete=bool(certify_result.get("documentation_complete", False)),
        tests_present=bool(certify_result.get("tests_present", False)),
        tier_layout_present=bool(certify_result.get("tier_layout_present", False)),
        no_upward_imports=bool(certify_result.get("no_upward_imports", False)),
    )
    return ReceiptCertify(
        score=float(certify_result.get("score", 0.0)),
        axes=axes,
        issues=list(certify_result.get("issues", []) or []),
    )


def _wire_block(wire_report: dict) -> ReceiptWire:
    verdict = wire_report.get("verdict", "FAIL")
    if verdict not in ("PASS", "FAIL"):
        verdict = "FAIL"
    return ReceiptWire(
        verdict=verdict,
        violation_count=int(wire_report.get("violation_count", 0)),
        auto_fixable=int(wire_report.get("auto_fixable", 0)),
    )


def _scout_block(scout_report: dict) -> ReceiptScout:
    return ReceiptScout(
        symbol_count=int(scout_report.get("symbol_count", 0)),
        tier_distribution=dict(scout_report.get("tier_distribution", {}) or {}),
        effect_distribution=dict(scout_report.get("effect_distribution", {}) or {}),
        primary_language=str(scout_report.get("primary_language", "python")),
    )


def build_receipt(
    *,
    certify_result: dict,
    wire_report: dict,
    scout_report: dict,
    project_name: str,
    project_root: Path,
    forge_version: str,
    package: str | None = None,
    vcs: dict[str, Any] | None = None,
    assimilate_digest: str | None = None,
    signatures: ReceiptSignatures | None = None,
    lean4_attestation: ReceiptLean4Attestation | None = None,
    lineage: ReceiptLineage | None = None,
    compliance_mappings: dict[str, str] | None = None,
    notes: list[str] | None = None,
    extra: dict[str, object] | None = None,
    certify_threshold: float = _DEFAULT_THRESHOLD,
    verdict_override: str | None = None,
    compute_artifact_hashes: bool = True,
) -> ForgeReceiptV1:
    """Build a v1 Forge Receipt from already-computed reports.

    Required inputs:
      certify_result, wire_report, scout_report, project_name,
      project_root, forge_version.

    Everything else is optional and defaults to a structurally-valid
    empty / None per the v1.0 spec. Producers MAY emit unsigned
    Receipts; this is the local-development path.

    Returns a TypedDict suitable for ``json.dumps`` (every value is
    JSON-serializable: str, int, float, bool, None, list, dict).
    """
    languages = scout_report.get("language_distribution") or scout_report.get("languages") or {}
    primary = scout_report.get("primary_language", "python")
    receipt: ForgeReceiptV1 = ForgeReceiptV1(
        schema_version=SCHEMA_VERSION_V1,
        generated_at_utc=_now_utc_iso(),
        forge_version=forge_version,
        verdict=_decide_verdict(
            wire_verdict=wire_report.get("verdict", "FAIL"),
            certify_score=float(certify_result.get("score", 0.0)),
            threshold=certify_threshold,
            override=verdict_override,
        ),
        project=_project_block(
            name=project_name,
            root=Path(project_root).resolve(),
            package=package,
            primary_language=primary,
            languages=dict(languages),
            vcs=vcs,
        ),
        certify=_certify_block(certify_result),
        wire=_wire_block(wire_report),
        scout=_scout_block(scout_report),
        assimilate_digest=assimilate_digest,
        artifacts=_gather_artifacts(
            Path(project_root).resolve(),
            compute_hashes=compute_artifact_hashes,
        ),
        signatures=signatures or ReceiptSignatures(sigstore=None, aaaa_nexus=None),
        lean4_attestation=lean4_attestation or ReceiptLean4Attestation(),
        lineage=lineage or ReceiptLineage(),
        compliance_mappings=dict(compliance_mappings or {}),
        notes=list(notes or []),
        extra=dict(extra or {}),
    )
    # Spot-check that we populated every required v1 field. Defensive
    # — TypedDict does not enforce at runtime.
    for f in REQUIRED_RECEIPT_V1_FIELDS:
        if f not in receipt:
            raise RuntimeError(
                f"receipt_emitter built a Receipt missing required field "
                f"{f!r} — schema/emitter drift"
            )
    return receipt


def receipt_to_json(receipt: ForgeReceiptV1, *, indent: int = 2) -> str:
    """Serialize a Receipt to a stable JSON string.

    Sorted-keys NOT used — the emitter writes fields in spec order so
    the wire format is human-readable. ``indent`` defaults to 2 to
    match Forge's other manifest writers.
    """
    import json
    return json.dumps(receipt, indent=indent, default=str)
