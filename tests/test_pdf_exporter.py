"""Tests for PDF export formatting."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import shutil
import subprocess
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

import src.html_pdf_exporter as html_pdf_exporter
import src.pdf_report_core as pdf_report_core
import src.reportlab_pdf_exporter as reportlab_pdf_exporter
from src.reportlab_pdf_exporter import generate_full_pdf
from src.reportlab_pdf_renderer import _render_reportlab_pdf
from src.pdf_report_core import _build_yoy_map, _is_negative_display_value


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

    model = pdf_report_core.build_pdf_document_model(report, "en")

    assert [row["label"] for row in model["summary"]["company_profile_rows"]] == [
        "Sector",
        "Industry",
        "Country",
    ]
    assert model["statements"][0]["rows"][0]["label"] == "Income 0"
    assert model["kpi"]["headers"][2] == "Q3 FY24"


def test_normalize_statement_rows_splits_merged_label_and_value_lines():
    rows = html_pdf_exporter._normalize_statement_rows([
        {
            "label": "EBITDA\nEBIT\nNet Interest Income",
            "value": "160.2B\n126.0B\n262.0M",
        }
    ])

    assert [row["label"] for row in rows] == ["EBITDA", "EBIT", "Net Interest Income"]
    assert [row["value"] for row in rows] == ["160.2B", "126.0B", "262.0M"]


def test_build_pdf_document_model_normalizes_statement_labels():
    report = _build_report()
    report["history"][0]["statements"]["balance"] = {
        "tradeand_other_payables_non_current": 26_000_000_000.0,
        "gross_ppe": 100_000_000_000.0,
        "diluted_ni_availto_com_stockholders": 101_800_000_000.0,
    }
    report["history"][0]["statements"]["cash"] = {
        "free_cf": 71_611_000_000.0,
        "operating_cf": 136_200_000_000.0,
    }

    model = pdf_report_core.build_pdf_document_model(report, "en")

    balance_labels = [row["label"] for row in model["statements"][1]["rows"][:3]]
    assert balance_labels == [
        "Trade and Other Payables Non Current",
        "Gross PPE",
        "Diluted NI Avail to Com Stockholders",
    ]
    cash_labels = [row["label"] for row in model["statements"][2]["rows"][:2]]
    assert cash_labels == ["Free CF", "Operating CF"]


def test_build_pdf_document_model_exposes_statement_levels():
    report = _build_report()
    report["history"][0]["statements"]["balance"] = {
        "current_assets": 100_000_000.0,
        "total_assets": 200_000_000.0,
        "current_liabilities": 50_000_000.0,
        "total_liabilities": 125_000_000.0,
    }

    model = pdf_report_core.build_pdf_document_model(report, "en")

    balance_rows = model["statements"][1]["detail_rows"]
    levels = {row["label"]: row["level"] for row in balance_rows if row["label"] in {"Current Assets", "Total Assets", "Current Liabilities", "Total Liabilities"}}

    assert levels["Total Assets"] == 0
    assert levels["Total Liabilities"] == 0
    assert levels["Current Assets"] == 1
    assert levels["Current Liabilities"] == 1


def test_build_pdf_document_model_validates_statement_table_matrix():
    report = _build_report()
    model = html_pdf_exporter.build_pdf_document_model(report, "en")
    model["statements"][0]["rows"][0]["summary_display_values"] = ["105.2"]

    with pytest.raises(ValueError, match="PDF table row length mismatch"):
        pdf_report_core._sanitize_pdf_document_model(model)


def test_build_pdf_document_model_separates_magnitude_units_and_repairs_ocr_suffixes(tmp_path):
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")

    report = _build_report()
    report["history"] = [report["history"][0]]
    report["history"][0]["statements"]["income"] = [
        {"label": "Normalized EBITDA", "value": "105.28"},
        {"label": "EBIT", "value": "110.78"},
        {"label": "Revenue", "value": "245.18"},
        {"label": "Cost of Revenue", "value": "87.88"},
        {"label": "Tax Rate for Calcs", "value": "0.18"},
    ]

    model = pdf_report_core.build_pdf_document_model(report, "en")

    income_rows = model["statements"][0]["detail_rows"][:5]
    assert [row["values"][0] for row in income_rows] == [
        "105,200",
        "110,700",
        "245,100",
        "87,800",
        "0.18",
    ]
    assert model["kpi"]["rows"][0][1] == "0.02"
    assert model["kpi"]["unit_note"] == "Values in USD billions; ratios in x"
    assert model["statements"][0]["unit_note"] == "Values in USD billions; ratios in x"
    assert model["statements"][0]["detail_unit_note"] == "Values in USD millions"
    assert income_rows[0]["summary_display_values"][0] == "105.2"
    assert income_rows[0]["detail_display_values"][0] == "105,200"

    pdf_bytes = generate_full_pdf(report, lang="en")
    pdf_file = tmp_path / "statement-unit-repair.pdf"
    pdf_file.write_bytes(pdf_bytes)

    if shutil.which("pdftotext"):
        extracted = subprocess.check_output(["pdftotext", str(pdf_file), "-"], text=True)
        normalized = re.sub(r"\s+", " ", extracted)
        assert "105.2" in normalized
        assert "110.7" in normalized
        assert "245.1" in normalized
        assert "87,800" in normalized
        assert "0.18" in normalized
        assert "105.28" not in normalized
    assert html_pdf_exporter._format_statement_display_value("269.0. M", "Other Non Operating Income Expenses") == "269"
    assert html_pdf_exporter._format_statement_display_value("76.7\nB", "Net Debt") == "76,700"
    assert html_pdf_exporter._format_statement_display_value("-0,06", "Working Capital") == "-0.06"


def test_generate_full_pdf_rejects_invalid_numeric_payload():
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    report = _build_report()
    report["history"][0]["raw_metrics"]["debt_ebitda"] = "18..60x"

    with pytest.raises(ValueError, match="Invalid numeric value"):
        generate_full_pdf(report, lang="en")


def test_generate_full_pdf_rejects_company_identity_mismatch():
    report = _build_report()
    report["company_profile"]["ticker"] = "MSFT"

    with pytest.raises(ValueError, match="Company profile ticker mismatch"):
        generate_full_pdf(report, lang="en")


def test_generate_full_pdf_rejects_history_identity_mismatch():
    report = _build_report()
    report["history"][0]["ticker"] = "MSFT"

    with pytest.raises(ValueError, match="History entry 1 ticker mismatch"):
        generate_full_pdf(report, lang="en")


def test_generate_full_pdf_hides_empty_data_quality_panel(tmp_path):
    report = _build_report()
    report["history"][0]["assessment"]["data_quality"] = []

    pdf_bytes = generate_full_pdf(report, lang="en")
    pdf_file = tmp_path / "no-data-quality.pdf"
    pdf_file.write_bytes(pdf_bytes)

    if shutil.which("pdftotext"):
        extracted = subprocess.check_output(["pdftotext", "-layout", str(pdf_file), "-"], text=True)
        assert "Data Quality" not in extracted


def test_generate_full_pdf_accepts_multiline_statement_rows(tmp_path):
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    report = _build_report()
    report["history"] = [report["history"][0]]
    report["history"][0]["statements"]["income"] = [
        {
            "label": "EBITDA\nEBIT\nNet Interest Income",
            "value": "160.2B\n126.0B\n262.0M",
        }
    ]
    report["history"][0]["statements"]["balance"] = [
        {
            "label": "Tradeand Other Payables Non Current",
            "value": "26.0B",
        }
    ]

    model = pdf_report_core.build_pdf_document_model(report, lang="en")

    assert [row["label"] for row in model["statements"][0]["detail_rows"]] == ["EBITDA", "EBIT", "Net Interest Income"]
    assert [row["values"][0] for row in model["statements"][0]["detail_rows"]] == [
        "160,200",
        "126,000",
        "262",
    ]

    pdf_bytes = generate_full_pdf(report, lang="en")
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 8000

    pdf_file = tmp_path / "multiline-statement.pdf"
    pdf_file.write_bytes(pdf_bytes)
    if shutil.which("pdftotext"):
        extracted = subprocess.check_output(["pdftotext", str(pdf_file), "-"], text=True)
        normalized = re.sub(r"\s+", " ", extracted)
        assert "EBITDA" in normalized
        assert "Net Interest Income" in normalized


def test_generate_full_pdf_rejects_inline_breaks_outside_statements():
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    report = _build_report()
    report["company_name"] = "Alpha\nBeta"

    with pytest.raises(ValueError, match="FATAL: 渲染层拒绝接收硬合并的多行数据"):
        pdf_report_core.build_pdf_document_model(report, lang="en")


def test_generate_full_pdf_rejects_merged_metric_labels():
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    report = _build_report()
    report["history"][0]["statements"]["income"]["income_0"] = {
        "label": "Income 2 Income 3",
        "value": 300,
    }

    with pytest.raises(ValueError, match="Merged metric text"):
        pdf_report_core.build_pdf_document_model(report, lang="en")


def test_reportlab_renderer_rejects_inline_breaks_in_sanitized_model():
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    model = pdf_report_core.build_pdf_document_model(_build_report(), "en")
    model["kpi"]["rows"][0][0] = "Metric\nSplit"

    with pytest.raises(ValueError, match="FATAL: Renderer rejects hard-merged multiline data"):
        _render_reportlab_pdf(model)


def test_reportlab_renderer_pads_cover_hero_slots():
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    model = pdf_report_core.build_pdf_document_model(_build_report(), "en")
    model["cover"]["hero_summary"]["items"] = [
        {"label": "Only Slot", "value": "1.0", "tone": "info"},
    ]

    pdf_bytes = _render_reportlab_pdf(model)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 8000


def test_generate_full_pdf_renders_empty_statement_pages_without_table_headers(tmp_path):
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")

    report = _build_report()
    for entry in report["history"]:
        entry["statements"]["balance"] = {}
        entry["statements"]["cash"] = {}

    pdf_bytes = generate_full_pdf(report, lang="en")
    pdf_file = tmp_path / "empty-state.pdf"
    pdf_file.write_bytes(pdf_bytes)

    if shutil.which("pdftotext"):
        extracted = subprocess.check_output(["pdftotext", str(pdf_file), "-"], text=True)
        pages = extracted.split("\f")
        assert len(pages) >= 6
        assert "RiskLens Financial Report" not in pages[0]
        assert "Apple Inc." in pages[0]
        assert "Contents" not in pages[0]
        assert "Methodology Note" not in pages[0]
        empty_pages = [page for page in pages if ("Balance Sheet" in page or "Cash Flow Statement" in page) and "[No valid data provided for this period]" in page]
        assert len(empty_pages) == 0


def test_generate_full_pdf_renders_normalized_statement_labels(tmp_path):
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")

    report = _build_report()
    report["history"][0]["statements"]["income"] = {
        "ebitda": 160_165_000_000.0,
        "ebit": 126_012_000_000.0,
        "net_interest_income": 262_000_000.0,
    }
    report["history"][0]["statements"]["balance"] = {
        "tradeand_other_payables_non_current": 26_000_000_000.0,
        "gross_ppe": 100_000_000_000.0,
    }
    report["history"][0]["statements"]["cash"] = {
        "free_cf": 71_611_000_000.0,
        "operating_cf": 136_200_000_000.0,
    }

    pdf_bytes = generate_full_pdf(report, lang="en")
    pdf_file = tmp_path / "normalized-statement-labels.pdf"
    pdf_file.write_bytes(pdf_bytes)

    if shutil.which("pdftotext"):
        extracted = subprocess.check_output(["pdftotext", str(pdf_file), "-"], text=True)
        normalized = re.sub(r"\s+", " ", extracted)
        assert "Trade and Other Payables Non Current" in normalized
        assert "Gross PPE" in normalized
        assert "Free CF" in normalized
        assert "Operating CF" in normalized
        assert "EBITDA" in normalized
        assert "Net Interest Income" in normalized


def test_generate_full_pdf_keeps_long_statement_rows_and_interest_expense_alignment(tmp_path):
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")

    report = {
        "ticker": "MSFT",
        "company_name": "Microsoft Corp.",
        "currency": "USD",
        "history": [
            {
                "fiscal_year": "FY25",
                "assessment": {
                    "altman_z_score": 4.2,
                    "zone": "Safe",
                    "implied_rating": "AAA",
                    "strengths": ["Strong cash generation"],
                    "weaknesses": ["None"],
                },
                "ratios": {
                    "debt_to_ebitda": 0.38,
                    "interest_coverage": 53.9,
                    "fcf_to_debt": 1.18,
                    "current_ratio": 1.35,
                },
                "raw_metrics": {
                    "ebit": 126_012_000_000.0,
                    "ebitda": 160_165_000_000.0,
                    "total_debt": 60_600_000_000.0,
                    "free_cf": 71_611_000_000.0,
                },
                "statements": {
                    "income_statement": [
                        {"label": "Tax Effect of Unusual Items", "value": -77_100_000.0},
                        {"label": "Tax Rate for Calcs", "value": 0.18},
                        {"label": "Normalized EBITDA", "value": 160_600_000_000.0},
                        {"label": "Total Unusual Items", "value": -438_000_000.0},
                        {"label": "EBIT", "value": 126_000_000_000.0},
                        {"label": "Net Interest Income", "value": 262_000_000.0},
                        {"label": "Diluted Average Shares", "value": 7_500_000_000.0},
                        {"label": "Basic Average Shares", "value": 7_400_000_000.0},
                        {"label": "Interest Expense", "value": 2_354_000_000.0},
                    ],
                    "balance_sheet": [
                        {"label": "Net Tangible Assets", "value": 201_400_000_000.0},
                        {"label": "Total Equity", "value": 343_500_000_000.0},
                        {"label": "Retained Earnings", "value": 237_700_000_000.0},
                        {"label": "Total Liabilities", "value": 275_500_000_000.0},
                        {"label": "Other Current Assets", "value": 25_700_000_000.0},
                        {"label": "Hedging Assets Current", "value": 10_000_000.0},
                        {"label": "Inventory", "value": 938_000_000.0},
                        {"label": "Accounts Receivable", "value": 69_900_000_000.0},
                    ],
                    "cash_flow_statement": [
                        {"label": "Sale of Investment", "value": 25_400_000_000.0},
                        {"label": "Purchase of Investment", "value": -29_800_000_000.0},
                        {"label": "Net Business Purchase and Sale", "value": -6_000_000_000.0},
                        {"label": "Net PPE Purchase and Sale", "value": -64_600_000_000.0},
                        {"label": "Finished Goods", "value": None},
                        {"label": "Work in Process", "value": None},
                        {"label": "Raw Materials", "value": None},
                    ],
                },
            },
            {
                "fiscal_year": "FY24",
                "assessment": {
                    "altman_z_score": 4.0,
                    "zone": "Safe",
                    "implied_rating": "AAA",
                    "strengths": ["Strong cash generation"],
                    "weaknesses": ["None"],
                },
                "ratios": {
                    "debt_to_ebitda": 0.50,
                    "interest_coverage": 37.3,
                    "fcf_to_debt": 1.10,
                    "current_ratio": 1.27,
                },
                "raw_metrics": {
                    "ebit": 110_700_000_000.0,
                    "ebitda": 133_000_000_000.0,
                    "total_debt": 67_100_000_000.0,
                    "free_cf": 74_100_000_000.0,
                },
                "statements": {
                    "income_statement": [
                        {"label": "Tax Effect of Unusual Items", "value": -99_900_000.0},
                        {"label": "Tax Rate for Calcs", "value": 0.18},
                        {"label": "Normalized EBITDA", "value": 133_600_000_000.0},
                        {"label": "Total Unusual Items", "value": -549_000_000.0},
                        {"label": "EBIT", "value": 110_700_000_000.0},
                        {"label": "Net Interest Income", "value": 222_000_000.0},
                        {"label": "Diluted Average Shares", "value": 7_500_000_000.0},
                        {"label": "Basic Average Shares", "value": 7_400_000_000.0},
                        {"label": "Interest Expense", "value": 2_895_000_000.0},
                    ],
                    "balance_sheet": [
                        {"label": "Net Tangible Assets", "value": 121_700_000_000.0},
                        {"label": "Total Equity", "value": 268_500_000_000.0},
                        {"label": "Retained Earnings", "value": 173_100_000_000.0},
                        {"label": "Total Liabilities", "value": 243_700_000_000.0},
                        {"label": "Other Current Assets", "value": 26_000_000_000.0},
                        {"label": "Hedging Assets Current", "value": 12_000_000.0},
                        {"label": "Inventory", "value": 1_200_000_000.0},
                        {"label": "Accounts Receivable", "value": 56_900_000_000.0},
                    ],
                    "cash_flow_statement": [
                        {"label": "Sale of Investment", "value": 35_700_000_000.0},
                        {"label": "Purchase of Investment", "value": -17_700_000_000.0},
                        {"label": "Net Business Purchase and Sale", "value": -69_100_000_000.0},
                        {"label": "Net PPE Purchase and Sale", "value": -44_500_000_000.0},
                        {"label": "Finished Goods", "value": 845_000_000.0},
                        {"label": "Work in Process", "value": 7_000_000.0},
                        {"label": "Raw Materials", "value": 394_000_000.0},
                    ],
                },
            },
            {
                "fiscal_year": "FY23",
                "assessment": {
                    "altman_z_score": 3.8,
                    "zone": "Safe",
                    "implied_rating": "AAA",
                    "strengths": ["Strong cash generation"],
                    "weaknesses": ["None"],
                },
                "ratios": {
                    "debt_to_ebitda": 0.57,
                    "interest_coverage": 45.0,
                    "fcf_to_debt": 0.99,
                    "current_ratio": 1.77,
                },
                "raw_metrics": {
                    "ebit": 91_300_000_000.0,
                    "ebitda": 105_100_000_000.0,
                    "total_debt": 60_000_000_000.0,
                    "free_cf": 59_500_000_000.0,
                },
                "statements": {
                    "income_statement": [
                        {"label": "Tax Effect of Unusual Items", "value": -2_900_000.0},
                        {"label": "Tax Rate for Calcs", "value": 0.19},
                        {"label": "Normalized EBITDA", "value": 105_200_000_000.0},
                        {"label": "Total Unusual Items", "value": -15_000_000.0},
                        {"label": "EBIT", "value": 91_300_000_000.0},
                        {"label": "Net Interest Income", "value": 1_000_000_000.0},
                        {"label": "Diluted Average Shares", "value": 7_500_000_000.0},
                        {"label": "Basic Average Shares", "value": 7_400_000_000.0},
                        {"label": "Interest Expense", "value": 1_941_000_000.0},
                    ],
                    "balance_sheet": [
                        {"label": "Net Tangible Assets", "value": 129_000_000_000.0},
                        {"label": "Total Equity", "value": 206_200_000_000.0},
                        {"label": "Retained Earnings", "value": 118_800_000_000.0},
                        {"label": "Total Liabilities", "value": 205_800_000_000.0},
                        {"label": "Other Current Assets", "value": 21_800_000_000.0},
                        {"label": "Hedging Assets Current", "value": 6_000_000.0},
                        {"label": "Inventory", "value": 2_500_000_000.0},
                        {"label": "Accounts Receivable", "value": 48_700_000_000.0},
                    ],
                    "cash_flow_statement": [
                        {"label": "Sale of Investment", "value": 47_900_000_000.0},
                        {"label": "Purchase of Investment", "value": -37_700_000_000.0},
                        {"label": "Net Business Purchase and Sale", "value": -1_700_000_000.0},
                        {"label": "Net PPE Purchase and Sale", "value": -28_100_000_000.0},
                        {"label": "Finished Goods", "value": 1_800_000_000.0},
                        {"label": "Work in Process", "value": 23_000_000.0},
                        {"label": "Raw Materials", "value": 709_000_000.0},
                    ],
                },
            },
        ],
    }

    model = pdf_report_core.build_pdf_document_model(report, "en")
    income_section = next(section for section in model["statements"] if section["title"] == "income_statement")
    interest_row = next(row for row in income_section["detail_rows"] if row["label"] == "Interest Expense")
    assert interest_row["yoy_q"] == "-18.7%"
    assert interest_row["yoy_fy"] == "+49.1%"

    balance_section = next(section for section in model["statements"] if section["title"] == "balance_sheet")
    assert [row["label"] for row in balance_section["detail_rows"][:4]] == [
        "Net Tangible Assets",
        "Total Equity",
        "Retained Earnings",
        "Total Liabilities",
    ]

    cash_section = next(section for section in model["statements"] if section["title"] == "cash_flow_statement")
    assert [row["label"] for row in cash_section["detail_rows"][:4]] == [
        "Sale of Investment",
        "Purchase of Investment",
        "Net Business Purchase and Sale",
        "Net PPE Purchase and Sale",
    ]

    pdf_bytes = generate_full_pdf(report, lang="en")
    pdf_file = tmp_path / "long-statement-rows.pdf"
    pdf_file.write_bytes(pdf_bytes)

    if shutil.which("pdftotext"):
        extracted = subprocess.check_output(["pdftotext", str(pdf_file), "-"], text=True)
        normalized = re.sub(r"\s+", " ", extracted)
        for label in [
            "Tax Effect of Unusual Items",
            "Tax Rate for Calcs",
            "Normalized EBITDA",
            "Total Unusual Items",
            "EBIT",
            "Net Interest Income",
            "Diluted Average Shares",
            "Basic Average Shares",
            "Interest Expense",
            "Net Tangible Assets",
            "Total Equity",
            "Retained Earnings",
            "Total Liabilities",
            "Other Current Assets",
            "Hedging Assets Current",
            "Inventory",
            "Accounts Receivable",
            "Sale of Investment",
            "Purchase of Investment",
            "Net Business Purchase and Sale",
            "Net PPE Purchase and Sale",
        ]:
            assert label in normalized


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
    model = pdf_report_core.build_pdf_document_model(_build_report(), "en", "light")
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


def test_compare_script_supports_canary_replacement(tmp_path):
    script = Path(ROOT) / "scripts" / "compare_aapl_real_pdf.py"
    if not script.exists():
        pytest.skip("compare script is missing")
    if not shutil.which("pdftotext") or not shutil.which("pdftocairo"):
        pytest.skip("pdf comparison tools are not installed")
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")

    fixture_path = Path(__file__).resolve().parent / "fixtures" / "aapl_real_report.json"
    reference_pdf = tmp_path / "aapl_reference_for_compare.pdf"
    with fixture_path.open("r", encoding="utf-8") as fh:
        report = json.load(fh)
    reference_pdf.write_bytes(generate_full_pdf(report, lang="en", theme="dark"))

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.compare_aapl_real_pdf",
            "--reference",
            str(reference_pdf),
            "--replace",
            "Apple Inc.=Apple Inc. (Cache Break)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Applied replacements:" in result.stdout
    assert "Apple Inc. (Cache Break)" in result.stdout
    assert "Canary check: replacement target 'Apple Inc. (Cache Break)' found in generated text." in result.stdout
