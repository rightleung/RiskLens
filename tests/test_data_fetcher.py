"""
Test suite for data_fetcher module.

Run with: pytest tests/test_data_fetcher.py -v
"""

import pytest
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

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
