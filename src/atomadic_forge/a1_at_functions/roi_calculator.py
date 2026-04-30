"""Tier a1 — pure ROI calculator for ForgeReceiptV1.

Golden Path Lane F W3.

Given a ForgeReceiptV1 dict, applies the CISQ cost model to estimate:
  * structural defects identified by Forge (wire violations + certify axes)
  * avoided remediation cost (finding at architecture layer vs production)
  * annual technical-debt carry cost eliminated
  * CIO-facing ROI summary in USD

All numbers use conservative CISQ 2022 lower-bound figures so enterprise
claims remain defensible. See ``a0_qk_constants/roi_constants.py`` for
source citations.
"""
from __future__ import annotations

from atomadic_forge.a0_qk_constants.roi_constants import (
    ANNUAL_CARRY_COST_PER_KLOC_USD,
    CISQ_CITATION,
    CISQ_REFERENCE_YEAR,
    COST_PER_CERTIFY_AXIS_FAIL_USD,
    COST_PER_DEFECT_PRODUCTION_USD,
    COST_PER_STRUCTURAL_DEFECT_USD,
    DEFAULT_TEAM_HOURLY_RATE_USD,
    HOURS_PER_CERTIFY_AXIS_FIX,
    HOURS_PER_STRUCTURAL_DEFECT_FIX,
    NIST_CITATION,
    SCORE_THRESHOLD_GOOD,
    SCORE_THRESHOLD_PASS,
    SYMBOLS_PER_KLOC,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _wire(r: dict) -> dict:
    return r.get("wire") or {}


def _certify(r: dict) -> dict:
    return r.get("certify") or {}


def _scout(r: dict) -> dict:
    return r.get("scout") or {}


def _axes_fail_count(r: dict) -> int:
    axes = _certify(r).get("axes") or {}
    return sum(1 for v in axes.values() if not v)


def _symbol_count(r: dict) -> int:
    return int(_scout(r).get("symbol_count") or 0)


def _kloc_estimate(r: dict) -> float:
    symbols = _symbol_count(r)
    if symbols <= 0:
        return 0.0
    return symbols / SYMBOLS_PER_KLOC


def _score(r: dict) -> float:
    return float(_certify(r).get("score", 0.0))


def _wire_violations(r: dict) -> int:
    return int(_wire(r).get("violation_count") or 0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def calculate_roi(
    receipt: dict,
    team_hourly_rate: float = DEFAULT_TEAM_HOURLY_RATE_USD,
) -> dict:
    """Calculate TD-principal reduction estimate from a ForgeReceiptV1.

    Returns a dict with all figures in USD, ready to embed in a Receipt
    or render as a Markdown report::

        {
            "wire_violations": int,
            "certify_score": float,
            "certify_axes_failing": int,
            "estimated_structural_defects": float,
            "avoided_remediation_cost_usd": float,   # catch-at-arch vs catch-at-prod
            "annual_carry_reduction_usd": float,
            "fix_effort_hours": float,
            "fix_effort_cost_usd": float,
            "roi_multiplier": float,                 # avoided_cost / fix_cost
            "grade": str,                            # PASS / GOOD / FAIR / POOR
            "cisq_reference_year": str,
            "team_hourly_rate_usd": float,
        }

    Never raises. Returns zeros for an empty receipt.
    """
    if not receipt:
        return _zero_roi()

    violations = _wire_violations(receipt)
    axes_failing = _axes_fail_count(receipt)
    kloc = _kloc_estimate(receipt)
    score = _score(receipt)

    # Total structural defects: each wire violation is 1 defect;
    # each failing certify axis contributes 0.5 (weaker signal).
    estimated_defects = float(violations) + axes_failing * 0.5

    # Remediation cost at architecture layer (cheap — caught now).
    review_cost = violations * COST_PER_STRUCTURAL_DEFECT_USD
    review_cost += axes_failing * COST_PER_CERTIFY_AXIS_FAIL_USD

    # Avoided cost = what it would cost if these reached production.
    avoided_cost = violations * COST_PER_DEFECT_PRODUCTION_USD
    avoided_cost += axes_failing * COST_PER_CERTIFY_AXIS_FAIL_USD * 3.0

    # Annual carry cost eliminated by resolving all identified issues.
    # We credit the full KLOC carry for projects at PASS; partial for others.
    if score >= SCORE_THRESHOLD_PASS:
        carry_credit = 0.0  # already clean
    else:
        debt_fraction = max(0.0, (SCORE_THRESHOLD_PASS - score) / SCORE_THRESHOLD_PASS)
        carry_credit = kloc * ANNUAL_CARRY_COST_PER_KLOC_USD * debt_fraction

    # Fix effort — how long it would take to address everything Forge found.
    fix_hours = violations * HOURS_PER_STRUCTURAL_DEFECT_FIX
    fix_hours += axes_failing * HOURS_PER_CERTIFY_AXIS_FIX
    fix_cost = fix_hours * team_hourly_rate

    # ROI multiplier: how many dollars of avoided future cost per dollar of fix cost.
    total_avoided = avoided_cost + carry_credit
    roi_mult = (total_avoided / fix_cost) if fix_cost > 0.0 else 0.0

    grade = _grade(score)

    return {
        "wire_violations": violations,
        "certify_score": round(score, 2),
        "certify_axes_failing": axes_failing,
        "estimated_structural_defects": round(estimated_defects, 1),
        "avoided_remediation_cost_usd": round(avoided_cost, 2),
        "annual_carry_reduction_usd": round(carry_credit, 2),
        "fix_effort_hours": round(fix_hours, 1),
        "fix_effort_cost_usd": round(fix_cost, 2),
        "roi_multiplier": round(roi_mult, 1),
        "grade": grade,
        "cisq_reference_year": CISQ_REFERENCE_YEAR,
        "team_hourly_rate_usd": team_hourly_rate,
    }


def _zero_roi() -> dict:
    return {
        "wire_violations": 0,
        "certify_score": 0.0,
        "certify_axes_failing": 0,
        "estimated_structural_defects": 0.0,
        "avoided_remediation_cost_usd": 0.0,
        "annual_carry_reduction_usd": 0.0,
        "fix_effort_hours": 0.0,
        "fix_effort_cost_usd": 0.0,
        "roi_multiplier": 0.0,
        "grade": "UNKNOWN",
        "cisq_reference_year": CISQ_REFERENCE_YEAR,
        "team_hourly_rate_usd": DEFAULT_TEAM_HOURLY_RATE_USD,
    }


def _grade(score: float) -> str:
    if score >= SCORE_THRESHOLD_PASS:
        return "PASS"
    if score >= SCORE_THRESHOLD_GOOD:
        return "GOOD"
    if score >= 60.0:
        return "FAIR"
    return "POOR"


def render_roi_markdown(roi: dict, project_name: str = "Project") -> str:
    """Render an ROI dict as a CIO-ready Markdown report.

    The output is a concise Markdown document suitable for:
      * direct email attachment (rendered by most email clients)
      * pasting into Confluence / Notion
      * converting to PDF via ``pandoc`` or ``wkhtmltopdf``
    """
    violations = roi["wire_violations"]
    axes_fail = roi["certify_axes_failing"]
    defects = roi["estimated_structural_defects"]
    avoided = roi["avoided_remediation_cost_usd"]
    carry = roi["annual_carry_reduction_usd"]
    fix_h = roi["fix_effort_hours"]
    fix_cost = roi["fix_effort_cost_usd"]
    mult = roi["roi_multiplier"]
    grade = roi["grade"]
    score = roi["certify_score"]
    rate = roi["team_hourly_rate_usd"]
    year = roi["cisq_reference_year"]

    grade_icon = {"PASS": "✓", "GOOD": "~", "FAIR": "!", "POOR": "✗"}.get(grade, "?")

    lines = [
        f"# Forge ROI Report — {project_name}",
        "",
        f"**Conformity grade: {grade_icon} {grade}** | Certify score: {score:.0f}/100",
        "",
        "## Findings",
        "",
        f"| Metric | Count |",
        f"|---|---|",
        f"| Wire violations (structural defects) | {violations} |",
        f"| Certify axes failing | {axes_fail} |",
        f"| Estimated total structural defects | {defects:.1f} |",
        "",
        "## Financial impact (CISQ {year} cost model)".format(year=year),
        "",
        f"| Item | USD |",
        f"|---|---|",
        f"| Avoided production-defect cost | ${avoided:,.0f} |",
        f"| Annual technical-debt carry eliminated | ${carry:,.0f} |",
        f"| Fix effort ({fix_h:.0f} h × ${rate:,.0f}/h) | ${fix_cost:,.0f} |",
        f"| **ROI multiplier** | **{mult:.1f}×** |",
        "",
    ]
    if mult >= 1.0:
        lines += [
            f"Forge identified **{defects:.1f} structural defects**. "
            f"Fixing them now costs an estimated **${fix_cost:,.0f}** "
            f"and avoids **${avoided + carry:,.0f}** in future remediation "
            f"and annual carry — a **{mult:.1f}× return on investment**.",
            "",
        ]
    else:
        lines += [
            "No actionable defects detected. This project is already at "
            "or near structural quality floor.",
            "",
        ]
    lines += [
        "## Methodology",
        "",
        "Cost-per-defect figures are CISQ 2022 lower-bound (conservative):",
        "",
        f"- Structural defect caught at architecture layer: ${COST_PER_STRUCTURAL_DEFECT_USD:,.0f}",
        f"- Same defect reaching production: ${COST_PER_DEFECT_PRODUCTION_USD:,.0f}",
        f"- Annual carry per KLOC of technical debt: ${ANNUAL_CARRY_COST_PER_KLOC_USD:,.0f}",
        "",
        "**References**",
        "",
        f"1. {CISQ_CITATION}",
        f"2. {NIST_CITATION}",
        "",
        "_Generated by Atomadic Forge. Figures are estimates based on "
        "industry-average defect costs; actual costs may vary._",
    ]
    return "\n".join(lines) + "\n"
