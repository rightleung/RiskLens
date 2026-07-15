# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RiskLens is an institutional credit risk assessment platform. It takes stock tickers, fetches financial data (yfinance, optionally AKShare), computes ~40+ financial ratios, calculates the Altman Z-Score to produce an S&P-style credit rating, and generates JSON/Excel/PDF reports. It also supports post-lending covenant monitoring. The platform targets four languages: EN, zh-CN, zh-TW, ja.

## Common Commands

### Backend (Python 3.12+)

```bash
# Editable install
pip install -e ".[dev]"

# Run the dashboard (FastAPI + React SPA on port 8000)
./run_app.sh

# Run the CLI
./run_cli.sh assess AAPL MSFT --data-source yfinance
./run_cli.sh search apple --limit 10
./run_cli.sh covenants AAPL --min-current-ratio 1.2 --max-debt-to-equity 2.0

# Run all tests (expect 101 passed)
pytest

# Run a single test file
pytest tests/test_zscore.py

# Run a single test function
pytest tests/test_zscore.py::test_calculate_z_score -k "safe"

# Run with verbose output
pytest -v
```

### Frontend (web/)

```bash
cd web
npm run dev          # Vite dev server
npm run build        # TypeScript compile + Vite bundle
npm run lint         # ESLint
npm run e2e:preflight  # Playwright E2E smoke tests
```

### Clean rebuild

```bash
./scripts/rebuild_workspace.sh                    # Full rebuild (venv + frontend)
RISKLENS_WITH_CN_DATA=1 ./scripts/rebuild_workspace.sh  # With Chinese data support
```

### Smoke tests (against a running dashboard)

```bash
./smoke_test.sh http://127.0.0.1:8000
```

## Architecture

### Data flow

```
User Input -> POST /api/v1/assess -> src/api.py -> RichAssessmentService
  -> FinancialDataFetcher (yfinance/AKShare) -> RatioAnalyzer (~40 ratios)
  -> calculate_z_score() -> CovenantMonitor -> JSON payload -> React Dashboard
```

### Two service layers

- **`AssessmentService`** (`src/services/assessment_service.py`): Simple single-period orchestrator, used by the legacy MVP (`main.py`).
- **`RichAssessmentService`** (`src/services/rich_assessment_service.py`): Multi-period pipeline (annualizes quarterly data, per-period ratios, quarterly-to-FY rating fallback), used by the dashboard (`src/api.py`).

### Key design decisions

- **Concurrency model**: `src/api.py` uses `asyncio.Semaphore` for concurrency control and `run_in_threadpool` to offload synchronous pandas/network work to worker threads, with per-ticker timeouts.
- **Covenant breach-on-missing-data**: When a covenant threshold is configured but data is unavailable, `CovenantMonitor` defaults to **breach** (not pass) for due-diligence safety. Referenced as "OR-002" in comments.
- **Proxy environment clearing**: yfinance searches are retried with proxy env vars (`HTTP_PROXY`, `HTTPS_PROXY`, etc.) temporarily cleared to avoid corporate proxy issues. Implemented in `src/api.py` via `_temporarily_clear_proxy_env`.
- **Sentry is optional**: Sentry error monitoring only activates when `SENTRY_DSN` is set in the environment. If empty, it logs "Sentry disabled" and continues.
- **SPA catch-all**: FastAPI serves the React SPA at `/`, mounts `/assets` for built assets, and has a wildcard catch-all (`GET /{full_path:path}`) returning `index.html` for unmatched routes.

### Entry points

| Launcher | Backend | Purpose |
|----------|---------|---------|
| `./run_app.sh` | `src/api.py` (uvicorn) | Dashboard (primary) |
| `./run_cli.sh` | `src/risklens_cli.py` | CLI batch assessment |
| `main.py` (direct) | `main.py` (uvicorn) | Legacy MVP |

### API surface (dashboard)

- `GET /` — React SPA
- `GET /health` — health check
- `GET /docs` — OpenAPI docs
- `POST /api/v1/assess` — single/multi ticker assessment
- `GET /api/v1/symbols/search` — company finder symbol search
- `POST /api/v1/covenants/check` — covenant threshold check
- `POST /api/v1/reports/pdf` — PDF report generation

## Module Responsibilities

| Module | Role |
|--------|------|
| `src/api.py` | FastAPI app: routes, CORS, error handlers, static serving, SPA catch-all |
| `src/risklens_cli.py` | CLI parser (argparse): `assess`, `search`, `covenants`, `sources`, `version` |
| `src/data_fetcher.py` | Financial data retrieval via yfinance (primary) and AKShare (optional). Includes `SimpleCache` with TTL. |
| `src/ratio_analyzer.py` | Computes ~40+ financial ratios across liquidity, solvency, profitability, efficiency categories. |
| `src/zscore.py` | Pure functions for Altman Z-Score and zone/rating mapping. Side-effect-free. |
| `src/covenant_monitor.py` | Pydantic-based covenant checking with conservative breach-default-on-missing-data. |
| `src/services/rich_assessment_service.py` | Multi-period assessment pipeline (annualizes, per-period ratios, quarterly-to-FY fallback). |
| `src/services/assessment_service.py` | Simple single-period orchestrator for legacy MVP. |
| `src/services/_utils.py` | Shared: `json_safe()` (NaN/inf → None), `safe_number()`, CJK detection. |
| `src/reportlab_pdf_exporter.py` | PDF generation entry point (ReportLab). |
| `src/reportlab_pdf_renderer.py` | ReportLab rendering layer (cover page, ratio tables, z-score, covenant). |
| `src/html_pdf_exporter.py` | HTML-to-PDF data extraction and model building. |
| `src/pdf_report_core.py` | PDF data sanitization and proxy layer. |
| `src/akshare_data.py` | A-share/HK market data (optional, gated by `cn-data` extra). |

## Important Conventions

- **Python 3.12+ required** (enforced in `pyproject.toml`).
- **Editable install**: The project uses `pip install -e .` with `setuptools`. Tests rely on `tests/conftest.py` to set up module aliases (e.g., `from services import RichAssessmentService`).
- **`web/dist/` must exist before running the dashboard** — `run_app.sh` exits with an error if `web/dist/index.html` is missing. Build the frontend first.
- **No Makefile**: All build/run/rebuild operations are shell scripts (`run_app.sh`, `run_cli.sh`, `scripts/rebuild_workspace.sh`, `smoke_test.sh`).
- **Legacy compatibility is explicit**: the deprecated `src/legacy/` and `tests/legacy/` trees have been removed; the supported compatibility surface is the root `main.py` MVP and its smoke test.
- **Monolithic components**: `web/src/App.tsx` (~3800 lines), `data_fetcher.py` (~1100 lines), `ratio_analyzer.py` (~1100 lines), `html_pdf_exporter.py` (~1600 lines), `reportlab_pdf_renderer.py` (~1100 lines). These are flagged for decomposition in `REFACTORING_TODO.md` Phase 8.
- **Frontend translations**: `web/src/translations.ts` maps assessment terms to EN/zh-CN/zh-TW/ja. Backend detects CJK/Japanese text for localized company names.
- **Environment variables**: Config is via `.env.example` — `APP_NAME`, `APP_PORT`, `SENTRY_DSN`, `ENVIRONMENT`, `DEBUG`, `CORS_ORIGINS`, concurrency/tuning vars.
