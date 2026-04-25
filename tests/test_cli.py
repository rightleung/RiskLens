"""Tests for RiskLens CLI."""

from __future__ import annotations

import json
import os
import sys

import risklens_cli as cli


class _OkService:
    def __init__(self, report_dir: str) -> None:
        self.report_dir = report_dir

    def assess(self, ticker: str, data_source: str, fiscal_year: int | None):
        return {
            "ticker": ticker,
            "data_source": data_source,
            "fiscal_year": fiscal_year,
            "report_dir": self.report_dir,
        }


class _MixedService:
    def __init__(self, report_dir: str) -> None:
        self.report_dir = report_dir

    def assess(self, ticker: str, data_source: str, fiscal_year: int | None):
        del data_source, fiscal_year
        if ticker == "BAD":
            raise cli.AssessmentServiceError("Ticker not found", status_code=404, details={"ticker": ticker})
        return {"ticker": ticker, "report_dir": self.report_dir}


class _FailService:
    def __init__(self, report_dir: str) -> None:
        self.report_dir = report_dir

    def assess(self, ticker: str, data_source: str, fiscal_year: int | None):
        del data_source, fiscal_year
        raise cli.AssessmentServiceError("No data", status_code=404, details={"ticker": ticker})


class _CovenantService:
    def __init__(self, report_dir: str) -> None:
        self.report_dir = report_dir

    def assess(self, ticker: str, data_source: str, fiscal_year: int | None):
        del data_source
        return {
            "ticker": ticker,
            "company_name": "Demo Corp",
            "period": "FY24",
            "ratios": {
                "current_ratio": 2.0,
                "quick_ratio": 1.5,
                "interest_coverage": 4.2,
                "debt_to_ebitda": 2.1,
                "debt_to_equity": 0.6,
                "fcf_to_debt": 0.2,
                "fiscal_year": fiscal_year or 2024,
                "company_name": "Demo Corp",
            },
        }


def test_sources_command(monkeypatch, capsys):
    monkeypatch.setattr(cli, "AssessmentService", _OkService)

    exit_code = cli.main(["sources"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["command"] == "sources"
    assert "yfinance" in payload["data_sources"]


def test_assess_success(monkeypatch, capsys):
    monkeypatch.setattr(cli, "AssessmentService", _OkService)

    exit_code = cli.main(
        [
            "assess",
            "aapl",
            "--data-source",
            "demo",
            "--fiscal-year",
            "2024",
            "--report-dir",
            "data/custom_reports",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["count"] == 1
    assert payload["results"][0]["ticker"] == "AAPL"
    assert payload["results"][0]["data_source"] == "demo"
    assert payload["results"][0]["fiscal_year"] == 2024
    assert payload["results"][0]["report_dir"] == "data/custom_reports"


def test_assess_partial_failure_returns_zero(monkeypatch, capsys):
    monkeypatch.setattr(cli, "AssessmentService", _MixedService)

    exit_code = cli.main(["assess", "AAPL", "BAD"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["count"] == 1
    assert len(payload["errors"]) == 1
    assert payload["errors"][0]["ticker"] == "BAD"
    assert payload["errors"][0]["status_code"] == 404


def test_assess_all_failures_returns_one_and_writes_file(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(cli, "AssessmentService", _FailService)
    output_path = tmp_path / "cli-output.json"

    exit_code = cli.main(["assess", "BAD1", "BAD2", "--output", str(output_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "Wrote output to" in captured.err
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["count"] == 0
    assert len(payload["errors"]) == 2


def test_search_success(monkeypatch, capsys):
    class _FakeSearch:
        def __init__(self, _query: str):
            self.quotes = [
                {"symbol": "MSFLX", "shortname": "Mutual Fund", "quoteType": "MUTUALFUND"},
                {"symbol": "MSFT", "shortname": "Microsoft Corporation", "quoteType": "EQUITY"},
                {"symbol": "msft", "shortname": "Microsoft Duplicate", "quoteType": "EQUITY"},
            ]

    monkeypatch.setitem(sys.modules, "yfinance", type("_YF", (), {"Search": _FakeSearch}))

    exit_code = cli.main(["search", "micro", "--limit", "10"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["command"] == "search"
    assert payload["count"] == 1
    assert payload["results"][0]["symbol"] == "MSFT"


def test_search_upstream_error(monkeypatch, capsys):
    class _BrokenSearch:
        def __init__(self, _query: str):
            raise RuntimeError("upstream unavailable")

    monkeypatch.setitem(sys.modules, "yfinance", type("_YF", (), {"Search": _BrokenSearch}))

    exit_code = cli.main(["search", "micro"])
    captured = capsys.readouterr()

    assert exit_code == 1
    payload = json.loads(captured.out)
    assert payload["command"] == "search"
    assert "error" in payload


def test_covenants_pass(monkeypatch, capsys):
    monkeypatch.setattr(cli, "AssessmentService", _CovenantService)

    exit_code = cli.main(
        [
            "covenants",
            "AAPL",
            "--min-current-ratio",
            "1.2",
            "--max-debt-to-equity",
            "1.0",
            "--min-interest-coverage",
            "3.0",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["command"] == "covenants"
    assert payload["covenants_breached"] == 0
    assert payload["covenants_passed"] == 3


def test_covenants_breach_returns_one(monkeypatch, capsys):
    monkeypatch.setattr(cli, "AssessmentService", _CovenantService)

    exit_code = cli.main(
        [
            "covenants",
            "AAPL",
            "--min-current-ratio",
            "2.5",
            "--max-debt-to-equity",
            "0.5",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    payload = json.loads(captured.out)
    assert payload["command"] == "covenants"
    assert payload["covenants_breached"] == 2


def test_covenants_requires_threshold(capsys):
    exit_code = cli.main(["covenants", "AAPL"])
    captured = capsys.readouterr()

    assert exit_code == 2
    payload = json.loads(captured.out)
    assert payload["command"] == "covenants"
    assert "threshold" in payload["error"].lower()
