"""Tier a1 — pure compliance-mapping checker for ForgeReceiptV1.

Golden Path Lane F W2.

Evaluates a ForgeReceiptV1 dict against EU AI Act Annex IV, SR 11-7,
FDA PCCP, and CMMC-AI and returns a ``compliance_mappings`` dict
suitable for embedding in the Receipt or rendering in the CS-1
Conformity Statement.

Status values per framework:
  PASS          — all required checks pass
  PARTIAL       — at least one required check fails, no critical failure
  FAIL          — a critical check fails (wire FAIL or certify below floor)
  NOT_ASSESSED  — essential Receipt fields missing; cannot evaluate
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

COMPLIANCE_FRAMEWORK_KEYS: tuple[str, ...] = (
    "eu_ai_act",
    "sr_11_7",
    "fda_pccp",
    "cmmc_ai",
)

ComplianceStatus = str  # "PASS" | "PARTIAL" | "FAIL" | "NOT_ASSESSED"

_VALID_STATUSES: frozenset[str] = frozenset(
    {"PASS", "PARTIAL", "FAIL", "NOT_ASSESSED"}
)

# ---------------------------------------------------------------------------
# Internal accessors
# ---------------------------------------------------------------------------


def _wire_pass(r: dict) -> bool:
    return (r.get("wire") or {}).get("verdict") == "PASS"


def _score(r: dict) -> float:
    return float((r.get("certify") or {}).get("score", 0.0))


def _axes(r: dict) -> dict:
    return (r.get("certify") or {}).get("axes") or {}


def _lean4(r: dict) -> dict:
    return r.get("lean4_attestation") or {}


def _lineage(r: dict) -> dict:
    return r.get("lineage") or {}


def _project(r: dict) -> dict:
    return r.get("project") or {}


def _has_lean4_clean(r: dict) -> bool:
    """True iff at least one corpus present and all have sorry_count == 0."""
    corpora = _lean4(r).get("corpora") or []
    return bool(corpora) and all(
        int(c.get("sorry_count", 1)) == 0 for c in corpora
    )


def _has_any_signature(r: dict) -> bool:
    sigs = r.get("signatures") or {}
    return bool(
        (sigs.get("sigstore") or {}).get("rekor_uuid")
        or (sigs.get("aaaa_nexus") or {}).get("signature")
        or (sigs.get("local_sign") or {}).get("signature")
    )


def _chain_depth(r: dict) -> int:
    return int(_lineage(r).get("chain_depth") or 0)


# ---------------------------------------------------------------------------
# Per-framework checkers
# ---------------------------------------------------------------------------


def _check_eu_ai_act(r: dict) -> ComplianceStatus:
    """EU AI Act Annex IV, Regulation (EU) 2024/1689.

    Critical (FAIL / NOT_ASSESSED):
      §1  project.name + project.language must be present
      §2  wire scan must PASS (structural documentation of architecture)
      §2  certify.score >= 60

    Required (PARTIAL if any false):
      §3  Lean4 corpora present with all sorry_count == 0
      §4  lineage.chain_depth >= 1 (monitoring record exists)
      §5  certify.axes.documentation_complete
    """
    proj = _project(r)
    if not proj.get("name") or not proj.get("language"):
        return "NOT_ASSESSED"
    if not _wire_pass(r) or _score(r) < 60.0:
        return "FAIL"
    required = [
        _has_lean4_clean(r),
        _chain_depth(r) >= 1,
        _axes(r).get("documentation_complete", False),
    ]
    return "PASS" if all(required) else "PARTIAL"


def _check_sr_11_7(r: dict) -> ComplianceStatus:
    """Federal Reserve SR Letter 11-7 (2011) + FAQ (2021).

    Critical:
      §III.A  tier_layout_present (governance framework exists)
      §IV     certify.score >= 70 (development-process standards)
      §IV.A   wire scan PASS (conceptual soundness)

    Required (PARTIAL if any false):
      §IV.A   Lean4 attestation (formal soundness evidence)
      §IV.B   tests_present (outcomes analysis capability)
      §V.A    lineage.chain_depth >= 2 (ongoing-monitoring track record)
    """
    if not _axes(r).get("tier_layout_present", False):
        return "NOT_ASSESSED"
    if _score(r) < 70.0 or not _wire_pass(r):
        return "FAIL"
    required = [
        _has_lean4_clean(r),
        _axes(r).get("tests_present", False),
        _chain_depth(r) >= 2,
    ]
    return "PASS" if all(required) else "PARTIAL"


def _check_fda_pccp(r: dict) -> ComplianceStatus:
    """FDA Predetermined Change Control Plan (Draft 2023).

    Critical:
      §II.A  schema_version must be present (version-controlled artifact)
      §II.A  lineage.chain_depth >= 1 (algorithm change protocol in place)

    Required (PARTIAL if any false):
      §II.B  certify.score >= 80 (impact-assessment standard met)
      §II.C  tests_present (re-validation methodology exists)
    """
    if not r.get("schema_version"):
        return "NOT_ASSESSED"
    if _chain_depth(r) < 1:
        return "FAIL"
    required = [
        _score(r) >= 80.0,
        _axes(r).get("tests_present", False),
    ]
    return "PASS" if all(required) else "PARTIAL"


def _check_cmmc_ai(r: dict) -> ComplianceStatus:
    """CMMC 2.0 + NIST AI RMF 1.0 (2023).

    Critical:
      GOVERN 1.1  wire scan PASS (no architecture policy violations)
      GOVERN 1.2  tier_layout_present (systematic governance structure)
      (floor)     certify.score >= 60

    Required (PARTIAL if any false):
      MAP 1.1     Lean4 corpora with sorry_count == 0
      MEASURE 2.5 certify.score >= 80
      MANAGE 1.3  at least one signature present
    """
    if not _wire_pass(r) or not _axes(r).get("tier_layout_present", False):
        return "FAIL"
    if _score(r) < 60.0:
        return "FAIL"
    required = [
        _has_lean4_clean(r),
        _score(r) >= 80.0,
        _has_any_signature(r),
    ]
    return "PASS" if all(required) else "PARTIAL"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_CHECKERS: dict[str, object] = {
    "eu_ai_act": _check_eu_ai_act,
    "sr_11_7":   _check_sr_11_7,
    "fda_pccp":  _check_fda_pccp,
    "cmmc_ai":   _check_cmmc_ai,
}


def check_compliance(receipt: dict) -> dict[str, str]:
    """Evaluate a ForgeReceiptV1 dict against all 4 compliance frameworks.

    Returns a ``compliance_mappings`` dict ready to embed in the Receipt
    or pass to ``cs1_renderer.render_cs1``::

        {
            "eu_ai_act":  "PASS" | "PARTIAL" | "FAIL" | "NOT_ASSESSED",
            "sr_11_7":    "PASS" | "PARTIAL" | "FAIL" | "NOT_ASSESSED",
            "fda_pccp":   "PASS" | "PARTIAL" | "FAIL" | "NOT_ASSESSED",
            "cmmc_ai":    "PASS" | "PARTIAL" | "FAIL" | "NOT_ASSESSED",
        }

    Never raises. Returns all ``"NOT_ASSESSED"`` for an empty or None receipt.
    """
    if not receipt:
        return {k: "NOT_ASSESSED" for k in COMPLIANCE_FRAMEWORK_KEYS}
    return {k: _CHECKERS[k](receipt) for k in COMPLIANCE_FRAMEWORK_KEYS}  # type: ignore[operator]


def check_compliance_framework(receipt: dict, framework: str) -> str:
    """Evaluate a single framework by key.

    Returns ``"NOT_ASSESSED"`` for unknown framework keys.
    """
    checker = _CHECKERS.get(framework)
    if checker is None:
        return "NOT_ASSESSED"
    return checker(receipt)  # type: ignore[operator]
