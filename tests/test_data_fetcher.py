"""
Test suite for data_fetcher module — helpers, error classification, edge cases.

Run with: pytest tests/test_data_fetcher.py -v
"""

import pytest
import sys
import time
import types
import threading
import pandas as pd

import data_fetcher
from data_fetcher import (
    FinancialDataFetcher,
    DataFetchError,
    DataFetchErrorType,
    _standardize_name,
    _extract_single_column,
    _normalize_ticker,
)


def _build_fake_statement(rows: dict) -> pd.DataFrame:
    return pd.DataFrame({pd.Timestamp("2024-12-31"): rows})


class _FakeTicker:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.info = {"longName": "Fake Corp", "marketCap": 123456789}
        self.income_stmt = _build_fake_statement({
            "Total Revenue": 1000.0, "Cost Of Revenue": 400.0, "Gross Profit": 600.0,
            "Operating Income": 250.0, "Net Income": 200.0, "Interest Expense": 25.0,
            "EBITDA": 300.0,
        })
        self.balance_sheet = _build_fake_statement({
            "Total Assets": 2000.0, "Total Liabilities": 900.0,
            "Stockholders Equity": 1100.0, "Current Assets": 800.0,
            "Current Liabilities": 350.0, "Cash": 200.0, "Retained Earnings": 500.0,
            "Accounts Receivable": 150.0, "Inventory": 120.0, "Accounts Payable": 130.0,
            "Total Debt": 600.0,
        })
        self.cashflow = _build_fake_statement({
            "Operating Cash Flow": 220.0, "Free Cash Flow": 180.0,
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
            "Total Revenue": 1000.0, "Operating Income": 250.0, "Net Income": 200.0,
        })
        self.balance_sheet = pd.DataFrame()
        self.cashflow = _build_fake_statement({
            "Operating Cash Flow": 220.0, "Free Cash Flow": 180.0,
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


# ── _standardize_name ───────────────────────────────────────────────────────

class TestStandardizeName:
    def test_known_yfinance_fields(self):
        assert _standardize_name("Total Assets") == "total_assets"
        assert _standardize_name("Current Liabilities") == "total_current_liabilities"
        assert _standardize_name("Stockholders Equity") == "total_equity"
        assert _standardize_name("Operating Cash Flow") == "operating_cf"
        assert _standardize_name("Total Revenue") == "revenue"
        assert _standardize_name("Accounts Receivable") == "accounts_receivable"
        assert _standardize_name("Retained Earnings") == "retained_earnings"

    def test_camel_case_variants(self):
        assert _standardize_name("TotalAssets") == "total_assets"
        assert _standardize_name("OperatingIncome") == "operating_income"

    def test_unknown_fallback(self):
        result = _standardize_name("Some Unknown Field")
        assert result == "some_unknown_field"


# ── _extract_single_column ───────────────────────────────────────────────────

class TestExtractSingleColumn:
    def test_extracts_single_column_standardizes_index(self):
        df = pd.DataFrame({
            pd.Timestamp("2024-12-31"): {"Total Assets": 1000.0, "Total Revenue": 500.0},
            pd.Timestamp("2023-12-31"): {"Total Assets": 900.0, "Total Revenue": 450.0},
        })
        result = _extract_single_column(df, 0)
        assert result.loc["total_assets", "Value"] == 1000.0
        assert result.loc["revenue", "Value"] == 500.0

    def test_filters_nan_values(self):
        import numpy as np
        df = pd.DataFrame({
            pd.Timestamp("2024-12-31"): {"Total Assets": np.nan, "Total Revenue": 500.0},
        })
        result = _extract_single_column(df, 0)
        assert "total_assets" not in result.index
        assert result.loc["revenue", "Value"] == 500.0

    def test_filters_non_numeric_values(self):
        df = pd.DataFrame({
            pd.Timestamp("2024-12-31"): {"Total Assets": "N/A", "Total Revenue": 500.0},
        })
        result = _extract_single_column(df, 0)
        assert "total_assets" not in result.index
        assert result.loc["revenue", "Value"] == 500.0

    def test_first_valid_wins_duplicate_keys(self):
        df = pd.DataFrame({
            pd.Timestamp("2024-12-31"): {
                "Total Assets": 1000.0, "TotalAssets": 900.0, "Total Revenue": 500.0,
            },
        })
        result = _extract_single_column(df, 0)
        assert result.loc["total_assets", "Value"] == 1000.0

    def test_empty_dataframe_returns_empty(self):
        assert _extract_single_column(pd.DataFrame(), 0).empty
        assert _extract_single_column(None, 0).empty

    def test_out_of_bounds_col_idx_returns_empty(self):
        df = pd.DataFrame({pd.Timestamp("2024-12-31"): {"Total Assets": 1000.0}})
        assert _extract_single_column(df, 5).empty


# ── _normalize_ticker ────────────────────────────────────────────────────────

class TestNormalizeTicker:
    def test_brk_b_to_hyphen(self):
        assert _normalize_ticker("BRK.B") == "BRK-B"

    def test_bf_a_to_hyphen(self):
        assert _normalize_ticker("BF.A") == "BF-A"

    def test_trim_and_uppercase(self):
        assert _normalize_ticker("  aapl  ") == "AAPL"

    def test_no_change_for_normal_ticker(self):
        assert _normalize_ticker("AAPL") == "AAPL"


# ── FinancialDataFetcher.get_financial_data() ─────────────────────────────────

class TestFinancialDataFetcher:
    def test_invalid_ticker_raises_exception(self, monkeypatch):
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(data_fetcher.yf, "Ticker",
                            lambda _ticker: (_ for _ in ()).throw(Exception("404 not found")))
        with pytest.raises(DataFetchError) as exc_info:
            fetcher.get_financial_data("INVALID_TICKER_XYZ", "yfinance")
        # "404" and "not found" in msg → INVALID_TICKER
        assert exc_info.value.error_type == DataFetchErrorType.INVALID_TICKER
        assert exc_info.value.ticker == "INVALID_TICKER_XYZ"

    def test_empty_ticker_raises_exception(self):
        fetcher = FinancialDataFetcher()
        with pytest.raises(DataFetchError):
            fetcher.get_financial_data("", "yfinance")

    def test_valid_ticker_returns_data(self, monkeypatch):
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(data_fetcher.yf, "Ticker", _FakeTicker)
        result = fetcher.get_financial_data("AAPL", "yfinance")
        assert result is not None
        assert result["ticker"] == "AAPL"
        assert result["company_name"] == "Fake Corp"
        assert len(result["history"]) > 0

    def test_result_structure_and_specific_values(self, monkeypatch):
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(data_fetcher.yf, "Ticker", _FakeTicker)
        result = fetcher.get_financial_data("AAPL", "yfinance")
        assert "ticker" in result
        assert "company_name" in result
        assert "market_cap" in result
        assert "history" in result

        period = result["history"][0]
        assert "year_label" in period
        assert "is_quarterly" in period
        assert "income" in period
        assert "balance" in period
        assert "cash" in period

        # Specific standardized values
        income = period["income"]
        assert income.loc["revenue", "Value"] == 1000.0
        assert income.loc["operating_income", "Value"] == 250.0
        balance = period["balance"]
        assert balance.loc["total_assets", "Value"] == 2000.0
        assert balance.loc["total_liabilities", "Value"] == 900.0
        cash = period["cash"]
        assert cash.loc["operating_cf", "Value"] == 220.0
        assert cash.loc["free_cf", "Value"] == 180.0

    def test_cache_hit_does_not_reinstantiate_ticker(self, monkeypatch):
        call_count = 0
        _orig_ticker = data_fetcher.yf.Ticker

        def _counting_ticker(symbol):
            nonlocal call_count
            call_count += 1
            return _FakeTicker(symbol)

        monkeypatch.setattr(data_fetcher.yf, "Ticker", _counting_ticker)
        fetcher = FinancialDataFetcher()
        result1 = fetcher.get_financial_data("AAPL", "yfinance")
        assert call_count == 1
        result2 = fetcher.get_financial_data("AAPL", "yfinance")
        assert call_count == 1  # cache hit, no new Ticker
        assert result1 is result2

    def test_invalid_data_source_falls_back_to_auto(self, monkeypatch):
        """Invalid data_source should fallback to 'auto' internally."""
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(data_fetcher.yf, "Ticker", _FakeTicker)
        result = fetcher.get_financial_data("AAPL", "garbage_source")
        assert result is not None
        assert len(result["history"]) > 0

    def test_rate_limit_error_classification(self, monkeypatch):
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(
            data_fetcher.yf, "Ticker",
            lambda _ticker: (_ for _ in ()).throw(Exception("429 Too Many Requests")),
        )
        with pytest.raises(DataFetchError) as exc_info:
            fetcher.get_financial_data("AAPL", "yfinance")
        assert exc_info.value.error_type == DataFetchErrorType.RATE_LIMIT

    def test_rate_limit_text_classification(self, monkeypatch):
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(
            data_fetcher.yf, "Ticker",
            lambda _ticker: (_ for _ in ()).throw(Exception("rate limit exceeded")),
        )
        with pytest.raises(DataFetchError) as exc_info:
            fetcher.get_financial_data("AAPL", "yfinance")
        assert exc_info.value.error_type == DataFetchErrorType.RATE_LIMIT

    def test_network_connection_error_classification(self, monkeypatch):
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(
            data_fetcher.yf, "Ticker",
            lambda _ticker: (_ for _ in ()).throw(Exception("connection refused")),
        )
        with pytest.raises(DataFetchError) as exc_info:
            fetcher.get_financial_data("AAPL", "yfinance")
        assert exc_info.value.error_type == DataFetchErrorType.NETWORK_ERROR

    def test_network_timeout_error_classification(self, monkeypatch):
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(
            data_fetcher.yf, "Ticker",
            lambda _ticker: (_ for _ in ()).throw(Exception("timeout occurred")),
        )
        with pytest.raises(DataFetchError) as exc_info:
            fetcher.get_financial_data("AAPL", "yfinance")
        assert exc_info.value.error_type == DataFetchErrorType.NETWORK_ERROR

    def test_network_proxy_error_classification(self, monkeypatch):
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(
            data_fetcher.yf, "Ticker",
            lambda _ticker: (_ for _ in ()).throw(Exception("proxy error")),
        )
        with pytest.raises(DataFetchError) as exc_info:
            fetcher.get_financial_data("AAPL", "yfinance")
        assert exc_info.value.error_type == DataFetchErrorType.NETWORK_ERROR

    def test_unknown_error_classification(self, monkeypatch):
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(
            data_fetcher.yf, "Ticker",
            lambda _ticker: (_ for _ in ()).throw(Exception("something unexpected happened")),
        )
        with pytest.raises(DataFetchError) as exc_info:
            fetcher.get_financial_data("AAPL", "yfinance")
        assert exc_info.value.error_type == DataFetchErrorType.UNKNOWN

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
        fetcher = FinancialDataFetcher()
        monkeypatch.setattr(data_fetcher.yf, "Ticker", _FakeTicker)
        result = fetcher.get_financial_data("600519.SS", "yfinance")
        assert result is not None
        # Suffix is stripped then re-added: 600519 → 600519.SS
        assert result["ticker"] == "600519.SS"
        assert "history" in result
        assert len(result["history"]) > 0

    def test_latest_quarter_keeps_prior_year_same_quarter(self, monkeypatch):
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

    # ── AKShare tests ──────────────────────────────────────────────────────

    def test_fetch_a_share_akshare_builds_annual_and_quarterly_history(self, monkeypatch):
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

    def test_akshare_statement_exception_surfaces_network_error(self, monkeypatch):
        class FakeAk:
            @staticmethod
            def stock_individual_info_em(symbol):
                return pd.DataFrame({"item": ["股票简称"], "value": ["测试"]})

            @staticmethod
            def stock_profile_cninfo(symbol):
                return pd.DataFrame()

            @staticmethod
            def stock_zygc_em(symbol):
                return pd.DataFrame()

            @staticmethod
            def stock_financial_report_sina(stock, symbol):
                raise ConnectionError("AKShare API unavailable")

        monkeypatch.setitem(sys.modules, "akshare", types.SimpleNamespace(
            stock_individual_info_em=FakeAk.stock_individual_info_em,
            stock_profile_cninfo=FakeAk.stock_profile_cninfo,
            stock_zygc_em=FakeAk.stock_zygc_em,
            stock_financial_report_sina=FakeAk.stock_financial_report_sina,
        ))
        monkeypatch.setattr(data_fetcher, "akshare_get_data", None)

        with pytest.raises(DataFetchError) as exc_info:
            data_fetcher._fetch_a_share_akshare("600519")
        assert exc_info.value.error_type == DataFetchErrorType.NETWORK_ERROR
        assert "AKShare" in exc_info.value.message
        assert exc_info.value.ticker == "600519"

    def test_akshare_network_error_falls_back_to_yfinance_in_auto_mode(self, monkeypatch):
        import logging

        def _raise_network_error(ticker, **kwargs):
            raise DataFetchError(
                f"AKShare API error: {ticker}",
                error_type=DataFetchErrorType.NETWORK_ERROR,
                ticker=ticker,
                details={"source": "akshare"},
            )

        monkeypatch.setattr(data_fetcher, "_fetch_a_share_akshare", _raise_network_error)
        monkeypatch.setattr(data_fetcher.yf, "Ticker", _FakeTicker)

        fetcher = FinancialDataFetcher()
        with monkeypatch.context() as m:
            m.setattr(logging, "warning", lambda *a, **kw: None)
            m.setattr(logging, "info", lambda *a, **kw: None)
            result = fetcher.get_financial_data("600519", "auto")
        assert result is not None
        assert len(result["history"]) > 0
        assert result["company_name"] == "Fake Corp"

    def test_akshare_network_error_surfaces_in_explicit_akshare_mode(self, monkeypatch):
        def _raise_network_error(ticker, **kwargs):
            raise DataFetchError(
                f"AKShare API error: {ticker}",
                error_type=DataFetchErrorType.NETWORK_ERROR,
                ticker=ticker,
                details={"source": "akshare"},
            )

        monkeypatch.setattr(data_fetcher, "_fetch_a_share_akshare", _raise_network_error)
        fetcher = FinancialDataFetcher()
        with pytest.raises(DataFetchError) as exc_info:
            fetcher.get_financial_data("600519", "akshare")
        assert exc_info.value.error_type == DataFetchErrorType.NETWORK_ERROR

    def test_exception_to_dict(self):
        error = DataFetchError(
            message="Test error",
            error_type=DataFetchErrorType.INVALID_TICKER,
            ticker="TEST",
            details={"reason": "test"},
        )
        error_dict = error.to_dict()
        assert error_dict["error"] == "Test error"
        assert error_dict["error_type"] == "invalid_ticker"
        assert error_dict["ticker"] == "TEST"
        assert error_dict["details"]["reason"] == "test"


# ── Cache Maxsize Eviction ────────────────────────────────────────────────────

def test_cache_evicts_when_maxsize_exceeded():
    from data_fetcher import SimpleCache
    cache = SimpleCache(default_ttl=600, maxsize=3)
    for i in range(5):
        cache.set(f"key_{i}", f"value_{i}")
    # Only the last 3 entries should remain (LRU eviction)
    assert cache.get("key_0") is None
    assert cache.get("key_1") is None
    assert cache.get("key_2") == "value_2"
    assert cache.get("key_3") == "value_3"
    assert cache.get("key_4") == "value_4"


def test_cache_lru_updates_on_get():
    from data_fetcher import SimpleCache
    cache = SimpleCache(default_ttl=600, maxsize=3)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    # Access "a" to make it most recently used
    assert cache.get("a") == 1
    # Add new entry — "b" should be evicted (oldest), not "a"
    cache.set("d", 4)
    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("c") == 3
    assert cache.get("d") == 4


# ── Single-Flight Coalescing ──────────────────────────────────────────────────

def test_single_flight_coalesces_concurrent_misses(monkeypatch):
    """Concurrent cache misses for the same key must trigger exactly one upstream call."""
    import threading
    from data_fetcher import _in_flight, _in_flight_lock, _data_cache

    _data_cache.clear()
    with _in_flight_lock:
        _in_flight.clear()

    ticker_call_count = [0]
    fetch_started = threading.Event()

    class _CountingTicker:
        def __init__(self, symbol):
            ticker_call_count[0] += 1
            fetch_started.set()  # signal that the first fetch has begun
            self.symbol = symbol
            self.info = {"longName": "Concurrent Corp", "marketCap": 100}
            self.income_stmt = pd.DataFrame({pd.Timestamp("2024-12-31"): {"Total Revenue": 1000.0}})
            self.balance_sheet = pd.DataFrame({pd.Timestamp("2024-12-31"): {"Total Assets": 2000.0, "Total Liabilities": 900.0}})
            self.cashflow = pd.DataFrame({pd.Timestamp("2024-12-31"): {"Operating Cash Flow": 200.0}})
            self.quarterly_income_stmt = pd.DataFrame()
            self.quarterly_balance_sheet = pd.DataFrame()
            self.quarterly_cashflow = pd.DataFrame()

    monkeypatch.setattr(data_fetcher.yf, "Ticker", _CountingTicker)

    results = []

    def _fetch_and_record(ticker):
        try:
            result = FinancialDataFetcher.get_financial_data(ticker, "yfinance")
            results.append(("success", result))
        except Exception as exc:
            results.append(("error", exc))

    t1 = threading.Thread(target=_fetch_and_record, args=("TEST",))
    t2 = threading.Thread(target=_fetch_and_record, args=("TEST",))

    t1.start()
    # Wait for the first thread to actually start the upstream fetch
    # before starting the second thread, ensuring a cache miss for both
    fetch_started.wait(timeout=5)
    t2.start()

    t1.join(timeout=10)
    t2.join(timeout=10)

    assert len(results) == 2
    assert results[0][0] == "success"
    assert results[1][0] == "success"
    # Single-flight: yf.Ticker must be called exactly once
    assert ticker_call_count[0] == 1, (
        f"Expected 1 upstream call with single-flight, got {ticker_call_count[0]}"
    )


def test_single_flight_cleanup_on_failure(monkeypatch):
    """In-flight tracking must be cleaned up even when fetch fails."""
    import threading
    from data_fetcher import _in_flight, _in_flight_lock, _data_cache

    _data_cache.clear()
    with _in_flight_lock:
        _in_flight.clear()

    class _ErrorTicker:
        def __init__(self, symbol):
            raise RuntimeError("Simulated upstream failure")

    monkeypatch.setattr(data_fetcher.yf, "Ticker", _ErrorTicker)

    try:
        FinancialDataFetcher.get_financial_data("FAIL", "yfinance")
    except DataFetchError:
        pass

    # After fetch failure, in_flight should be clean
    with _in_flight_lock:
        assert "FAIL:yfinance" not in _in_flight


# ── run_yfinance_call wrapper ───────────────────────────────────────────────

def test_run_yfinance_call_wraps_upstream_fetch(monkeypatch):
    """All yf.Ticker calls in get_financial_data must go through a proxy wrapper."""
    wrapper_count = [0]

    def _counting_wrapper(fn):
        wrapper_count[0] += 1
        return fn()

    monkeypatch.setattr(data_fetcher, "run_yfinance_call_with_proxy_retry", _counting_wrapper)
    monkeypatch.setattr(data_fetcher.yf, "Ticker", _FakeTicker)

    result = FinancialDataFetcher.get_financial_data("AAPL", "yfinance")
    assert result is not None
    assert wrapper_count[0] >= 1, (
        f"yfinance Ticker calls must go through run_yfinance_call_with_proxy_retry, got {wrapper_count[0]}"
    )


def test_run_yfinance_call_wraps_akshare_yfinance_supplement(monkeypatch):
    """AKShare's yfinance supplement path must also use a proxy wrapper."""
    wrapper_count = [0]

    def _counting_wrapper(fn):
        wrapper_count[0] += 1
        return fn()

    monkeypatch.setattr(data_fetcher, "run_yfinance_call_with_proxy_retry", _counting_wrapper)

    # Build a minimal AKShare mock that triggers the yfinance supplement path
    class FakeAk:
        @staticmethod
        def stock_individual_info_em(symbol):
            return pd.DataFrame({"item": ["股票简称"], "value": ["测试"]})
        @staticmethod
        def stock_profile_cninfo(symbol):
            return pd.DataFrame()
        @staticmethod
        def stock_zygc_em(symbol):
            return pd.DataFrame()
        @staticmethod
        def stock_financial_report_sina(stock, symbol):
            if symbol == "利润表":
                return pd.DataFrame({"报告日": ["2024-12-31"], "营业总收入": [1000.0], "营业利润": [200.0], "净利润": [150.0]})
            if symbol == "资产负债表":
                return pd.DataFrame({"报告日": ["2024-12-31"], "资产总计": [2000.0], "负债合计": [800.0]})
            if symbol == "现金流量表":
                return pd.DataFrame({"报告日": ["2024-12-31"], "经营活动产生的现金流量净额": [300.0]})
            raise AssertionError(f"Unexpected: {symbol}")

    monkeypatch.setitem(sys.modules, "akshare", types.SimpleNamespace(
        stock_individual_info_em=FakeAk.stock_individual_info_em,
        stock_profile_cninfo=FakeAk.stock_profile_cninfo,
        stock_zygc_em=FakeAk.stock_zygc_em,
        stock_financial_report_sina=FakeAk.stock_financial_report_sina,
    ))
    monkeypatch.setattr(data_fetcher, "akshare_get_data", None)

    class FakeYFTicker:
        def __init__(self, symbol):
            assert symbol == "600519.SS"
            self.info = {"marketCap": 100_000}
            self.income_stmt = pd.DataFrame()

    monkeypatch.setattr(data_fetcher.yf, "Ticker", FakeYFTicker)

    result = data_fetcher._fetch_a_share_akshare("600519")
    assert result is not None
    assert wrapper_count[0] >= 1, (
        f"AKShare yfinance supplement must go through run_yfinance_call, got {wrapper_count[0]}"
    )


# ── Negative cache + error type coercion ─────────────────────────────────────

def test_negative_cache_hit_preserves_error_type_enum(monkeypatch):
    """Second request for a failed ticker hits _error_cache with correct enum type."""
    call_count = [0]

    class _ErrorTicker:
        def __init__(self, symbol):
            call_count[0] += 1
            raise RuntimeError("429 rate limit")

    monkeypatch.setattr(data_fetcher.yf, "Ticker", _ErrorTicker)

    with pytest.raises(DataFetchError) as first:
        FinancialDataFetcher.get_financial_data("FAIL", "yfinance")
    assert first.value.error_type is DataFetchErrorType.RATE_LIMIT
    assert call_count[0] == 1

    with pytest.raises(DataFetchError) as second:
        FinancialDataFetcher.get_financial_data("FAIL", "yfinance")
    assert second.value.error_type is DataFetchErrorType.RATE_LIMIT
    # Second attempt must not call yf.Ticker
    assert call_count[0] == 1


def test_negative_cache_hit_error_type_is_enum_not_str(monkeypatch):
    """Negative cache hit must raise DataFetchError with DataFetchErrorType enum."""
    from data_fetcher import _error_cache, _coerce_error_type

    # Pre-seed the cache with a string error_type (mimics the old serialised value)
    _error_cache.set("TEST:yfinance:dashboard:ps", {
        "message": "Cached failure",
        "error_type": "rate_limit",
        "ticker": "TEST",
        "details": {},
    }, ttl=300)

    with pytest.raises(DataFetchError) as exc_info:
        FinancialDataFetcher.get_financial_data("TEST", "yfinance")
    exc = exc_info.value
    assert isinstance(exc.error_type, DataFetchErrorType)
    assert exc.error_type is DataFetchErrorType.RATE_LIMIT
    # Accessing .value must not raise AttributeError
    assert exc.error_type.value == "rate_limit"


# ── Proxy mode tests ─────────────────────────────────────────────────────────

def test_run_yfinance_call_never_mode_does_not_clear_proxy(monkeypatch):
    """yfinance_clear_proxy_mode='never' never acquires the lock or clears env."""
    counts = {"cleared": 0}

    def _counting_cleared(fn):
        counts["cleared"] += 1
        return fn()

    monkeypatch.setattr(data_fetcher.settings, "yfinance_clear_proxy_mode", "never")
    monkeypatch.setattr(data_fetcher, "_run_with_cleared_proxy", _counting_cleared)

    assert data_fetcher.run_yfinance_call(lambda: "ok", clear_proxy=True) == "ok"
    assert counts["cleared"] == 0


def test_run_yfinance_call_always_mode_clears_proxy(monkeypatch):
    """yfinance_clear_proxy_mode='always' always holds the lock and clears proxy."""
    counts = {"cleared": 0}

    def _counting_cleared(fn):
        counts["cleared"] += 1
        return fn()

    monkeypatch.setattr(data_fetcher.settings, "yfinance_clear_proxy_mode", "always")
    monkeypatch.setattr(data_fetcher, "_run_with_cleared_proxy", _counting_cleared)

    assert data_fetcher.run_yfinance_call(lambda: "ok", clear_proxy=True) == "ok"
    assert counts["cleared"] == 1


def test_run_yfinance_call_retry_only_holds_lock_even_without_clear_proxy(monkeypatch):
    """retry_only + clear_proxy=False: holds proxy lock, no proxy clearing."""
    locked_count = {"count": 0}

    def _counting_lock(fn):
        locked_count["count"] += 1
        return fn()

    monkeypatch.setattr(data_fetcher.settings, "yfinance_clear_proxy_mode", "retry_only")
    monkeypatch.setattr(data_fetcher, "_run_with_proxy_lock", _counting_lock)

    assert data_fetcher.run_yfinance_call(lambda: "ok", clear_proxy=False) == "ok"
    assert locked_count["count"] == 1, (
        f"retry_only+clear_proxy=False must hold proxy lock, got {locked_count['count']}"
    )


def test_proxy_retry_only_retries_on_proxy_error(monkeypatch):
    """retry_only: first call fails with proxy, second (cleared) succeeds."""
    call_count = [0]

    def _sometimes_fails():
        call_count[0] += 1
        if call_count[0] == 1:
            raise OSError("proxy tunnel failed")
        return "recovered"

    monkeypatch.setattr(data_fetcher.settings, "yfinance_clear_proxy_mode", "retry_only")
    result = data_fetcher.run_yfinance_call_with_proxy_retry(_sometimes_fails)
    assert result == "recovered"
    assert call_count[0] == 2


def test_proxy_retry_only_does_not_retry_non_proxy_error(monkeypatch):
    """retry_only: non-proxy errors are not retried."""
    monkeypatch.setattr(data_fetcher.settings, "yfinance_clear_proxy_mode", "retry_only")

    with pytest.raises(ValueError, match="something else"):
        data_fetcher.run_yfinance_call_with_proxy_retry(lambda: (_ for _ in ()).throw(ValueError("something else")))


# ── Single-flight failure reuse ──────────────────────────────────────────────

def test_single_flight_reuses_failure_for_waiters(monkeypatch):
    """When leader fails, waiting threads get the same exception via _InFlightEntry."""
    call_count = [0]
    leader_ready = threading.Event()
    leader_go = threading.Event()

    class _SlowErrorTicker:
        def __init__(self, symbol):
            call_count[0] += 1
            leader_ready.set()   # signal: I'm the leader, waiter can proceed
            leader_go.wait(timeout=5)  # block so waiter reaches in-flight entry
            raise RuntimeError("rate limit exceeded")

    monkeypatch.setattr(data_fetcher.yf, "Ticker", _SlowErrorTicker)

    errors: list = []

    def _fetch():
        try:
            FinancialDataFetcher.get_financial_data("FAIL2", "yfinance")
        except DataFetchError as exc:
            errors.append(exc.error_type)

    t1 = threading.Thread(target=_fetch)
    t2 = threading.Thread(target=_fetch)
    t1.start()
    leader_ready.wait(timeout=5)  # wait for leader to enter Ticker.__init__
    t2.start()
    leader_go.set()  # release leader to raise error
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert call_count[0] == 1, f"Expected 1 upstream call, got {call_count[0]}"
    assert errors == [DataFetchErrorType.RATE_LIMIT, DataFetchErrorType.RATE_LIMIT]


def test_single_flight_waiter_timeout_raises_network_error(monkeypatch):
    """Waiter times out when leader blocks beyond single_flight_wait_timeout_seconds."""
    leader_blocking = threading.Event()
    leader_done = threading.Event()

    class _BlockingTicker:
        def __init__(self, symbol):
            leader_blocking.set()  # signal: waiter can proceed
            # block indefinitely — waiter should time out
            while not leader_done.is_set():
                time.sleep(0.05)
            # Provide minimal attributes so the leader thread doesn't crash
            # after the test releases it (avoids thread exception warnings).
            self.info = {}
            self.income_stmt = pd.DataFrame()
            self.balance_sheet = pd.DataFrame()
            self.cashflow = pd.DataFrame()
            self.quarterly_income_stmt = pd.DataFrame()
            self.quarterly_balance_sheet = pd.DataFrame()
            self.quarterly_cashflow = pd.DataFrame()

    monkeypatch.setattr(data_fetcher.settings, "single_flight_wait_timeout_seconds", 0.1)
    monkeypatch.setattr(data_fetcher.yf, "Ticker", _BlockingTicker)

    waiter_error: list[DataFetchError] = []

    def _waiter():
        try:
            FinancialDataFetcher.get_financial_data("SLOW_LEADER", "yfinance")
        except DataFetchError as exc:
            waiter_error.append(exc)

    def _leader():
        try:
            FinancialDataFetcher.get_financial_data("SLOW_LEADER", "yfinance")
        except DataFetchError:
            pass  # leader fails after being unblocked — expected

    t1 = threading.Thread(target=_leader)
    t2 = threading.Thread(target=_waiter)
    t1.start()
    # Wait for leader to enter Ticker and block
    leader_blocking.wait(timeout=5)
    t2.start()
    t2.join(timeout=10)

    assert len(waiter_error) == 1
    exc = waiter_error[0]
    assert exc.error_type == DataFetchErrorType.NETWORK_ERROR, (
        f"Expected NETWORK_ERROR, got {exc.error_type}"
    )
    assert exc.details.get("reason") == "single_flight_timeout", (
        f"Expected reason=single_flight_timeout, got {exc.details}"
    )
    assert exc.details.get("cache_key") is not None

    # Clean up: release leader
    leader_done.set()
    t1.join(timeout=10)


# ── mode='latest' regression tests ───────────────────────────────────────────

def _stmt(cols, base):
    return pd.DataFrame(
        {
            cols[0]: {
                "Total Revenue": base + 1,
                "Total Assets": base + 2,
                "Total Liabilities Net Minority Interest": base + 3,
                "Stockholders Equity": base + 4,
                "Operating Cash Flow": base + 5,
            }
        }
    )


def test_latest_mode_prefers_newer_quarter_over_annual(monkeypatch):
    """mode='latest' returns the newest quarter when it is newer than annual."""

    class _LatestTicker:
        def __init__(self, symbol):
            self.info = {"longName": "Latest Co", "marketCap": 1000}
            self.income_stmt = _stmt([pd.Timestamp("2024-12-31")], 100.0)
            self.balance_sheet = _stmt([pd.Timestamp("2024-12-31")], 200.0)
            self.cashflow = _stmt([pd.Timestamp("2024-12-31")], 300.0)
            self.quarterly_income_stmt = _stmt([pd.Timestamp("2025-09-30")], 400.0)
            self.quarterly_balance_sheet = _stmt([pd.Timestamp("2025-09-30")], 500.0)
            self.quarterly_cashflow = _stmt([pd.Timestamp("2025-09-30")], 600.0)

    monkeypatch.setattr(data_fetcher.yf, "Ticker", _LatestTicker)

    result = FinancialDataFetcher.get_financial_data("AAPL", "yfinance", mode="latest")

    assert result is not None
    assert len(result["history"]) == 1
    period = result["history"][0]
    assert period["year_label"] == "Q3 '25 (U)"
    assert period["is_quarterly"] is True
    assert period["income"].loc["revenue", "Value"] == 401.0
    assert period["balance"].loc["total_assets", "Value"] == 502.0
    assert period["cash"].loc["operating_cf", "Value"] == 605.0


def test_latest_mode_uses_annual_when_quarter_not_newer(monkeypatch):
    """mode='latest' falls back to annual when quarter is absent or not newer."""

    class _LatestTicker:
        def __init__(self, symbol):
            self.info = {"longName": "Latest Co", "marketCap": 1000}
            self.income_stmt = _stmt([pd.Timestamp("2024-12-31")], 100.0)
            self.balance_sheet = _stmt([pd.Timestamp("2024-12-31")], 200.0)
            self.cashflow = _stmt([pd.Timestamp("2024-12-31")], 300.0)
            self.quarterly_income_stmt = _stmt([pd.Timestamp("2024-09-30")], 400.0)
            self.quarterly_balance_sheet = _stmt([pd.Timestamp("2024-09-30")], 500.0)
            self.quarterly_cashflow = _stmt([pd.Timestamp("2024-09-30")], 600.0)

    monkeypatch.setattr(data_fetcher.yf, "Ticker", _LatestTicker)

    result = FinancialDataFetcher.get_financial_data("AAPL", "yfinance", mode="latest")

    assert result is not None
    assert len(result["history"]) == 1
    period = result["history"][0]
    assert period["year_label"] == "FY24"
    assert period["is_quarterly"] is False
    assert period["income"].loc["revenue", "Value"] == 101.0
    assert period["balance"].loc["total_assets", "Value"] == 202.0
    assert period["cash"].loc["operating_cf", "Value"] == 305.0


# ── Different-ticker cold miss concurrency ────────────────────────────────────

def test_retry_only_serializes_different_ticker_cold_misses_behind_proxy_lock(monkeypatch):
    """Different ticker cold misses must be serialised behind _PROXY_CLEAR_LOCK.

    This is the intended trade-off for P2: correctness over throughput.
    When one request is inside _run_with_proxy_lock/_run_with_cleared_proxy,
    another thread must wait for the lock before calling yfinance, so it
    cannot observe an inconsistent os.environ state.
    """
    entered: list[str] = []
    release_first = threading.Event()
    lock = threading.Lock()

    def _stmt(base):
        return pd.DataFrame(
            {
                pd.Timestamp("2024-12-31"): {
                    "Total Revenue": base + 1,
                    "Total Assets": base + 2,
                    "Total Liabilities Net Minority Interest": base + 3,
                    "Stockholders Equity": base + 4,
                    "Operating Cash Flow": base + 5,
                }
            }
        )

    class _SerialTicker:
        def __init__(self, symbol):
            with lock:
                entered.append(symbol)
            base = 100.0 if symbol == "AAA" else 200.0
            self.info = {"longName": f"{symbol} Co", "marketCap": 1000}
            self.income_stmt = _stmt(base)
            self.balance_sheet = _stmt(base + 1000)
            self.cashflow = _stmt(base + 2000)
            self.quarterly_income_stmt = pd.DataFrame()
            self.quarterly_balance_sheet = pd.DataFrame()
            self.quarterly_cashflow = pd.DataFrame()

    monkeypatch.setattr(data_fetcher.settings, "yfinance_clear_proxy_mode", "retry_only")
    monkeypatch.setattr(data_fetcher.yf, "Ticker", _SerialTicker)

    results: list[tuple[str, str]] = []

    def _fetch(symbol):
        result = FinancialDataFetcher.get_financial_data(symbol, "yfinance")
        results.append((symbol, result["ticker"]))

    t1 = threading.Thread(target=_fetch, args=("AAA",))
    t2 = threading.Thread(target=_fetch, args=("BBB",))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert sorted(symbol for symbol, _ in results) == ["AAA", "BBB"]
    # Both tickers are fetched successfully, but serially (not overlapped).
    # The proxy lock serialises them — this is correct P2 behaviour.
    assert len(entered) == 2, (
        f"Expected both tickers to be fetched, got {len(entered)}"
    )


# ── P4: AKShare date format normalisation ────────────────────────────────────

def test_akshare_date_digits_cross_format_matching(monkeypatch):
    """Production _fetch_a_share_akshare merges cross-format dates into non-empty period frames.

    Income uses compact format ('20250930'), balance/cashflow use dashed format
    ('2025-09-30').  The production _find_row must normalise both via _date_digits
    so the same reporting period gets matched across all three statements.
    """
    import sys as _sys
    import types

    # ── Fake AKShare module ────────────────────────────────────────────────
    _fake_ak = types.SimpleNamespace()

    # stock_individual_info_em returns a minimally valid DataFrame.
    _fake_ak.stock_individual_info_em = lambda symbol: pd.DataFrame(
        {"item": ["股票简称"], "value": ["测试控股"]}
    )

    def _fake_sina(stock, symbol):
        if symbol == "利润表":
            return pd.DataFrame({
                "报告日": ["20250930", "20241231", "20231231"],
                "营业总收入": [100, 200, 150],
                "营业成本": [60, 120, 90],
                "营业利润": [20, 40, 30],
                "利息费用": [2, 3, 2],
            })
        if symbol == "资产负债表":
            return pd.DataFrame({
                "报告日": ["2025-09-30", "2024-12-31", "2023-12-31"],
                "流动资产合计": [500, 400, 350],
                "资产总计": [1000, 900, 800],
                "流动负债合计": [300, 280, 250],
                "负债合计": [500, 480, 450],
                "股东权益合计(含少数股东权益)": [500, 420, 350],
            })
        # 现金流量表
        return pd.DataFrame({
            "报告日": ["2025-09-30", "2024-12-31", "2023-12-31"],
            "经营活动产生的现金流量净额": [50, 45, 40],
            "购建固定资产、无形资产和其他长期资产支付的现金": [10, 8, 9],
            "筹资活动产生的现金流量净额": [5, 4, 3],
        })

    _fake_ak.stock_financial_report_sina = _fake_sina

    # Make 'import akshare as ak' inside _fetch_a_share_akshare resolve to the fake.
    monkeypatch.setitem(_sys.modules, "akshare", _fake_ak)

    from data_fetcher import _fetch_a_share_akshare

    result = _fetch_a_share_akshare("600000", include_profile=False, include_supplement=False)

    assert result is not None
    assert result.get("ticker") == "600000"
    history = result.get("history", [])
    assert len(history) >= 1

    # The quarterly period Q3 '25 (U) should match across all three statements.
    q3_periods = [p for p in history if p.get("year_label") == "Q3 '25 (U)"]
    assert len(q3_periods) == 1, f"Expected one Q3 '25 (U) period, got {[p.get('year_label') for p in history]}"
    period = q3_periods[0]
    assert period["is_quarterly"] is True

    # All three statement DataFrames must be non-empty.
    for stmt_key, expected_loc, expected_val in [
        ("income", "revenue", 100.0),
        ("balance", "total_assets", 1000.0),
        ("cash", "operating_cf", 50.0),
    ]:
        df = period.get(stmt_key)
        assert df is not None and not df.empty, (
            f"{stmt_key} DataFrame must be non-empty for Q3 '25 (U)"
        )
        actual = df.loc[expected_loc, "Value"]
        assert actual == expected_val, (
            f"{stmt_key}[{expected_loc}] expected {expected_val}, got {actual}"
        )


# ── P5: AKShare total_debt derivation with bonds/current-portion only ─────────

def test_akshare_total_debt_derived_when_only_bonds_payable_present():
    """total_debt is derived when only bonds_payable is present (no short/long debt keys at all)."""
    from data_fetcher import _akshare_row_to_df, _SINA_BALANCE_MAP

    row = pd.Series({
        '报告日': '2024-12-31',
        '流动资产合计': 500,
        '资产总计': 1000,
        '流动负债合计': 300,
        '负债合计': 600,
        '股东权益合计(含少数股东权益)': 400,
        '一年内到期的非流动负债': 50,
        '应付债券': 150,
    })

    result = _akshare_row_to_df(row, _SINA_BALANCE_MAP)
    bs_map = dict(zip(result.index, result["Value"]))

    # Only bonds_payable(150) + current_portion_lt_debt(50) are present.
    assert bs_map.get("total_debt") == 200, (
        f"Expected total_debt=200 (50+150), got {bs_map.get('total_debt')}"
    )
    assert bs_map.get("total_assets") == 1000
    # short_term_debt and long_term_debt must not appear since keys were absent.
    assert "short_term_debt" not in bs_map
    assert "long_term_debt" not in bs_map


def test_akshare_total_debt_derived_when_only_current_portion_present():
    """total_debt is derived when only current_portion_lt_debt is present."""
    from data_fetcher import _akshare_row_to_df, _SINA_BALANCE_MAP

    row = pd.Series({
        '报告日': '2024-12-31',
        '流动资产合计': 300,
        '资产总计': 800,
        '流动负债合计': 200,
        '负债合计': 400,
        '股东权益合计(含少数股东权益)': 400,
        '一年内到期的非流动负债': 80,
    })

    result = _akshare_row_to_df(row, _SINA_BALANCE_MAP)
    bs_map = dict(zip(result.index, result["Value"]))

    # Only current_portion_lt_debt(80) is present.
    assert bs_map.get("total_debt") == 80, (
        f"Expected total_debt=80, got {bs_map.get('total_debt')}"
    )
    assert "short_term_debt" not in bs_map
    assert "long_term_debt" not in bs_map
