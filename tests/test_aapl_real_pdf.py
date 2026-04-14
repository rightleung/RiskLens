from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

import pdf_exporter


REPORTLAB_AVAILABLE = importlib.util.find_spec("reportlab") is not None
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "aapl_real_report.json"


def _load_real_aapl_report() -> dict:
    with FIXTURE_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _page_texts(pdf_path: Path) -> list[str]:
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext is not installed")
    extracted = subprocess.check_output(["pdftotext", "-layout", str(pdf_path), "-"], text=True)
    pages = extracted.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    return pages


def _collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def test_real_aapl_context_keeps_alignment_and_placeholders():
    report = _load_real_aapl_report()
    context = pdf_exporter.build_pdf_context(report, "en", "dark")

    assert context["ticker"] == "AAPL"
    assert context["company_name"] == "Apple Inc."
    assert [row["label"] for row in context["kpi_rows"]] == [
        "EBIT",
        "EBITDA",
        "Total Debt",
        "Debt / EBITDA",
        "Interest Coverage",
        "Free CF",
        "FCF / Debt",
        "Current Ratio",
    ]

    interest_row = next(row for row in context["kpi_rows"] if row["label"] == "Interest Coverage")
    assert interest_row["values"] == ["--", "--", "29.06x"]
    assert interest_row["yoy_q"] == "N/A"
    assert interest_row["yoy_fy"] == "N/A"

    breakdown = context["hero_summary"]["breakdown"]
    assert len(breakdown) == 3
    assert [item["label"] for item in breakdown] == [
        "Working Capital / Total Assets",
        "Retained Earnings / Total Assets",
        "EBIT / Total Assets",
    ]
    assert [item["value"] for item in breakdown] == ["-4.92%", "-3.97%", "37.04%"]
    assert [item["contribution"] for item in breakdown] == ["-0.06", "-0.06", "+1.22"]

    cash_flow = next(section for section in context["statement_sections"] if section["title"] == "cash_flow_statement")
    balance_sheet = next(section for section in context["statement_sections"] if section["title"] == "balance_sheet")

    cash_labels = [row["label"] for row in cash_flow["rows"]]
    balance_labels = [row["label"] for row in balance_sheet["rows"]]

    assert "Cash Flow From Continuing Financing Activities" in cash_labels
    assert "Cash Flow From Continuing Investing Activities" in cash_labels
    assert "Net Other Financing Charges" in cash_labels
    for label in [
        "Net Debt",
        "Total Debt",
        "Cash",
        "Short Term Investments",
        "Cash Equivalents",
        "Trade and Other Payables Non Current",
    ]:
        assert label in balance_labels

    assert cash_flow["rows"][0]["label"] == "Free CF"
    assert balance_sheet["rows"][0]["label"] == "Ordinary Shares Number"


@pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab is not installed")
def test_real_aapl_pdf_smoke_and_layout(tmp_path):
    report = _load_real_aapl_report()
    pdf_bytes = pdf_exporter.generate_full_pdf(report, lang="en", theme="dark")

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 8000

    pdf_file = tmp_path / "aapl-real.pdf"
    pdf_file.write_bytes(pdf_bytes)

    pdfinfo = subprocess.check_output(["pdfinfo", str(pdf_file)], text=True)
    page_match = re.search(r"^Pages:\s+(\d+)$", pdfinfo, flags=re.MULTILINE)
    assert page_match is not None
    assert int(page_match.group(1)) == 12

    pages = _page_texts(pdf_file)
    assert len(pages) == 12

    page1 = _collapse_spaces(pages[0])
    page4 = _collapse_spaces(pages[3])
    page5 = _collapse_spaces(pages[4])
    page6 = _collapse_spaces(pages[5])
    page7 = _collapse_spaces(pages[6])
    page9 = _collapse_spaces(pages[8])
    cash_flow_financing_page = _collapse_spaces(next(page for page in pages if "Cash Flow From Continuing Financing Activities" in page))
    cash_flow_investing_page = _collapse_spaces(next(page for page in pages if "Cash Flow From Continuing Investing Activities" in page))
    all_text = _collapse_spaces("\n".join(pages))

    assert "Working Capital / Total Assets -4.92%" in page1
    assert "Retained Earnings / Total Assets -3.97%" in page1
    assert "EBIT / Total Assets 37.04%" in page1
    assert "Contribution: -0.06" in page1
    assert "Contribution: +1.22" in page1

    assert "Interest Coverage -- -- 29.06x N/A N/A" in page4
    assert "Free CF 98.8 B 108.8 B 99.6 B -9.2% +9.3%" in page4

    assert "269.0. M" not in page6
    assert "Other Non Operating Income Expenses -321.0 M 269.0 M -565.0 M" in page6

    assert "Net Debt 62.7 B 76.7 B 81.1 B -18.2% -5.5%" in page7
    assert "76.7\nB" not in pages[6]

    assert "Trade and Other Payables Non Current -- 9.3 B 15.5 B N/A -40.1%" in page9

    assert "Cash Flow From Continuing Financing Activities -120.7 B -122.0 B -108.5 B -1.1% +12.4%" in cash_flow_financing_page
    assert "Cash Flow From Continuing Investing Activities 15.2 B 2.9 B 3.7 B +417.7% -20.8%" in cash_flow_investing_page
    assert "269.0. M" not in all_text
    assert "+1.2% % 1.2 +" not in all_text
