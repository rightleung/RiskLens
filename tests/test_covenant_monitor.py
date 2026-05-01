"""
Test suite for covenant_monitor module — full parametrized coverage.

Run with: pytest tests/test_covenant_monitor.py -v
"""

import pytest

from covenant_monitor import FinancialCovenants, CovenantMonitor
from ratio_analyzer import CreditRatioAnalysis


# ── Per-field parametrized tests ──────────────────────────────────────────────

COVENANT_FIELDS = [
    # (covenant_attr, ratio_attr, direction, label, pass_value, breach_value, threshold)
    ("min_interest_coverage", "interest_coverage", "min", "Interest Coverage", 5.0, 1.0, 3.0),
    ("max_debt_to_ebitda", "debt_to_ebitda", "max", "Debt to EBITDA", 2.0, 6.0, 4.0),
    ("max_debt_to_equity", "debt_to_equity", "max", "Debt to Equity", 0.5, 3.0, 1.5),
    ("min_current_ratio", "current_ratio", "min", "Current Ratio", 2.0, 0.5, 1.2),
    ("min_quick_ratio", "quick_ratio", "min", "Quick Ratio", 1.5, 0.3, 0.8),
    ("min_fcf_to_debt", "fcf_to_debt", "min", "FCF to Debt", 0.3, -0.1, 0.1),
]


class TestCovenantFieldPass:
    @pytest.mark.parametrize("covenant_attr, ratio_attr, direction, label, pass_value, breach_value, threshold", COVENANT_FIELDS)
    def test_pass(self, covenant_attr, ratio_attr, direction, label, pass_value, breach_value, threshold):
        ratios = CreditRatioAnalysis()
        setattr(ratios, ratio_attr, pass_value)
        covenants = FinancialCovenants(**{covenant_attr: threshold})
        monitor = CovenantMonitor()
        report = monitor.check_covenants("TestCo", 2024, ratios, covenants)
        assert report.covenants_passed == 1
        assert report.covenants_breached == 0
        assert report.alerts[0].breached is False
        assert report.alerts[0].metric == ratio_attr


class TestCovenantFieldBreach:
    @pytest.mark.parametrize("covenant_attr, ratio_attr, direction, label, pass_value, breach_value, threshold", COVENANT_FIELDS)
    def test_breach(self, covenant_attr, ratio_attr, direction, label, pass_value, breach_value, threshold):
        ratios = CreditRatioAnalysis()
        setattr(ratios, ratio_attr, breach_value)
        covenants = FinancialCovenants(**{covenant_attr: threshold})
        monitor = CovenantMonitor()
        report = monitor.check_covenants("TestCo", 2024, ratios, covenants)
        assert report.covenants_passed == 0
        assert report.covenants_breached == 1
        assert report.alerts[0].breached is True


class TestCovenantFieldEqualToThreshold:
    @pytest.mark.parametrize("covenant_attr, ratio_attr, direction, label, pass_value, breach_value, threshold", COVENANT_FIELDS)
    def test_equal_to_threshold_not_breached(self, covenant_attr, ratio_attr, direction, label, pass_value, breach_value, threshold):
        """Equal to threshold is NOT a breach (min: actual>=threshold, max: actual<=threshold)."""
        ratios = CreditRatioAnalysis()
        setattr(ratios, ratio_attr, threshold)
        covenants = FinancialCovenants(**{covenant_attr: threshold})
        monitor = CovenantMonitor()
        report = monitor.check_covenants("TestCo", 2024, ratios, covenants)
        assert report.covenants_breached == 0
        assert report.alerts[0].breached is False


class TestCovenantFieldDataUnavailable:
    @pytest.mark.parametrize("covenant_attr, ratio_attr, direction, label, pass_value, breach_value, threshold", COVENANT_FIELDS)
    def test_data_unavailable_defaults_breach(self, covenant_attr, ratio_attr, direction, label, pass_value, breach_value, threshold):
        """OR-002: Missing actual → breach with DATA_UNAVAILABLE message."""
        ratios = CreditRatioAnalysis()  # All None
        covenants = FinancialCovenants(**{covenant_attr: threshold})
        monitor = CovenantMonitor()
        report = monitor.check_covenants("TestCo", 2024, ratios, covenants)
        assert report.covenants_breached == 1
        assert report.covenants_passed == 0
        alert = report.alerts[0]
        assert alert.breached is True
        assert alert.actual_value is None
        assert "DATA_UNAVAILABLE" in alert.message


class TestCovenantFieldThresholdNoneSkipped:
    @pytest.mark.parametrize("covenant_attr, ratio_attr, direction, label, pass_value, breach_value, threshold", COVENANT_FIELDS)
    def test_threshold_none_skips_covenant(self, covenant_attr, ratio_attr, direction, label, pass_value, breach_value, threshold):
        """When threshold is None, no alert is generated for that covenant."""
        ratios = CreditRatioAnalysis()
        setattr(ratios, ratio_attr, pass_value)
        covenants = FinancialCovenants(**{covenant_attr: None})
        monitor = CovenantMonitor()
        report = monitor.check_covenants("TestCo", 2024, ratios, covenants)
        assert report.covenants_passed == 0
        assert report.covenants_breached == 0
        assert len(report.alerts) == 0


# ── Combo test ────────────────────────────────────────────────────────────────

def test_mixed_covenants_pass_breach_missing():
    """Multiple covenants with mix of pass, breach, and missing data."""
    ratios = CreditRatioAnalysis()
    ratios.interest_coverage = 5.0       # pass (min 3.0)
    ratios.debt_to_ebitda = 6.0          # breach (max 4.0)
    ratios.current_ratio = None          # missing → breach
    ratios.quick_ratio = 1.5             # pass (min 0.8)
    # debt_to_equity, fcf_to_debt not set (threshold None → skipped)

    covenants = FinancialCovenants(
        min_interest_coverage=3.0,
        max_debt_to_ebitda=4.0,
        min_current_ratio=1.2,
        min_quick_ratio=0.8,
        # max_debt_to_equity not set
        # min_fcf_to_debt not set
    )
    monitor = CovenantMonitor()
    report = monitor.check_covenants("TestCo", 2024, ratios, covenants)

    assert report.company_name == "TestCo"
    assert report.fiscal_year == 2024
    assert report.covenants_passed == 2  # interest_coverage, quick_ratio
    assert report.covenants_breached == 2  # debt_to_ebitda, current_ratio (missing)
    assert len(report.alerts) == 4

    # Alerts are in check order: interest_coverage, debt_to_ebitda, current_ratio, quick_ratio
    alert_metrics = [a.metric for a in report.alerts]
    assert alert_metrics == ["interest_coverage", "debt_to_ebitda", "current_ratio", "quick_ratio"]

    breached_metrics = [a.metric for a in report.alerts if a.breached]
    assert set(breached_metrics) == {"debt_to_ebitda", "current_ratio"}


# ── Legacy smoke coverage ────────────────────────────────────────────────────

def test_covenant_breach_when_data_missing():
    ratios = CreditRatioAnalysis()
    covenants = FinancialCovenants(min_interest_coverage=3.0)
    monitor = CovenantMonitor()
    report = monitor.check_covenants("TestCo", 2024, ratios, covenants)
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
    report = monitor.check_covenants("TestCo", 2024, ratios, covenants)
    assert report.covenants_breached == 0
    assert report.covenants_passed == 1
    assert len(report.alerts) == 1
    assert report.alerts[0].breached is False
