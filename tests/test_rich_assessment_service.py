"""Tests for the rich assessment service — fake history end-to-end."""

from __future__ import annotations

import pandas as pd
import pytest

from services import RichAssessmentService
from ratio_analyzer import CreditRatioAnalysis
from src.services.assessment_service import AssessmentServiceError


def _df(values: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame.from_dict(values, orient="index", columns=["Value"])


def _make_fake_financial_data(history: list[dict]) -> dict:
    return {
        "ticker": "TEST",
        "company_name": "Test Corp",
        "market_cap": 50.0,
        "company_profile": {},
        "history": history,
    }


# ── Annual period end-to-end ─────────────────────────────────────────────────

def test_annual_period_end_to_end(monkeypatch):
    """Full pipeline with a single annual period: ratios, assessment, statements all populated."""
    service = RichAssessmentService()

    annual_period = {
        "year_label": "FY24",
        "is_quarterly": False,
        "income": _df({
            "revenue": 1000.0, "cost_of_revenue": 400.0, "gross_profit": 600.0,
            "operating_income": 250.0, "net_income": 200.0, "interest_expense": 25.0,
            "ebitda": 300.0,
        }),
        "balance": _df({
            "total_assets": 2000.0, "total_liabilities": 900.0, "total_equity": 1100.0,
            "total_current_assets": 800.0, "total_current_liabilities": 350.0,
            "cash": 200.0, "inventory": 120.0, "accounts_receivable": 150.0,
            "accounts_payable": 130.0, "total_debt": 600.0, "retained_earnings": 500.0,
        }),
        "cash": _df({
            "operating_cf": 220.0, "free_cf": 180.0,
        }),
    }

    monkeypatch.setattr(
        service, "_fetch_financial_data",
        lambda *_args, **_kwargs: _make_fake_financial_data([annual_period]),
    )

    result = service.analyze(ticker="TEST", data_source="yfinance")

    assert result["ticker"] == "TEST"
    assert result["company_name"] == "Test Corp"
    assert result["currency"] == "USD"
    assert len(result["history"]) == 1

    period = result["history"][0]
    assert period["fiscal_year"] == "FY24"
    assert period["is_quarterly"] is False

    # Assessment fields
    assessment = period["assessment"]
    assert isinstance(assessment, dict)
    assert assessment["risk_score"] is not None
    assert assessment["risk_score"] > 0
    assert assessment["overall_rating"] != "N/A"
    assert assessment["implied_rating"] != "N/A"
    assert "zscore_breakdown" in assessment
    assert len(assessment["zscore_breakdown"]) == 5

    # Ratios are populated
    ratios = period["ratios"]
    assert ratios["current_ratio"] is not None
    assert ratios["debt_to_equity"] is not None
    assert ratios["gross_margin"] is not None

    # Raw metrics populated
    raw = period["raw_metrics"]
    assert raw["total_debt"] is not None
    assert raw["operating_income"] is not None

    # Statements populated
    stmts = period["statements"]
    assert len(stmts["income"]) > 0
    assert len(stmts["balance"]) > 0


# ── USD quarterly annualization ──────────────────────────────────────────────

def test_usd_quarterly_annualizes_income_and_cash_not_balance(monkeypatch):
    """USD quarterly: income/cash flow multiplied by 4, balance sheet unchanged."""
    service = RichAssessmentService()

    quarterly_period = {
        "year_label": "25Q3",
        "is_quarterly": True,
        "income": _df({
            "revenue": 250.0, "operating_income": 62.5, "net_income": 50.0,
            "cost_of_revenue": 100.0, "interest_expense": 6.25, "ebitda": 75.0,
        }),
        "balance": _df({
            "total_assets": 2000.0, "total_liabilities": 900.0, "total_equity": 1100.0,
            "total_current_assets": 800.0, "total_current_liabilities": 350.0,
            "total_debt": 600.0, "retained_earnings": 500.0,
        }),
        "cash": _df({
            "operating_cf": 55.0, "free_cf": 45.0,
        }),
    }

    monkeypatch.setattr(
        service, "_fetch_financial_data",
        lambda *_args, **_kwargs: _make_fake_financial_data([quarterly_period]),
    )

    result = service.analyze(ticker="TEST", data_source="yfinance")
    period = result["history"][0]

    # Statements show annualized values
    stmts = period["statements"]
    assert stmts["income"]["revenue"] == pytest.approx(1000.0, rel=1e-6)   # 250 * 4
    assert stmts["income"]["operating_income"] == pytest.approx(250.0, rel=1e-6)
    assert stmts["income"]["net_income"] == pytest.approx(200.0, rel=1e-6)
    assert stmts["cash"]["operating_cf"] == pytest.approx(220.0, rel=1e-6)  # 55 * 4
    assert stmts["cash"]["free_cf"] == pytest.approx(180.0, rel=1e-6)

    # Balance sheet NOT annualized
    assert stmts["balance"]["total_assets"] == pytest.approx(2000.0, rel=1e-6)


# ── CNY Q3 quarterly annualization factor ─────────────────────────────────────

def test_cny_q3_quarterly_annualize_factor(monkeypatch):
    """CNY Q3: annualize factor = 12/9 for income/cash flow."""
    service = RichAssessmentService()

    quarterly_period = {
        "year_label": "25Q3",
        "is_quarterly": True,
        "income": _df({
            "revenue": 300.0, "operating_income": 75.0, "net_income": 60.0,
            "cost_of_revenue": 120.0, "interest_expense": 7.5, "ebitda": 90.0,
        }),
        "balance": _df({
            "total_assets": 2000.0, "total_liabilities": 900.0, "total_equity": 1100.0,
            "total_current_assets": 800.0, "total_current_liabilities": 350.0,
            "total_debt": 600.0, "retained_earnings": 500.0,
        }),
        "cash": _df({
            "operating_cf": 66.0, "free_cf": 54.0,
        }),
    }

    # _infer_currency returns CNY for 6-digit tickers
    monkeypatch.setattr(
        service, "_fetch_financial_data",
        lambda *_args, **_kwargs: _make_fake_financial_data([quarterly_period]),
    )

    # Use a 6-digit ticker to trigger CNY
    result = service.analyze(ticker="600519", data_source="yfinance")
    period = result["history"][0]

    assert result["currency"] == "CNY"
    factor = 12.0 / 9.0
    stmts = period["statements"]
    assert stmts["income"]["revenue"] == pytest.approx(300.0 * factor, rel=1e-6)


# ── Missing working capital → N/A ─────────────────────────────────────────────

def test_missing_working_capital_gives_na_assessment(monkeypatch):
    """When current assets/liabilities are missing, WC can't be computed → N/A rating."""
    service = RichAssessmentService()

    period = {
        "year_label": "FY24",
        "is_quarterly": False,
        "income": _df({
            "revenue": 1000.0, "operating_income": 250.0, "net_income": 200.0,
        }),
        "balance": _df({
            "total_assets": 2000.0, "total_liabilities": 900.0, "total_equity": 1100.0,
            # No total_current_assets or total_current_liabilities → WC can't be computed
        }),
        "cash": _df({"operating_cf": 220.0, "free_cf": 180.0}),
    }

    monkeypatch.setattr(
        service, "_fetch_financial_data",
        lambda *_args, **_kwargs: _make_fake_financial_data([period]),
    )

    result = service.analyze(ticker="TEST", data_source="yfinance")
    assessment = result["history"][0]["assessment"]
    assert assessment["overall_rating"] == "N/A"


# ── Quarterly N/A falls back to latest FY ─────────────────────────────────────

def test_quarterly_na_falls_back_to_latest_fy(monkeypatch):
    """Quarterly periods with N/A inherit the latest fiscal year assessment."""
    service = RichAssessmentService()

    history = [
        {
            "year_label": "25Q3",
            "is_quarterly": True,
            "income": _df({"revenue": 250.0, "operating_income": 62.5, "net_income": 50.0}),
            # Missing WC → N/A
            "balance": _df({"total_assets": 2000.0, "total_liabilities": 900.0, "total_equity": 1100.0}),
            "cash": _df({"operating_cf": 55.0, "free_cf": 45.0}),
        },
        {
            "year_label": "FY24",
            "is_quarterly": False,
            "income": _df({
                "revenue": 1000.0, "operating_income": 250.0, "net_income": 200.0,
                "cost_of_revenue": 400.0, "interest_expense": 25.0, "ebitda": 300.0,
            }),
            "balance": _df({
                "total_assets": 2000.0, "total_liabilities": 900.0, "total_equity": 1100.0,
                "total_current_assets": 800.0, "total_current_liabilities": 350.0,
                "total_debt": 600.0, "retained_earnings": 500.0,
            }),
            "cash": _df({"operating_cf": 220.0, "free_cf": 180.0}),
        },
    ]

    monkeypatch.setattr(
        service, "_fetch_financial_data",
        lambda *_args, **_kwargs: _make_fake_financial_data(history),
    )

    result = service.analyze(ticker="TEST", data_source="yfinance")
    quarterly = next(p for p in result["history"] if p["is_quarterly"])
    annual = next(p for p in result["history"] if not p["is_quarterly"])

    assert quarterly["assessment"]["overall_rating"] != "N/A"
    assert quarterly["assessment"]["overall_rating"] == annual["assessment"]["overall_rating"]


# ── All periods fail → 422 ───────────────────────────────────────────────────

def test_all_periods_fail_raises_calculation_failed(monkeypatch):
    """When every period fails ratio calculation, AssessmentServiceError(422) is raised."""
    service = RichAssessmentService()

    # Balance sheet missing total_assets/total_equity → calculate_all_ratios will fail validation
    period = {
        "year_label": "FY24",
        "is_quarterly": False,
        "income": _df({"revenue": 1000.0}),
        "balance": _df({"total_debt": 600.0}),  # Missing required total_assets, total_equity
        "cash": _df({"operating_cf": 220.0}),
    }

    monkeypatch.setattr(
        service, "_fetch_financial_data",
        lambda *_args, **_kwargs: _make_fake_financial_data([period]),
    )

    with pytest.raises(AssessmentServiceError) as exc_info:
        service.analyze(ticker="TEST", data_source="yfinance")

    assert exc_info.value.status_code == 422
    assert exc_info.value.details.get("error_type") == "calculation_failed"


# ── Existing tests (kept) ────────────────────────────────────────────────────

def _assert_history_entry_structure(period: dict[str, object]) -> None:
    assert "fiscal_year" in period
    assert "is_quarterly" in period
    assert "assessment" in period
    assert "ratios" in period
    assert "raw_metrics" in period
    assert "statements" in period


def test_demo_payload_contains_multiple_periods():
    payload = RichAssessmentService._build_demo_data("DEMO")
    history = payload["history"]
    assert len(history) >= 5
    assert history[0]["is_quarterly"] is True
    assert [entry["year_label"] for entry in history[:5]] == ["25Q3", "24Q3", "FY24", "FY23", "FY22"]
    assert history[1]["income"].shape[0] >= 10
    assert history[1]["balance"].shape[0] >= 10
    assert history[1]["cash"].shape[0] >= 10


def test_analyze_with_demo_source():
    service = RichAssessmentService()
    result = service.analyze(ticker="DEMO", data_source="demo")
    assert result["ticker"] == "DEMO"
    assert result["company_name"]
    assert result["currency"] == "USD"
    assert len(result["history"]) >= 5
    for period in result["history"]:
        _assert_history_entry_structure(period)
        assert isinstance(period["ratios"], dict)
        assert isinstance(period["statements"], dict)


def test_analyze_with_empty_ticker():
    service = RichAssessmentService()
    with pytest.raises(AssessmentServiceError) as exc_info:
        service.analyze(ticker="", data_source="demo")
    assert exc_info.value.status_code == 422


def test_analyze_with_invalid_source():
    service = RichAssessmentService()
    with pytest.raises(AssessmentServiceError) as exc_info:
        service.analyze(ticker="DEMO", data_source="invalid_source")
    assert exc_info.value.status_code == 422


def test_analyze_with_empty_history_raises_404(monkeypatch):
    service = RichAssessmentService()
    monkeypatch.setattr(
        service, "_fetch_financial_data",
        lambda *_args, **_kwargs: {"ticker": "DEMO", "company_name": "Demo", "history": []},
    )
    with pytest.raises(AssessmentServiceError) as exc_info:
        service.analyze(ticker="DEMO", data_source="demo")
    assert exc_info.value.status_code == 404


def test_covenant_pre_check_missing_metric_defaults_breach():
    service = RichAssessmentService()
    balance_df = pd.DataFrame(
        {"Value": [100.0, 40.0, 60.0, 20.0, 10.0, 5.0]},
        index=[
            "total_assets", "total_liabilities", "total_current_assets",
            "total_current_liabilities", "retained_earnings", "total_debt",
        ],
    )
    income_df = pd.DataFrame(
        {"Value": [15.0, 5.0]},
        index=["operating_income", "interest_expense"],
    )

    class FakeRatios:
        revenue = 80.0
        debt_to_ebitda = None
        interest_coverage = None
        current_ratio = 1.5
        fcf_to_debt = None
        ebitda = None

    assessment = service._build_assessment(balance_df, income_df, FakeRatios(), market_cap=50.0)
    pre_check = assessment.get("covenant_pre_check", [])
    missing_checks = [c for c in pre_check if c["actual"] is None]
    assert len(missing_checks) > 0
    for check in missing_checks:
        assert check["status"] == "Breach"
        assert check["signal"] == "Red"
        assert "defaulting to breach" in check.get("notes", "")


def test_analyze_quarterly_assessment_falls_back_to_latest_fy(monkeypatch):
    service = RichAssessmentService()
    history = [
        {
            "year_label": "25Q3",
            "is_quarterly": True,
            "income": pd.DataFrame(),
            "balance": pd.DataFrame(),
            "cash": pd.DataFrame(),
        },
        {
            "year_label": "FY24",
            "is_quarterly": False,
            "income": pd.DataFrame(),
            "balance": pd.DataFrame(),
            "cash": pd.DataFrame(),
        },
    ]
    monkeypatch.setattr(
        service, "_fetch_financial_data",
        lambda *_args, **_kwargs: {
            "ticker": "DEMO", "company_name": "Demo", "company_profile": {},
            "market_cap": 1.0, "history": history,
        },
    )
    monkeypatch.setattr(service, "_calculate_ratios", lambda *_args, **_kwargs: CreditRatioAnalysis())
    monkeypatch.setattr(service, "_build_raw_metrics", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(service, "_statement_values", lambda *_args, **_kwargs: {})

    call_count = {"value": 0}

    def _fake_build_assessment(*_args, **_kwargs):
        call_count["value"] += 1
        if call_count["value"] == 1:
            return {"overall_rating": "N/A", "risk_score": None}
        return {"overall_rating": "BBB", "risk_score": 1.0}

    monkeypatch.setattr(service, "_build_assessment", _fake_build_assessment)

    result = service.analyze(ticker="DEMO", data_source="demo")
    quarterly = next(period for period in result["history"] if period["is_quarterly"])
    annual = next(period for period in result["history"] if not period["is_quarterly"])
    assert quarterly["assessment"]["overall_rating"] == "BBB"
    assert annual["assessment"]["overall_rating"] == "BBB"


# ── Data Quality (Partial Period Success) ──────────────────────────────────────

def test_data_quality_partial_when_some_periods_fail(monkeypatch):
    """When some periods fail and some succeed, data_quality.status == 'partial'."""
    service = RichAssessmentService()

    period_good = {
        "year_label": "FY24",
        "is_quarterly": False,
        "income": _df({
            "revenue": 1000.0, "cost_of_revenue": 400.0, "gross_profit": 600.0,
            "operating_income": 250.0, "net_income": 200.0, "interest_expense": 25.0,
            "ebitda": 300.0,
        }),
        "balance": _df({
            "total_assets": 2000.0, "total_liabilities": 900.0, "total_equity": 1100.0,
            "total_current_assets": 800.0, "total_current_liabilities": 350.0,
            "cash": 200.0, "inventory": 120.0, "accounts_receivable": 150.0,
            "accounts_payable": 130.0, "total_debt": 600.0, "retained_earnings": 500.0,
        }),
        "cash": _df({"operating_cf": 220.0, "free_cf": 180.0}),
    }

    period_bad = {
        "year_label": "FY23",
        "is_quarterly": False,
        "income": None,  # Will cause an exception when processing
        "balance": None,
        "cash": None,
    }

    monkeypatch.setattr(
        service, "_fetch_financial_data",
        lambda *_args, **_kwargs: _make_fake_financial_data([period_good, period_bad]),
    )

    result = service.analyze(ticker="TEST", data_source="yfinance")
    assert "data_quality" in result
    dq = result["data_quality"]
    assert dq["status"] == "partial"
    assert len(dq["failed_periods"]) == 1
    assert "FY23" in dq["failed_periods"]
    assert dq["latest_period_valid"] is True


def test_data_quality_complete_when_all_periods_succeed(monkeypatch):
    """When all periods succeed, data_quality.status == 'complete'."""
    service = RichAssessmentService()

    period = {
        "year_label": "FY24",
        "is_quarterly": False,
        "income": _df({
            "revenue": 1000.0, "cost_of_revenue": 400.0, "gross_profit": 600.0,
            "operating_income": 250.0, "net_income": 200.0, "interest_expense": 25.0,
            "ebitda": 300.0,
        }),
        "balance": _df({
            "total_assets": 2000.0, "total_liabilities": 900.0, "total_equity": 1100.0,
            "total_current_assets": 800.0, "total_current_liabilities": 350.0,
            "cash": 200.0, "total_debt": 600.0, "retained_earnings": 500.0,
        }),
        "cash": _df({"operating_cf": 220.0, "free_cf": 180.0}),
    }

    monkeypatch.setattr(
        service, "_fetch_financial_data",
        lambda *_args, **_kwargs: _make_fake_financial_data([period]),
    )

    result = service.analyze(ticker="TEST", data_source="yfinance")
    assert "data_quality" in result
    dq = result["data_quality"]
    assert dq["status"] == "complete"
    assert dq["failed_periods"] == []
    assert dq["latest_period_valid"] is True


def test_failed_period_uses_safe_reason_code(monkeypatch):
    """Failed periods should use safe reason codes, not raw exception strings."""
    service = RichAssessmentService()

    period_bad = {
        "year_label": "FY23",
        "is_quarterly": False,
        "income": None,
        "balance": None,
        "cash": None,
    }

    period_good = {
        "year_label": "FY24",
        "is_quarterly": False,
        "income": _df({
            "revenue": 1000.0, "cost_of_revenue": 400.0, "gross_profit": 600.0,
            "operating_income": 250.0, "net_income": 200.0, "interest_expense": 25.0,
            "ebitda": 300.0,
        }),
        "balance": _df({
            "total_assets": 2000.0, "total_liabilities": 900.0, "total_equity": 1100.0,
            "total_current_assets": 800.0, "total_current_liabilities": 350.0,
            "cash": 200.0, "total_debt": 600.0, "retained_earnings": 500.0,
        }),
        "cash": _df({"operating_cf": 220.0, "free_cf": 180.0}),
    }

    monkeypatch.setattr(
        service, "_fetch_financial_data",
        lambda *_args, **_kwargs: _make_fake_financial_data([period_good, period_bad]),
    )

    result = service.analyze(ticker="TEST", data_source="yfinance")
    failed = next(p for p in result["history"] if p.get("error"))
    # Should be a safe code like "calculation_error" or "insufficient_data"
    assert failed["error"] in ("calculation_error", "insufficient_data")
    assert "NoneType" not in failed["error"]
    assert "AttributeError" not in failed["error"]
