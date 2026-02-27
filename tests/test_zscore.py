"""
Test suite for zscore module.

Run with: pytest tests/test_zscore.py -v
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zscore import (
    calculate_z_score,
    map_z_score_to_zone,
    map_z_score_to_implied_rating,
)


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


def test_calculate_z_score_expected_value():
    result = calculate_z_score(
        total_assets=100.0,
        total_liabilities=40.0,
        working_capital=10.0,
        retained_earnings=20.0,
        ebit=15.0,
        sales=80.0,
        market_cap=50.0,
    )
    assert result.z_score is not None
    assert math.isclose(result.z_score, 2.445, rel_tol=1e-6)
    assert result.zone == "Grey (G)"
    assert result.implied_rating == "BB"


def test_calculate_z_score_missing_inputs():
    result = calculate_z_score(
        total_assets=None,
        total_liabilities=40.0,
        working_capital=10.0,
        retained_earnings=20.0,
        ebit=15.0,
        sales=80.0,
        market_cap=50.0,
    )
    assert result.z_score is None
    assert result.zone == "N/A"
    assert result.implied_rating == "N/A"


def test_calculate_z_score_invalid_assets():
    result = calculate_z_score(
        total_assets=0.0,
        total_liabilities=40.0,
        working_capital=10.0,
        retained_earnings=20.0,
        ebit=15.0,
        sales=80.0,
        market_cap=50.0,
    )
    assert result.z_score is None
    assert result.zone == "N/A"
    assert result.implied_rating == "N/A"
