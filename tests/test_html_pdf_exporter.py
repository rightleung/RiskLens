import asyncio
import inspect

import api
import pdf_exporter
from fastapi.testclient import TestClient


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


def test_pdf_exporter_generates_pdf_bytes():
    report = _sample_report()

    assert pdf_exporter._format_period_label("25Q3") == "Q3 FY25"
    assert pdf_exporter._build_yoy_map(["25Q3", "24Q3", "FY24", "FY23"]) == {
        "25Q3": "24Q3",
        "FY24": "FY23",
    }

    pdf_bytes = pdf_exporter.generate_full_pdf(report, "zh-CN")

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 5000
    assert pdf_bytes.count(b"/Type /Page") >= 8


def test_pdf_export_api_is_async_and_returns_pdf():
    assert inspect.iscoroutinefunction(api.export_full_pdf)

    client = TestClient(api.app)
    response = client.post("/api/v1/reports/pdf", json={"report": _sample_report(), "lang": "en"})

    assert response.status_code == 200
    assert response.media_type == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 5000


def test_async_pdf_export_direct_call():
    report = _sample_report()
    pdf_bytes = asyncio.run(pdf_exporter.generate_full_pdf_async(report, "en"))

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 5000
