import asyncio
import importlib.util
import inspect
import re
import subprocess
import shutil
import os
import sys

import api
import src.pdf_report_core as pdf_report_core
import src.reportlab_pdf_exporter as reportlab_pdf_exporter
import pytest
from fastapi.testclient import TestClient


REPORTLAB_AVAILABLE = importlib.util.find_spec("reportlab") is not None


def _sample_report():
    return {
        "ticker": "DEMO",
        "company_name": "Demo Industrial Co.",
        "company_name_localized": "Demo 工业公司",
        "currency": "USD",
        "history": [
            {
                "fiscal_year": "25Q3",
                "assessment": {
                    "altman_z_score": 2.7,
                    "zone": "Safe",
                    "implied_rating": "BBB",
                    "strengths": ["Strong liquidity", "Low leverage"],
                    "watch_items": ["Margin pressure"],
                    "covenant_pre_check": [
                        {
                            "metric": "Debt/EBITDA",
                            "actual": 2.1,
                            "threshold": 3.5,
                            "status": "Pass",
                            "signal": "Green",
                            "notes": "Comfortable",
                        }
                    ],
                    "data_quality": [{"label": "Coverage", "value": 92, "notes": "Good"}],
                },
                "raw_metrics": {
                    "ebit": 120,
                    "ebitda": 160,
                    "total_debt": 300,
                    "debt_ebitda": 1.9,
                    "interest_coverage": 6.2,
                    "free_cash_flow": 80,
                    "fcf_debt": 0.27,
                    "current_ratio": 1.8,
                },
                "statements": {
                    "income_statement": [
                        {"label": "Revenue", "value": 500},
                        {"label": "EBIT", "value": 120},
                    ],
                    "balance_sheet": [
                        {"label": "Cash", "value": 200},
                        {"label": "Debt", "value": 300},
                    ],
                    "cash_flow_statement": [
                        {"label": "Operating CF", "value": 95},
                        {"label": "Capex", "value": -15},
                    ],
                },
            },
            {
                "fiscal_year": "24Q3",
                "raw_metrics": {
                    "ebit": 100,
                    "ebitda": 140,
                    "total_debt": 320,
                    "debt_ebitda": 2.3,
                    "interest_coverage": 5.0,
                    "free_cash_flow": 70,
                    "fcf_debt": 0.22,
                    "current_ratio": 1.6,
                },
                "statements": {
                    "income_statement": [
                        {"label": "Revenue", "value": 470},
                        {"label": "EBIT", "value": 100},
                    ],
                    "balance_sheet": [
                        {"label": "Cash", "value": 180},
                        {"label": "Debt", "value": 320},
                    ],
                    "cash_flow_statement": [
                        {"label": "Operating CF", "value": 88},
                        {"label": "Capex", "value": -18},
                    ],
                },
            },
            {
                "fiscal_year": "FY24",
                "raw_metrics": {
                    "ebit": 420,
                    "ebitda": 560,
                    "total_debt": 300,
                    "debt_ebitda": 0.5,
                    "interest_coverage": 5.5,
                    "free_cash_flow": 250,
                    "fcf_debt": 0.83,
                    "current_ratio": 1.9,
                },
                "statements": {
                    "income_statement": [
                        {"label": "Revenue", "value": 1800},
                        {"label": "EBIT", "value": 420},
                    ],
                    "balance_sheet": [
                        {"label": "Cash", "value": 210},
                        {"label": "Debt", "value": 300},
                    ],
                    "cash_flow_statement": [
                        {"label": "Operating CF", "value": 330},
                        {"label": "Capex", "value": -40},
                    ],
                },
            },
            {
                "fiscal_year": "FY23",
                "raw_metrics": {
                    "ebit": 390,
                    "ebitda": 530,
                    "total_debt": 280,
                    "debt_ebitda": 0.5,
                    "interest_coverage": 5.1,
                    "free_cash_flow": 230,
                    "fcf_debt": 0.82,
                    "current_ratio": 1.7,
                },
                "statements": {
                    "income_statement": [
                        {"label": "Revenue", "value": 1680},
                        {"label": "EBIT", "value": 390},
                    ],
                    "balance_sheet": [
                        {"label": "Cash", "value": 205},
                        {"label": "Debt", "value": 280},
                    ],
                    "cash_flow_statement": [
                        {"label": "Operating CF", "value": 310},
                        {"label": "Capex", "value": -38},
                    ],
                },
            },
        ],
    }


def test_pdf_exporter_generates_pdf_bytes(tmp_path):
    report = _sample_report()

    model = pdf_report_core.build_pdf_document_model(report, "zh-CN")
    assert model["cover"]["company_name"] == "Demo Industrial Co."
    assert model["context"]["labels"]["contents"] == "目录"
    assert model["statements"][0]["headers"][0] == "指标"
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")

    assert pdf_report_core._format_period_label("25Q3") == "Q3 FY25"
    assert pdf_report_core._build_yoy_map(["25Q3", "24Q3", "FY24", "FY23"]) == {
        "25Q3": "24Q3",
        "FY24": "FY23",
    }

    context = pdf_report_core.build_pdf_context(report, "zh-CN")
    assert context["kpi_yoy_label_q"] == "Q3'25 vs Q3'24"
    assert context["kpi_yoy_label_fy"] == "FY24 vs FY23"
    assert context["yoy_note"] == "（截至FY24及FY23财政年度）"
    assert context["hero_summary"]["items"] == [
        {"label": "Altman Z 分数", "value": "2.70", "tone": "neutral"},
        {"label": "区间", "value": "Safe", "tone": "success"},
        {"label": "隐含评级", "value": "BBB", "tone": "info"},
    ]
    assert context["hero_summary"]["note"].startswith("方法论注解:")
    assert context["zone_text"] == "Safe"
    assert context["covenant_rows"][0]["status_signal"] == "Pass"
    assert context["covenant_rows"][0]["description"] == "衡量杠杆与偿债能力"
    assert context["covenant_notes"][0]["metric"] == "Debt/EBITDA"
    assert context["covenant_note_title"] == "指标说明"
    assert context["periods"][2]["group_start"] is True
    assert context["periods"][2]["benchmark"] is False
    assert context["periods"][2]["benchmark_style"] == ""
    assert [section["title"] for section in context["statement_sections"]] == [
        "income_statement",
        "balance_sheet",
        "cash_flow_statement",
    ]
    assert all(section["yoy_label_q"] == "Q3'25 vs Q3'24" for section in context["statement_sections"])
    assert all(section["yoy_label_fy"] == "FY24 vs FY23" for section in context["statement_sections"])
    assert all(section["yoy_note"] == context["yoy_note"] for section in context["statement_sections"])
    assert context["data_quality_rows"][0]["value"] == "92%"
    assert len(context["methodology_notes"]) == 3
    assert context["benchmark_note"] == ""
    assert context["kpi_rows"][3]["values"][0] == "1.90"
    cash_flow_section = next(section for section in context["statement_sections"] if section["title"] == "cash_flow_statement")
    capex_row = next(row for row in cash_flow_section["rows"] if row["label"] == "Capex")
    assert capex_row["yoy_q"] == "-16.7%"
    assert capex_row["yoy_fy"] == "+5.3%"
    assert not hasattr(pdf_report_core, "render_pdf_html")

    pdf_bytes = reportlab_pdf_exporter.generate_full_pdf(report, "zh-CN")

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 5000
    pdf_file = tmp_path / "report.pdf"
    pdf_file.write_bytes(pdf_bytes)
    pdfinfo = subprocess.check_output(["pdfinfo", str(pdf_file)], text=True)
    assert "Pages:" in pdfinfo
    page_count = int(pdfinfo.split("Pages:")[1].splitlines()[0].strip())
    assert page_count >= 5
    assert "Page size:" in pdfinfo
    size_line = next(line for line in pdfinfo.splitlines() if line.startswith("Page size:"))
    match = re.search(r"Page size:\s*([0-9.]+)\s*x\s*([0-9.]+)", size_line)
    assert match is not None
    assert float(match.group(1)) > float(match.group(2))
    if shutil.which("pdftotext"):
        extracted = subprocess.check_output(["pdftotext", str(pdf_file), "-"], text=True)
        first_page = extracted.split("\f")[0]
        assert "Demo Industrial Co." in extracted
        assert "FY24" in extracted
        assert "Capex" in extracted
        assert "Page 1" not in first_page


def test_pdf_export_api_is_async_and_returns_pdf(tmp_path):
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    assert inspect.iscoroutinefunction(api.export_full_pdf)

    client = TestClient(api.app)
    response = client.post("/api/v1/reports/pdf", json={"report": _sample_report(), "lang": "en"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 5000
    if shutil.which("pdftotext"):
        pdf_file = tmp_path / "api.pdf"
        pdf_file.write_bytes(response.content)
        extracted = subprocess.check_output(["pdftotext", str(pdf_file), "-"], text=True)
        assert "FY24" in extracted
        assert "Capex" in extracted


def test_build_pdf_context_prefers_ratio_fields_and_weakness_fallback():
    report = _sample_report()
    latest = report["history"][0]
    latest["assessment"].pop("watch_items", None)
    latest["assessment"]["weaknesses"] = ["Liquidity sensitivity"]
    latest.setdefault("ratios", {})["debt_to_ebitda"] = 0.38
    latest["ratios"].pop("fcf_debt", None)
    latest["ratios"]["fcf_to_debt"] = 0.22
    latest["raw_metrics"].pop("ebit", None)
    latest["raw_metrics"].pop("free_cash_flow", None)
    latest["raw_metrics"]["free_cf"] = 71_611_000_000.0
    latest["raw_metrics"]["operating_income"] = 18_300_000.0
    latest["raw_metrics"]["ebitda"] = 160_165_000_000.0

    context = pdf_report_core.build_pdf_context(report, "en")

    assert context["watch_items"] == ["Liquidity sensitivity"]
    assert context["kpi_rows"][3]["values"][0] == "0.38"
    assert context["kpi_rows"][5]["values"][0] == "71.6"
    assert context["kpi_rows"][6]["values"][0] == "0.22"
    assert context["kpi_rows"][0]["values"][0] == "0.02"


def test_build_pdf_context_uses_none_state_and_covenant_fallback():
    report = _sample_report()
    latest = report["history"][0]
    latest["assessment"]["watch_items"] = []
    latest["assessment"]["concerns"] = []
    latest["assessment"]["weaknesses"] = []
    latest["watch_items"] = []
    latest["concerns"] = []
    latest["weaknesses"] = []
    latest["assessment"].pop("covenant_pre_check", None)
    latest.pop("covenant_pre_check", None)

    context = pdf_report_core.build_pdf_context(report, "en")

    assert context["watch_items"] == ["No significant watch items"]
    assert [row["metric"] for row in context["covenant_rows"]] == [
        "Debt/EBITDA",
        "Interest Coverage",
        "FCF / Debt",
        "Current Ratio",
    ]
    assert all(row["description"] for row in context["covenant_rows"])


def test_build_pdf_context_marks_missing_covenant_actual_as_insufficient_data():
    report = _sample_report()
    report["history"][0]["assessment"]["covenant_pre_check"] = [
        {
            "metric": "Interest Coverage",
            "actual": None,
            "threshold": 3.0,
            "status": "Fail",
            "signal": "Red",
            "notes": "Weak coverage",
        }
    ]

    context = pdf_report_core.build_pdf_context(report, "en")

    row = context["covenant_rows"][0]
    assert row["actual"] == "N/A"
    assert row["status_signal"] == "Insufficient Data"
    assert row["status_signal_tone"] == "neutral"
    assert row["notes"] == "Insufficient Data"


def test_build_pdf_context_filters_empty_company_profile_fields():
    report = _sample_report()
    report["company_profile"] = {
        "sector": "Industrials",
        "products": [],
        "coverage": "--",
        "metadata": {},
    }

    context = pdf_report_core.build_pdf_context(report, "en")

    assert context["company_profile_rows"] == [{"label": "Sector", "value": "Industrials"}]


def test_build_pdf_context_uses_period_span_note_for_annual_only_tables():
    report = _sample_report()
    report["history"] = [entry for entry in report["history"] if str(entry.get("fiscal_year", "")).startswith("FY")]

    context = pdf_report_core.build_pdf_context(report, "en")

    assert context["yoy_note"] == "(For the fiscal years ended FY24 and FY23)"
    assert all(section["yoy_note"] == "(For the fiscal years ended FY24 and FY23)" for section in context["statement_sections"])


def test_build_pdf_context_prefers_annual_period_span_note_in_mixed_tables():
    report = _sample_report()
    report["history"] = [
        {
            "fiscal_year": "25Q3",
            "assessment": report["history"][0]["assessment"],
            "raw_metrics": report["history"][0]["raw_metrics"],
            "statements": report["history"][0]["statements"],
        },
        {
            "fiscal_year": "FY24",
            "raw_metrics": report["history"][2]["raw_metrics"],
            "statements": report["history"][2]["statements"],
        },
        {
            "fiscal_year": "FY23",
            "raw_metrics": report["history"][3]["raw_metrics"],
            "statements": report["history"][3]["statements"],
        },
    ]

    context = pdf_report_core.build_pdf_context(report, "en")

    assert context["yoy_note"] == "(For the fiscal years ended FY24 and FY23)"
    assert all(section["yoy_note"] == "(For the fiscal years ended FY24 and FY23)" for section in context["statement_sections"])


def test_async_pdf_export_direct_call():
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab is not installed")
    report = _sample_report()
    pdf_bytes = asyncio.run(reportlab_pdf_exporter.generate_full_pdf_async(report, "en"))

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 5000
