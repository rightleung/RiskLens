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
import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
import pandas as pd
import urllib.request
import urllib.parse
import json
import concurrent.futures

logger = logging.getLogger(__name__)

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
        release=f"risklens@{os.environ.get('VERSION', '1.0.0')}",
    )
    logger.info("Sentry error monitoring enabled")
else:
    logger.info("Sentry disabled (set SENTRY_DSN env var to enable)")

from data_fetcher import FinancialDataFetcher, DataFetchError, DataFetchErrorType
from ratio_analyzer import RatioAnalyzer, CreditRatioAnalysis
from covenant_monitor import FinancialCovenants, CovenantMonitor, CovenantReport
from zscore import calculate_z_score

# ── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="RiskLens — Institutional Credit Risk Platform",
    description=(
        "An automated end-to-end framework for institutional credit assessment, "
        "financial ratio analysis, and post-lending covenant monitoring.\n\n"
        "**CONFIDENTIAL — FOR INTERNAL RISK MANAGEMENT USE ONLY**"
    ),
    version="1.0.0",
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
    # This will now raise DataFetchError instead of returning None
    data = fetcher.get_financial_data(ticker, data_source)

    company_name = data.get("company_name", ticker)
    history = data.get("history", [])
    mc = data.get('market_cap', 0)

    # Infer currency from ticker format
    def _infer_currency(t: str) -> str:
        t_up = t.upper()
        if t_up.endswith('.HK'): return 'HKD'
        raw = t_up.replace('.SS','').replace('.SZ','').replace('.SH','')
        if raw.isdigit() and len(raw) == 6: return 'CNY'
        return 'USD'
    currency = _infer_currency(ticker)
    
    company_name_localized = {
        'en': company_name, 
        'zh-CN': company_name, 
        'zh-TW': company_name, 
        'ja': company_name
    }
    
    # Global traditional Chinese fallback for the default fetched name
    try:
        import opencc
        converter_tw = opencc.OpenCC('s2t.json')
        company_name_localized['zh-TW'] = converter_tw.convert(company_name)
    except ImportError:
        pass
    
    # Simple logic to handle common A-Share translations without blocking
    import re
    if re.match(r'^\d{6}\.(SS|SZ|SH)$', ticker.upper()) or currency == 'CNY':
        # If it's a Chinese ticker, fetch the localized name directly from Sina Finance
        # to bypass the ProxyError caused by akshare -> EastMoney.
        try:
            import requests
            stock_code = ticker.split('.')[0]
            # Sina requires sz or sh prefix
            prefix = 'sh' if ticker.endswith(('.SS', '.SH')) or ticker.startswith('6') else 'sz'
            sina_ticker = f"{prefix}{stock_code}"
            
            # Use run_in_threadpool if needed, though this is fast enough mostly.
            # We are already in a threadpool context from process_ticker
            headers = {'Referer': 'http://finance.sina.com.cn/'}
            url = f"http://hq.sinajs.cn/list={sina_ticker}"
            response = requests.get(url, headers=headers, timeout=5)
            response.encoding = 'gbk' # Sina uses GBK
            content = response.text
            
            # Format: var hq_str_sz000002="万 科Ａ,4.990,..."
            if '="' in content:
                data_str = content.split('="')[1].split('";')[0]
                if data_str:
                    fields = data_str.split(',')
                    if len(fields) > 0:
                        cn_name = fields[0].replace(' ', '').replace('Ａ', 'A') # Clean up Sina's weird spacing
                        company_name_localized['zh-CN'] = cn_name
                        # Simple traditional conversion
                        try:
                            import opencc
                            converter = opencc.OpenCC('s2t.json')
                            company_name_localized['zh-TW'] = converter.convert(cn_name)
                        except ImportError:
                            company_name_localized['zh-TW'] = cn_name
        except Exception as e:
            logger.debug(f"Sina translation fetch failed for {ticker}: {e}")
            pass # Fallback to original name if fetch fails
    
    historical_results = []
    
    for period in history:
        try:
            fy_label = period.get('year_label', str(datetime.now().year))
            is_q = period.get('is_quarterly', False)
            
            # Build data object for this specific period
            fy_string = ''.join([c for c in fy_label if c.isdigit()])
            if len(fy_string) >= 4:
                fy_int = int(fy_string[-4:])
            elif len(fy_string) >= 2:
                fy_int = int(fy_string[-2:]) + 2000
            else:
                fy_int = fiscal_year or datetime.now().year
            
            def _safe_copy(df):
                """Safely copy a DataFrame, returning pd.DataFrame() if None/invalid."""
                if df is None:
                    return pd.DataFrame()
                try:
                    if df.empty:
                        return pd.DataFrame()
                    return df.copy()
                except Exception:
                    return pd.DataFrame()
            
            income_df = _safe_copy(period.get('income'))
            cash_df = _safe_copy(period.get('cash'))
            balance_df = _safe_copy(period.get('balance'))
            
            # Annualize flow statements for quarterly data
            # A-share reports from Sina are CUMULATIVE (e.g. Q3 = Jan-Sep),
            # while yFinance quarters are single-quarter figures.
            if is_q:
                annualize_factor = 4  # default for single-quarter (yFinance)
                # Only A-share (Sina) quarters are cumulative; yfinance quarters are single-period.
                if currency == 'CNY':
                    # Parse quarter number to determine cumulative months
                    q_match = None
                    import re as _re
                    q_match = _re.search(r'Q(\d)', fy_label)
                    if q_match:
                        q_num = int(q_match.group(1))
                        # Cumulative: Q1=3mo, Q2(H1)=6mo, Q3=9mo (Q4=annual, not here)
                        months_covered = q_num * 3
                        annualize_factor = 12 / months_covered if months_covered > 0 else 4
                
                if not income_df.empty and 'Value' in income_df.columns:
                    income_df['Value'] = income_df['Value'] * annualize_factor
                if not cash_df.empty and 'Value' in cash_df.columns:
                    cash_df['Value'] = cash_df['Value'] * annualize_factor
                    
            period_data = {
                'balance': balance_df,
                'income': income_df,
                'cash': cash_df,
                'company_name': company_name,
                'fiscal_year': fy_int,
            }
            
            ratios = _calculate_ratios(period_data)
            
            # ── Altman Z-Score (sole scoring model) ──────────────────────────
            ta = analyzer._get_value(balance_df, 'total_assets')
            tl = analyzer._get_value(balance_df, 'total_liabilities')
            tca = analyzer._get_value(balance_df, 'total_current_assets')
            tcl = analyzer._get_value(balance_df, 'total_current_liabilities')
            re = analyzer._get_value(balance_df, 'retained_earnings')
            ebit = analyzer._get_value(income_df, 'operating_income')
            sales = ratios.revenue

            z_score = None
            z_zone = "N/A"
            implied_rating = "N/A"
            strengths = []
            weaknesses = []

            z_result = calculate_z_score(
                total_assets=ta,
                total_liabilities=tl,
                working_capital=(tca or 0) - (tcl or 0),
                retained_earnings=re,
                ebit=ebit,
                sales=sales,
                market_cap=mc,
            )
            z_score = z_result.z_score
            z_zone = z_result.zone
            implied_rating = z_result.implied_rating

            if z_score is not None:
                # Derive strengths / weaknesses from Z-Score sub-components
                ic = ratios.interest_coverage
                d_e = ratios.debt_to_ebitda
                fcf_d = ratios.fcf_to_debt
                cr = ratios.current_ratio

                if ic is not None and ic > 5:
                    strengths.append(f"Strong interest coverage ({ic:.1f}x)")
                elif ic is not None and ic < 2:
                    weaknesses.append(f"Weak interest coverage ({ic:.1f}x)")
                if d_e is not None and d_e < 3:
                    strengths.append(f"Low leverage (Debt/EBITDA: {d_e:.1f})")
                elif d_e is not None and d_e > 5:
                    weaknesses.append(f"High leverage (Debt/EBITDA: {d_e:.1f})")
                if fcf_d is not None and fcf_d > 0.2:
                    strengths.append(f"Strong free cash flow ({fcf_d*100:.1f}% of debt)")
                elif fcf_d is not None and fcf_d < 0:
                    weaknesses.append("Negative free cash flow")
                if cr is not None and cr > 1.5:
                    strengths.append(f"Good liquidity (Current Ratio: {cr:.2f})")
                elif cr is not None and cr < 1:
                    weaknesses.append(f"Weak liquidity (Current Ratio: {cr:.2f})")

            # Build the assessment dict (Z-Score only — no legacy model)
            assessment = {
                "risk_score": float(round(z_score, 2)) if z_score is not None else 0.0,
                "overall_rating": z_zone,
                "implied_rating": implied_rating,
                "strengths": strengths,
                "weaknesses": weaknesses,
            }
            
            # Extract raw metrics for UI transparency
            def _sanitize(v):
                """Replace NaN/inf with None for JSON safety."""
                if v is None:
                    return None
                try:
                    if math.isnan(v) or math.isinf(v):
                        return None
                except TypeError:
                    pass
                return v
            
            raw_metrics = {
                'total_debt': _sanitize(analyzer._get_value(balance_df, 'total_debt')),
                'ebitda': _sanitize(ratios.ebitda),
                'operating_income': _sanitize(ebit),
                'interest_expense': _sanitize(analyzer._get_value(income_df, 'interest_expense')),
                'total_current_assets': _sanitize(tca),
                'total_current_liabilities': _sanitize(tcl),
                'free_cf': _sanitize(analyzer._get_value(cash_df, 'free_cf')),
            }
            
            def safely_to_dict(df):
                if df is None or df.empty: return {}
                try:
                    return df['Value'].dropna().to_dict()
                except Exception:
                    return {}

            historical_results.append({
                "fiscal_year": fy_label,
                "is_quarterly": is_q,
                "assessment": assessment,
                "ratios": ratios.to_dict(),
                "raw_metrics": raw_metrics,
                "statements": {
                    "income": safely_to_dict(period.get('income')),
                    "balance": safely_to_dict(period.get('balance')),
                    "cash": safely_to_dict(period.get('cash'))
                }
            })
        except Exception as exc:
            import traceback
            logger.warning(
                "Skipping period %s for %s: %s\n%s",
                period.get('year_label', '?'), ticker, exc,
                traceback.format_exc()
            )
            # Append a placeholder so the frontend can show a partial-data warning
            historical_results.append({
                "fiscal_year": period.get('year_label', '?'),
                "is_quarterly": period.get('is_quarterly', False),
                "error": str(exc),
                "assessment": None,
                "ratios": {},
                "raw_metrics": {},
                "statements": {}
            })
            continue

    # Fallback missing Quarterly Z-scores to latest FY
    latest_fy_assessment = None
    for res in historical_results:
        if not res.get("is_quarterly") and res.get("assessment") and res["assessment"].get("overall_rating") != "N/A":
            latest_fy_assessment = res["assessment"]
            break
            
    for res in historical_results:
        if res.get("assessment") and res["assessment"].get("overall_rating") == "N/A" and res.get("is_quarterly"):
            if latest_fy_assessment:
                res["assessment"]["risk_score"] = latest_fy_assessment["risk_score"]
                res["assessment"]["overall_rating"] = latest_fy_assessment["overall_rating"]
                res["assessment"]["implied_rating"] = latest_fy_assessment["implied_rating"]
                res["assessment"]["strengths"] = latest_fy_assessment["strengths"]
                res["assessment"]["weaknesses"] = latest_fy_assessment["weaknesses"]

    return {
        "ticker": ticker,
        "company_name": company_name,
        "company_name_localized": company_name_localized,
        "currency": currency,
        "history": historical_results
    }


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    """Health check — confirms the service is running."""
    return {
        "status": "healthy",
        "service": "Institutional Credit Risk API",
        "version": "1.0.0",
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
        except Exception:
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
            except Exception as exc:
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


def _search_tickers(query: str, limit: int = 5) -> list:
    """Search yfinance for similar tickers to suggest."""
    try:
        import yfinance as yf
        s = yf.Search(query)
        quotes = s.quotes if hasattr(s, 'quotes') else []
        return [
            {"symbol": q.get("symbol", ""), "name": q.get("shortname", q.get("longname", ""))}
            for q in quotes[:limit]
            if q.get("symbol")
        ]
    except Exception:
        return []


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
