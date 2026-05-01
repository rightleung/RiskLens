"""
Test suite for ratio_analyzer module — precise value tests.

Run with: pytest tests/test_ratio_analyzer.py -v
"""

import pytest
import pandas as pd

from ratio_analyzer import (
    CreditRatioAnalysis,
    RatioAnalyzer,
)


def _df(values: dict[str, float | None]) -> pd.DataFrame:
    """Build a standard DataFrame with metric-name index and a single 'Value' column."""
    records = {k: v for k, v in values.items() if v is not None}
    return pd.DataFrame.from_dict(records, orient="index", columns=["Value"])


# ── Liquidity ─────────────────────────────────────────────────────────────────

class TestLiquidityRatios:
    """Precise-value tests for calculate_liquidity_ratios()."""

    def test_current_ratio_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_current_assets": 15000, "total_current_liabilities": 5000})
        ratios = analyzer.calculate_liquidity_ratios(bs)
        assert ratios["current_ratio"] == 3.0

    def test_quick_ratio_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({
            "total_current_assets": 15000,
            "total_current_liabilities": 5000,
            "inventory": 6000,
            "cash": 2000,
        })
        ratios = analyzer.calculate_liquidity_ratios(bs)
        # (15000 - 6000) / 5000 = 1.8
        assert ratios["quick_ratio"] == 1.8

    def test_cash_ratio_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({
            "total_current_assets": 15000,
            "total_current_liabilities": 5000,
            "cash": 2000,
        })
        ratios = analyzer.calculate_liquidity_ratios(bs)
        assert ratios["cash_ratio"] == 0.4

    def test_quick_ratio_without_inventory_uses_current_assets(self):
        """When inventory is missing, quick ratio uses total_current_assets as numerator."""
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_current_assets": 15000, "total_current_liabilities": 5000})
        ratios = analyzer.calculate_liquidity_ratios(bs)
        assert ratios["quick_ratio"] == 3.0

    def test_current_ratio_denominator_zero_returns_none(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_current_assets": 15000, "total_current_liabilities": 0})
        ratios = analyzer.calculate_liquidity_ratios(bs)
        assert ratios["current_ratio"] is None

    @pytest.mark.parametrize("missing_key", ["total_current_assets", "total_current_liabilities"])
    def test_liquidity_ratios_none_when_key_missing(self, missing_key):
        analyzer = RatioAnalyzer("/tmp")
        values = {"total_current_assets": 15000, "total_current_liabilities": 5000}
        del values[missing_key]
        bs = _df(values)
        ratios = analyzer.calculate_liquidity_ratios(bs)
        assert ratios["current_ratio"] is None
        assert ratios["quick_ratio"] is None
        assert ratios["cash_ratio"] is None


# ── Leverage ──────────────────────────────────────────────────────────────────

class TestLeverageRatios:
    """Precise-value and edge-case tests for calculate_leverage_ratios()."""

    def test_debt_to_equity_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_debt": 600, "total_equity": 1100, "total_assets": 2000})
        ratios = analyzer.calculate_leverage_ratios(bs)
        assert ratios["debt_to_equity"] == pytest.approx(600 / 1100, rel=1e-9)

    def test_debt_to_assets_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_debt": 600, "total_equity": 1100, "total_assets": 2000})
        ratios = analyzer.calculate_leverage_ratios(bs)
        assert ratios["debt_to_assets"] == 0.3

    def test_financial_leverage_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_debt": 600, "total_equity": 1100, "total_assets": 2000})
        ratios = analyzer.calculate_leverage_ratios(bs)
        assert ratios["financial_leverage"] == pytest.approx(2000 / 1100, rel=1e-9)

    def test_negative_equity_gives_none_debt_to_equity(self):
        """OR-001: Negative equity makes D/E misleading, return None."""
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_debt": 600, "total_equity": -500, "total_assets": 2000})
        ratios = analyzer.calculate_leverage_ratios(bs)
        assert ratios["debt_to_equity"] is None
        # Other ratios still compute
        assert ratios["debt_to_assets"] == 0.3

    def test_interest_coverage_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_debt": 600, "total_equity": 1100, "total_assets": 2000})
        inc = _df({"operating_income": 250, "interest_expense": 25})
        ratios = analyzer.calculate_leverage_ratios(bs, inc)
        assert ratios["interest_coverage"] == 10.0

    def test_interest_coverage_negative_ebit_returns_none(self):
        """OR-001: EBIT <= 0 → interest_coverage is None."""
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_debt": 600, "total_equity": 1100, "total_assets": 2000})
        inc = _df({"operating_income": -100, "interest_expense": 25})
        ratios = analyzer.calculate_leverage_ratios(bs, inc)
        assert ratios["interest_coverage"] is None

    def test_interest_coverage_zero_ebit_returns_none(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_debt": 600, "total_equity": 1100, "total_assets": 2000})
        inc = _df({"operating_income": 0, "interest_expense": 25})
        ratios = analyzer.calculate_leverage_ratios(bs, inc)
        assert ratios["interest_coverage"] is None

    def test_interest_expense_negative_is_abs_normalized(self):
        """Negative interest_expense should be abs'd before division."""
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_debt": 600, "total_equity": 1100, "total_assets": 2000})
        inc = _df({"operating_income": 250, "interest_expense": -25})
        ratios = analyzer.calculate_leverage_ratios(bs, inc)
        assert ratios["interest_coverage"] == 10.0

    def test_debt_to_ebitda_direct_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_debt": 600, "total_equity": 1100, "total_assets": 2000})
        inc = _df({"operating_income": 250, "interest_expense": 25, "ebitda": 300})
        ratios = analyzer.calculate_leverage_ratios(bs, inc)
        assert ratios["debt_to_ebitda"] == 2.0

    def test_debt_to_ebitda_ebit_plus_da_fallback(self):
        """When ebitda is missing, fallback to ebit + |depreciation|."""
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_debt": 600, "total_equity": 1100, "total_assets": 2000})
        inc = _df({
            "operating_income": 250,
            "interest_expense": 25,
            "reconciled_depreciation": 50,
        })
        ratios = analyzer.calculate_leverage_ratios(bs, inc)
        assert ratios["ebitda"] == 300  # 250 + 50
        assert ratios["debt_to_ebitda"] == 2.0

    def test_debt_to_ebitda_negative_ebitda_returns_none(self):
        """OR-001: EBITDA <= 0 → debt_to_ebitda is None."""
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_debt": 600, "total_equity": 1100, "total_assets": 2000})
        inc = _df({"operating_income": 250, "interest_expense": 25, "ebitda": -50})
        ratios = analyzer.calculate_leverage_ratios(bs, inc)
        assert ratios["debt_to_ebitda"] is None

    def test_debt_to_ebitda_zero_ebitda_returns_none(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_debt": 600, "total_equity": 1100, "total_assets": 2000})
        inc = _df({"operating_income": 250, "interest_expense": 25, "ebitda": 0})
        ratios = analyzer.calculate_leverage_ratios(bs, inc)
        assert ratios["debt_to_ebitda"] is None


# ── Profitability ─────────────────────────────────────────────────────────────

class TestProfitabilityRatios:
    """Precise-value and edge-case tests for calculate_profitability_ratios()."""

    def test_gross_margin_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_assets": 2000, "total_equity": 1100})
        inc = _df({"revenue": 1000, "gross_profit": 600, "operating_income": 250,
                    "net_income": 200})
        ratios = analyzer.calculate_profitability_ratios(bs, inc)
        assert ratios["gross_margin"] == 60.0

    def test_gross_profit_fallback_from_revenue_minus_cost(self):
        """When gross_profit is missing, compute from revenue - cost_of_revenue."""
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_assets": 2000, "total_equity": 1100})
        inc = _df({"revenue": 1000, "cost_of_revenue": 400, "operating_income": 250,
                    "net_income": 200})
        ratios = analyzer.calculate_profitability_ratios(bs, inc)
        assert ratios["gross_margin"] == 60.0

    def test_operating_margin_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_assets": 2000, "total_equity": 1100})
        inc = _df({"revenue": 1000, "gross_profit": 600, "operating_income": 250,
                    "net_income": 200})
        ratios = analyzer.calculate_profitability_ratios(bs, inc)
        assert ratios["operating_margin"] == 25.0

    def test_net_margin_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_assets": 2000, "total_equity": 1100})
        inc = _df({"revenue": 1000, "gross_profit": 600, "operating_income": 250,
                    "net_income": 200})
        ratios = analyzer.calculate_profitability_ratios(bs, inc)
        assert ratios["net_margin"] == 20.0

    def test_roa_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_assets": 2000, "total_equity": 1100})
        inc = _df({"revenue": 1000, "net_income": 200})
        ratios = analyzer.calculate_profitability_ratios(bs, inc)
        assert ratios["roa"] == 10.0

    def test_roe_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_assets": 2000, "total_equity": 1100})
        inc = _df({"revenue": 1000, "net_income": 200})
        ratios = analyzer.calculate_profitability_ratios(bs, inc)
        assert ratios["roe"] == pytest.approx(200 / 1100 * 100, rel=1e-9)

    def test_profitability_missing_revenue_returns_none_margins(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_assets": 2000, "total_equity": 1100})
        inc = _df({"operating_income": 250, "net_income": 200})
        ratios = analyzer.calculate_profitability_ratios(bs, inc)
        assert ratios["gross_margin"] is None
        assert ratios["operating_margin"] is None
        assert ratios["net_margin"] is None
        # roa/roe still compute with net_income from inc and assets/equity from bs
        assert ratios["roa"] == 10.0
        assert ratios["roe"] is not None


# ── Efficiency ────────────────────────────────────────────────────────────────

class TestEfficiencyRatios:
    """Precise-value tests for calculate_efficiency_ratios()."""

    def test_asset_turnover_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_assets": 2000, "accounts_receivable": 150,
                   "inventory": 120, "accounts_payable": 130})
        inc = _df({"revenue": 1000, "cost_of_revenue": 400})
        ratios = analyzer.calculate_efficiency_ratios(bs, inc)
        assert ratios["asset_turnover"] == 0.5

    def test_receivables_turnover_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_assets": 2000, "accounts_receivable": 150,
                   "inventory": 120, "accounts_payable": 130})
        inc = _df({"revenue": 1000, "cost_of_revenue": 400})
        ratios = analyzer.calculate_efficiency_ratios(bs, inc)
        assert ratios["receivables_turnover"] == pytest.approx(1000 / 150, rel=1e-9)

    def test_inventory_turnover_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_assets": 2000, "accounts_receivable": 150,
                   "inventory": 120, "accounts_payable": 130})
        inc = _df({"revenue": 1000, "cost_of_revenue": 400})
        ratios = analyzer.calculate_efficiency_ratios(bs, inc)
        assert ratios["inventory_turnover"] == pytest.approx(400 / 120, rel=1e-9)

    def test_payables_turnover_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_assets": 2000, "accounts_receivable": 150,
                   "inventory": 120, "accounts_payable": 130})
        inc = _df({"revenue": 1000, "cost_of_revenue": 400})
        ratios = analyzer.calculate_efficiency_ratios(bs, inc)
        assert ratios["payables_turnover"] == pytest.approx(400 / 130, rel=1e-9)

    def test_efficiency_ratios_none_when_denom_zero(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_assets": 0, "accounts_receivable": 0,
                   "inventory": 0, "accounts_payable": 0})
        inc = _df({"revenue": 1000, "cost_of_revenue": 400})
        ratios = analyzer.calculate_efficiency_ratios(bs, inc)
        assert ratios["asset_turnover"] is None
        assert ratios["receivables_turnover"] is None
        assert ratios["inventory_turnover"] is None
        assert ratios["payables_turnover"] is None


# ── Cash Flow ─────────────────────────────────────────────────────────────────

class TestCashFlowRatios:
    """Precise-value tests for calculate_cash_flow_ratios()."""

    def test_fcf_to_debt_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        cf = _df({"operating_cf": 250, "free_cf": 180})
        bs = _df({"total_debt": 600})
        ratios = analyzer.calculate_cash_flow_ratios(cf, bs)
        assert ratios["fcf_to_debt"] == 0.3

    def test_fcf_to_revenue_from_is_data(self):
        analyzer = RatioAnalyzer("/tmp")
        cf = _df({"operating_cf": 250, "free_cf": 180})
        bs = _df({"total_debt": 600})
        inc = _df({"revenue": 1000})
        ratios = analyzer.calculate_cash_flow_ratios(cf, bs, inc)
        assert ratios["fcf_to_revenue"] == 0.18

    def test_fcf_to_revenue_fallback_to_cf_data(self):
        """When is_data has no revenue, fall back to cf_data revenue."""
        analyzer = RatioAnalyzer("/tmp")
        cf = _df({"operating_cf": 250, "free_cf": 180, "revenue": 800})
        bs = _df({"total_debt": 600})
        inc = _df({"operating_income": 100})
        ratios = analyzer.calculate_cash_flow_ratios(cf, bs, inc)
        assert ratios["fcf_to_revenue"] == 0.225

    def test_fcf_to_debt_missing_returns_none(self):
        analyzer = RatioAnalyzer("/tmp")
        cf = _df({"operating_cf": 250})
        bs = _df({"total_debt": 600})
        ratios = analyzer.calculate_cash_flow_ratios(cf, bs)
        assert ratios["fcf_to_debt"] is None

    def test_zero_revenue_returns_none_fcf_to_revenue(self):
        analyzer = RatioAnalyzer("/tmp")
        cf = _df({"operating_cf": 250, "free_cf": 180})
        inc = _df({"revenue": 0})
        ratios = analyzer.calculate_cash_flow_ratios(cf, None, inc)
        assert ratios["fcf_to_revenue"] is None

    def test_operating_cf_ratio_exact(self):
        analyzer = RatioAnalyzer("/tmp")
        cf = _df({"operating_cf": 250, "free_cf": 180})
        inc = _df({"revenue": 1000})
        ratios = analyzer.calculate_cash_flow_ratios(cf, None, inc)
        assert ratios["operating_cf_ratio"] == 0.25


# ── calculate_all_ratios() end-to-end ─────────────────────────────────────────

class TestCalculateAllRatios:
    """End-to-end tests for calculate_all_ratios()."""

    def test_all_ratios_populated_on_credit_ratio_analysis(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({
            "total_assets": 2000, "total_equity": 1100, "total_debt": 600,
            "total_current_assets": 800, "total_current_liabilities": 350,
            "cash": 200, "inventory": 120, "accounts_receivable": 150,
            "accounts_payable": 130,
        })
        inc = _df({
            "revenue": 1000, "cost_of_revenue": 400, "gross_profit": 600,
            "operating_income": 250, "net_income": 200, "interest_expense": 25,
            "ebitda": 300,
        })
        cf = _df({"operating_cf": 220, "free_cf": 180})

        analysis = analyzer.calculate_all_ratios(
            bs_data=bs, is_data=inc, cf_data=cf,
            company_name="TestCo", fiscal_year=2024,
        )

        # Liquidity
        assert analysis.current_ratio == pytest.approx(800 / 350, rel=1e-9)
        assert analysis.quick_ratio == pytest.approx((800 - 120) / 350, rel=1e-9)
        assert analysis.cash_ratio == pytest.approx(200 / 350, rel=1e-9)
        # Leverage
        assert analysis.debt_to_equity == pytest.approx(600 / 1100, rel=1e-9)
        assert analysis.debt_to_assets == 0.3
        assert analysis.interest_coverage == 10.0
        assert analysis.debt_to_ebitda == 2.0
        # Profitability
        assert analysis.gross_margin == 60.0
        assert analysis.operating_margin == 25.0
        assert analysis.net_margin == 20.0
        assert analysis.roa == 10.0
        assert analysis.roe == pytest.approx(200 / 1100 * 100, rel=1e-9)
        # Efficiency
        assert analysis.asset_turnover == 0.5
        assert analysis.receivables_turnover == pytest.approx(1000 / 150, rel=1e-9)
        assert analysis.inventory_turnover == pytest.approx(400 / 120, rel=1e-9)
        assert analysis.payables_turnover == pytest.approx(400 / 130, rel=1e-9)
        # Cash Flow
        assert analysis.fcf_to_debt == 0.3
        assert analysis.fcf_to_revenue == 0.18
        assert analysis.operating_cf_ratio == 0.22
        # Metadata
        assert analysis.company_name == "TestCo"
        assert analysis.fiscal_year == 2024

    def test_all_ratios_without_cf_data(self):
        analyzer = RatioAnalyzer("/tmp")
        bs = _df({"total_assets": 2000, "total_equity": 1100,
                   "total_current_assets": 800, "total_current_liabilities": 350})
        inc = _df({"revenue": 1000, "operating_income": 250, "net_income": 200})

        analysis = analyzer.calculate_all_ratios(
            bs_data=bs, is_data=inc, company_name="MinCo", fiscal_year=2024,
        )
        assert analysis.company_name == "MinCo"
        assert analysis.current_ratio is not None
        assert analysis.fcf_to_debt is None  # No CF data → cash flow ratios missing


# ── Export ────────────────────────────────────────────────────────────────────

class TestExport:
    """Export functionality tests."""

    def test_export_json(self, tmp_path):
        analyzer = RatioAnalyzer(str(tmp_path))
        analysis = CreditRatioAnalysis()
        analysis.current_ratio = 2.5
        analysis.debt_to_equity = 0.65

        result = analyzer.export_ratios(analysis, format="json")
        assert result.endswith(".json")

    def test_export_csv(self, tmp_path):
        analyzer = RatioAnalyzer(str(tmp_path))
        analysis = CreditRatioAnalysis()
        analysis.current_ratio = 2.5
        analysis.debt_to_equity = 0.65

        result = analyzer.export_ratios(analysis, format="csv")
        assert result.endswith(".csv")
