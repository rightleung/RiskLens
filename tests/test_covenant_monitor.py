"""
Test suite for covenant_monitor module.

Run with: pytest tests/test_covenant_monitor.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from covenant_monitor import FinancialCovenants, CovenantMonitor
from ratio_analyzer import CreditRatioAnalysis


def test_covenant_breach_when_data_missing():
    ratios = CreditRatioAnalysis()
    covenants = FinancialCovenants(min_interest_coverage=3.0)
    monitor = CovenantMonitor()

    report = monitor.check_covenants(
        company_name="TestCo",
        fiscal_year=2024,
        ratios=ratios,
        covenants=covenants,
    )

    assert report.covenants_breached == 1
    assert report.covenants_passed == 0
    assert len(report.alerts) == 1
    assert report.alerts[0].breached is True
    assert "DATA_UNAVAILABLE" in report.alerts[0].message


def test_covenant_pass_when_metric_meets_threshold():
    ratios = CreditRatioAnalysis()
    ratios.interest_coverage = 6.0
    covenants = FinancialCovenants(min_interest_coverage=3.0)
    monitor = CovenantMonitor()

    report = monitor.check_covenants(
        company_name="TestCo",
        fiscal_year=2024,
        ratios=ratios,
        covenants=covenants,
    )

    assert report.covenants_breached == 0
    assert report.covenants_passed == 1
    assert len(report.alerts) == 1
    assert report.alerts[0].breached is False
