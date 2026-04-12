from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from src.html_pdf_exporter import generate_full_pdf, generate_full_pdf_async


app = FastAPI(
    title="RiskLens Compatibility API",
    description="Minimal API surface for PDF export smoke tests.",
    version="0.0.0",
)


@dataclass(slots=True)
class PdfExportRequest:
    report: dict[str, Any]
    lang: str = "zh-CN"


def _coerce_request(request: PdfExportRequest | dict[str, Any]) -> PdfExportRequest:
    if isinstance(request, PdfExportRequest):
        return request
    if isinstance(request, dict):
        return PdfExportRequest(
            report=request.get("report", {}),
            lang=request.get("lang", "zh-CN"),
        )
    raise TypeError(f"Unsupported request type: {type(request)!r}")


@app.post("/api/v1/reports/pdf")
async def export_full_pdf(request: PdfExportRequest | dict[str, Any]) -> StreamingResponse:
    coerced = _coerce_request(request)
    pdf_bytes = await generate_full_pdf_async(coerced.report, coerced.lang)
    headers = {
        "Content-Disposition": 'attachment; filename="risklens_report.pdf"',
    }
    return StreamingResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers=headers,
        status_code=200,
    )


def export_full_pdf_sync(request: PdfExportRequest | dict[str, Any]) -> StreamingResponse:
    coerced = _coerce_request(request)
    pdf_bytes = generate_full_pdf(coerced.report, coerced.lang)
    headers = {
        "Content-Disposition": 'attachment; filename="risklens_report.pdf"',
    }
    return StreamingResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers=headers,
        status_code=200,
    )


__all__ = [
    "app",
    "PdfExportRequest",
    "export_full_pdf",
    "export_full_pdf_sync",
    "generate_full_pdf",
    "generate_full_pdf_async",
    "StreamingResponse",
]
