"""Backward-compatible PDF exporter facade."""

from src.pdf_report_core import *  # noqa: F401,F403
from src.reportlab_pdf_exporter import generate_full_pdf, generate_full_pdf_async  # noqa: F401
