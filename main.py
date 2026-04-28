"""RiskLens legacy MVP FastAPI entrypoint.

Run:
    uvicorn main:app --reload

The primary dashboard/API runtime is ``src.api:app``. This module remains for
backward compatibility with the legacy ``/api/assess`` smoke checks.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from pathlib import Path
from typing import Any

from fastapi.concurrency import run_in_threadpool
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

BASE_DIR = Path(__file__).resolve().parent

from src.services import AssessmentService, AssessmentServiceError
from src.config import settings

logger = logging.getLogger(__name__)


def _error_response(error: str, error_type: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "error": error,
        "error_type": error_type,
        "details": details,
    }

app = FastAPI(
    title=settings.app_name,
    description="Minimal runnable FastAPI MVP for credit assessment.",
    version="1.1.0",
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
service = AssessmentService(report_dir=settings.mvp_report_dir)


def _resolve_assess_timeout_seconds() -> float:
    return max(1.0, settings.assess_timeout_seconds)


async def _run_assessment_with_timeout(
    ticker: str,
    data_source: str,
    fiscal_year: int | None,
) -> dict[str, Any]:
    timeout_seconds = _resolve_assess_timeout_seconds()
    try:
        return await asyncio.wait_for(
            run_in_threadpool(
                service.assess,
                ticker=ticker,
                data_source=data_source,
                fiscal_year=fiscal_year,
            ),
            timeout=timeout_seconds,
        )
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail={
                "error": f"评估超时（>{timeout_seconds:.0f}s）",
                "error_type": "timeout",
                "ticker": ticker,
                "data_source": data_source,
            },
        ) from exc


class AssessRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker, e.g. NVDA")
    data_source: str = Field(default="yfinance", description="auto | yfinance | akshare | demo")
    fiscal_year: int | None = Field(default=None, ge=1900, le=2100)

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("ticker 不能为空")
        return value.strip().upper()


class LegacyAssessRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=1, max_length=50)
    data_source: str = Field(default="yfinance")
    fiscal_year: int | None = Field(default=None, ge=1900, le=2100)


@app.exception_handler(AssessmentServiceError)
async def handle_assessment_error(_request: Request, exc: AssessmentServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_response(exc.message, "business_error", exc.details),
    )


@app.exception_handler(HTTPException)
async def handle_http_error(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        error = str(detail.get("error") or detail.get("message") or "Request failed")
        error_type = str(detail.get("error_type") or "http_error")
        details = {key: value for key, value in detail.items() if key not in {"error", "error_type", "message"}}
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_response(error, error_type, details or None),
            headers=exc.headers,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_response(str(detail), "http_error", None),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    safe_details: list[dict[str, Any]] = []
    for item in exc.errors():
        row = dict(item)
        ctx = row.get("ctx")
        if isinstance(ctx, dict):
            row["ctx"] = {
                key: (str(value) if isinstance(value, Exception) else value)
                for key, value in ctx.items()
            }
        safe_details.append(row)

    return JSONResponse(
        status_code=422,
        content=_error_response("请求参数校验失败", "validation_error", {"errors": safe_details}),
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content=_error_response("服务器内部错误", "internal_server_error", {"path": str(request.url.path)}),
    )


@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def homepage(request: Request) -> HTMLResponse:
    return FileResponse(BASE_DIR / "templates" / "index.html", media_type="text/html")


@app.get("/health", tags=["System"])
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": app.title,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/assess", tags=["Assessment"])
async def assess(payload: AssessRequest) -> dict[str, Any]:
    return await _run_assessment_with_timeout(
        ticker=payload.ticker,
        data_source=payload.data_source,
        fiscal_year=payload.fiscal_year,
    )


@app.post("/api/v1/assess", tags=["Assessment"])
async def assess_v1(payload: LegacyAssessRequest) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    errors: list[str] = []

    for item in payload.tickers:
        ticker = (item or "").strip().upper()
        if not ticker:
            errors.append("empty ticker")
            continue
        try:
            result = await _run_assessment_with_timeout(
                ticker=ticker,
                data_source=payload.data_source,
                fiscal_year=payload.fiscal_year,
            )
            results.append(result)
        except AssessmentServiceError as exc:
            errors.append(f"{ticker}: {exc.message}")

    if not results:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "No assessments succeeded",
                "error_type": "no_data_available",
                "errors": errors,
            },
        )

    return {
        "count": len(results),
        "errors": errors or None,
        "results": results,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=settings.app_port, reload=True)
