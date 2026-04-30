"""Tier a0 — Forge Receipt JSON v1 schema.

The Receipt is the canonical wire format Forge emits for every
``forge auto`` / ``forge certify`` / ``forge enforce`` run. It bundles
the certify breakdown, wire scan summary, scout digest, optional
assimilate output, AAAA-Nexus signature placeholder, and Lean4
attestation citation into one signed-or-signable artifact.

Golden Path Lane A W0 deliverable. Lane A W1 fills in
``a1_at_functions/receipt_emitter.py`` (the pure transformer that
turns a CertifyResult + WireReport + ScoutReport into a Receipt) and
``a1_at_functions/card_renderer.py`` (the 60×24 box-drawing renderer
used by ``forge auto`` and the "62 → 5" viral demo). Lane A W2 fills
in ``a2_mo_composites/receipt_signer.py`` which calls AAAA-Nexus
``/v1/verify/forge-receipt`` to obtain a Sigstore Rekor uuid +
log_index + AAAA-Nexus signature.

Schema versioning:
  * v1.0 (this file)            — base schema; all signing / lineage /
                                  attestation fields are optional and
                                  default to None so unsigned Receipts
                                  are valid.
  * v1.1 (Golden Path W8)       — adds ``polyglot_breakdown`` (per-
                                  language certify score split).
  * v1.2 (Golden Path W12)      — adds ``slsa_attestation`` (a
                                  Sigstore-bundle-compatible
                                  ``slsa-provenance-ai/v1`` predicate).
  * v2.0 (Golden Path W24)      — adds ``bao_rompf_witnesses`` (full
                                  categorical effect signatures per
                                  public symbol).

Forward-compat rule: every optional field defaults to ``None`` (or
``[]`` / ``{}`` for collections). Consumers must accept and ignore
unknown fields. Producers MUST emit ``schema_version`` and SHOULD
emit every required field; everything else is optional.

Wire-format note: ``schema_version`` always matches the regex
``^atomadic-forge\\.receipt/v\\d+(?:\\.\\d+)?$`` so a single dispatcher
can route any future Receipt version.

This module is pure data shape — no logic, no imports beyond
``typing``. Keeps a0 invariant under the Atomadic monadic law.
"""
from __future__ import annotations

from typing import Literal, TypedDict

SCHEMA_VERSION_V1 = "atomadic-forge.receipt/v1"
SCHEMA_VERSION_V1_1 = "atomadic-forge.receipt/v1.1"
SCHEMA_VERSION_V1_2 = "atomadic-forge.receipt/v1.2"
SCHEMA_VERSION_V2 = "atomadic-forge.receipt/v2"

ReceiptVerdict = Literal["PASS", "FAIL", "REFINE", "QUARANTINE"]


class ReceiptVCS(TypedDict, total=False):
    """Version-control metadata for the project under Receipt.

    All optional. ``dirty`` is True when the working tree had
    uncommitted changes at Receipt-emission time. ``head_sha`` is the
    full commit SHA, ``branch`` the symbolic ref. Receipts emitted on
    detached HEAD report ``branch=None``.
    """
    head_sha: str
    short_sha: str
    branch: str | None
    remote_url: str
    dirty: bool


class ReceiptProject(TypedDict, total=False):
    """Identifies the project this Receipt covers."""
    name: str
    root: str                       # absolute path at emission time
    package: str | None             # python package name (if applicable)
    language: str                   # primary_language from scout
    languages: dict[str, int]       # per-language file counts
    vcs: ReceiptVCS


class ReceiptCertifyAxes(TypedDict):
    """Per-axis pass/fail flags from CertifyResult.

    The structural axes (always present in v1):
      * documentation_complete   — README.md OR ≥2 docs/*.md
      * tests_present            — tests/test_*.py OR tests/*_test.py
      * tier_layout_present      — ≥3 tier directories
      * no_upward_imports        — wire scan PASS
    """
    documentation_complete: bool
    tests_present: bool
    tier_layout_present: bool
    no_upward_imports: bool


class ReceiptCertify(TypedDict):
    """Compact certify summary embedded in the Receipt.

    Mirrors CertifyResult's score + axes; full details remain in
    ``.atomadic-forge/certify.json`` (referenced by ``artifacts``).
    """
    score: float                    # 0..100
    axes: ReceiptCertifyAxes
    issues: list[str]


class ReceiptWire(TypedDict):
    """Compact wire summary embedded in the Receipt.

    Mirrors WireReport's verdict + counts; the full violation list and
    repair suggestions remain in ``.atomadic-forge/wire.json``.
    """
    verdict: Literal["PASS", "FAIL"]
    violation_count: int
    auto_fixable: int               # populated only when --suggest-repairs


class ReceiptScout(TypedDict):
    """Compact scout summary embedded in the Receipt."""
    symbol_count: int
    tier_distribution: dict[str, int]
    effect_distribution: dict[str, int]
    primary_language: str


class ReceiptArtifact(TypedDict):
    """Pointer to an evidence file under .atomadic-forge/.

    A consuming verifier can re-hash the file at ``path`` and compare
    against ``sha256`` to confirm the Receipt references the exact
    artifact at issue. Hashing is the consumer's responsibility; the
    emitter populates the field when it can.
    """
    name: str                       # e.g. "scout", "wire", "certify"
    path: str                       # relative to project root
    sha256: str | None              # None when not computed (cheap mode)


class ReceiptSigstoreSignature(TypedDict, total=False):
    """Sigstore Rekor entry for the Receipt (Lane A W2)."""
    rekor_uuid: str
    log_index: int
    bundle_path: str                # path to the sigstore bundle file


class ReceiptAAAANexusSignature(TypedDict, total=False):
    """AAAA-Nexus signature attached via /v1/verify/forge-receipt (Lane A W2)."""
    signature: str                  # base64-encoded
    key_id: str
    issuer: str                     # e.g. "aaaa-nexus.atomadic.tech"
    issued_at_utc: str
    verify_endpoint: str            # e.g. "/v1/verify/forge-receipt"


class ReceiptLocalSignSignature(TypedDict, total=False):
    """Ed25519 local signing block (Lane G W5).

    Populated by ``a1_at_functions.local_signer.sign_receipt_local`` when
    the caller passes ``--local-sign``. The signature covers the canonical
    receipt hash (same content-addressed bytes used by the lineage chain),
    so re-signing after a notes append does not change the signed payload.
    """
    alg: str            # always "Ed25519"
    signature: str      # base64-encoded 64-byte Ed25519 signature
    public_key: str     # base64-encoded 32-byte raw public key
    key_id: str         # first 16 hex chars of SHA-256(raw_public_key)
    signed_at_utc: str  # YYYY-MM-DDTHH:MM:SSZ


class ReceiptSignatures(TypedDict, total=False):
    """All signature claims attached to this Receipt.

    Receipts can ship unsigned (all fields ``None``) — ``--emit-receipt``
    without ``--sign`` produces a structurally-valid but unattested
    Receipt suitable for local development. Lane A W2's signer fills
    ``sigstore`` and ``aaaa_nexus``; Lane G W5's local signer fills
    ``local_sign``.
    """
    sigstore: ReceiptSigstoreSignature | None
    aaaa_nexus: ReceiptAAAANexusSignature | None
    local_sign: ReceiptLocalSignSignature | None  # Lane G W5


class ReceiptLean4Corpus(TypedDict, total=False):
    """One Lean4 corpus citation. Multiple per Receipt.

    Cites a machine-checked theorem corpus that backs a claim made by
    this Receipt. The Golden Path threads two corpora through every
    Receipt: ``aethel-nexus-proofs`` (29 theorems, 0 sorry, 0 axioms)
    and ``mhed-toe-codex-v22`` (538 theorems, 0 sorry).
    """
    name: str                       # e.g. "aethel-nexus-proofs"
    repo_url: str
    ref_sha: str                    # commit SHA the Receipt cites
    theorem_count: int
    sorry_count: int                # MUST be 0 for an attesting Receipt
    axiom_count: int                # SHOULD be 0; record exceptions


class ReceiptLean4Attestation(TypedDict, total=False):
    """Lean4 attestation block (Lane A; cited in CS-1 at Lane F W16)."""
    corpora: list[ReceiptLean4Corpus]
    total_theorems: int             # sum across corpora — denormalized for ergonomics
    summary: str                    # human-readable one-liner


class ReceiptLineage(TypedDict, total=False):
    """Pointer to the Vanguard structural-change ledger entry (Lane A W4).

    ``lineage_path`` is opaque to the Receipt — Vanguard owns the
    schema. A consumer can dereference it via the AAAA-Nexus
    ``/v1/forge/lineage`` endpoint to fetch the full chain.
    """
    lineage_path: str               # opaque ledger path / URL
    parent_receipt_hash: str | None # SHA-256 of the immediately prior Receipt
    chain_depth: int                # 1 for first Receipt; n+1 for each successor


class ReceiptPolyglotBreakdown(TypedDict, total=False):
    """v1.1 — per-language file + symbol counts (Lane A W8 seed).

    Forward-compat: v0.4+ will add per-language certify scores; today
    we only ship the file + symbol breakdown so consumers can render
    'this repo is 80% Python, 15% TypeScript' badges from the Receipt
    alone (no separate scout call needed).
    """
    file_count: int
    languages: dict[str, int]            # {lang: file_count}
    symbol_count: int
    symbols_by_language: dict[str, int]  # {lang: symbol_count}
    primary_language: str


class ForgeReceiptV1(TypedDict, total=False):
    """The Forge Receipt v1.0 wire format.

    Required fields (every emitter MUST populate):
      * schema_version
      * generated_at_utc
      * forge_version
      * verdict
      * project
      * certify
      * wire
      * scout

    Optional fields (filled in by W2+ infrastructure or omitted in
    cheap-mode emission):
      * assimilate           — present only on --apply runs
      * artifacts            — pointers to .atomadic-forge/*.json files
      * signatures           — Sigstore + AAAA-Nexus claims
      * lean4_attestation    — corpus citations
      * lineage              — Vanguard ledger pointer (W4)
      * compliance_mappings  — populated at Lane F W18
      * extra                — escape hatch for forward-compat fields

    Reserved (will be required in future minor versions):
      * polyglot_breakdown   — v1.1 (Lane A W8)
      * slsa_attestation     — v1.2 (Lane A W12)
      * bao_rompf_witnesses  — v2.0 (Lane A W24)
    """
    # ---- required (v1.0) ----
    schema_version: str
    generated_at_utc: str           # YYYY-MM-DDTHH:MM:SSZ
    forge_version: str
    verdict: ReceiptVerdict
    project: ReceiptProject
    certify: ReceiptCertify
    wire: ReceiptWire
    scout: ReceiptScout
    # ---- optional (v1.0) ----
    assimilate_digest: str | None
    artifacts: list[ReceiptArtifact]
    signatures: ReceiptSignatures
    lean4_attestation: ReceiptLean4Attestation
    lineage: ReceiptLineage
    compliance_mappings: dict[str, str]    # mapping_name → status
    notes: list[str]                       # free-form human-facing notes
    extra: dict[str, object]               # forward-compat escape hatch
    # v1.1 (Lane A W8) — optional in v1.0, required in v1.1+:
    polyglot_breakdown: ReceiptPolyglotBreakdown


REQUIRED_RECEIPT_V1_FIELDS: tuple[str, ...] = (
    "schema_version",
    "generated_at_utc",
    "forge_version",
    "verdict",
    "project",
    "certify",
    "wire",
    "scout",
)
"""The minimum field set every v1 Receipt MUST populate.

Used by ``a1_at_functions/receipt_emitter.py`` to short-circuit
emission and by tests to guard against silent drift. The list itself
is part of the schema contract — adding a required field is a major
version bump.
"""


VALID_VERDICTS: tuple[str, ...] = ("PASS", "FAIL", "REFINE", "QUARANTINE")
"""The four UEP v20 verdict values. Every Receipt's ``verdict`` must
be exactly one of these strings.

PASS         — wire PASS AND certify ≥ threshold
FAIL         — at least one structural gate failed
REFINE       — incomplete; re-plan and re-emit
QUARANTINE   — pause; needs human audit
"""
