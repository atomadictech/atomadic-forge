"""Tier a1 -- pure Forge Conformity Statement CS-1 renderer.

Golden Path Lane F W1.

Composes a ForgeReceiptV1 dict (already validated by receipt_emitter)
into a ``ForgeCS1V1`` dict (schema ``atomadic-forge.cs1/v1``) and then
renders it to regulator-friendly Markdown.  Pure: no I/O, stdlib only.

CS-1 is the Atomadic Forge Conformity Statement -- a single artifact
that bundles EU AI Act Annex IV, Federal Reserve SR 11-7, FDA PCCP,
and DoD CMMC-AI compliance evidence into one signed-or-signable doc.

Compliance framework citations
  EU AI Act   -- Regulation (EU) 2024/1689, Annex IV
  SR 11-7     -- Federal Reserve SR Letter 11-7 (2011) + FAQ (2021)
  FDA PCCP    -- FDA Guidance: AI/ML-Based SaMD Action Plan 2021;
                 Predetermined Change Control Plan (PCCP) Draft 2023
  CMMC-AI     -- CMMC 2.0 (32 CFR Part 170) + NIST AI RMF 1.0 (2023)
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from typing import Any

CS1_SCHEMA_VERSION = "atomadic-forge.cs1/v1"

_REQUIRED_RECEIPT_FIELDS = (
    "schema_version",
    "generated_at_utc",
    "verdict",
    "project",
    "certify",
    "wire",
    "scout",
)

# ---------------------------------------------------------------------------
# Compliance claim templates
# ---------------------------------------------------------------------------

_EU_AI_ACT_CLAIMS: list[dict[str, str]] = [
    {
        "framework": "EU AI Act",
        "ref": "Annex IV §1",
        "title": "General description of the AI system",
        "citation": "Regulation (EU) 2024/1689, Annex IV, paragraph 1",
        "receipt_field": "project.name + project.language + scout.symbol_count",
        "evidence": (
            "The project block (Receipt field: ``project``) records the "
            "system name, primary programming language, and per-language "
            "file counts.  The scout block records total symbol count and "
            "tier distribution, providing the structural description "
            "required by Annex IV §1."
        ),
    },
    {
        "framework": "EU AI Act",
        "ref": "Annex IV §2(a)",
        "title": "Training, validation and testing data",
        "citation": "Regulation (EU) 2024/1689, Annex IV, paragraph 2(a)",
        "receipt_field": "lean4_attestation.corpora",
        "evidence": (
            "Lean4 corpora cited in ``lean4_attestation`` enumerate the "
            "machine-checked theorem corpora used to validate the system's "
            "structural invariants.  Each corpus entry records name, "
            "repo_url, ref_sha, theorem_count, sorry_count (MUST be 0), "
            "and axiom_count, satisfying the data-documentation obligation "
            "under Annex IV §2(a)."
        ),
    },
    {
        "framework": "EU AI Act",
        "ref": "Annex IV §2(b)",
        "title": "Data governance and data management practices",
        "citation": "Regulation (EU) 2024/1689, Annex IV, paragraph 2(b)",
        "receipt_field": "lineage.lineage_path + lineage.chain_depth",
        "evidence": (
            "The Vanguard lineage chain (``lineage.lineage_path``, "
            "``lineage.chain_depth``, ``lineage.parent_receipt_hash``) "
            "provides a tamper-evident audit log of every structural "
            "change, satisfying the data-governance traceability "
            "requirement of Annex IV §2(b)."
        ),
    },
    {
        "framework": "EU AI Act",
        "ref": "Annex IV §3",
        "title": "Description of the monitoring, functioning and control",
        "citation": "Regulation (EU) 2024/1689, Annex IV, paragraph 3",
        "receipt_field": "wire.verdict + wire.violation_count + certify.axes",
        "evidence": (
            "The wire scan verdict (``wire.verdict``) and violation count "
            "(``wire.violation_count``) document the outcome of automated "
            "architectural monitoring.  The certify axes block "
            "(``certify.axes``) records the four structural control checks "
            "(documentation_complete, tests_present, tier_layout_present, "
            "no_upward_imports), satisfying Annex IV §3."
        ),
    },
    {
        "framework": "EU AI Act",
        "ref": "Annex IV §4",
        "title": "Description of the changes to the AI system and its performance",
        "citation": "Regulation (EU) 2024/1689, Annex IV, paragraph 4",
        "receipt_field": "lineage.parent_receipt_hash + lineage.chain_depth",
        "evidence": (
            "Each Receipt records ``lineage.parent_receipt_hash`` (SHA-256 "
            "of the immediately prior Receipt) and ``lineage.chain_depth`` "
            "(monotonically increasing integer).  Together they provide the "
            "change-description log required by Annex IV §4; the full "
            "diff is recoverable via Vanguard ``/v1/forge/lineage``."
        ),
    },
    {
        "framework": "EU AI Act",
        "ref": "Annex IV §5",
        "title": "Post-market monitoring plan",
        "citation": "Regulation (EU) 2024/1689, Annex IV, paragraph 5",
        "receipt_field": "signatures.sigstore + signatures.aaaa_nexus",
        "evidence": (
            "Sigstore Rekor entry (``signatures.sigstore.rekor_uuid``, "
            "``signatures.sigstore.log_index``) and AAAA-Nexus signature "
            "(``signatures.aaaa_nexus``) provide the post-market "
            "attestation chain required by Annex IV §5.  Each Receipt "
            "emission produces a new Rekor entry, enabling continuous "
            "monitoring of structural compliance."
        ),
    },
]

_SR_11_7_CLAIMS: list[dict[str, str]] = [
    {
        "framework": "SR 11-7",
        "ref": "§III.A",
        "title": "Model development and implementation",
        "citation": "Federal Reserve SR Letter 11-7 (2011), Section III.A",
        "receipt_field": "certify.score + certify.axes",
        "evidence": (
            "The certify score (``certify.score``) and per-axis flags "
            "(``certify.axes``) document that the model has been developed "
            "and implemented against the four Atomadic structural axes "
            "(documentation, tests, tier layout, import discipline), "
            "satisfying the development-documentation obligation of SR 11-7 "
            "§III.A."
        ),
    },
    {
        "framework": "SR 11-7",
        "ref": "§IV",
        "title": "Validation",
        "citation": "Federal Reserve SR Letter 11-7 (2011), Section IV",
        "receipt_field": "lean4_attestation + wire.verdict",
        "evidence": (
            "Machine-checked Lean4 proofs (``lean4_attestation``) provide "
            "formal validation of the system's mathematical invariants. "
            "The wire scan PASS verdict (``wire.verdict``) provides "
            "automated structural validation.  Together they satisfy the "
            "independent validation requirement of SR 11-7 §IV."
        ),
    },
    {
        "framework": "SR 11-7",
        "ref": "§IV.A",
        "title": "Evaluating conceptual soundness",
        "citation": "Federal Reserve SR Letter 11-7 (2011), Section IV.A",
        "receipt_field": "lean4_attestation.corpora[*].sorry_count",
        "evidence": (
            "Every Lean4 corpus cited in ``lean4_attestation.corpora`` "
            "MUST record ``sorry_count = 0`` (no admitted but unproven "
            "theorems).  This zero-sorry constraint is the machine-checked "
            "evidence of conceptual soundness required by SR 11-7 §IV.A."
        ),
    },
    {
        "framework": "SR 11-7",
        "ref": "§V.A",
        "title": "Ongoing monitoring",
        "citation": "Federal Reserve SR Letter 11-7 (2011), Section V.A",
        "receipt_field": "lineage.chain_depth + generated_at_utc",
        "evidence": (
            "The Receipt emission timestamp (``generated_at_utc``) and "
            "lineage chain depth (``lineage.chain_depth``) together "
            "constitute the ongoing monitoring record required by SR 11-7 "
            "§V.A.  Each ``forge auto`` run produces a new Receipt and "
            "increments the chain depth, creating a time-stamped audit trail."
        ),
    },
]

_FDA_PCCP_CLAIMS: list[dict[str, str]] = [
    {
        "framework": "FDA PCCP",
        "ref": "§II.A",
        "title": "Description of modifications",
        "citation": (
            "FDA Guidance: Predetermined Change Control Plan for "
            "Machine Learning-Enabled Medical Devices (Draft, 2023), "
            "Section II.A"
        ),
        "receipt_field": "lineage.parent_receipt_hash + lineage.chain_depth",
        "evidence": (
            "The lineage block (``lineage.parent_receipt_hash``, "
            "``lineage.chain_depth``) provides the modification log "
            "required under FDA PCCP §II.A.  Each Receipt captures the "
            "structural state at a point in time; the parent hash chain "
            "links successive modifications into an auditable sequence."
        ),
    },
    {
        "framework": "FDA PCCP",
        "ref": "§II.B",
        "title": "Methodology for implementing and validating modifications",
        "citation": (
            "FDA Guidance: Predetermined Change Control Plan for "
            "Machine Learning-Enabled Medical Devices (Draft, 2023), "
            "Section II.B"
        ),
        "receipt_field": "lean4_attestation + certify.axes",
        "evidence": (
            "The Lean4 attestation block documents the formal validation "
            "methodology (machine-checked proofs, 0 sorry).  The certify "
            "axes provide the structural validation checklist (tests_present, "
            "documentation_complete, tier_layout_present, no_upward_imports). "
            "Together they satisfy the methodology-documentation obligation "
            "of FDA PCCP §II.B."
        ),
    },
    {
        "framework": "FDA PCCP",
        "ref": "§II.C",
        "title": "Performance monitoring plan",
        "citation": (
            "FDA Guidance: Predetermined Change Control Plan for "
            "Machine Learning-Enabled Medical Devices (Draft, 2023), "
            "Section II.C"
        ),
        "receipt_field": "signatures.sigstore + generated_at_utc",
        "evidence": (
            "The Sigstore Rekor entry (``signatures.sigstore``) and "
            "AAAA-Nexus signature (``signatures.aaaa_nexus``) provide "
            "the timestamped, immutable performance-monitoring record "
            "required by FDA PCCP §II.C.  The ``generated_at_utc`` field "
            "pins the monitoring event to a specific UTC instant."
        ),
    },
]

_CMMC_AI_CLAIMS: list[dict[str, str]] = [
    {
        "framework": "CMMC-AI",
        "ref": "GOVERN 1.1",
        "title": "AI risk management policy",
        "citation": "NIST AI RMF 1.0 (2023), GOVERN 1.1",
        "receipt_field": "certify.axes + wire.verdict",
        "evidence": (
            "The certify axes and wire verdict demonstrate that an "
            "AI risk management policy (Atomadic UEP v20 Monadic "
            "Development Standard) is implemented and enforced via "
            "automated gate checks on every Receipt emission."
        ),
    },
    {
        "framework": "CMMC-AI",
        "ref": "MAP 1.5",
        "title": "Organizational risk tolerances",
        "citation": "NIST AI RMF 1.0 (2023), MAP 1.5",
        "receipt_field": "verdict + certify.score",
        "evidence": (
            "The Receipt verdict (PASS / FAIL / REFINE / QUARANTINE) "
            "and certify score (0..100) encode the organization's "
            "risk tolerance thresholds.  PASS requires wire PASS AND "
            "certify.score >= threshold (default 100.0), satisfying "
            "the risk-tolerance documentation obligation of MAP 1.5."
        ),
    },
    {
        "framework": "CMMC-AI",
        "ref": "MEASURE 2.5",
        "title": "AI system to be evaluated for trustworthiness characteristics",
        "citation": "NIST AI RMF 1.0 (2023), MEASURE 2.5",
        "receipt_field": "lean4_attestation + certify.axes",
        "evidence": (
            "Trustworthiness characteristics are evaluated via Lean4 "
            "machine-checked proofs (mathematical correctness) and the "
            "four certify axes (documentation, tests, tier layout, "
            "import discipline).  Results are recorded in the Receipt "
            "and versioned in the Vanguard lineage chain."
        ),
    },
    {
        "framework": "CMMC-AI",
        "ref": "MANAGE 1.3",
        "title": "Responses to identified AI risks are prioritized",
        "citation": "NIST AI RMF 1.0 (2023), MANAGE 1.3",
        "receipt_field": "wire.violation_count + wire.auto_fixable + certify.issues",
        "evidence": (
            "Wire violation count (``wire.violation_count``), auto-fixable "
            "count (``wire.auto_fixable``), and certify issue list "
            "(``certify.issues``) enumerate identified risks in priority "
            "order.  Auto-fixable items are addressed first by ``forge wire "
            "--apply``; remaining items are surfaced in the receipt for "
            "human review, satisfying MANAGE 1.3."
        ),
    },
]

_REGULATOR_QUESTIONS: list[dict[str, str]] = [
    {
        "id": "RQ-1",
        "question": "What is the AI system and what does it do?",
        "answer_fields": "project.name, project.language, scout.symbol_count, scout.tier_distribution",
        "framework_refs": "EU AI Act Annex IV §1; SR 11-7 §III.A",
    },
    {
        "id": "RQ-2",
        "question": "How was the system validated and what formal proofs exist?",
        "answer_fields": "lean4_attestation.corpora, lean4_attestation.total_theorems, certify.axes",
        "framework_refs": "EU AI Act Annex IV §2(a); SR 11-7 §IV, §IV.A; FDA PCCP §II.B",
    },
    {
        "id": "RQ-3",
        "question": "What structural controls are in place?",
        "answer_fields": "wire.verdict, wire.violation_count, certify.score, certify.axes",
        "framework_refs": "EU AI Act Annex IV §3; SR 11-7 §III.A; CMMC-AI GOVERN 1.1, MAP 1.5",
    },
    {
        "id": "RQ-4",
        "question": "How are changes tracked and what is the audit trail?",
        "answer_fields": "lineage.lineage_path, lineage.parent_receipt_hash, lineage.chain_depth",
        "framework_refs": "EU AI Act Annex IV §2(b), §4; SR 11-7 §V.A; FDA PCCP §II.A",
    },
    {
        "id": "RQ-5",
        "question": "Is this statement signed and independently attested?",
        "answer_fields": "signatures.sigstore, signatures.aaaa_nexus, signatures.local_sign",
        "framework_refs": "EU AI Act Annex IV §5; FDA PCCP §II.C; CMMC-AI MEASURE 2.5",
    },
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _signatures_status(receipt: dict[str, Any]) -> str:
    """Return 'SIGNED', 'PARTIAL', or 'UNSIGNED'."""
    sigs = receipt.get("signatures") or {}
    has_sigstore = bool((sigs.get("sigstore") or {}).get("rekor_uuid"))
    has_nexus = bool((sigs.get("aaaa_nexus") or {}).get("signature"))
    has_local = bool((sigs.get("local_sign") or {}).get("signature"))
    if has_sigstore and has_nexus:
        return "SIGNED"
    if has_sigstore or has_nexus or has_local:
        return "PARTIAL"
    return "UNSIGNED"


def _lineage_digest(receipt: dict[str, Any]) -> str | None:
    """Return sha256 of the canonical lineage block, or None."""
    lineage = receipt.get("lineage")
    if not lineage:
        return None
    canonical = json.dumps(lineage, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _receipt_summary(receipt: dict[str, Any]) -> dict[str, Any]:
    project = receipt.get("project") or {}
    certify = receipt.get("certify") or {}
    wire = receipt.get("wire") or {}
    scout = receipt.get("scout") or {}
    return {
        "schema_version": receipt.get("schema_version", ""),
        "generated_at_utc": receipt.get("generated_at_utc", ""),
        "forge_version": receipt.get("forge_version", ""),
        "verdict": receipt.get("verdict", "FAIL"),
        "project_name": project.get("name", ""),
        "project_language": project.get("language", "python"),
        "certify_score": float(certify.get("score", 0.0)),
        "wire_verdict": wire.get("verdict", "FAIL"),
        "wire_violation_count": int(wire.get("violation_count", 0)),
        "symbol_count": int(scout.get("symbol_count", 0)),
    }


def _attestation_block(receipt: dict[str, Any]) -> dict[str, Any]:
    lean4 = receipt.get("lean4_attestation") or {}
    corpora = lean4.get("corpora") or []
    return {
        "total_theorems": int(lean4.get("total_theorems", 0)),
        "total_sorry": sum(int(c.get("sorry_count", 0)) for c in corpora),
        "corpora_count": len(corpora),
        "summary": lean4.get("summary", "no attestation"),
        "corpora": [
            {
                "name": c.get("name", ""),
                "ref_sha": c.get("ref_sha", ""),
                "theorem_count": int(c.get("theorem_count", 0)),
                "sorry_count": int(c.get("sorry_count", 0)),
            }
            for c in corpora
        ],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_cs1(receipt: dict[str, Any]) -> dict[str, Any]:
    """Build a CS-1 dict from a ForgeReceiptV1.

    Raises ValueError if required Receipt fields are missing.
    Returns a JSON-serializable dict with schema_version
    ``atomadic-forge.cs1/v1``.
    """
    for field in _REQUIRED_RECEIPT_FIELDS:
        if field not in receipt:
            raise ValueError(f"Receipt missing required field: {field!r}")

    return {
        "schema_version": CS1_SCHEMA_VERSION,
        "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "receipt_schema_version": receipt.get("schema_version", ""),
        "receipt_generated_at_utc": receipt.get("generated_at_utc", ""),
        "project": dict(receipt.get("project") or {}),
        "receipt_summary": _receipt_summary(receipt),
        "attestation": _attestation_block(receipt),
        "compliance_claims": (
            _EU_AI_ACT_CLAIMS
            + _SR_11_7_CLAIMS
            + _FDA_PCCP_CLAIMS
            + _CMMC_AI_CLAIMS
        ),
        "regulator_questions": _REGULATOR_QUESTIONS,
        "lineage_chain_digest": _lineage_digest(receipt),
        "signatures_status": _signatures_status(receipt),
        "notes": list(receipt.get("notes") or []),
    }


def render_cs1_markdown(cs1: dict[str, Any]) -> str:
    """Render a CS-1 dict to a regulator-friendly Markdown string.

    Pure: no I/O, stdlib only.  The output is structured Markdown
    that regulators can read directly or convert to PDF via pandoc.
    """
    lines: list[str] = []
    a = lines.append

    rs = cs1.get("receipt_summary") or {}
    proj = cs1.get("project") or {}
    att = cs1.get("attestation") or {}
    sig_status = cs1.get("signatures_status", "UNSIGNED")
    lineage_digest = cs1.get("lineage_chain_digest")

    a("# Atomadic Forge Conformity Statement CS-1")
    a("")
    a(f"**Schema version:** `{cs1.get('schema_version', '')}`  ")
    a(f"**Generated:** {cs1.get('generated_at_utc', '')}  ")
    a(f"**Receipt schema:** `{cs1.get('receipt_schema_version', '')}`  ")
    a(f"**Receipt timestamp:** {cs1.get('receipt_generated_at_utc', '')}  ")
    a(f"**Signature status:** {sig_status}  ")
    a("")
    a("---")
    a("")

    # Project
    a("## Project")
    a("")
    a("| Field | Value |")
    a("|-------|-------|")
    a(f"| Name | `{rs.get('project_name', '')}` |")
    a(f"| Primary language | {rs.get('project_language', 'python')} |")
    if proj.get("languages"):
        langs = ", ".join(
            f"{k}: {v}" for k, v in sorted(proj["languages"].items())
        )
        a(f"| Languages | {langs} |")
    if proj.get("vcs"):
        vcs = proj["vcs"]
        branch = vcs.get("branch", "")
        sha = vcs.get("short_sha", "")
        dirty = " (dirty)" if vcs.get("dirty") else ""
        a(f"| VCS | {branch}@{sha}{dirty} |")
    a("")

    # Verdict summary
    a("## Verdict Summary")
    a("")
    verdict = rs.get("verdict", "FAIL")
    glyph = {"PASS": "✓", "FAIL": "✗", "REFINE": "↻", "QUARANTINE": "⏸"}.get(
        verdict, "?"
    )
    a(f"**{glyph} {verdict}**")
    a("")
    a("| Check | Result |")
    a("|-------|--------|")
    a(f"| Wire scan | {rs.get('wire_verdict', 'FAIL')} ({rs.get('wire_violation_count', 0)} violations) |")
    a(f"| Certify score | {rs.get('certify_score', 0.0):.1f} / 100 |")
    a(f"| Symbol count | {rs.get('symbol_count', 0)} |")
    a("")

    # Lean4 attestation
    a("## Lean4 Attestation")
    a("")
    if att.get("corpora_count", 0) == 0:
        a("_No Lean4 attestation attached to this Receipt._")
    else:
        a(f"**{att.get('total_theorems', 0)} theorems** across "
          f"**{att.get('corpora_count', 0)} corpus/corpora** — "
          f"**{att.get('total_sorry', 0)} sorry**")
        a("")
        a("| Corpus | Ref SHA | Theorems | Sorry |")
        a("|--------|---------|----------|-------|")
        for c in att.get("corpora") or []:
            sha = (c.get("ref_sha") or "")[:12]
            a(f"| {c.get('name', '')} | `{sha}` | "
              f"{c.get('theorem_count', 0)} | {c.get('sorry_count', 0)} |")
    a("")

    # Lineage
    a("## Vanguard Lineage Chain")
    a("")
    if lineage_digest:
        a(f"Lineage block SHA-256: `{lineage_digest}`")
    else:
        a("_No lineage block attached to this Receipt._")
    a("")

    # Regulator questions
    a("## Regulator Questions and Answers")
    a("")
    for rq in cs1.get("regulator_questions") or []:
        a(f"### {rq.get('id', '')} — {rq.get('question', '')}")
        a("")
        a(f"**Receipt fields:** `{rq.get('answer_fields', '')}`  ")
        a(f"**Framework refs:** {rq.get('framework_refs', '')}  ")
        a("")

    # Compliance claims by framework
    claims = cs1.get("compliance_claims") or []
    frameworks_seen: list[str] = []
    frameworks_order: list[str] = []
    for c in claims:
        fw = c.get("framework", "")
        if fw not in frameworks_seen:
            frameworks_seen.append(fw)
            frameworks_order.append(fw)

    a("## Compliance Claims")
    a("")
    for fw in frameworks_order:
        a(f"### {fw}")
        a("")
        fw_claims = [c for c in claims if c.get("framework") == fw]
        for claim in fw_claims:
            a(f"#### {claim.get('ref', '')} — {claim.get('title', '')}")
            a("")
            a(f"**Citation:** {claim.get('citation', '')}  ")
            a(f"**Receipt field(s):** `{claim.get('receipt_field', '')}`  ")
            a("")
            a(claim.get("evidence", ""))
            a("")

    # Mapping doc references
    a("## Mapping Document References")
    a("")
    a("| Document | Path |")
    a("|----------|------|")
    a("| EU AI Act Annex IV Mapping | `docs/compliance/EU_AI_ACT_ANNEX_IV.md` |")
    a("| SR 11-7 Mapping | `docs/compliance/SR_11-7_MAPPING.md` |")
    a("| FDA PCCP Mapping | `docs/compliance/FDA_PCCP_MAPPING.md` |")
    a("| CMMC-AI Mapping | `docs/compliance/CMMC_AI_MAPPING.md` |")
    a("")

    # Footer
    a("---")
    a("")
    a(f"_Generated by Atomadic Forge CS-1 renderer — "
      f"`{cs1.get('schema_version', '')}`_")
    a("")

    return "\n".join(lines)
