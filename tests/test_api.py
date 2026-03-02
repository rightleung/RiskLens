"""
API Integration Tests
=====================
Tests for FastAPI endpoints using TestClient.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os
import types

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import api
from data_fetcher import DataFetchError, DataFetchErrorType

app = api.app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200(self, client):
        """Health endpoint should return 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        """Health endpoint should return JSON."""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"

    def test_health_response_structure(self, client):
        """Health endpoint should return expected fields."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "timestamp" in data


class TestAssessEndpoint:
    """Tests for /api/v1/assess endpoint."""

    def test_assess_invalid_ticker(self, client, monkeypatch):
        """Test invalid ticker returns 404 when all fail."""
        def _raise_invalid(*_args, **_kwargs):
            raise DataFetchError(
                "Invalid ticker",
                error_type=DataFetchErrorType.INVALID_TICKER,
                ticker="INVALID_TICKER_XYZ",
            )

        monkeypatch.setattr(api, "_analyze_single_ticker", _raise_invalid)
        monkeypatch.setattr(api, "_search_tickers", lambda *_args, **_kwargs: [])

        response = client.post(
            "/api/v1/assess",
            json={
                "tickers": ["INVALID_TICKER_XYZ"],
                "fiscal_year": 2024,
                "data_source": "yfinance"
            }
        )
        # Returns 404 when no results available
        assert response.status_code == 404
        data = response.json()
        # FastAPI wraps HTTPException in "detail" key
        detail = data.get("detail", data)
        assert "errors" in detail
        assert "suggestions" in detail

    def test_assess_valid_ticker(self, client, monkeypatch):
        """Test valid ticker returns analysis results."""
        monkeypatch.setattr(
            api,
            "_analyze_single_ticker",
            lambda ticker, fiscal_year, data_source: {
                "ticker": ticker,
                "company_name": "Apple Inc.",
                "company_name_localized": {"en": "Apple Inc."},
                "currency": "USD",
                "history": [
                    {
                        "fiscal_year": "FY24",
                        "is_quarterly": False,
                        "assessment": {
                            "risk_score": 2.5,
                            "overall_rating": "Safe (S)",
                            "implied_rating": "A",
                            "strengths": ["Strong interest coverage"],
                            "weaknesses": [],
                        },
                        "ratios": {},
                        "raw_metrics": {},
                        "statements": {},
                    }
                ],
            },
        )

        response = client.post(
            "/api/v1/assess",
            json={
                "tickers": ["AAPL"],
                "fiscal_year": 2024,
                "data_source": "yfinance"
            }
        )
        assert response.status_code == 200
        data = response.json()
        # Should have results structure
        assert "results" in data
        assert "count" in data

    def test_assess_missing_tickers(self, client):
        """Test missing tickers field returns validation error."""
        response = client.post(
            "/api/v1/assess",
            json={"fiscal_year": 2024, "data_source": "yfinance"}
        )
        assert response.status_code == 422  # Validation error

    def test_assess_empty_tickers(self, client):
        """Test empty tickers list."""
        response = client.post(
            "/api/v1/assess",
            json={"tickers": [], "fiscal_year": 2024, "data_source": "yfinance"}
        )
        # Should handle gracefully
        assert response.status_code in [200, 422]

    def test_assess_whitespace_tickers(self, client):
        """Whitespace-only tickers should be rejected."""
        response = client.post(
            "/api/v1/assess",
            json={"tickers": ["   ", ""], "fiscal_year": 2024, "data_source": "yfinance"}
        )
        assert response.status_code == 422

    def test_assess_ticker_count_limit(self, client):
        """Ticker list over max length should fail validation."""
        response = client.post(
            "/api/v1/assess",
            json={
                "tickers": [f"T{i}" for i in range(51)],
                "fiscal_year": 2024,
                "data_source": "yfinance",
            }
        )
        assert response.status_code == 422

    def test_assess_fiscal_year_out_of_range(self, client):
        """fiscal_year should respect model bounds."""
        response = client.post(
            "/api/v1/assess",
            json={"tickers": ["AAPL"], "fiscal_year": 1800, "data_source": "yfinance"}
        )
        assert response.status_code == 422


class TestSymbolSearch:
    """Tests for /api/v1/symbols/search and suggestion filtering."""

    def test_symbol_search_endpoint_returns_results(self, client, monkeypatch):
        monkeypatch.setattr(
            api,
            "_search_tickers",
            lambda q, limit=5, strict=False: [{"symbol": "MSFT", "name": "Microsoft Corporation"}],
        )
        response = client.get("/api/v1/symbols/search", params={"q": "micro", "limit": 20})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["symbol"] == "MSFT"

    def test_search_tickers_filters_non_equity_and_duplicates(self, monkeypatch):
        class FakeSearch:
            def __init__(self, _query):
                self.quotes = [
                    {"symbol": "MSFLX", "shortname": "Morgan Stanley Institutional", "quoteType": "MUTUALFUND"},
                    {"symbol": "MSFT", "shortname": "Microsoft Corporation", "quoteType": "EQUITY"},
                    {"symbol": "msft", "shortname": "Microsoft Duplicate", "quoteType": "EQUITY"},
                    {"symbol": "MSFLX", "shortname": "Same As Query", "quoteType": "EQUITY"},
                ]

        monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(Search=FakeSearch))
        suggestions = api._search_tickers("MSFLX", limit=5)
        assert suggestions == [{"symbol": "MSFT", "name": "Microsoft Corporation"}]


class TestCovenantEndpoint:
    """Tests for /api/v1/covenants/check endpoint."""

    def test_covenant_invalid_ticker(self, client, monkeypatch):
        """Test invalid ticker returns 404."""
        def _raise_invalid(*_args, **_kwargs):
            raise DataFetchError(
                "Ticker not found",
                error_type=DataFetchErrorType.INVALID_TICKER,
                ticker="INVALID_TICKER_XYZ",
            )

        monkeypatch.setattr(api.fetcher, "get_financial_data", _raise_invalid)

        response = client.post(
            "/api/v1/covenants/check",
            json={
                "ticker": "INVALID_TICKER_XYZ",
                "fiscal_year": 2024,
                "data_source": "yfinance",
                "covenants": {
                    "min_current_ratio": 1.5,
                    "max_debt_to_equity": 2.0
                }
            }
        )
        assert response.status_code == 404

    def test_covenant_handles_empty_fetch_result(self, client, monkeypatch):
        """Empty fetch result should return 404 instead of 500."""
        monkeypatch.setattr(api.fetcher, "get_financial_data", lambda *_args, **_kwargs: None)

        response = client.post(
            "/api/v1/covenants/check",
            json={
                "ticker": "600519",
                "fiscal_year": 2024,
                "data_source": "akshare",
                "covenants": {"min_current_ratio": 1.2}
            }
        )
        assert response.status_code == 404
        detail = response.json().get("detail", {})
        assert detail.get("error_type") == "no_data_available"

    def test_covenant_missing_ticker(self, client):
        """Test missing ticker returns validation error."""
        response = client.post(
            "/api/v1/covenants/check",
            json={
                "fiscal_year": 2024,
                "data_source": "yfinance",
                "covenants": {"min_current_ratio": 1.5}
            }
        )
        assert response.status_code == 422

    def test_covenant_missing_covenants(self, client):
        """Test missing covenants returns validation error."""
        response = client.post(
            "/api/v1/covenants/check",
            json={
                "ticker": "AAPL",
                "fiscal_year": 2024,
                "data_source": "yfinance"
            }
        )
        assert response.status_code == 422

    def test_covenant_fiscal_year_out_of_range(self, client):
        """Covenant request fiscal_year should respect model bounds."""
        response = client.post(
            "/api/v1/covenants/check",
            json={
                "ticker": "AAPL",
                "fiscal_year": 2201,
                "data_source": "yfinance",
                "covenants": {"min_current_ratio": 1.5}
            }
        )
        assert response.status_code == 422


class TestUIEndpoints:
    """Tests for UI endpoints."""

    def test_root_returns_html(self, client):
        """Root endpoint should return HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_catch_all_returns_html(self, client):
        """Catch-all path returns HTML (SPA fallback)."""
        response = client.get("/nonexistent-page")
        # Returns 200 for SPA fallback
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
