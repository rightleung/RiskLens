"""
Test suite for data_fetcher module.

Run with: pytest tests/test_data_fetcher.py -v
"""

import pytest
import sys
import types
import pandas as pd

import data_fetcher
from data_fetcher import FinancialDataFetcher, DataFetchError, DataFetchErrorType


def _build_fake_statement(rows: dict) -> pd.DataFrame:
    return pd.DataFrame({pd.Timestamp("2024-12-31"): rows})


class _FakeTicker:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.info = {"longName": "Fake Corp", "marketCap": 123456789}

        self.income_stmt = _build_fake_statement({
            "Total Revenue": 1000.0,
            "Cost Of Revenue": 400.0,
            "Gross Profit": 600.0,
            "Operating Income": 250.0,
            "Net Income": 200.0,
            "Interest Expense": 25.0,
            "EBITDA": 300.0,
        })
        self.balance_sheet = _build_fake_statement({
            "Total Assets": 2000.0,
            "Total Liabilities": 900.0,
            "Stockholders Equity": 1100.0,
            "Current Assets": 800.0,
            "Current Liabilities": 350.0,
            "Cash": 200.0,
            "Retained Earnings": 500.0,
            "Accounts Receivable": 150.0,
            "Inventory": 120.0,
            "Accounts Payable": 130.0,
            "Total Debt": 600.0,
        })
        self.cashflow = _build_fake_statement({
            "Operating Cash Flow": 220.0,
            "Free Cash Flow": 180.0,
        })
        self.quarterly_income_stmt = pd.DataFrame()
        self.quarterly_balance_sheet = pd.DataFrame()
        self.quarterly_cashflow = pd.DataFrame()


class _EmptyTicker:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.info = {"longName": "Empty Corp", "marketCap": 0}
        self.income_stmt = pd.DataFrame()
        self.balance_sheet = pd.DataFrame()
        self.cashflow = pd.DataFrame()
        self.quarterly_income_stmt = pd.DataFrame()
        self.quarterly_balance_sheet = pd.DataFrame()
        self.quarterly_cashflow = pd.DataFrame()


class _PartialTicker:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.info = {"longName": "Partial Corp", "marketCap": 42}
        self.income_stmt = _build_fake_statement({
            "Total Revenue": 1000.0,
            "Operating Income": 250.0,
            "Net Income": 200.0,
        })
        self.balance_sheet = pd.DataFrame()
        self.cashflow = _build_fake_statement({
            "Operating Cash Flow": 220.0,
            "Free Cash Flow": 180.0,
        })
        self.quarterly_income_stmt = pd.DataFrame()
        self.quarterly_balance_sheet = pd.DataFrame()
        self.quarterly_cashflow = pd.DataFrame()


@pytest.fixture(autouse=True)
def _reset_cache_and_sleep(monkeypatch):
    FinancialDataFetcher.clear_cache()
    monkeypatch.setattr(data_fetcher.time, "sleep", lambda *_args, **_kwargs: None)
    yield
    FinancialDataFetcher.clear_cache()


class TestFinancialDataFetcher:
    """Tests for FinancialDataFetcher class."""

    def test_invalid_ticker_raises_exception(self, monkeypatch):
        """Test that invalid ticker raises DataFetchError instead of returning None."""
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(data_fetcher.yf, "Ticker", lambda _ticker: (_ for _ in ()).throw(Exception("404 not found")))

        # Test with clearly invalid ticker
        with pytest.raises(DataFetchError) as exc_info:
            fetcher.get_financial_data("INVALID_TICKER_XYZ", "yfinance")

        # Verify exception details
        assert exc_info.value.error_type in [
            DataFetchErrorType.INVALID_TICKER,
            DataFetchErrorType.NO_DATA_AVAILABLE
        ]
        assert exc_info.value.ticker == "INVALID_TICKER_XYZ"

    def test_empty_ticker_raises_exception(self):
        """Test that empty ticker raises DataFetchError."""
        fetcher = FinancialDataFetcher()

        with pytest.raises(DataFetchError):
            fetcher.get_financial_data("", "yfinance")

    def test_valid_ticker_returns_data(self, monkeypatch):
        """Test that valid ticker returns data with non-empty history."""
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(data_fetcher.yf, "Ticker", _FakeTicker)

        result = fetcher.get_financial_data("AAPL", "yfinance")

        assert result is not None, "Valid ticker should return data"
        assert 'ticker' in result, "Result should have ticker field"
        assert 'company_name' in result, "Result should have company_name field"
        assert 'history' in result, "Result should have history field"
        assert len(result['history']) > 0, "Valid ticker should have non-empty history"

    def test_result_structure(self, monkeypatch):
        """Test that returned data has correct structure."""
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(data_fetcher.yf, "Ticker", _FakeTicker)

        result = fetcher.get_financial_data("AAPL", "yfinance")

        if result:
            # Check top-level keys
            assert 'ticker' in result
            assert 'company_name' in result
            assert 'market_cap' in result
            assert 'history' in result

            # Check history structure
            if result['history']:
                period = result['history'][0]
                assert 'year_label' in period
                assert 'is_quarterly' in period
                assert 'income' in period
                assert 'balance' in period
                assert 'cash' in period

    def test_empty_response_raises_no_data_available(self, monkeypatch):
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(data_fetcher.yf, "Ticker", _EmptyTicker)

        with pytest.raises(DataFetchError) as exc_info:
            fetcher.get_financial_data("EMPTY", "yfinance")

        assert exc_info.value.error_type == DataFetchErrorType.NO_DATA_AVAILABLE

    def test_partial_data_returns_history_with_missing_statements(self, monkeypatch):
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(data_fetcher.yf, "Ticker", _PartialTicker)

        result = fetcher.get_financial_data("PARTIAL", "yfinance")

        assert result is not None
        assert len(result["history"]) > 0
        assert any(period["balance"].empty for period in result["history"])
        assert any(not period["income"].empty for period in result["history"])

    def test_a_share_ticker_format(self, monkeypatch):
        """Test that A-share ticker format is handled correctly."""
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(data_fetcher.yf, "Ticker", _FakeTicker)

        # Test with .SS suffix (should be stripped)
        result = fetcher.get_financial_data("600519.SS", "yfinance")
        assert result is not None
        assert result["ticker"] == "600519.SS"
        assert "history" in result
        assert len(result["history"]) > 0

    def test_latest_quarter_keeps_prior_year_same_quarter(self, monkeypatch):
        """Latest quarterly period should retain same quarter last year for YoY."""
        fetcher = FinancialDataFetcher()

        def _build_statement(cols: list[str], value: float) -> pd.DataFrame:
            return pd.DataFrame({pd.Timestamp(col): {"Total Revenue": value} for col in cols})

        class _QuarterlyYoYTicker:
            def __init__(self, _symbol: str):
                self.info = {"longName": "Quarterly YoY Corp", "marketCap": 1000}
                self.income_stmt = _build_statement(["2024-12-31", "2023-12-31"], 1000.0)
                self.balance_sheet = _build_statement(["2024-12-31", "2023-12-31"], 900.0)
                self.cashflow = _build_statement(["2024-12-31", "2023-12-31"], 800.0)
                quarter_cols = ["2025-09-30", "2025-06-30", "2024-09-30", "2024-06-30"]
                self.quarterly_income_stmt = _build_statement(quarter_cols, 100.0)
                self.quarterly_balance_sheet = _build_statement(quarter_cols, 90.0)
                self.quarterly_cashflow = _build_statement(quarter_cols, 80.0)

        monkeypatch.setattr(data_fetcher.yf, "Ticker", _QuarterlyYoYTicker)
        result = fetcher.get_financial_data("AAPL", "yfinance")

        quarterly_labels = [p["year_label"] for p in result["history"] if p["is_quarterly"]]
        assert "Q3 '25 (U)" in quarterly_labels
        assert "Q3 '24 (U)" in quarterly_labels
        assert "Q2 '24 (U)" not in quarterly_labels

    def test_does_not_keep_prior_year_quarter_when_latest_fy_exists(self, monkeypatch):
        """Do not keep prior-year same quarter when latest quarter is not displayed."""
        fetcher = FinancialDataFetcher()

        def _build_statement(cols: list[str], value: float) -> pd.DataFrame:
            return pd.DataFrame({pd.Timestamp(col): {"Total Revenue": value} for col in cols})

        class _AnnualSupersedesQ4Ticker:
            def __init__(self, _symbol: str):
                self.info = {"longName": "Annual Supersedes Q4 Corp", "marketCap": 1000}
                self.income_stmt = _build_statement(["2025-12-31", "2024-12-31"], 1000.0)
                self.balance_sheet = _build_statement(["2025-12-31", "2024-12-31"], 900.0)
                self.cashflow = _build_statement(["2025-12-31", "2024-12-31"], 800.0)
                quarter_cols = ["2025-12-31", "2024-12-31"]
                self.quarterly_income_stmt = _build_statement(quarter_cols, 100.0)
                self.quarterly_balance_sheet = _build_statement(quarter_cols, 90.0)
                self.quarterly_cashflow = _build_statement(quarter_cols, 80.0)

        monkeypatch.setattr(data_fetcher.yf, "Ticker", _AnnualSupersedesQ4Ticker)
        result = fetcher.get_financial_data("AAPL", "yfinance")

        quarterly_labels = [p["year_label"] for p in result["history"] if p["is_quarterly"]]
        assert "Q4 '24 (U)" not in quarterly_labels
        assert "Q4 '25 (U)" not in quarterly_labels

    def test_fetch_a_share_akshare_builds_annual_and_quarterly_history(self, monkeypatch):
        """AKShare path should normalize report dates and map Sina fields."""
        report_dates = ["20250930", "20240930", "2024-12-31", "2023-12-31"]

        class FakeAk:
            @staticmethod
            def stock_individual_info_em(symbol):
                assert symbol == "600519"
                return pd.DataFrame({
                    "item": ["股票简称", "所属行业", "网址", "员工人数", "公司简介"],
                    "value": ["贵州茅台", "白酒", "https://www.moutaichina.com", "30000", "A-share issuer"],
                })

            @staticmethod
            def stock_profile_cninfo(symbol):
                assert symbol == "600519"
                return pd.DataFrame([{"主营业务": "酒类产品生产与销售"}])

            @staticmethod
            def stock_zygc_em(symbol):
                assert symbol == "SH600519"
                return pd.DataFrame({
                    "分类方向": ["产品", "产品"],
                    "主营构成": ["茅台酒", "系列酒"],
                })

            @staticmethod
            def stock_financial_report_sina(stock, symbol):
                assert stock == "600519"
                if symbol == "利润表":
                    return pd.DataFrame({
                        "报告日": report_dates,
                        "营业总收入": [900.0, 700.0, 1200.0, 1000.0],
                        "营业利润": [500.0, 400.0, 800.0, 650.0],
                        "净利润": [400.0, 320.0, 650.0, 520.0],
                    })
                if symbol == "资产负债表":
                    return pd.DataFrame({
                        "报告日": report_dates,
                        "资产总计": [3000.0, 2600.0, 2800.0, 2400.0],
                        "负债合计": [900.0, 800.0, 850.0, 760.0],
                        "流动资产合计": [1800.0, 1600.0, 1700.0, 1500.0],
                        "流动负债合计": [500.0, 450.0, 480.0, 430.0],
                        "短期借款": [100.0, 90.0, 95.0, 85.0],
                        "长期借款": [200.0, 180.0, 190.0, 170.0],
                    })
                if symbol == "现金流量表":
                    return pd.DataFrame({
                        "报告日": report_dates,
                        "经营活动产生的现金流量净额": [450.0, 360.0, 700.0, 600.0],
                        "购建固定资产、无形资产和其他长期资产所支付的现金": [-50.0, -40.0, -80.0, -60.0],
                    })
                raise AssertionError(f"Unexpected report symbol: {symbol}")

        class FakeYFTicker:
            def __init__(self, symbol):
                assert symbol == "600519.SS"
                self.info = {
                    "marketCap": 123_000_000,
                    "sector": "Consumer Defensive",
                    "industry": "Beverages",
                }
                self.income_stmt = pd.DataFrame()

        monkeypatch.setitem(sys.modules, "akshare", types.SimpleNamespace(
            stock_individual_info_em=FakeAk.stock_individual_info_em,
            stock_profile_cninfo=FakeAk.stock_profile_cninfo,
            stock_zygc_em=FakeAk.stock_zygc_em,
            stock_financial_report_sina=FakeAk.stock_financial_report_sina,
        ))
        monkeypatch.setattr(data_fetcher.yf, "Ticker", FakeYFTicker)

        result = data_fetcher._fetch_a_share_akshare("600519")

        assert result is not None
        assert result["ticker"] == "600519"
        assert result["company_name"] == "贵州茅台"
        assert result["market_cap"] == 123_000_000
        assert result["company_profile"]["industry"] == "白酒"
        assert result["company_profile"]["products"] == ["茅台酒", "系列酒"]

        labels = [period["year_label"] for period in result["history"]]
        assert labels == ["Q3 '25 (U)", "Q3 '24 (U)", "FY24", "FY23"]

        latest_quarter = result["history"][0]
        assert latest_quarter["is_quarterly"] is True
        assert latest_quarter["income"].loc["revenue", "Value"] == 900.0
        assert latest_quarter["balance"].loc["total_assets", "Value"] == 3000.0
        assert latest_quarter["balance"].loc["total_debt", "Value"] == 300.0
        assert latest_quarter["cash"].loc["free_cf", "Value"] == 400.0

        latest_annual = result["history"][2]
        assert latest_annual["is_quarterly"] is False
        assert latest_annual["income"].loc["revenue", "Value"] == 1200.0

    def test_exception_to_dict(self):
        """Test that DataFetchError can be serialized to dict."""
        error = DataFetchError(
            message="Test error",
            error_type=DataFetchErrorType.INVALID_TICKER,
            ticker="TEST",
            details={"reason": "test"}
        )

        error_dict = error.to_dict()
        assert error_dict["error"] == "Test error"
        assert error_dict["error_type"] == "invalid_ticker"
        assert error_dict["ticker"] == "TEST"
        assert error_dict["details"]["reason"] == "test"
