"""
Altman Z-Score Utilities
========================
Pure functions for computing Z-Score and mapping it to zones/ratings.

This module is intentionally side-effect free to support deterministic tests.
"""

from dataclasses import dataclass
from typing import Any, Optional
import math


@dataclass(frozen=True)
class ZScoreResult:
    """Result container for Z-Score computation."""
    z_score: Optional[float]
    zone: str
    implied_rating: str


def map_z_score_to_zone(z_score: float) -> str:
    """Map raw Z-Score to risk zone label."""
    if z_score >= 2.99:
        return "Safe (S)"
    if z_score >= 1.81:
        return "Grey (G)"
    return "Distress (D)"


def map_z_score_to_implied_rating(z_score: float) -> str:
    """Map raw Z-Score to implied S&P-style rating."""
    if z_score >= 4.5:
        return "AAA"
    if z_score >= 3.5:
        return "AA"
    if z_score >= 2.99:
        return "A"
    if z_score >= 2.5:
        return "BBB"
    if z_score >= 1.81:
        return "BB"
    if z_score >= 1.2:
        return "B"
    if z_score >= 0.5:
        return "CCC"
    return "D"


def calculate_z_score(
    total_assets: Optional[float],
    total_liabilities: Optional[float],
    working_capital: Optional[float],
    retained_earnings: Optional[float],
    ebit: Optional[float],
    sales: Optional[float],
    market_cap: Optional[float],
) -> ZScoreResult:
    """
    Calculate Altman Z-Score using public-company formulation.

    Required inputs: total_assets, total_liabilities, ebit, sales.
    Optional inputs default to 0 where appropriate to preserve prior behavior.

    Note: Market cap is typically current market value; historical market cap
    is not available for past periods in this project.
    """
    if total_assets is None or total_liabilities is None or ebit is None or sales is None:
        return ZScoreResult(None, "N/A", "N/A")
    if total_assets <= 0:
        return ZScoreResult(None, "N/A", "N/A")

    wc = working_capital or 0
    re = retained_earnings or 0
    mc = market_cap or 0

    A = wc / total_assets
    B = re / total_assets
    C = ebit / total_assets
    D = mc / total_liabilities if total_liabilities and total_liabilities > 0 else 0
    E = sales / total_assets

    raw_z = 1.2 * A + 1.4 * B + 3.3 * C + 0.6 * D + 1.0 * E
    if not math.isfinite(raw_z):
        return ZScoreResult(None, "N/A", "N/A")

    zone = map_z_score_to_zone(raw_z)
    implied_rating = map_z_score_to_implied_rating(raw_z)
    return ZScoreResult(raw_z, zone, implied_rating)


def build_z_score_breakdown(
    total_assets: Optional[float],
    total_liabilities: Optional[float],
    working_capital: Optional[float],
    retained_earnings: Optional[float],
    ebit: Optional[float],
    sales: Optional[float],
    market_cap: Optional[float],
) -> list[dict[str, Any]]:
    """Return the Altman Z-Score term breakdown with weighted contributions."""
    def safe_ratio(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
        if numerator is None or denominator is None or denominator <= 0:
            return None
        value = numerator / denominator
        return value if math.isfinite(value) else None

    entries = [
        ("WC / TA", working_capital, total_assets, 1.2),
        ("RE / TA", retained_earnings, total_assets, 1.4),
        ("EBIT / TA", ebit, total_assets, 3.3),
        ("MVE / TL", market_cap, total_liabilities, 0.6),
        ("Sales / TA", sales, total_assets, 1.0),
    ]
    breakdown: list[dict[str, Any]] = []
    for label, numerator, denominator, weight in entries:
        ratio = safe_ratio(numerator, denominator)
        contribution = ratio * weight if ratio is not None else None
        breakdown.append(
            {
                "label": label,
                "ratio": ratio,
                "weight": weight,
                "contribution": contribution,
            }
        )
    return breakdown
