"""Tests for PDF export formatting."""

from __future__ import annotations

import importlib.util
import os
import sys
import shutil
import subprocess

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

import pdf_exporter
from reportlab_pdf_renderer import _render_reportlab_pdf
from pdf_exporter import _build_yoy_map, _is_negative_display_value, generate_full_pdf


REPORTLAB_AVAILABLE = importlib.util.find_spec("reportlab") is not None


def _statement_rows(prefix: str, count: int) -> dict[str, float]:
    return {f"{prefix}_{idx}": float(idx + 1) * 100.0 for idx in range(count)}


def _build_report() -> dict:
    income_keys = _statement_rows("income", 16)
    balance_keys = _statement_rows("balance", 16)
    cash_keys = _statement_rows("cash", 16)

    history = [
        {
            "fiscal_year": "25Q3",
            "is_quarterly": True,
            "assessment": {
                "risk_score": 4.56,
                "overall_rating": "Safe (S)",
                "implied_rating": "A",
                "strengths": ["Strong cash flow", "Low leverage"],
                "weaknesses": ["Watch liquidity"],
            },
            "ratios": {
                "interest_coverage": 5.2,
                "debt_to_ebitda": 2.1,
                "current_ratio": 1.4,
                "fcf_to_debt": 0.22,
            },
            "raw_metrics": {
                "operating_income": 18_300_000.0,
                "total_debt": 26_000_000.0,
                "free_cf": 7_800_000.0,
            },
            "statements": {
                "income": income_keys,
                "balance": balance_keys,
                "cash": cash_keys,
            },
        },
        {
            "fiscal_year": "24Q3",
            "is_quarterly": True,
            "assessment": {
                "risk_score": 4.32,
                "overall_rating": "Grey (G)",
                "implied_rating": "BBB+",
                "strengths": ["Seasonal demand stable"],
                "weaknesses": ["Quarterly leverage remains elevated"],
            },
            "ratios": {
                "interest_coverage": 4.8,
                "debt_to_ebitda": 2.5,
                "current_ratio": 1.25,
                "fcf_to_debt": 0.2,
            },
            "raw_metrics": {
                "operating_income": 16_900_000.0,
                "total_debt": 27_500_000.0,
                "free_cf": 6_900_000.0,
            },
            "statements": {
                "income": income_keys,
                "balance": balance_keys,
                "cash": cash_keys,
            },
        },
        {
            "fiscal_year": "FY24",
            "is_quarterly": False,
            "assessment": {
                "risk_score": 4.10,
                "overall_rating": "Grey (G)",
                "implied_rating": "BBB",
                "strengths": ["Stable revenue"],
                "weaknesses": ["Higher leverage"],
            },
            "ratios": {
                "interest_coverage": 4.3,
                "debt_to_ebitda": 2.7,
                "current_ratio": 1.2,
                "fcf_to_debt": 0.18,
            },
            "raw_metrics": {
                "operating_income": 17_000_000.0,
                "total_debt": 28_000_000.0,
                "free_cf": 6_400_000.0,
            },
            "statements": {
                "income": income_keys,
                "balance": balance_keys,
                "cash": cash_keys,
            },
        },
        {
            "fiscal_year": "FY23",
            "is_quarterly": False,
            "assessment": {
                "risk_score": 3.88,
                "overall_rating": "Grey (G)",
                "implied_rating": "BBB",
                "strengths": ["Positive FCF"],
                "weaknesses": ["Liquidity dipped"],
            },
            "ratios": {
                "interest_coverage": 3.9,
                "debt_to_ebitda": 3.0,
                "current_ratio": 1.1,
                "fcf_to_debt": 0.15,
            },
            "raw_metrics": {
                "operating_income": 15_700_000.0,
                "total_debt": 29_500_000.0,
                "free_cf": 5_100_000.0,
            },
            "statements": {
                "income": income_keys,
                "balance": balance_keys,
                "cash": cash_keys,
            },
        },
        {
            "fiscal_year": "FY22",
            "is_quarterly": False,
            "assessment": {
                "risk_score": 3.55,
                "overall_rating": "Grey (G)",
                "implied_rating": "BBB-",
                "strengths": ["Recurring cash generation"],
                "weaknesses": ["Higher working capital needs"],
            },
            "ratios": {
                "interest_coverage": 3.5,
                "debt_to_ebitda": 3.2,
                "current_ratio": 1.0,
                "fcf_to_debt": 0.12,
            },
            "raw_metrics": {
                "operating_income": 14_100_000.0,
                "total_debt": 31_000_000.0,
                "free_cf": 4_600_000.0,
            },
            "statements": {
                "income": income_keys,
                "balance": balance_keys,
                "cash": cash_keys,
            },
        },
    ]

    return {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "currency": "USD",
        "company_profile": {
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "country": "US",
            "employees": 161000,
            "website": "https://apple.com",
        },
        "history": history,
    }


def test_build_yoy_map_handles_quarter_and_annual_history():
    history = _build_report()["history"]
    yoy_map = _build_yoy_map(history)

    assert len(yoy_map) == 2
    assert yoy_map[0]["yearCode"] == "25Q3"
    assert yoy_map[0]["prevYearCode"] == "24Q3"
    assert yoy_map[1]["yearCode"] == "FY24"
    assert yoy_map[1]["prevYearCode"] == "FY23"


def test_negative_display_helper_ignores_placeholders():
    assert _is_negative_display_value("-12.3")
    assert _is_negative_display_value(" -12.3 ")
    assert not _is_negative_display_value("--")
    assert not _is_negative_display_value("")


def test_build_pdf_document_model_cleans_profile_labels():
    report = _build_report()
    report["company_profile"] = {
        "sector.": "Technology",
        "industry:": "Consumer Electronics",
        "country。": "US",
    }

    model = pdf_exporter.build_pdf_document_model(report, "en")

    assert [row["label"] for row in model["summary"]["company_profile_rows"]] == [
        "Sector",
        "Industry",
        "Country",
    ]
    assert model["statements"][0]["rows"][0]["label"] == "Income 0"
    assert model["kpi"]["headers"][2] == "Q3 FY24"


def test_generate_full_pdf_rejects_invalid_numeric_payload():
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    report = _build_report()
    report["history"][0]["raw_metrics"]["debt_ebitda"] = "18..60x"

    with pytest.raises(ValueError, match="Invalid numeric value"):
        generate_full_pdf(report, lang="en")


def test_generate_full_pdf_rejects_inline_breaks():
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    report = _build_report()
    report["history"][0]["statements"]["income"]["income\nSplit"] = 100

    with pytest.raises(ValueError, match="FATAL: 渲染层拒绝接收硬合并的多行数据"):
        pdf_exporter.build_pdf_document_model(report, lang="en")


def test_generate_full_pdf_rejects_merged_metric_labels():
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    report = _build_report()
    report["history"][0]["statements"]["income"]["income_0"] = {
        "label": "Income 2 Income 3",
        "value": 300,
    }

    with pytest.raises(ValueError, match="Merged metric text"):
        pdf_exporter.build_pdf_document_model(report, lang="en")


def test_reportlab_renderer_rejects_inline_breaks_in_sanitized_model():
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    model = pdf_exporter.build_pdf_document_model(_build_report(), "en")
    model["kpi"]["rows"][0][0] = "Metric\nSplit"

    with pytest.raises(ValueError, match="FATAL: Renderer rejects hard-merged multiline data"):
        _render_reportlab_pdf(model)


def test_reportlab_renderer_pads_cover_hero_slots():
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    model = pdf_exporter.build_pdf_document_model(_build_report(), "en")
    model["cover"]["hero_summary"]["items"] = [
        {"label": "Only Slot", "value": "1.0", "tone": "info"},
    ]

    pdf_bytes = _render_reportlab_pdf(model)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 8000


def test_generate_full_pdf_renders_empty_statement_pages_without_table_headers(tmp_path):
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")

    pdf_bytes = generate_full_pdf(_build_report(), lang="en")
    pdf_file = tmp_path / "empty-state.pdf"
    pdf_file.write_bytes(pdf_bytes)

    if shutil.which("pdftotext"):
        extracted = subprocess.check_output(["pdftotext", str(pdf_file), "-"], text=True)
        pages = extracted.split("\f")
        assert len(pages) >= 7
        assert "RiskLens Financial Report" not in pages[0]
        assert "Apple Inc." in pages[0]
        assert "Contents" not in pages[0]
        assert "Methodology Note" not in pages[0]
        assert "Q3'25 vs Q3'24" in extracted
        assert "FY24 vs FY23" in extracted
        empty_pages = [page for page in pages if ("Balance Sheet" in page or "Cash Flow Statement" in page) and "[No valid data provided for this period]" in page]
        assert len(empty_pages) >= 2
        assert all("Metric" in page for page in empty_pages)
        assert all("YoY" not in page for page in empty_pages)


@pytest.mark.parametrize("lang", ["en", "zh-CN", "zh-TW", "ja"])
def test_generate_full_pdf_supports_all_languages(lang):
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    pdf_bytes = generate_full_pdf(_build_report(), lang=lang)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 8000
    assert pdf_bytes.count(b"/Type /Page") >= 5


def test_generate_full_pdf_supports_light_theme():
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    model = pdf_exporter.build_pdf_document_model(_build_report(), "en", "light")
    assert model["theme"] == "light"
    assert model["context"]["theme"] == "light"
    pdf_bytes = generate_full_pdf(_build_report(), lang="en", theme="light")
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 8000


def test_generate_full_pdf_rejects_empty_history():
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    report = _build_report()
    report["history"] = []

    with pytest.raises(ValueError, match="No history available"):
        generate_full_pdf(report, lang="en")
