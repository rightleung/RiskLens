"""Pytest configuration - centralized import path setup."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_MODULE_ALIASES = {
    "api": "src.api",
    "data_fetcher": "src.data_fetcher",
    "ratio_analyzer": "src.ratio_analyzer",
    "zscore": "src.zscore",
    "covenant_monitor": "src.covenant_monitor",
    "services": "src.services",
    "risklens_cli": "src.risklens_cli",
    "html_pdf_exporter": "src.html_pdf_exporter",
    "pdf_exporter": "src.pdf_exporter",
    "reportlab_pdf_exporter": "src.reportlab_pdf_exporter",
    "reportlab_pdf_renderer": "src.reportlab_pdf_renderer",
    "pdf_report_core": "src.pdf_report_core",
    "akshare_data": "src.akshare_data",
    "credit_risk_assessment": "src.legacy.credit_risk_assessment",
}

for alias, target in _MODULE_ALIASES.items():
    sys.modules.setdefault(alias, importlib.import_module(target))
