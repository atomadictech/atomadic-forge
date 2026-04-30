"""Tier verification -- Lane F W3 ROI calculator."""
from __future__ import annotations
import json
import pytest
from atomadic_forge.a0_qk_constants.roi_constants import (
    CISQ_REFERENCE_YEAR,
    COST_PER_STRUCTURAL_DEFECT_USD,
    DEFAULT_TEAM_HOURLY_RATE_USD,
)
from atomadic_forge.a1_at_functions.roi_calculator import (
    calculate_roi,
    render_roi_markdown,
    _grade,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _r(**ov) -> dict:
    base = {
        "schema_version": "atomadic-forge.receipt/v1",
        "wire": {"verdict": "PASS", "violation_count": 0, "auto_fixable": 0},
        "certify": {
            "score": 100.0,
            "axes": {
                "documentation_complete": True,
                "tests_present": True,
                "tier_layout_present": True,
                "no_upward_imports": True,
            },
            "issues": [],
        },
        "scout": {"symbol_count": 200, "tier_distribution": {}, "effect_distribution": {}},
    }
    base.update(ov)
    return base


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_calculate_roi_returns_expected_keys():
    keys = {
        "wire_violations", "certify_score", "certify_axes_failing",
        "estimated_structural_defects", "avoided_remediation_cost_usd",
        "annual_carry_reduction_usd", "fix_effort_hours", "fix_effort_cost_usd",
        "roi_multiplier", "grade", "cisq_reference_year", "team_hourly_rate_usd",
    }
    assert set(calculate_roi(_r()).keys()) == keys


def test_cisq_reference_year_matches_constant():
    roi = calculate_roi(_r())
    assert roi["cisq_reference_year"] == CISQ_REFERENCE_YEAR


def test_default_rate_matches_constant():
    roi = calculate_roi(_r())
    assert roi["team_hourly_rate_usd"] == DEFAULT_TEAM_HOURLY_RATE_USD


# ---------------------------------------------------------------------------
# Clean PASS receipt
# ---------------------------------------------------------------------------

def test_pass_receipt_zero_violations():
    roi = calculate_roi(_r())
    assert roi["wire_violations"] == 0


def test_pass_receipt_score_100():
    roi = calculate_roi(_r())
    assert roi["certify_score"] == 100.0


def test_pass_receipt_grade_pass():
    roi = calculate_roi(_r())
    assert roi["grade"] == "PASS"


def test_pass_receipt_zero_defects():
    roi = calculate_roi(_r())
    assert roi["estimated_structural_defects"] == 0.0


def test_pass_receipt_zero_carry_reduction():
    roi = calculate_roi(_r())
    assert roi["annual_carry_reduction_usd"] == 0.0


def test_pass_receipt_zero_fix_hours():
    roi = calculate_roi(_r())
    assert roi["fix_effort_hours"] == 0.0


# ---------------------------------------------------------------------------
# Wire violations
# ---------------------------------------------------------------------------

def test_wire_violations_count_propagates():
    r = _r(wire={"verdict": "FAIL", "violation_count": 5, "auto_fixable": 2})
    roi = calculate_roi(r)
    assert roi["wire_violations"] == 5


def test_wire_violations_avoided_cost_positive():
    r = _r(wire={"verdict": "FAIL", "violation_count": 3, "auto_fixable": 0})
    roi = calculate_roi(r)
    assert roi["avoided_remediation_cost_usd"] > 0.0


def test_wire_violations_fix_hours_positive():
    r = _r(wire={"verdict": "FAIL", "violation_count": 2, "auto_fixable": 0})
    roi = calculate_roi(r)
    assert roi["fix_effort_hours"] > 0.0


def test_single_wire_violation_avoided_cost():
    r = _r(wire={"verdict": "FAIL", "violation_count": 1, "auto_fixable": 0})
    roi = calculate_roi(r)
    # Avoided = 1 defect × production cost
    from atomadic_forge.a0_qk_constants.roi_constants import COST_PER_DEFECT_PRODUCTION_USD
    assert roi["avoided_remediation_cost_usd"] == pytest.approx(COST_PER_DEFECT_PRODUCTION_USD, rel=1e-3)


# ---------------------------------------------------------------------------
# Certify axes failures
# ---------------------------------------------------------------------------

def test_certify_axes_failing_count():
    r = _r(certify={
        "score": 75.0,
        "axes": {"documentation_complete": False, "tests_present": False,
                 "tier_layout_present": True, "no_upward_imports": True},
        "issues": [],
    })
    roi = calculate_roi(r)
    assert roi["certify_axes_failing"] == 2


def test_axes_failures_contribute_half_defect_each():
    r = _r(certify={
        "score": 75.0,
        "axes": {"documentation_complete": False, "tests_present": True,
                 "tier_layout_present": True, "no_upward_imports": True},
        "issues": [],
    })
    roi = calculate_roi(r)
    assert roi["estimated_structural_defects"] == pytest.approx(0.5, rel=1e-3)


# ---------------------------------------------------------------------------
# Grade thresholds
# ---------------------------------------------------------------------------

def test_grade_pass():
    assert _grade(100.0) == "PASS"


def test_grade_good():
    assert _grade(85.0) == "GOOD"


def test_grade_fair():
    assert _grade(65.0) == "FAIR"


def test_grade_poor():
    assert _grade(30.0) == "POOR"


# ---------------------------------------------------------------------------
# ROI multiplier
# ---------------------------------------------------------------------------

def test_roi_multiplier_positive_when_violations():
    r = _r(wire={"verdict": "FAIL", "violation_count": 5, "auto_fixable": 0})
    roi = calculate_roi(r)
    assert roi["roi_multiplier"] > 0.0


def test_roi_multiplier_zero_for_clean():
    roi = calculate_roi(_r())
    assert roi["roi_multiplier"] == 0.0


# ---------------------------------------------------------------------------
# Custom hourly rate
# ---------------------------------------------------------------------------

def test_custom_hourly_rate_reflected():
    r = _r(wire={"verdict": "FAIL", "violation_count": 2, "auto_fixable": 0})
    roi = calculate_roi(r, team_hourly_rate=200.0)
    assert roi["team_hourly_rate_usd"] == 200.0


def test_custom_rate_affects_fix_cost():
    r = _r(wire={"verdict": "FAIL", "violation_count": 2, "auto_fixable": 0})
    roi_low = calculate_roi(r, team_hourly_rate=100.0)
    roi_high = calculate_roi(r, team_hourly_rate=300.0)
    assert roi_high["fix_effort_cost_usd"] > roi_low["fix_effort_cost_usd"]


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

def test_render_roi_markdown_returns_string():
    assert isinstance(render_roi_markdown(calculate_roi(_r())), str)


def test_render_roi_markdown_contains_project_name():
    md = render_roi_markdown(calculate_roi(_r()), project_name="my-app")
    assert "my-app" in md


def test_render_roi_markdown_contains_cisq_citation():
    md = render_roi_markdown(calculate_roi(_r()))
    assert "CISQ" in md


def test_render_roi_markdown_json_roundtrip():
    roi = calculate_roi(_r(wire={"verdict": "FAIL", "violation_count": 3, "auto_fixable": 0}))
    assert json.loads(json.dumps(roi)) == roi


# ---------------------------------------------------------------------------
# Empty / None receipt
# ---------------------------------------------------------------------------

def test_empty_receipt_returns_zeros():
    roi = calculate_roi({})
    assert roi["wire_violations"] == 0
    assert roi["avoided_remediation_cost_usd"] == 0.0


def test_none_receipt_returns_zeros():
    roi = calculate_roi(None)
    assert roi["estimated_structural_defects"] == 0.0
