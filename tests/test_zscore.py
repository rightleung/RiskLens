"""
Test suite for zscore module — breakdown and edge cases.

Run with: pytest tests/test_zscore.py -v
"""

import math

from zscore import (
    calculate_z_score,
    build_z_score_breakdown,
    map_z_score_to_zone,
    map_z_score_to_implied_rating,
)

# ── Zone / Rating boundaries ──────────────────────────────────────────────────

def test_map_z_score_to_zone_boundaries():
    assert map_z_score_to_zone(2.99) == "Safe (S)"
    assert map_z_score_to_zone(2.5) == "Grey (G)"
    assert map_z_score_to_zone(1.81) == "Grey (G)"
    assert map_z_score_to_zone(1.80) == "Distress (D)"


def test_map_z_score_to_implied_rating_boundaries():
    assert map_z_score_to_implied_rating(4.5) == "AAA"
    assert map_z_score_to_implied_rating(3.5) == "AA"
    assert map_z_score_to_implied_rating(2.99) == "A"
    assert map_z_score_to_implied_rating(2.5) == "BBB"
    assert map_z_score_to_implied_rating(2.49) == "BB"
    assert map_z_score_to_implied_rating(1.2) == "B"
    assert map_z_score_to_implied_rating(0.5) == "CCC"
    assert map_z_score_to_implied_rating(0.49) == "D"


# ── calculate_z_score ────────────────────────────────────────────────────────

def test_calculate_z_score_expected_value():
    result = calculate_z_score(
        total_assets=100.0, total_liabilities=40.0, working_capital=10.0,
        retained_earnings=20.0, ebit=15.0, sales=80.0, market_cap=50.0,
    )
    # Manually: A=0.1, B=0.2, C=0.15, D=50/40=1.25, E=0.8
    # 1.2*0.1 + 1.4*0.2 + 3.3*0.15 + 0.6*1.25 + 1.0*0.8 = 0.12+0.28+0.495+0.75+0.8 = 2.445
    assert result.z_score is not None
    assert math.isclose(result.z_score, 2.445, rel_tol=1e-6)
    assert result.zone == "Grey (G)"
    assert result.implied_rating == "BB"


def test_calculate_z_score_missing_total_assets():
    result = calculate_z_score(
        total_assets=None, total_liabilities=40.0, working_capital=10.0,
        retained_earnings=20.0, ebit=15.0, sales=80.0, market_cap=50.0,
    )
    assert result.z_score is None
    assert result.zone == "N/A"


def test_calculate_z_score_missing_working_capital():
    result = calculate_z_score(
        total_assets=100.0, total_liabilities=40.0, working_capital=None,
        retained_earnings=20.0, ebit=15.0, sales=80.0, market_cap=50.0,
    )
    assert result.z_score is None
    assert result.zone == "N/A"


def test_working_capital_zero_is_valid():
    result = calculate_z_score(
        total_assets=100.0, total_liabilities=40.0, working_capital=0.0,
        retained_earnings=20.0, ebit=15.0, sales=80.0, market_cap=50.0,
    )
    assert result.z_score is not None
    assert result.z_score > 0


def test_calculate_z_score_invalid_assets():
    result = calculate_z_score(
        total_assets=0.0, total_liabilities=40.0, working_capital=10.0,
        retained_earnings=20.0, ebit=15.0, sales=80.0, market_cap=50.0,
    )
    assert result.z_score is None


def test_retained_earnings_none_treated_as_zero():
    """retained_earnings=None → term B = 0, score still computes."""
    result = calculate_z_score(
        total_assets=100.0, total_liabilities=40.0, working_capital=10.0,
        retained_earnings=None, ebit=15.0, sales=80.0, market_cap=50.0,
    )
    assert result.z_score is not None
    # Without RE term: 0.12 + 0 + 0.495 + 0.75 + 0.8 = 2.165
    assert math.isclose(result.z_score, 2.165, rel_tol=1e-6)


def test_market_cap_none_treated_as_zero():
    """market_cap=None → term D = 0, score still computes."""
    result = calculate_z_score(
        total_assets=100.0, total_liabilities=40.0, working_capital=10.0,
        retained_earnings=20.0, ebit=15.0, sales=80.0, market_cap=None,
    )
    assert result.z_score is not None
    # Without MVE term: 0.12 + 0.28 + 0.495 + 0 + 0.8 = 1.695
    assert math.isclose(result.z_score, 1.695, rel_tol=1e-6)


def test_total_liabilities_zero_mve_term_zero():
    """total_liabilities=0 → D term = 0 (division avoided)."""
    result = calculate_z_score(
        total_assets=100.0, total_liabilities=0.0, working_capital=10.0,
        retained_earnings=20.0, ebit=15.0, sales=80.0, market_cap=50.0,
    )
    assert result.z_score is not None
    # D = 0, so: 0.12+0.28+0.495+0+0.8 = 1.695
    assert math.isclose(result.z_score, 1.695, rel_tol=1e-6)


def test_math_inf_input_produces_finite_result():
    """inf in denominator makes ratio terms → 0, producing a finite (if low) score."""
    result = calculate_z_score(
        total_assets=float("inf"), total_liabilities=40.0, working_capital=10.0,
        retained_earnings=20.0, ebit=15.0, sales=80.0, market_cap=50.0,
    )
    # MVE/TL = 50/40 = 1.25 is the only non-zero term: 0.6 * 1.25 = 0.75
    assert result.z_score is not None
    assert math.isclose(result.z_score, 0.75, rel_tol=1e-9)
    assert result.zone == "Distress (D)"


def test_math_nan_input_returns_na():
    result = calculate_z_score(
        total_assets=float("nan"), total_liabilities=40.0, working_capital=10.0,
        retained_earnings=20.0, ebit=15.0, sales=80.0, market_cap=50.0,
    )
    assert result.z_score is None
    assert result.zone == "N/A"


# ── build_z_score_breakdown ───────────────────────────────────────────────────

def test_breakdown_has_five_entries_ordered():
    breakdown = build_z_score_breakdown(
        total_assets=100.0, total_liabilities=40.0, working_capital=10.0,
        retained_earnings=20.0, ebit=15.0, sales=80.0, market_cap=50.0,
    )
    assert len(breakdown) == 5
    labels = [entry["label"] for entry in breakdown]
    assert labels == ["WC / TA", "RE / TA", "EBIT / TA", "MVE / TL", "Sales / TA"]


def test_breakdown_weights():
    breakdown = build_z_score_breakdown(
        total_assets=100.0, total_liabilities=40.0, working_capital=10.0,
        retained_earnings=20.0, ebit=15.0, sales=80.0, market_cap=50.0,
    )
    expected_weights = [1.2, 1.4, 3.3, 0.6, 1.0]
    for entry, expected_w in zip(breakdown, expected_weights):
        assert entry["weight"] == expected_w


def test_breakdown_ratios_and_contributions():
    breakdown = build_z_score_breakdown(
        total_assets=100.0, total_liabilities=40.0, working_capital=10.0,
        retained_earnings=20.0, ebit=15.0, sales=80.0, market_cap=50.0,
    )
    # WC/TA = 10/100 = 0.1, contrib = 0.12
    assert breakdown[0]["ratio"] == 0.1
    assert math.isclose(breakdown[0]["contribution"], 0.12, rel_tol=1e-9)
    # RE/TA = 20/100 = 0.2, contrib = 0.28
    assert breakdown[1]["ratio"] == 0.2
    assert math.isclose(breakdown[1]["contribution"], 0.28, rel_tol=1e-9)
    # EBIT/TA = 15/100 = 0.15, contrib = 0.495
    assert breakdown[2]["ratio"] == 0.15
    assert math.isclose(breakdown[2]["contribution"], 0.495, rel_tol=1e-9)
    # MVE/TL = 50/40 = 1.25, contrib = 0.75
    assert breakdown[3]["ratio"] == 1.25
    assert math.isclose(breakdown[3]["contribution"], 0.75, rel_tol=1e-9)
    # Sales/TA = 80/100 = 0.8, contrib = 0.8
    assert breakdown[4]["ratio"] == 0.8
    assert math.isclose(breakdown[4]["contribution"], 0.8, rel_tol=1e-9)


def test_breakdown_total_liabilities_zero_mve_none():
    """MVE/TL ratio/contribution is None when total_liabilities=0."""
    breakdown = build_z_score_breakdown(
        total_assets=100.0, total_liabilities=0.0, working_capital=10.0,
        retained_earnings=20.0, ebit=15.0, sales=80.0, market_cap=50.0,
    )
    mve_entry = breakdown[3]
    assert mve_entry["label"] == "MVE / TL"
    assert mve_entry["ratio"] is None
    assert mve_entry["contribution"] is None


def test_breakdown_retained_earnings_none():
    """RE/TA ratio/contribution is None when retained_earnings is None."""
    breakdown = build_z_score_breakdown(
        total_assets=100.0, total_liabilities=40.0, working_capital=10.0,
        retained_earnings=None, ebit=15.0, sales=80.0, market_cap=50.0,
    )
    re_entry = breakdown[1]
    assert re_entry["label"] == "RE / TA"
    assert re_entry["ratio"] is None
    assert re_entry["contribution"] is None


def test_breakdown_market_cap_none():
    """MVE/TL ratio/contribution is None when market_cap is None."""
    breakdown = build_z_score_breakdown(
        total_assets=100.0, total_liabilities=40.0, working_capital=10.0,
        retained_earnings=20.0, ebit=15.0, sales=80.0, market_cap=None,
    )
    mve_entry = breakdown[3]
    assert mve_entry["label"] == "MVE / TL"
    assert mve_entry["ratio"] is None
    assert mve_entry["contribution"] is None
