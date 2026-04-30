"""Tier a0 — CISQ cost-model constants for ROI calculation.

Golden Path Lane F W3.

Data sources:
  * CISQ "Cost of Poor Software Quality in the US" (2022 edition)
    — $2.41 trillion total cost of poor software quality
    — $1.52 trillion in accumulated technical debt
    — Average cost per defect: $1,480 (detection) to $14,102 (production)
  * IBM Systems Sciences Institute: defect cost multiplier 100× from
    design to production
  * NIST: "The Economic Impacts of Inadequate Infrastructure for
    Software Testing" (2002) — $59.5B/yr avoidable with better tooling
  * McKinsey Digital: 20-40% of technology spend on managing technical debt

These constants are intentionally conservative (use lower-bound estimates)
so Forge ROI claims remain defensible in enterprise sales contexts.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# CISQ 2022 reference figures
# ---------------------------------------------------------------------------

CISQ_TOTAL_COST_USD: float = 2_410_000_000_000.0
"""$2.41 trillion — total annual cost of poor software quality in the US (2022)."""

CISQ_TECH_DEBT_USD: float = 1_520_000_000_000.0
"""$1.52 trillion — accumulated technical debt burden (CISQ 2022)."""

CISQ_REFERENCE_YEAR: str = "2022"

# ---------------------------------------------------------------------------
# Per-defect cost model (conservative / IBM lower-bound)
# ---------------------------------------------------------------------------

COST_PER_STRUCTURAL_DEFECT_USD: float = 1_480.0
"""Cost to detect and fix one structural defect at the code-review stage ($1,480).

Source: CISQ 2022 lower-bound detection cost. Use this for wire violations
found by Forge (caught at the architecture layer, not production).
"""

COST_PER_DEFECT_PRODUCTION_USD: float = 14_102.0
"""Cost of a defect that reaches production ($14,102).

Use this as the *avoided* cost when Forge catches a violation pre-production.
"""

COST_PER_CERTIFY_AXIS_FAIL_USD: float = 2_200.0
"""Cost estimate per certify-axis failure (documentation, test coverage, etc.).

Conservative mid-point between review cost and rework cost.
"""

# ---------------------------------------------------------------------------
# Hourly / per-symbol baselines
# ---------------------------------------------------------------------------

DEFAULT_TEAM_HOURLY_RATE_USD: float = 150.0
"""Default fully-loaded engineering hourly rate used when no override provided."""

HOURS_PER_STRUCTURAL_DEFECT_FIX: float = 4.0
"""Average hours to fix one structural defect (architecture-layer violation)."""

HOURS_PER_CERTIFY_AXIS_FIX: float = 8.0
"""Average hours to address one failing certify axis (e.g. add test suite)."""

ANNUAL_CARRY_COST_PER_KLOC_USD: float = 14_500.0
"""Annual maintenance burden per KLOC of technical debt (McKinsey / CISQ composite)."""

SYMBOLS_PER_KLOC: float = 50.0
"""Empirical Python: ~50 public symbols per 1,000 lines for well-factored code."""

# ---------------------------------------------------------------------------
# Forge scoring thresholds for ROI bands
# ---------------------------------------------------------------------------

SCORE_THRESHOLD_PASS: float = 100.0
SCORE_THRESHOLD_GOOD: float = 80.0
SCORE_THRESHOLD_FAIR: float = 60.0
SCORE_THRESHOLD_POOR: float = 40.0

# ---------------------------------------------------------------------------
# Report template strings
# ---------------------------------------------------------------------------

CISQ_CITATION: str = (
    "CISQ, \"The Cost of Poor Software Quality in the U.S.: A 2022 Report,\" "
    "Consortium for Information & Software Quality, 2022."
)

NIST_CITATION: str = (
    "NIST Planning Report 02-3, \"The Economic Impacts of Inadequate "
    "Infrastructure for Software Testing,\" May 2002."
)
