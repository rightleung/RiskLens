# RiskLens

Language: [English](./README.md) | [简体中文](./docs/readme/README_zh-CN.md) | [繁體中文](./docs/readme/README_zh-TW.md) | [日本語](./docs/readme/README_ja.md)

RiskLens is an institutional credit risk assessment platform. It fetches financial data for listed companies, computes 40+ credit and operating ratios, maps Altman Z-Score outputs to an S&P-style rating, checks post-lending covenants, and exports dashboard, JSON, Excel, and PDF reports.

## What It Provides

- Multi-ticker credit assessment through the FastAPI + React dashboard.
- Financial data retrieval through `yfinance`, with optional AKShare support for Chinese market data.
- Liquidity, solvency, profitability, efficiency, and cash-flow ratio analysis.
- Altman Z-Score zone and S&P-style rating mapping.
- Covenant threshold checks with conservative breach-on-missing-data behavior.
- Localized dashboard terms for English, Simplified Chinese, Traditional Chinese, and Japanese.
- Report outputs for API JSON, frontend workbook export, and full PDF export.

## Runtime Paths

RiskLens has two backend paths:

| Path | Entrypoint | Purpose |
|------|------------|---------|
| Dashboard | `./run_app.sh` -> `src/api.py` | Primary FastAPI API and React SPA on `http://127.0.0.1:8000` |
| MVP compatibility | `main.py` | Legacy `/api/assess` compatibility and smoke checks |

The dashboard path serves the React build from `web/dist/`. Build the frontend before running `./run_app.sh`.

## Requirements

- Python 3.12+
- Node.js and npm for the frontend
- Network access for live `yfinance`/AKShare data

## Quick Start

For a clean local setup:

```bash
./scripts/rebuild_workspace.sh
```

This recreates `.venv`, installs Python dev dependencies, runs `npm ci`, and builds `web/dist/`.

To include AKShare-backed Chinese market data:

```bash
RISKLENS_WITH_CN_DATA=1 ./scripts/rebuild_workspace.sh
```

Run the dashboard:

```bash
./run_app.sh
```

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## Manual Setup

Backend:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e ".[dev]"
```

Frontend:

```bash
cd web
npm ci
npm run build
```

Frontend development server:

```bash
cd web
npm run dev
```

## CLI

Use the launcher from the repository root:

```bash
./run_cli.sh assess AAPL MSFT --data-source yfinance
./run_cli.sh search apple --limit 10
./run_cli.sh covenants AAPL --min-current-ratio 1.2 --max-debt-to-equity 2.0
./run_cli.sh sources
./run_cli.sh version
```

The CLI supports `auto`, `yfinance`, `akshare`, and `demo` as data-source choices where applicable. Use `--output path/to/file.json` to write JSON output to a file and `--compact` for compact JSON.

Optional shell shortcut:

```bash
mkdir -p ~/.local/bin
ln -sf "$(pwd)/risklens" ~/.local/bin/risklens
```

Then run:

```bash
risklens assess NVDA AMD --data-source yfinance
```

## API Examples

### Credit Assessment

```bash
curl -X POST http://127.0.0.1:8000/api/v1/assess \
  -H "Content-Type: application/json" \
  -d '{"tickers":["NVDA","0700.HK"],"data_source":"yfinance","include_suggestions":true}'
```

### Company Search

```bash
curl "http://127.0.0.1:8000/api/v1/symbols/search?q=apple&limit=20"
```

### Covenant Check

```bash
curl -X POST http://127.0.0.1:8000/api/v1/covenants/check \
  -H "Content-Type: application/json" \
  -d '{"ticker":"NVDA","data_source":"yfinance","covenants":{"min_current_ratio":1.2,"max_debt_to_equity":2.0}}'
```

### PDF Export

`POST /api/v1/reports/pdf` accepts a single-company assessment payload returned by `/api/v1/assess`. Abbreviated shape:

```json
{
  "report": { "ticker": "NVDA" },
  "lang": "en",
  "theme": "dark"
}
```

Supported languages are `en`, `zh-CN`, `zh-TW`, and `ja`. Supported themes are `dark` and `light`.

For batch downloads, use `POST /api/v1/reports/pdf/batch` with `reports` (1–10
payloads). The response is `RiskLens_PDF_Reports.zip` and includes
`X-ZIP-SHA256`/`X-ZIP-Bytes` integrity headers. CJK exports use the bundled
Noto font assets under `src/assets/fonts/`; set `RISKLENS_FONT_ZH_CN`,
`RISKLENS_FONT_ZH_TW`, `RISKLENS_FONT_JA_BODY`, or
`RISKLENS_FONT_JA_HEADING` to override them in a deployment image.

## Testing

Run backend tests:

```bash
pytest
```

Run a focused test file:

```bash
pytest tests/test_zscore.py
```

Run frontend checks:

```bash
cd web
npm run lint
npm run build
npm run e2e:preflight
```

Run legacy smoke checks against the MVP compatibility app:

```bash
./.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 18000
./smoke_test.sh http://127.0.0.1:18000
```

## Release Review Checklist

Run the following checks before opening a release PR. Use the official npm
registry so the lockfile and audit results are reproducible:

```bash
./.venv/bin/python -m pip check
./.venv/bin/python -m pytest -q
git diff --check
uvx pip-audit -r requirements.txt

cd web
npm ci --registry=https://registry.npmjs.org
npm run lint
npm run build
npm run e2e:preflight
npm audit --audit-level=high --registry=https://registry.npmjs.org
```

The npm audit is expected to report zero High/Critical findings. The only
accepted residual is the moderate `uuid` advisory pulled by ExcelJS 4.x;
`npm audit fix --force` would downgrade ExcelJS to 3.4.x and is therefore not
used. Live PDF acceptance should additionally cover the A/H/US market matrix,
both themes, all four supported languages, ZIP integrity headers, and a
Poppler-rendered visual check of representative CJK pages.

## Project Structure

```text
RiskLens/
├── run_app.sh
├── run_cli.sh
├── smoke_test.sh
├── scripts/
│   ├── rebuild_workspace.sh
│   └── venv_bootstrap.sh
├── src/
│   ├── api.py
│   ├── risklens_cli.py
│   ├── data_fetcher.py
│   ├── ratio_analyzer.py
│   ├── zscore.py
│   ├── covenant_monitor.py
│   ├── reportlab_pdf_exporter.py
│   ├── reportlab_pdf_renderer.py
│   ├── html_pdf_exporter.py
│   ├── pdf_report_core.py
│   ├── services/
├── web/
│   ├── src/
│   └── dist/
├── docs/
│   ├── architecture/
│   ├── methodology/
│   ├── readme/
│   └── report-workbook/
└── main.py
```

## Key Modules

| Module | Responsibility |
|--------|----------------|
| `src/api.py` | Dashboard FastAPI app, API routes, static SPA serving, concurrency limits |
| `src/services/rich_assessment_service.py` | Multi-period dashboard assessment pipeline |
| `src/services/assessment_service.py` | Legacy single-period MVP/CLI assessment pipeline |
| `src/data_fetcher.py` | Financial data retrieval and caching |
| `src/ratio_analyzer.py` | 40+ financial ratio calculations |
| `src/zscore.py` | Altman Z-Score and rating mapping |
| `src/covenant_monitor.py` | Covenant threshold checking |
| `src/reportlab_pdf_exporter.py` | Full PDF report generation entrypoint |
| `web/src/App.tsx` | Main React dashboard surface |

## Configuration

Settings are loaded from environment variables and optional `.env`. Start from `.env.example` when creating a local file.

Common settings:

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_PORT` | `8000` | Dashboard app port used by local scripts |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Frontend dev origins |
| `ASSESS_MAX_CONCURRENCY` | `8` | Concurrent ticker assessments |
| `ASSESS_TICKER_TIMEOUT_SECONDS` | `20` | Per-ticker assessment timeout |
| `SYMBOL_SEARCH_TIMEOUT_SECONDS` | `8` | Company search timeout |
| `CACHE_TTL_SECONDS` | `600` | Financial data cache TTL |
| `SENTRY_DSN` | empty | Enables Sentry only when set |
| `API_REPORT_DIR` | `/tmp/credit_api_reports` | Dashboard ratio/report artifact directory |

## Documentation

- [Architecture](./docs/architecture/ARCHITECTURE.md)
- [Methodology](./docs/methodology/METHODOLOGY.md)
- [Report workbook spec](./docs/report-workbook/REPORT_WORKBOOK_SPEC.md)
- [Release review checklist](./docs/review/repository-release-checklist.md)
- README translations: [zh-CN](./docs/readme/README_zh-CN.md), [zh-TW](./docs/readme/README_zh-TW.md), [ja](./docs/readme/README_ja.md)

English documentation is the source of truth when translated wording conflicts.
