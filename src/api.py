"""
Institutional Credit Risk API
=============================
FastAPI backend for automated credit risk assessment and covenant monitoring.

Run with:
    cd src && uvicorn api:app --reload --port 8000

Swagger UI:
    http://localhost:8000/docs
"""

import math
import hashlib
import logging
import io
import re
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Any, Dict
from datetime import datetime
import pandas as pd
import json

logger = logging.getLogger(__name__)

_PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)

_LOCALIZED_NAME_CACHE: Dict[str, Dict[str, str]] = {}

# ── Error Monitoring (Sentry) ─────────────────────────────────────────────────
# Initialize Sentry for error tracking
# Set SENTRY_DSN environment variable to enable, or leave empty to disable
import os
sentry_dsn = os.environ.get("SENTRY_DSN", "")
environment = os.environ.get("ENVIRONMENT", "development").lower()
debug_enabled = os.environ.get("DEBUG", "").lower() in {"1", "true", "yes", "on"}
debug_error_details_enabled = debug_enabled and environment != "production"
if sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
        ],
        traces_sample_rate=0.1,
        environment=environment,
        release=f"risklens@{os.environ.get('VERSION', '1.1.0')}",
    )
    logger.info("Sentry error monitoring enabled")
else:
    logger.info("Sentry disabled (set SENTRY_DSN env var to enable)")

from data_fetcher import FinancialDataFetcher, DataFetchError, DataFetchErrorType
from ratio_analyzer import RatioAnalyzer, CreditRatioAnalysis
from covenant_monitor import FinancialCovenants, CovenantMonitor, CovenantReport
from zscore import calculate_z_score
from src.reportlab_pdf_exporter import generate_full_pdf, generate_full_pdf_async
from services import AssessmentServiceError, RichAssessmentService

# ── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="RiskLens — Institutional Credit Risk Platform",
    description=(
        "An automated end-to-end framework for institutional credit assessment, "
        "financial ratio analysis, and post-lending covenant monitoring.\n\n"
        "**CONFIDENTIAL — FOR INTERNAL RISK MANAGEMENT USE ONLY**"
    ),
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
def _parse_cors_origins() -> List[str]:
    configured = os.environ.get("CORS_ORIGINS", "").strip()
    if configured:
        origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
        return origins or ["*"]
    # Safe local defaults when env is not provided.
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


cors_origins = _parse_cors_origins()
cors_allow_credentials = "*" not in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-PDF-SHA256", "X-PDF-Bytes"],
)


# ── Exception Handlers ─────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Catch unhandled exceptions and return proper error response."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if debug_error_details_enabled else "An unexpected error occurred",
            "path": str(request.url),
        },
    )


# ── Shared Instances ─────────────────────────────────────────────────────────

fetcher = FinancialDataFetcher()
analyzer = RatioAnalyzer(report_dir="/tmp/credit_api_reports")
# NOTE: covenant_monitor is stateless (no mutable state), safe as a singleton
covenant_monitor = CovenantMonitor()
rich_assessment_service = RichAssessmentService(report_dir="/tmp/credit_api_reports")
# assessor is NOT a singleton — instantiated per-request in _assess_risk()
# to avoid race conditions on self.assessments list in concurrent requests.


# ── Request / Response Models (Pydantic) ─────────────────────────────────────

class AssessmentRequest(BaseModel):
    """Request body for credit assessment."""
    tickers: List[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of stock tickers to analyze",
        examples=[["AAPL", "MSFT"]],
    )
    fiscal_year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Fiscal year (defaults to current year)",
    )
    data_source: str = Field(
        default="yfinance",
        description="Data source: 'yfinance' or 'akshare'",
    )


class CovenantCheckRequest(BaseModel):
    """Request body for covenant breach checking."""
    ticker: str = Field(..., description="Stock ticker to check")
    fiscal_year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Fiscal year (defaults to current year)",
    )
    data_source: str = Field(
        default="yfinance",
        description="Data source: 'yfinance' or 'akshare'",
    )
    covenants: FinancialCovenants = Field(
        ...,
        description="Financial covenant thresholds to check against",
    )


class PdfExportRequest(BaseModel):
    """Request body for full PDF export."""
    report: Dict[str, Any] = Field(..., description="Single-company assessment payload")
    lang: str = Field(default="en", description="Language code")
    theme: str = Field(default="dark", description="PDF theme: 'dark' or 'light'")


# ── Helper Functions ─────────────────────────────────────────────────────────

def _calculate_ratios(data: dict) -> CreditRatioAnalysis:
    """Calculate financial ratios from fetched data (mirrors web/app.py logic)."""
    return analyzer.calculate_all_ratios(
        bs_data=data["balance"],
        is_data=data["income"],
        cf_data=data["cash"],
        company_name=data["company_name"],
        fiscal_year=data["fiscal_year"],
    )




def _analyze_single_ticker(ticker: str, fiscal_year: int, data_source: str) -> dict:
    """Full pipeline for a single ticker: fetch → ratios → assessment.

    Raises:
        DataFetchError: When data fetching fails with detailed error type
    """
    return rich_assessment_service.analyze(
        ticker=ticker,
        data_source=data_source,
        fiscal_year=fiscal_year,
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    """Health check — confirms the service is running."""
    return {
        "status": "healthy",
        "service": "Institutional Credit Risk API",
        "version": "1.1.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/v1/assess", tags=["Credit Assessment"])
async def run_credit_assessment(request: AssessmentRequest):
    """
    Run credit assessments for one or more tickers.

    Returns a list of assessment results, each containing the credit rating,
    risk score, risk factors, strengths/weaknesses, and full financial ratios.
    """
    tickers = [ticker.strip().upper() for ticker in request.tickers if isinstance(ticker, str) and ticker.strip()]
    if not tickers:
        raise HTTPException(status_code=422, detail={"errors": ["At least one non-empty ticker is required."]})

    fiscal_year = request.fiscal_year or datetime.now().year
    results: List[dict] = []
    errors: List[str] = []
    suggestions: Dict[str, list] = {}

    from fastapi.concurrency import run_in_threadpool
    import asyncio

    try:
        max_concurrency = max(1, int(os.environ.get("ASSESS_MAX_CONCURRENCY", "8")))
    except ValueError:
        max_concurrency = 8
    try:
        per_ticker_timeout = max(1.0, float(os.environ.get("ASSESS_TICKER_TIMEOUT_SECONDS", "20")))
    except ValueError:
        per_ticker_timeout = 20.0
    suggestions_timeout = min(8.0, max(1.0, per_ticker_timeout / 3))
    semaphore = asyncio.Semaphore(max_concurrency)

    async def fetch_suggestions(ticker: str) -> list:
        """Bound suggestion lookup latency to avoid cascading slowdowns."""
        try:
            return await asyncio.wait_for(
                run_in_threadpool(_search_tickers, ticker),
                timeout=suggestions_timeout,
            )
        except (asyncio.TimeoutError, DataFetchError, KeyError, AttributeError):
            return []

    async def process_ticker(ticker: str):
        async with semaphore:
            try:
                # Dispatch blocking analysis logic to worker thread with a hard timeout.
                result = await asyncio.wait_for(
                    run_in_threadpool(
                        _analyze_single_ticker, ticker, fiscal_year, request.data_source
                    ),
                    timeout=per_ticker_timeout,
                )
                if result and result.get('history') and len(result['history']) > 0:
                    return {"type": "success", "data": result}
                else:
                    sugg = await fetch_suggestions(ticker)
                    return {
                        "type": "error",
                        "ticker": ticker,
                        "msg": "No financial data available",
                        "error_type": "no_data_available",
                        "sugg": sugg
                    }
            except asyncio.TimeoutError:
                sugg = await fetch_suggestions(ticker)
                return {
                    "type": "error",
                    "ticker": ticker,
                    "msg": f"Timed out after {per_ticker_timeout:.0f}s",
                    "error_type": "timeout",
                    "sugg": sugg,
                }
            except AssessmentServiceError as exc:
                sugg = await fetch_suggestions(ticker)
                error_type = str(exc.details.get("error_type") or "business_error")
                return {
                    "type": "error",
                    "ticker": ticker,
                    "msg": exc.message,
                    "error_type": error_type,
                    "status_code": exc.status_code,
                    "details": exc.details,
                    "sugg": sugg,
                }
            except DataFetchError as exc:
                # Handle detailed data fetching errors with specific error types
                sugg = await fetch_suggestions(ticker)
                return {
                    "type": "error",
                    "ticker": ticker,
                    "msg": exc.message,
                    "error_type": exc.error_type.value,
                    "details": exc.details,
                    "sugg": sugg
                }
            except DataFetchError as exc:
                # Fallback for unexpected errors
                sugg = await fetch_suggestions(ticker)
                return {
                    "type": "error",
                    "ticker": ticker,
                    "msg": str(exc),
                    "error_type": "unknown",
                    "sugg": sugg
                }

    # Gather results concurrently
    tasks = [process_ticker(t) for t in tickers]
    outcomes = await asyncio.gather(*tasks)

    for outcome in outcomes:
        if outcome["type"] == "success":
            results.append(outcome["data"])
        else:
            errors.append(f"{outcome['ticker']}: {outcome['msg']}")
            suggestions[outcome['ticker']] = outcome["sugg"]

    if not results and errors:
        raise HTTPException(status_code=404, detail={
            "errors": errors,
            "suggestions": suggestions,
        })

    return {
        "count": len(results),
        "errors": errors if errors else None,
        "suggestions": suggestions if suggestions else None,
        "results": results,
    }


@contextmanager
def _temporarily_clear_proxy_env(enabled: bool):
    if not enabled:
        yield
        return
    backup = {k: os.environ.get(k) for k in _PROXY_ENV_KEYS}
    try:
        for k in _PROXY_ENV_KEYS:
            os.environ.pop(k, None)
        yield
    finally:
        for k, v in backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _contains_japanese_text(value: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff]", value or ""))


def _contains_cjk_text(value: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", value or ""))


def _extract_company_name_from_stock_info(stock_info: Any) -> Optional[str]:
    if stock_info is None:
        return None
    try:
        if hasattr(stock_info, "empty") and stock_info.empty:
            return None
    except (KeyError, AttributeError, TypeError):
        pass

    try:
        if hasattr(stock_info, "columns") and {"item", "value"}.issubset(set(stock_info.columns)):
            for column_name in ("股票简称", "公司名称", "名称", "name"):
                matches = stock_info[stock_info["item"] == column_name]
                if not matches.empty:
                    value = matches.iloc[0].get("value")
                    if value is not None:
                        text = str(value).strip()
                        if text:
                            return text
    except (KeyError, AttributeError, TypeError, IndexError):
        pass

    try:
        if hasattr(stock_info, "columns") and "value" in stock_info.columns and not stock_info.empty:
            value = stock_info.iloc[0].get("value")
            if value is not None:
                text = str(value).strip()
                if text:
                    return text
    except (KeyError, AttributeError, TypeError, IndexError):
        pass

    return None


def _convert_simplified_to_traditional(text: str) -> str:
    try:
        import opencc

        return opencc.OpenCC("s2t.json").convert(text)
    except (ImportError, RuntimeError):
        return text


def _build_company_name_localized(
    company_name: str,
    ticker: str,
    quote: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    normalized_ticker = str(ticker or "").strip().upper()
    fallback_name = str(company_name or normalized_ticker or "N/A").strip() or normalized_ticker or "N/A"

    cache_key = normalized_ticker or fallback_name
    cached = _LOCALIZED_NAME_CACHE.get(cache_key)
    if cached is not None:
        merged = dict(cached)
        merged.setdefault("en", fallback_name)
        return merged

    localized: Dict[str, str] = {"en": fallback_name}

    source_text = ""
    if isinstance(quote, dict):
        for key in ("shortname", "longname", "displayName", "name"):
            value = quote.get(key)
            if isinstance(value, str) and value.strip():
                source_text = value.strip()
                break

    if source_text:
        if _contains_japanese_text(source_text):
            localized["ja"] = source_text
        elif _contains_cjk_text(source_text):
            localized["zh-CN"] = source_text
            localized["zh-TW"] = _convert_simplified_to_traditional(source_text)

    lookup_symbol = normalized_ticker
    for suffix in (".HK", ".SS", ".SZ", ".SH"):
        if lookup_symbol.endswith(suffix):
            lookup_symbol = lookup_symbol[: -len(suffix)]
            break

    if lookup_symbol.isdigit():
        try:
            import akshare as ak

            stock_info = ak.stock_individual_info_em(symbol=lookup_symbol)
            cn_name = _extract_company_name_from_stock_info(stock_info)
            if cn_name:
                localized["zh-CN"] = cn_name
                localized["zh-TW"] = _convert_simplified_to_traditional(cn_name)
        except (ImportError, KeyError, AttributeError) as exc:
            logger.debug("Localized name lookup failed for %s: %s", normalized_ticker, exc)

    _LOCALIZED_NAME_CACHE[cache_key] = dict(localized)
    return localized


def _search_tickers(query: str, limit: int = 5, strict: bool = False) -> list:
    """Search yfinance for similar tickers to suggest.

    - strict=False: swallow upstream failures and return [] (used by assess suggestions)
    - strict=True: raise the last upstream error (used by company finder endpoint)
    """
    query_symbol = query.strip().upper()
    allowed_quote_types = {"EQUITY"}
    last_error: Optional[Exception] = None

    for clear_proxy in (False, True):
        try:
            with _temporarily_clear_proxy_env(clear_proxy):
                import yfinance as yf
                s = yf.Search(query)
                quotes = s.quotes if hasattr(s, 'quotes') else []

                suggestions: list = []
                seen_symbols: set[str] = set()
                for q in quotes:
                    symbol = str(q.get("symbol", "")).strip().upper()
                    if not symbol or symbol == query_symbol or symbol in seen_symbols:
                        continue
                    quote_type = str(q.get("quoteType", "")).strip().upper()
                    if quote_type not in allowed_quote_types:
                        continue

                    seen_symbols.add(symbol)
                    display_name = str(q.get("shortname") or q.get("longname") or "").strip() or symbol
                    localized_name = _build_company_name_localized(display_name, symbol, q)
                    suggestions.append({
                        "symbol": symbol,
                        "name": display_name,
                        "company_name": display_name,
                        "name_localized": dict(localized_name),
                        "company_name_localized": dict(localized_name),
                    })
                    if len(suggestions) >= limit:
                        break

                return suggestions
        except (KeyError, AttributeError, TypeError, ValueError) as exc:
            last_error = exc
            continue

    if strict and last_error is not None:
        raise last_error
    return []


@app.get("/api/v1/symbols/search", tags=["Credit Assessment"])
async def search_symbols(
    q: str = Query(..., min_length=1, description="Ticker/company keyword"),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of results"),
):
    """Search candidate equity tickers for the company finder dialog."""
    import asyncio
    from fastapi.concurrency import run_in_threadpool

    try:
        timeout_seconds = max(0.5, float(os.environ.get("SYMBOL_SEARCH_TIMEOUT_SECONDS", "8")))
    except ValueError:
        timeout_seconds = 8.0

    try:
        results = await asyncio.wait_for(
            run_in_threadpool(_search_tickers, q, limit, True),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail={
                "error": "Symbol search timed out",
                "error_type": "timeout",
                "message": f"Unable to search symbols within {timeout_seconds:.1f}s",
                "query": q,
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Symbol search upstream unavailable",
                "message": f"Unable to search symbols right now: {exc}",
                "query": q,
            },
        ) from exc
    return {
        "query": q,
        "count": len(results),
        "results": results,
    }


@app.post("/api/v1/covenants/check", tags=["Post-Lending Monitoring"])
def check_covenants(request: CovenantCheckRequest):
    """
    Check a company's latest financials against internal credit covenants.

    Useful for continuous monitoring of an existing loan portfolio.
    Returns a report listing each covenant, its threshold, the actual value,
    and whether it was breached.
    """
    ticker = request.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=422, detail={"error": "Ticker cannot be empty."})

    fiscal_year = request.fiscal_year or datetime.now().year

    try:
        data = fetcher.get_financial_data(ticker, request.data_source)
    except DataFetchError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": exc.message,
                "error_type": exc.error_type.value,
                "ticker": exc.ticker,
                "details": exc.details
            }
        )

    if not data:
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"No financial data available for '{ticker}'",
                "error_type": DataFetchErrorType.NO_DATA_AVAILABLE.value,
                "ticker": ticker,
                "details": {"reason": "empty_response"},
            },
        )

    company_name = data.get("company_name", ticker)

    # Extract the latest period's statements for ratio calculation
    history = data.get("history", [])
    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"No financial history available for '{ticker}'",
        )
    latest_period = history[0]
    period_data = {
        'balance': latest_period.get('balance', pd.DataFrame()),
        'income': latest_period.get('income', pd.DataFrame()),
        'cash': latest_period.get('cash', pd.DataFrame()),
        'company_name': company_name,
        'fiscal_year': fiscal_year,
    }
    ratios = _calculate_ratios(period_data)

    report: CovenantReport = covenant_monitor.check_covenants(
        company_name=company_name,
        fiscal_year=fiscal_year,
        ratios=ratios,
        covenants=request.covenants,
    )
    return report


@app.post("/api/v1/reports/pdf", tags=["Reporting"])
async def export_full_pdf(request: PdfExportRequest | dict[str, Any]):
    """Export a single-company full report as a downloadable PDF."""
    if isinstance(request, dict):
        try:
            request = PdfExportRequest(**request)
        except ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail={"error": "Invalid PDF export request", "details": exc.errors()},
            ) from exc
    report = request.report or {}
    lang = request.lang if request.lang in {"en", "zh-CN", "zh-TW", "ja"} else "en"
    theme = request.theme if request.theme in {"dark", "light"} else "dark"
    ticker = str(report.get("ticker") or "RiskLens").upper()

    try:
        pdf_bytes = await generate_full_pdf_async(report, lang, theme)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error": str(exc), "ticker": ticker}) from exc
    except Exception as exc:
        logger.error("PDF export failed for %s: %s", ticker, exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to generate PDF report", "ticker": ticker},
        ) from exc

    filename = f"{ticker}_Full_Report.pdf"
    pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-PDF-SHA256": pdf_sha256,
            "X-PDF-Bytes": str(len(pdf_bytes)),
        },
    )


import os

# ── Static Files (Frontend) ──────────────────────────────────────────────────

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_WEB_DIR = os.path.join(_BASE_DIR, "..", "web", "dist")

@app.get("/", tags=["UI"])
async def serve_frontend():
    """Serve the root index.html SPA."""
    index_path = os.path.join(_WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "Frontend not found. Please create web/index.html"}

# Mount AFTER the explicit "/" route so it doesn't shadow it
_ASSETS_DIR = os.path.join(_WEB_DIR, "assets")
if os.path.isdir(_ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="assets")
if os.path.isdir(_WEB_DIR):
    app.mount("/static", StaticFiles(directory=_WEB_DIR), name="static")

@app.get("/{full_path:path}", tags=["UI"], include_in_schema=False)
async def spa_fallback(full_path: str):
    """SPA catch-all: return index.html for any unmatched GET route.
    
    This enables React Router to handle deep links (e.g. /results/AAPL)
    without returning a 404 on page refresh.
    """
    index_path = os.path.join(_WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="Frontend not built.")

# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
