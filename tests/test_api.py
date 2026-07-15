"""
API Integration Tests
=====================
Tests for FastAPI endpoints using TestClient.
"""

import hashlib
import asyncio
import threading
import io
import zipfile
import pytest
from fastapi.testclient import TestClient
import sys
import types
from unittest.mock import AsyncMock
import pandas as pd

import api
from data_fetcher import DataFetchError, DataFetchErrorType, SimpleCache

app = api.app


def _df(values: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame.from_dict(values, orient="index", columns=["Value"])


@pytest.fixture
def client():
    return TestClient(app)


# ── Health ───────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        assert client.get("/health").status_code == 200

    def test_health_returns_json(self, client):
        assert client.get("/health").headers["content-type"] == "application/json"

    def test_health_response_structure(self, client):
        data = client.get("/health").json()
        assert "status" in data
        assert "timestamp" in data


# ── /api/v1/assess ───────────────────────────────────────────────────────────

class TestAssessEndpoint:
    def test_assess_invalid_ticker(self, client, monkeypatch):
        def _raise_invalid(*_args, **_kwargs):
            raise DataFetchError(
                "Invalid ticker", error_type=DataFetchErrorType.INVALID_TICKER, ticker="INVALID_TICKER_XYZ",
            )
        monkeypatch.setattr(api, "_analyze_single_ticker", _raise_invalid)
        monkeypatch.setattr(api, "_search_tickers", lambda *_args, **_kwargs: [])

        response = client.post("/api/v1/assess", json={
            "tickers": ["INVALID_TICKER_XYZ"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 404
        data = response.json()
        assert data["error_type"] == "all_tickers_failed"
        assert "errors" in data["details"]

    def test_assess_valid_ticker(self, client, monkeypatch):
        monkeypatch.setattr(api, "_analyze_single_ticker",
            lambda ticker, fiscal_year, data_source: {
                "ticker": ticker, "company_name": "Apple Inc.",
                "company_name_localized": {"en": "Apple Inc."},
                "currency": "USD",
                "history": [{
                    "fiscal_year": "FY24", "is_quarterly": False,
                    "assessment": {
                        "risk_score": 2.5, "overall_rating": "Safe (S)",
                        "implied_rating": "A", "strengths": ["Strong"], "weaknesses": [],
                    },
                    "ratios": {}, "raw_metrics": {}, "statements": {},
                }],
            },
        )
        response = client.post("/api/v1/assess", json={
            "tickers": ["AAPL"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["count"] == 1

    def test_assess_missing_tickers(self, client):
        response = client.post("/api/v1/assess", json={"fiscal_year": 2024, "data_source": "yfinance"})
        assert response.status_code == 422

    def test_assess_empty_tickers(self, client):
        response = client.post("/api/v1/assess", json={"tickers": [], "fiscal_year": 2024, "data_source": "yfinance"})
        assert response.status_code == 422

    def test_assess_whitespace_tickers(self, client):
        response = client.post("/api/v1/assess", json={"tickers": ["   ", ""], "fiscal_year": 2024, "data_source": "yfinance"})
        assert response.status_code == 422

    def test_assess_ticker_count_limit(self, client):
        response = client.post("/api/v1/assess", json={
            "tickers": [f"T{i}" for i in range(51)], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 422

    def test_assess_fiscal_year_out_of_range(self, client):
        response = client.post("/api/v1/assess", json={"tickers": ["AAPL"], "fiscal_year": 1800, "data_source": "yfinance"})
        assert response.status_code == 422

    def test_assess_all_periods_failed_returns_calculation_failed(self, client, monkeypatch):
        from services import AssessmentServiceError

        def _return_calc_failed(ticker, fiscal_year, data_source):
            raise AssessmentServiceError(
                "No valid financial periods could be analyzed.",
                status_code=422,
                details={"error_type": "calculation_failed", "period_errors": [
                    {"fiscal_year": "FY24", "error": "Simulated failure"}
                ]},
            )
        monkeypatch.setattr(api, "_analyze_single_ticker", _return_calc_failed)
        monkeypatch.setattr(api, "_search_tickers", lambda *_args, **_kwargs: [])

        response = client.post("/api/v1/assess", json={
            "tickers": ["AAPL"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 422
        data = response.json()
        assert data.get("error_type") == "all_tickers_failed"

    def test_assess_timeout_returns_504(self, client, monkeypatch):
        # Fake wait_for raises TimeoutError without awaiting the inner awaitable.
        async def _fake_wait_for(fut, timeout):
            raise asyncio.TimeoutError()

        # Prevent _run_in_fetch_executor from submitting real work to the shared
        # production executor.  Return a completed concurrent future so the fake
        # wait_for never sees a coroutine (avoids RuntimeWarning).
        import concurrent.futures
        def _noop_executor(*_args, **_kwargs):
            cf: concurrent.futures.Future = concurrent.futures.Future()
            cf.set_result(None)
            return asyncio.wrap_future(cf)

        monkeypatch.setattr(api, "_search_tickers", lambda *_args, **_kwargs: [])
        monkeypatch.setattr(asyncio, "wait_for", _fake_wait_for)
        monkeypatch.setattr(api, "_run_in_fetch_executor", _noop_executor)

        response = client.post("/api/v1/assess", json={
            "tickers": ["AAPL"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 504
        assert response.json()["error_type"] == "all_tickers_failed"

    def test_assess_no_history_service_error_returns_404(self, client, monkeypatch):
        from services import AssessmentServiceError

        def _raise_no_history(ticker, fiscal_year, data_source):
            raise AssessmentServiceError(f"Ticker '{ticker}' 没有可用财务历史数据。", status_code=404)

        monkeypatch.setattr(api, "_analyze_single_ticker", _raise_no_history)
        monkeypatch.setattr(api, "_search_tickers", lambda *_args, **_kwargs: [])

        response = client.post("/api/v1/assess", json={
            "tickers": ["AAPL"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 404
        assert response.json()["error_type"] == "all_tickers_failed"

    # ── Multi-ticker ─────────────────────────────────────────────────────

    def test_multi_ticker_one_success_one_fail(self, client, monkeypatch):
        monkeypatch.setattr(api, "_search_tickers", lambda *_args, **_kwargs: [])

        def _mixed(ticker, fiscal_year, data_source):
            if ticker == "GOOD":
                return {
                    "ticker": ticker, "company_name": "Good Co",
                    "company_name_localized": {"en": "Good Co"}, "currency": "USD",
                    "history": [{
                        "fiscal_year": "FY24", "is_quarterly": False,
                        "assessment": {"risk_score": 2.0, "overall_rating": "Grey (G)", "implied_rating": "BB", "strengths": [], "weaknesses": []},
                        "ratios": {}, "raw_metrics": {}, "statements": {},
                    }],
                }
            raise DataFetchError("Bad ticker", error_type=DataFetchErrorType.INVALID_TICKER, ticker=ticker)

        monkeypatch.setattr(api, "_analyze_single_ticker", _mixed)

        response = client.post("/api/v1/assess", json={
            "tickers": ["GOOD", "BAD"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["ticker"] == "GOOD"
        assert data["errors"] is not None
        assert "BAD" in str(data["errors"])
        assert "BAD" in data["suggestions"]

    # ── All-fail priority ────────────────────────────────────────────────

    def test_all_fail_timeout_plus_invalid_returns_504(self, client, monkeypatch):
        monkeypatch.setattr(api, "_search_tickers", lambda *_args, **_kwargs: [])

        async def _fake_wait_for(fut, timeout):
            raise asyncio.TimeoutError()

        import concurrent.futures
        def _noop_executor(*_args, **_kwargs):
            cf: concurrent.futures.Future = concurrent.futures.Future()
            cf.set_result(None)
            return asyncio.wrap_future(cf)

        monkeypatch.setattr(asyncio, "wait_for", _fake_wait_for)
        monkeypatch.setattr(api, "_run_in_fetch_executor", _noop_executor)

        response = client.post("/api/v1/assess", json={
            "tickers": ["A", "B"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        # Both timeout → 504 via _priority_status_for_all_fail
        assert response.status_code == 504

    def test_all_fail_rate_limit_plus_no_data_returns_429(self, client, monkeypatch):
        monkeypatch.setattr(api, "_search_tickers", lambda *_args, **_kwargs: [])

        def _raise(ticker, fiscal_year, data_source):
            if ticker == "A":
                raise DataFetchError("rate limit", error_type=DataFetchErrorType.RATE_LIMIT, ticker=ticker)
            raise DataFetchError("no data", error_type=DataFetchErrorType.NO_DATA_AVAILABLE, ticker=ticker)

        monkeypatch.setattr(api, "_analyze_single_ticker", _raise)

        response = client.post("/api/v1/assess", json={
            "tickers": ["A", "B"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 429

    def test_all_fail_network_plus_invalid_returns_503(self, client, monkeypatch):
        monkeypatch.setattr(api, "_search_tickers", lambda *_args, **_kwargs: [])

        def _raise(ticker, fiscal_year, data_source):
            if ticker == "A":
                raise DataFetchError("network", error_type=DataFetchErrorType.NETWORK_ERROR, ticker=ticker)
            raise DataFetchError("invalid", error_type=DataFetchErrorType.INVALID_TICKER, ticker=ticker)

        monkeypatch.setattr(api, "_analyze_single_ticker", _raise)

        response = client.post("/api/v1/assess", json={
            "tickers": ["A", "B"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 503

    def test_all_fail_unknown_plus_invalid_returns_502(self, client, monkeypatch):
        monkeypatch.setattr(api, "_search_tickers", lambda *_args, **_kwargs: [])

        def _raise(ticker, fiscal_year, data_source):
            if ticker == "A":
                raise DataFetchError("unknown", error_type=DataFetchErrorType.UNKNOWN, ticker=ticker)
            raise DataFetchError("invalid", error_type=DataFetchErrorType.INVALID_TICKER, ticker=ticker)

        monkeypatch.setattr(api, "_analyze_single_ticker", _raise)

        response = client.post("/api/v1/assess", json={
            "tickers": ["A", "B"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 502

    def test_all_fail_calculation_failed_only_returns_422(self, client, monkeypatch):
        from services import AssessmentServiceError

        def _raise(ticker, fiscal_year, data_source):
            raise AssessmentServiceError("calc failed", status_code=422,
                                         details={"error_type": "calculation_failed"})

        monkeypatch.setattr(api, "_analyze_single_ticker", _raise)
        monkeypatch.setattr(api, "_search_tickers", lambda *_args, **_kwargs: [])

        response = client.post("/api/v1/assess", json={
            "tickers": ["A"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 422


# ── /api/v1/symbols/search ───────────────────────────────────────────────────

class TestSymbolSearch:
    def test_symbol_search_endpoint_returns_results(self, client, monkeypatch):
        monkeypatch.setattr(api, "_search_tickers",
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
                    {"symbol": "MSFLX", "shortname": "MS Inst", "quoteType": "MUTUALFUND"},
                    {"symbol": "MSFT", "shortname": "Microsoft Corporation", "quoteType": "EQUITY"},
                    {"symbol": "msft", "shortname": "MS Duplicate", "quoteType": "EQUITY"},
                    {"symbol": "MSFLX", "shortname": "Same As Query", "quoteType": "EQUITY"},
                ]
        monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(Search=FakeSearch))
        suggestions = api._search_tickers("MSFLX", limit=5)
        assert len(suggestions) == 1
        assert suggestions[0]["symbol"] == "MSFT"

    def test_search_tickers_enriches_localized_name(self, monkeypatch):
        class FakeSearch:
            def __init__(self, _query):
                self.quotes = [{"symbol": "0700.HK", "shortname": "Tencent Holdings", "quoteType": "EQUITY"}]

        class FakeAk:
            @staticmethod
            def stock_individual_info_em(symbol):
                assert symbol == "0700"
                return pd.DataFrame({"item": ["股票简称"], "value": ["腾讯控股"]})

        monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(Search=FakeSearch))
        monkeypatch.setitem(sys.modules, "akshare", types.SimpleNamespace(stock_individual_info_em=FakeAk.stock_individual_info_em))
        monkeypatch.setattr(api, "_convert_simplified_to_traditional", lambda text: f"TW:{text}")
        api._LOCALIZED_NAME_CACHE.clear()

        suggestions = api._search_tickers("0700", limit=5)
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["symbol"] == "0700.HK"
        assert s["company_name_localized"]["zh-CN"] == "腾讯控股"
        assert s["company_name_localized"]["zh-TW"] == "TW:腾讯控股"

    def test_symbol_search_timeout_returns_504(self, client, monkeypatch):
        async def _fake_wait_for(fut, timeout):
            raise asyncio.TimeoutError()

        import concurrent.futures
        def _noop_executor(*_args, **_kwargs):
            cf: concurrent.futures.Future = concurrent.futures.Future()
            cf.set_result([])
            return asyncio.wrap_future(cf)

        monkeypatch.setattr(asyncio, "wait_for", _fake_wait_for)
        monkeypatch.setattr(api, "_run_in_fetch_executor", _noop_executor)

        response = client.get("/api/v1/symbols/search", params={"q": "nio", "limit": 20})
        assert response.status_code == 504
        assert response.json()["error_type"] == "timeout"


# ── /api/v1/covenants/check ──────────────────────────────────────────────────

class TestCovenantEndpoint:
    def test_covenant_invalid_ticker(self, client, monkeypatch):
        def _raise_invalid(*_args, **_kwargs):
            raise DataFetchError("Ticker not found", error_type=DataFetchErrorType.INVALID_TICKER, ticker="INVALID_TICKER_XYZ")
        monkeypatch.setattr(api.fetcher, "get_financial_data", _raise_invalid)

        response = client.post("/api/v1/covenants/check", json={
            "ticker": "INVALID_TICKER_XYZ", "fiscal_year": 2024, "data_source": "yfinance",
            "covenants": {"min_current_ratio": 1.5, "max_debt_to_equity": 2.0},
        })
        assert response.status_code == 404

    def test_covenant_handles_empty_fetch_result(self, client, monkeypatch):
        monkeypatch.setattr(api.fetcher, "get_financial_data", lambda *_args, **_kwargs: None)
        response = client.post("/api/v1/covenants/check", json={
            "ticker": "600519", "fiscal_year": 2024, "data_source": "akshare",
            "covenants": {"min_current_ratio": 1.2},
        })
        assert response.status_code == 404
        assert response.json()["error_type"] == "no_data_available"

    def test_covenant_missing_ticker(self, client):
        response = client.post("/api/v1/covenants/check", json={
            "fiscal_year": 2024, "data_source": "yfinance", "covenants": {"min_current_ratio": 1.5},
        })
        assert response.status_code == 422

    def test_covenant_missing_covenants(self, client):
        response = client.post("/api/v1/covenants/check", json={
            "ticker": "AAPL", "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 422

    def test_covenant_fiscal_year_out_of_range(self, client):
        response = client.post("/api/v1/covenants/check", json={
            "ticker": "AAPL", "fiscal_year": 2201, "data_source": "yfinance",
            "covenants": {"min_current_ratio": 1.5},
        })
        assert response.status_code == 422

    def test_covenant_datafetch_rate_limit_returns_429(self, client, monkeypatch):
        def _raise_rate_limit(*_args, **_kwargs):
            raise DataFetchError("Rate limit exceeded", error_type=DataFetchErrorType.RATE_LIMIT, ticker="AAPL")
        monkeypatch.setattr(api.fetcher, "get_financial_data", _raise_rate_limit)

        response = client.post("/api/v1/covenants/check", json={
            "ticker": "AAPL", "fiscal_year": 2024, "data_source": "yfinance",
            "covenants": {"min_current_ratio": 1.2},
        })
        assert response.status_code == 429
        assert response.json()["error_type"] == DataFetchErrorType.RATE_LIMIT.value

    def test_covenant_datafetch_network_error_returns_503(self, client, monkeypatch):
        def _raise_network_error(*_args, **_kwargs):
            raise DataFetchError("Network error", error_type=DataFetchErrorType.NETWORK_ERROR, ticker="AAPL")
        monkeypatch.setattr(api.fetcher, "get_financial_data", _raise_network_error)

        response = client.post("/api/v1/covenants/check", json={
            "ticker": "AAPL", "fiscal_year": 2024, "data_source": "yfinance",
            "covenants": {"min_current_ratio": 1.2},
        })
        assert response.status_code == 503

    def test_covenant_invalid_data_source_returns_422(self, client):
        response = client.post("/api/v1/covenants/check", json={
            "ticker": "AAPL", "fiscal_year": 2024, "data_source": "invalid_source_xyz",
            "covenants": {"min_current_ratio": 1.2},
        })
        assert response.status_code == 422
        assert "Unsupported data source" in response.json()["error"]

    def test_covenant_timeout_returns_504(self, client, monkeypatch):
        async def _fake_wait_for(fut, timeout):
            raise asyncio.TimeoutError()

        import concurrent.futures
        def _noop_executor(*_args, **_kwargs):
            cf: concurrent.futures.Future = concurrent.futures.Future()
            cf.set_result(None)
            return asyncio.wrap_future(cf)

        monkeypatch.setattr(asyncio, "wait_for", _fake_wait_for)
        monkeypatch.setattr(api, "_run_in_fetch_executor", _noop_executor)

        response = client.post("/api/v1/covenants/check", json={
            "ticker": "AAPL", "fiscal_year": 2024, "data_source": "yfinance",
            "covenants": {"min_current_ratio": 1.2},
        })
        assert response.status_code == 504
        assert response.json()["error_type"] == "timeout"

    def test_covenant_success_path(self, client, monkeypatch):
        """Full covenant check success path with fake financial data."""
        fake_data = {
            "ticker": "AAPL", "company_name": "Apple Inc.",
            "history": [{
                "year_label": "FY24",
                "is_quarterly": False,
                "income": _df({
                    "revenue": 1000.0, "cost_of_revenue": 400.0, "gross_profit": 600.0,
                    "operating_income": 250.0, "net_income": 200.0, "interest_expense": 25.0,
                    "ebitda": 300.0,
                }),
                "balance": _df({
                    "total_assets": 2000.0, "total_equity": 1100.0, "total_debt": 600.0,
                    "total_current_assets": 800.0, "total_current_liabilities": 350.0,
                    "cash": 200.0, "inventory": 120.0, "accounts_receivable": 150.0,
                    "accounts_payable": 130.0,
                }),
                "cash": _df({"operating_cf": 220.0, "free_cf": 180.0}),
            }],
            "market_cap": 50.0,
        }
        monkeypatch.setattr(api.fetcher, "get_financial_data", lambda *a, **kw: fake_data)

        response = client.post("/api/v1/covenants/check", json={
            "ticker": "AAPL", "fiscal_year": 2024, "data_source": "yfinance",
            "covenants": {"min_current_ratio": 1.0, "min_interest_coverage": 2.0},
        })
        assert response.status_code == 200
        data = response.json()
        assert data["company_name"] == "Apple Inc."
        assert data["fiscal_year"] == 2024
        assert data["covenants_passed"] >= 0
        assert len(data["alerts"]) == 2

    def test_covenant_empty_history_returns_404(self, client, monkeypatch):
        monkeypatch.setattr(api.fetcher, "get_financial_data", lambda *a, **kw: {
            "ticker": "AAPL", "company_name": "Apple Inc.", "history": [],
        })
        response = client.post("/api/v1/covenants/check", json={
            "ticker": "AAPL", "fiscal_year": 2024, "data_source": "yfinance",
            "covenants": {"min_current_ratio": 1.0},
        })
        assert response.status_code == 404


# ── Validation error format ──────────────────────────────────────────────────

class TestErrorFormats:
    def test_422_validation_response_has_error_type(self, client):
        response = client.post("/api/v1/assess", json={"fiscal_year": 2024})
        assert response.status_code == 422
        data = response.json()
        assert data["error_type"] == "validation_error"
        assert "details" in data

    def test_http_exception_detail_string_has_error_type(self):
        """HTTPException with string detail gets error_type == 'http_error'."""
        import json
        import asyncio
        from fastapi import HTTPException, Request

        exc = HTTPException(status_code=400, detail="Something went wrong")
        scope = {"type": "http", "method": "GET", "path": "/", "headers": [],
                 "server": ("test", 80), "client": ("test", 12345)}

        # Call the handler in a fresh event loop to avoid pytest loop conflicts
        loop = asyncio.new_event_loop()
        try:
            request = Request(scope)
            response = loop.run_until_complete(api.http_exception_handler(request, exc))
            assert response.status_code == 400
            body = json.loads(response.body)
            assert body["error_type"] == "http_error"
            assert body["error"] == "Something went wrong"
        finally:
            loop.close()

    def test_pdf_value_error_returns_422(self, client, monkeypatch):
        def _fake_pdf(*_args, **_kwargs):
            raise ValueError("Invalid report structure")

        monkeypatch.setattr(api, "generate_full_pdf", _fake_pdf)

        response = client.post("/api/v1/reports/pdf", json={
            "report": {"ticker": "TEST", "company_name": "Test", "currency": "USD", "history": []},
            "lang": "en",
        })
        assert response.status_code == 422


# ── PDF Export ───────────────────────────────────────────────────────────────

class TestPdfExportEndpoint:
    def test_pdf_export_rejects_unknown_theme(self, client):
        response = client.post("/api/v1/reports/pdf", json={
            "report": {"ticker": "TEST", "history": [{"fiscal_year": "FY24"}]},
            "theme": "sepia",
        })
        assert response.status_code == 422

    def test_pdf_export_returns_attachment(self, client, monkeypatch):
        def _fake_generate_full_pdf(_report, _lang, _theme):
            return b"%PDF-1.4\n%Test\n%%EOF"

        monkeypatch.setattr(api, "generate_full_pdf", _fake_generate_full_pdf)
        payload = {
            "report": {
                "ticker": "AAPL", "company_name": "Apple Inc.", "currency": "USD",
                "history": [{
                    "fiscal_year": "FY24", "is_quarterly": False,
                    "assessment": {
                        "risk_score": 10.0, "overall_rating": "Safe (S)", "implied_rating": "AAA",
                        "strengths": [], "weaknesses": [],
                    },
                    "ratios": {}, "raw_metrics": {}, "statements": {},
                }],
            },
            "lang": "zh-CN",
        }
        response = client.post("/api/v1/reports/pdf", json=payload, headers={"Origin": "http://localhost:5173"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/pdf")
        assert "attachment" in response.headers["content-disposition"]
        assert "AAPL_Full_Report.pdf" in response.headers["content-disposition"]
        assert response.content.startswith(b"%PDF")
        assert response.headers["x-pdf-bytes"] == str(len(response.content))
        assert response.headers["x-pdf-sha256"] == hashlib.sha256(response.content).hexdigest()
        expose_headers = response.headers["access-control-expose-headers"].lower()
        assert "x-pdf-sha256" in expose_headers
        assert "x-pdf-bytes" in expose_headers
        assert "content-disposition" in expose_headers

    def test_pdf_export_validation_error(self, client):
        response = client.post("/api/v1/reports/pdf", json={"lang": "zh-CN"})
        assert response.status_code == 422

    def test_pdf_batch_export_returns_integrity_verifiable_zip(self, client, monkeypatch):
        def _fake_generate_full_pdf(report, _lang, _theme):
            return f"%PDF {report.get('ticker')}".encode()

        async def _fake_executor(func, *args):
            return func(*args)

        monkeypatch.setattr(api, "generate_full_pdf", _fake_generate_full_pdf)
        monkeypatch.setattr(api, "_run_in_pdf_executor", _fake_executor)
        response = client.post("/api/v1/reports/pdf/batch", json={
            "lang": "en",
            "theme": "light",
            "reports": [{"ticker": "AAPL"}, {"ticker": "AAPL"}],
        })

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert response.headers["x-zip-bytes"] == str(len(response.content))
        assert response.headers["x-zip-sha256"] == hashlib.sha256(response.content).hexdigest()
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert archive.namelist() == ["AAPL_Full_Report.pdf", "AAPL_2_Full_Report.pdf"]

    def test_pdf_batch_export_rejects_more_than_ten_reports(self, client):
        response = client.post("/api/v1/reports/pdf/batch", json={
            "reports": [{"ticker": str(idx)} for idx in range(11)],
        })
        assert response.status_code == 422


# ── Input Validation (Security Hardening) ──────────────────────────────────────

class TestInputValidation:
    def test_ticker_with_invalid_characters_rejected(self, client):
        response = client.post("/api/v1/assess", json={
            "tickers": ["<script>alert(1)</script>"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 422
        body = str(response.json()).lower()
        assert "invalid" in body or "character" in body or "too long" in body

    def test_ticker_too_long_rejected(self, client):
        response = client.post("/api/v1/assess", json={
            "tickers": ["A" * 25], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 422
        assert "too long" in str(response.json()).lower()

    def test_covenant_negative_threshold_rejected(self, client):
        response = client.post("/api/v1/covenants/check", json={
            "ticker": "AAPL", "fiscal_year": 2024, "data_source": "yfinance",
            "covenants": {"min_current_ratio": -1.5},
        })
        assert response.status_code == 422

    def test_covenant_nan_threshold_rejected(self, client):
        response = client.post("/api/v1/covenants/check", json={
            "ticker": "AAPL", "fiscal_year": 2024, "data_source": "yfinance",
            "covenants": {"min_current_ratio": "NaN"},
        })
        assert response.status_code == 422

    def test_covenant_inf_threshold_rejected(self, client):
        response = client.post("/api/v1/covenants/check", json={
            "ticker": "AAPL", "fiscal_year": 2024, "data_source": "yfinance",
            "covenants": {"min_current_ratio": "Infinity"},
        })
        assert response.status_code == 422

    def test_pdf_report_too_large_rejected(self, client):
        large_history = [{"fiscal_year": f"FY{i}", "is_quarterly": False,
                          "assessment": {}, "ratios": {}, "raw_metrics": {}, "statements": {}}
                         for i in range(60)]
        response = client.post("/api/v1/reports/pdf", json={
            "report": {"ticker": "TEST", "company_name": "Test", "currency": "USD", "history": large_history},
            "lang": "en",
        })
        assert response.status_code == 422


# ── Error Sanitization ─────────────────────────────────────────────────────────

class TestErrorSanitization:
    def test_symbol_search_error_no_str_exc(self, client, monkeypatch):
        async def _fake_executor(_func, *_args, **_kwargs):
            raise RuntimeError("internal details XYZ")
        monkeypatch.setattr(api, "_run_in_fetch_executor", _fake_executor)
        monkeypatch.setenv("SYMBOL_SEARCH_TIMEOUT_SECONDS", "0.05")
        # The search should surface a RuntimeError which hits the except Exception handler
        response = client.get("/api/v1/symbols/search", params={"q": "test", "limit": 20})
        assert response.status_code in (503, 504)
        body = str(response.json())
        assert "internal details XYZ" not in body
        assert "RuntimeError" not in body

    def test_unhandled_exception_in_process_ticker_isolated(self, client, monkeypatch):
        monkeypatch.setattr(api, "_search_tickers", lambda *_args, **_kwargs: [])
        # All tickers raise an unexpected exception type → catch-all must handle it
        def _raise_unexpected(ticker, fiscal_year, data_source):
            raise AttributeError("Something broke internally XYZ")
        monkeypatch.setattr(api, "_analyze_single_ticker", _raise_unexpected)

        response = client.post("/api/v1/assess", json={
            "tickers": ["AAPL"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        # internal_error maps to 500 in _priority_status_for_all_fail
        assert response.status_code == 500
        data = response.json()
        # The response must not leak the raw exception string
        body_str = str(data)
        assert "Something broke internally XYZ" not in body_str
        assert "AttributeError" not in body_str


# ── PDF Filename Sanitization ─────────────────────────────────────────────────

class TestPdfFilenameSanitization:
    def test_malicious_ticker_sanitized_in_filename(self, client, monkeypatch):
        def _fake_pdf(_report, _lang, _theme):
            return b"%PDF-1.4\n%%EOF"

        monkeypatch.setattr(api, "generate_full_pdf", _fake_pdf)
        response = client.post("/api/v1/reports/pdf", json={
            "report": {"ticker": "A/B\\..\\etc\\passwd", "company_name": "Test", "history": [{
                "fiscal_year": "FY24", "is_quarterly": False,
                "assessment": {"risk_score": 1.0, "overall_rating": "Safe (S)", "implied_rating": "A", "strengths": [], "weaknesses": []},
                "ratios": {}, "raw_metrics": {}, "statements": {},
            }]},
            "lang": "en",
        })
        assert response.status_code == 200
        cd = response.headers["content-disposition"]
        # Path traversal characters should be stripped
        assert "\\" not in cd
        assert "/" not in cd
        # Dots are valid ticker characters (e.g., BRK.B); the sanitization
        # replaces non-whitelisted chars with underscores
        assert ".." not in cd or cd.startswith("attachment; filename=\"A_B_.._")
        assert "A_B_.._ETC_PASSWD_Full_Report.pdf" in cd or "A_B___etc_passwd_Full_Report.pdf" in cd


# ── UI ───────────────────────────────────────────────────────────────────────

class TestUIEndpoints:
    def test_root_returns_html(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_catch_all_returns_html(self, client):
        response = client.get("/nonexistent-page")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


# ── Upstream Capacity Isolation ──────────────────────────────────────────────

class TestUpstreamCapacity:
    def test_assess_capacity_exhausted_returns_503(self, client, monkeypatch):
        """When the fetch executor is at capacity, assess returns 503 upstream_busy."""
        monkeypatch.setattr(api, "_search_tickers", lambda *_args, **_kwargs: [])

        def _block_semaphore(*_args, **_kwargs):
            raise api.UpstreamCapacityError("Upstream fetch capacity exhausted")

        monkeypatch.setattr(api, "_run_in_fetch_executor", _block_semaphore)

        response = client.post("/api/v1/assess", json={
            "tickers": ["AAPL"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 503
        data = response.json()
        assert data["error_type"] == "all_tickers_failed"
        # The per-ticker error carries upstream_busy; check that all_tickers_failed is returned
        assert "errors" in data.get("details", data)


    def test_search_capacity_exhausted_returns_503(self, client, monkeypatch):
        """Symbol search returns 503 when executor is full."""
        monkeypatch.setattr(api, "_run_in_fetch_executor",
                            lambda *_args, **_kwargs: (_ for _ in ()).throw(api.UpstreamCapacityError()))
        response = client.get("/api/v1/symbols/search", params={"q": "test", "limit": 5})
        assert response.status_code == 503
        assert response.json()["error_type"] == "upstream_busy"

    def test_covenant_capacity_exhausted_returns_503(self, client, monkeypatch):
        """Covenant check returns 503 when executor is full."""
        monkeypatch.setattr(api, "_run_in_fetch_executor",
                            lambda *_args, **_kwargs: (_ for _ in ()).throw(api.UpstreamCapacityError()))
        response = client.post("/api/v1/covenants/check", json={
            "ticker": "AAPL", "fiscal_year": 2024, "data_source": "yfinance",
            "covenants": {"min_current_ratio": 1.2},
        })
        assert response.status_code == 503
        assert response.json()["error_type"] == "upstream_busy"

    def test_pdf_capacity_exhausted_returns_503(self, client, monkeypatch):
        """PDF export returns 503 when executor is full."""
        monkeypatch.setattr(api, "_run_in_pdf_executor",
                            lambda *_args, **_kwargs: (_ for _ in ()).throw(api.UpstreamCapacityError()))
        response = client.post("/api/v1/reports/pdf", json={
            "report": {"ticker": "TEST", "company_name": "Test", "currency": "USD", "history": [{"fiscal_year": "2024"}]},
            "lang": "en",
        })
        assert response.status_code == 503
        assert response.json()["error_type"] == "upstream_busy"


class TestFetchExecutorIsolation:
    def test_assess_uses_dedicated_executor_not_default(self, client, monkeypatch):
        """All blocking calls in /assess must go through _run_in_fetch_executor."""
        calls = []

        async def _tracking_executor(func, *args):
            calls.append(func.__name__ if hasattr(func, '__name__') else str(func))
            # Simulate a successful (empty) assessment
            raise api.UpstreamCapacityError()

        monkeypatch.setattr(api, "_run_in_fetch_executor", _tracking_executor)
        monkeypatch.setattr(api, "_search_tickers", lambda *_args, **_kwargs: [])
        client.post("/api/v1/assess", json={
            "tickers": ["AAPL"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert len(calls) > 0, "No calls to _run_in_fetch_executor"

    def test_search_uses_dedicated_executor(self, client, monkeypatch):
        """Symbol search blocking call goes through _run_in_fetch_executor."""
        called = [False]

        async def _tracking_executor(*_args, **_kwargs):
            called[0] = True
            raise api.UpstreamCapacityError()

        monkeypatch.setattr(api, "_run_in_fetch_executor", _tracking_executor)
        client.get("/api/v1/symbols/search", params={"q": "test", "limit": 5})
        assert called[0], "Symbol search did not use _run_in_fetch_executor"


# ── Error Response Content Verification ──────────────────────────────────────

class TestErrorResponseContent:
    def test_global_error_path_does_not_include_query_string(self):
        """Unhandled-error responses must not echo query-string secrets."""
        from starlette.requests import Request

        request = Request({
            "type": "http",
            "method": "GET",
            "path": "/api/v1/health",
            "query_string": b"token=do-not-echo",
            "headers": [],
            "client": ("testclient", 123),
            "server": ("testserver", 80),
            "scheme": "http",
        })
        response = asyncio.run(api.global_exception_handler(request, RuntimeError("internal")))
        body = response.body.decode("utf-8")
        assert '"path":"/api/v1/health"' in body
        assert "do-not-echo" not in body

    def test_assess_internal_error_no_raw_strings(self, client, monkeypatch):
        """All-tickers internal_error must not leak exception details."""
        monkeypatch.setattr(api, "_search_tickers", lambda *_args, **_kwargs: [])

        def _raise_unexpected(*_args, **_kwargs):
            raise AttributeError("confidential db password xyz")

        monkeypatch.setattr(api, "_analyze_single_ticker", _raise_unexpected)
        response = client.post("/api/v1/assess", json={
            "tickers": ["AAPL"], "fiscal_year": 2024, "data_source": "yfinance",
        })
        assert response.status_code == 500
        body = response.text
        assert "confidential db password xyz" not in body
        assert "AttributeError" not in body

    def test_search_503_no_raw_strings(self, client, monkeypatch):
        """Symbol search 503 must not leak internal exception text."""
        async def _fail(*_args, **_kwargs):
            raise RuntimeError("secret internal path /etc/config")
        monkeypatch.setattr(api, "_run_in_fetch_executor", _fail)
        response = client.get("/api/v1/symbols/search", params={"q": "test", "limit": 5})
        assert response.status_code in (503, 504)
        body = response.text
        assert "secret internal path /etc/config" not in body
        assert "RuntimeError" not in body


# ── Localized Name Cache ────────────────────────────────────────────────────

class TestLocalizedNameCache:
    def test_cache_eviction_when_maxsize_exceeded(self, monkeypatch):
        """_LOCALIZED_NAME_CACHE evicts old entries when maxsize is exceeded."""
        api._LOCALIZED_NAME_CACHE.clear()
        # Use a small cache for testing
        small_cache = SimpleCache(default_ttl=86400, maxsize=3)
        monkeypatch.setattr(api, "_LOCALIZED_NAME_CACHE", small_cache)

        for i in range(5):
            api._build_company_name_localized(f"Company{i}", f"TICKER{i}")

        # Only the last 3 entries should remain (LRU eviction)
        assert small_cache.get("TICKER0") is None
        assert small_cache.get("TICKER1") is None
        assert small_cache.get("TICKER2") is not None
        assert small_cache.get("TICKER3") is not None
        assert small_cache.get("TICKER4") is not None
        assert small_cache.stats()["size"] == 3


# ── Suggestions downgrade tests ─────────────────────────────────────────────

class TestSuggestionsDowngrade:
    def test_assess_failure_does_not_fetch_suggestions_by_default(self, client, monkeypatch):
        """Default failure must not call _search_tickers."""
        called = {"search": 0}

        def _raise_invalid(*_args, **_kwargs):
            raise DataFetchError("Bad ticker", error_type=DataFetchErrorType.INVALID_TICKER, ticker="BAD")

        def _tracking_search(*_args, **_kwargs):
            called["search"] += 1
            return []

        monkeypatch.setattr(api, "_analyze_single_ticker", _raise_invalid)
        monkeypatch.setattr(api, "_search_tickers", _tracking_search)

        response = client.post("/api/v1/assess", json={
            "tickers": ["BAD"],
            "fiscal_year": 2024,
            "data_source": "yfinance",
        })

        assert response.status_code == 404
        assert called["search"] == 0, (
            f"Default failure must not trigger _search_tickers, got {called['search']}"
        )

    def test_assess_failure_fetches_suggestions_when_explicitly_enabled(self, client, monkeypatch):
        """include_suggestions=True must trigger _search_tickers on invalid ticker."""
        called = {"search": 0}

        def _raise_invalid(*_args, **_kwargs):
            raise DataFetchError("Bad ticker", error_type=DataFetchErrorType.INVALID_TICKER, ticker="BAD")

        def _tracking_search(*_args, **_kwargs):
            called["search"] += 1
            return []

        monkeypatch.setattr(api, "_analyze_single_ticker", _raise_invalid)
        monkeypatch.setattr(api, "_search_tickers", _tracking_search)

        response = client.post("/api/v1/assess", json={
            "tickers": ["BAD"],
            "fiscal_year": 2024,
            "data_source": "yfinance",
            "include_suggestions": True,
        })

        assert response.status_code == 404
        assert called["search"] == 1, (
            f"include_suggestions=True must trigger _search_tickers, got {called['search']}"
        )

    def test_assess_timeout_does_not_fetch_suggestions_even_when_enabled(self, client, monkeypatch):
        """timeout errors never trigger suggestions, even when include_suggestions=True."""
        called = {"search": 0}

        async def _raise_timeout(*_args, **_kwargs):
            raise asyncio.TimeoutError()

        def _tracking_search(*_args, **_kwargs):
            called["search"] += 1
            return []

        monkeypatch.setattr(api, "_run_in_fetch_executor", _raise_timeout)
        monkeypatch.setattr(api, "_search_tickers", _tracking_search)

        response = client.post("/api/v1/assess", json={
            "tickers": ["SLOW"],
            "fiscal_year": 2024,
            "data_source": "yfinance",
            "include_suggestions": True,
        })

        # timeout returns 504 for all_tickers_failed
        assert response.status_code in (404, 504)
        assert called["search"] == 0, (
            f"timeout must not trigger _search_tickers, got {called['search']}"
        )


# ── PDF executor isolation test ──────────────────────────────────────────────

class TestPdfExecutorIsolation:
    def test_pdf_export_uses_pdf_executor_not_fetch_executor(self, client, monkeypatch):
        """PDF route must go through _run_in_pdf_executor, not _run_in_fetch_executor."""
        called = {"pdf": 0, "fetch": 0}

        async def _fake_pdf_executor(func, *args):
            called["pdf"] += 1
            return b"%PDF-1.4\n%%EOF"

        async def _fake_fetch_executor(*_args, **_kwargs):
            called["fetch"] += 1
            raise AssertionError("PDF route must not use fetch executor")

        monkeypatch.setattr(api, "_run_in_pdf_executor", _fake_pdf_executor)
        monkeypatch.setattr(api, "_run_in_fetch_executor", _fake_fetch_executor)

        response = client.post("/api/v1/reports/pdf", json={
            "report": {
                "ticker": "TEST",
                "company_name": "Test",
                "history": [{
                    "fiscal_year": "FY24",
                    "is_quarterly": False,
                    "assessment": {"risk_score": 1.0, "overall_rating": "Safe (S)", "implied_rating": "A"},
                    "ratios": {},
                    "raw_metrics": {},
                    "statements": {},
                }],
            },
            "lang": "en",
        })

        assert response.status_code == 200
        assert called["pdf"] == 1
        assert called["fetch"] == 0


# ── P0: Executor capacity not released until worker done ────────────────────

class TestExecutorCapacityAfterTimeout:
    def test_capacity_not_released_until_worker_done_after_timeout(self):
        """Capacity stays consumed after asyncio.wait_for timeout until the worker finishes."""
        import asyncio
        import time as _time
        import concurrent.futures

        cap = threading.BoundedSemaphore(1)
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        worker_started = threading.Event()
        worker_done = threading.Event()

        def _slow_worker():
            worker_started.set()
            _time.sleep(0.3)
            worker_done.set()
            return "done"

        async def _run():
            try:
                await asyncio.wait_for(
                    api._submit_with_capacity(ex, cap, "busy", _slow_worker),
                    timeout=0.01,
                )
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())

        # After timeout: worker still running, capacity must NOT be restored.
        assert worker_started.is_set(), "worker must have started before timeout"
        assert cap._value == 0, (
            f"Capacity must NOT be restored while worker still runs, got {cap._value}"
        )

        # Wait for worker to actually finish, then capacity must be restored.
        worker_done.wait(timeout=5)
        _time.sleep(0.05)
        assert cap._value == 1, (
            f"Capacity must be restored after worker completes, got {cap._value}"
        )
        ex.shutdown(wait=True)

    def test_pdf_style_capacity_not_released_until_worker_done(self):
        """Same behaviour proven with the shared helper (covers PDF-like usage)."""
        import asyncio
        import time as _time
        import concurrent.futures

        cap = threading.BoundedSemaphore(1)
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        worker_started = threading.Event()
        worker_done = threading.Event()

        def _slow_worker():
            worker_started.set()
            _time.sleep(0.3)
            worker_done.set()
            return b"%PDF-done"

        async def _run():
            try:
                await asyncio.wait_for(
                    api._submit_with_capacity(ex, cap, "pdf busy", _slow_worker),
                    timeout=0.01,
                )
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run())

        assert worker_started.is_set()
        assert cap._value == 0, (
            f"Capacity must NOT be restored while worker still runs, got {cap._value}"
        )

        worker_done.wait(timeout=5)
        _time.sleep(0.05)
        assert cap._value == 1, (
            f"Capacity must be restored after worker completes, got {cap._value}"
        )
        ex.shutdown(wait=True)

    def test_submit_with_capacity_raises_when_exhausted(self):
        """_submit_with_capacity raises UpstreamCapacityError when semaphore is full."""
        import concurrent.futures
        cap = threading.BoundedSemaphore(0)
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        import asyncio

        async def _run():
            return await api._submit_with_capacity(
                ex, cap, "test busy", lambda: "ok",
            )

        with pytest.raises(api.UpstreamCapacityError, match="test busy"):
            asyncio.run(_run())
        ex.shutdown(wait=False)


# ── P1: PDF export timeout ──────────────────────────────────────────────────

class TestPdfExportTimeout:
    def test_pdf_export_timeout_returns_504(self, client, monkeypatch):
        """PDF export must return 504 when asyncio.wait_for times out."""
        _original_wait_for = asyncio.wait_for

        async def _fake_wait_for(aw, *, timeout):
            if timeout == max(1.0, api.settings.pdf_export_timeout_seconds):
                raise asyncio.TimeoutError()
            return await _original_wait_for(aw, timeout=timeout)

        monkeypatch.setattr(asyncio, "wait_for", _fake_wait_for)

        # Use a callable that returns an awaitable future (not a coroutine)
        # to avoid "coroutine was never awaited" warnings.
        import concurrent.futures

        def _ok_executor(*_args, **_kwargs):
            f: concurrent.futures.Future = concurrent.futures.Future()
            f.set_result(b"%PDF-ok")
            return asyncio.wrap_future(f)

        monkeypatch.setattr(api, "_run_in_pdf_executor", _ok_executor)

        response = client.post("/api/v1/reports/pdf", json={
            "report": {
                "ticker": "TEST",
                "company_name": "Test",
                "history": [{
                    "fiscal_year": "FY24",
                    "is_quarterly": False,
                    "assessment": {"risk_score": 1.0, "overall_rating": "Safe (S)", "implied_rating": "A"},
                    "ratios": {}, "raw_metrics": {}, "statements": {},
                }],
            },
            "lang": "en",
        })

        assert response.status_code == 504
        detail = response.json()
        assert detail["error_type"] == "timeout"
        assert detail["details"]["ticker"] == "TEST"

    def test_pdf_capacity_exhausted_still_returns_503(self, client, monkeypatch):
        """When PDF capacity is exhausted, 503 is returned before waiting for timeout."""
        monkeypatch.setattr(api.settings, "pdf_export_timeout_seconds", 30.0)

        async def _busy_executor(*_args, **_kwargs):
            raise api.UpstreamCapacityError("PDF export capacity exhausted")

        monkeypatch.setattr(api, "_run_in_pdf_executor", _busy_executor)

        response = client.post("/api/v1/reports/pdf", json={
            "report": {
                "ticker": "TEST",
                "company_name": "Test",
                "history": [{
                    "fiscal_year": "FY24",
                    "is_quarterly": False,
                    "assessment": {"risk_score": 1.0, "overall_rating": "Safe (S)", "implied_rating": "A"},
                    "ratios": {}, "raw_metrics": {}, "statements": {},
                }],
            },
            "lang": "en",
        })

        assert response.status_code == 503
        assert response.json()["error_type"] == "upstream_busy"

    def test_pdf_export_normal_path_still_works(self, client, monkeypatch):
        """Normal PDF export returns 200 with correct headers when no timeout."""
        monkeypatch.setattr(api.settings, "pdf_export_timeout_seconds", 30.0)

        async def _ok_executor(*_args, **_kwargs):
            return b"%PDF-1.4\n%%EOF"

        monkeypatch.setattr(api, "_run_in_pdf_executor", _ok_executor)

        response = client.post("/api/v1/reports/pdf", json={
            "report": {
                "ticker": "TEST",
                "company_name": "Test",
                "history": [{
                    "fiscal_year": "FY24",
                    "is_quarterly": False,
                    "assessment": {"risk_score": 1.0, "overall_rating": "Safe (S)", "implied_rating": "A"},
                    "ratios": {}, "raw_metrics": {}, "statements": {},
                }],
            },
            "lang": "en",
        })

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "X-PDF-SHA256" in response.headers
        assert "X-PDF-Bytes" in response.headers


# ── P6: Config field validation ──────────────────────────────────────────────

class TestConfigValidation:
    def test_default_settings_load_without_error(self):
        """Default settings must load successfully."""
        from config import Settings
        s = Settings()
        assert s.assess_max_concurrency == 8
        assert s.upstream_max_workers == 12
        assert s.pdf_export_timeout_seconds == 20.0

    def test_zero_workers_rejected(self):
        """Zero workers are rejected at the settings layer."""
        from pydantic import ValidationError
        from config import Settings
        with pytest.raises(ValidationError):
            Settings(upstream_max_workers=0)

    def test_negative_timeout_rejected(self):
        """Negative timeout values are rejected at the settings layer."""
        from pydantic import ValidationError
        from config import Settings
        with pytest.raises(ValidationError):
            Settings(assess_ticker_timeout_seconds=-1)

    def test_zero_cache_maxsize_rejected(self):
        """Zero cache maxsize is rejected at the settings layer."""
        from pydantic import ValidationError
        from config import Settings
        with pytest.raises(ValidationError):
            Settings(data_cache_maxsize=0)
