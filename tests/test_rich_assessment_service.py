"""Tests for the rich assessment service demo payload."""

from __future__ import annotations

import pandas as pd
import pytest

from services import RichAssessmentService
from ratio_analyzer import CreditRatioAnalysis
from src.services.assessment_service import AssessmentServiceError


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
        service,
        "_fetch_financial_data",
        lambda *_args, **_kwargs: {"ticker": "DEMO", "company_name": "Demo", "history": []},
    )

    with pytest.raises(AssessmentServiceError) as exc_info:
        service.analyze(ticker="DEMO", data_source="demo")

    assert exc_info.value.status_code == 404


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
        service,
        "_fetch_financial_data",
        lambda *_args, **_kwargs: {
            "ticker": "DEMO",
            "company_name": "Demo",
            "company_profile": {},
            "market_cap": 1.0,
            "history": history,
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
