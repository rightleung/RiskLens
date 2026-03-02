"""RiskLens MVP FastAPI entrypoint.

Run:
    uvicorn main:app --reload
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from fastapi.concurrency import run_in_threadpool
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from services import AssessmentService, AssessmentServiceError

logger = logging.getLogger(__name__)

app = FastAPI(
    title=os.getenv("APP_NAME", "RiskLens MVP"),
    description="Minimal runnable FastAPI MVP for credit assessment.",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
service = AssessmentService(report_dir=str(BASE_DIR / "data" / "reports"))


def _resolve_assess_timeout_seconds() -> float:
    raw = os.getenv("ASSESS_TIMEOUT_SECONDS", "25")
    try:
        timeout = float(raw)
    except ValueError:
        timeout = 25.0
    return max(1.0, timeout)


async def _run_assessment_with_timeout(
    ticker: str,
    data_source: str,
    fiscal_year: Optional[int],
) -> Dict[str, Any]:
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
    except asyncio.TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail={
                "error": f"评估超时（>{timeout_seconds:.0f}s）",
                "ticker": ticker,
                "data_source": data_source,
            },
        ) from exc


class AssessRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker, e.g. AAPL")
    data_source: str = Field(default="yfinance", description="auto | yfinance | akshare | demo")
    fiscal_year: Optional[int] = Field(default=None, ge=1900, le=2100)

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("ticker 不能为空")
        return value.strip().upper()


class LegacyAssessRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, max_length=50)
    data_source: str = Field(default="yfinance")
    fiscal_year: Optional[int] = Field(default=None, ge=1900, le=2100)


@app.exception_handler(AssessmentServiceError)
async def handle_assessment_error(_request: Request, exc: AssessmentServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    safe_details: List[Dict[str, Any]] = []
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
        content={
            "error": "请求参数校验失败",
            "details": safe_details,
        },
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "服务器内部错误",
            "details": {"path": str(request.url.path)},
        },
    )


@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def homepage(request: Request) -> HTMLResponse:
    return FileResponse(BASE_DIR / "templates" / "index.html", media_type="text/html")


@app.get("/health", tags=["System"])
def health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": app.title,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/assess", tags=["Assessment"])
async def assess(payload: AssessRequest) -> Dict[str, Any]:
    return await _run_assessment_with_timeout(
        ticker=payload.ticker,
        data_source=payload.data_source,
        fiscal_year=payload.fiscal_year,
    )


@app.post("/api/v1/assess", tags=["Assessment"])
async def assess_v1(payload: LegacyAssessRequest) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    errors: List[str] = []

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
        raise HTTPException(status_code=404, detail={"errors": errors})

    return {
        "count": len(results),
        "errors": errors or None,
        "results": results,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=int(os.getenv("APP_PORT", "8000")), reload=True)
