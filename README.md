# RiskLens

Language: [English](./README.md) | [简体中文](./docs/readme/README_zh-CN.md) | [繁體中文](./docs/readme/README_zh-TW.md) | [日本語](./docs/readme/README_ja.md)

RiskLens turns public-company financial data into a clear credit-risk view. Enter one or more stock tickers to review financial health, compare companies, check lending covenants, and export a report you can share.

It is designed for screening and analysis—not as a replacement for a formal credit rating or professional lending judgment.

## What you can do

- Assess one company or a group of companies in the dashboard.
- Review 40+ liquidity, leverage, profitability, efficiency, and cash-flow ratios.
- See the Altman Z-Score, risk zone, and an easy-to-read implied rating.
- Set covenant limits and highlight passes, breaches, or missing data.
- Compare periods and companies without rebuilding spreadsheets by hand.
- Export results to JSON, Excel, or a presentation-ready PDF.
- Use the product in English, Simplified Chinese, Traditional Chinese, or Japanese.

## From ticker to risk view

```text
Enter ticker(s) → Collect and normalize financials → Calculate risk signals → Review or export
```

RiskLens uses Yahoo Finance through `yfinance` for global listed companies. AKShare support can be enabled for additional China-market coverage.

## Quick start

You need Python 3.12+, Node.js, npm, and network access for live market data.

Build the local workspace:

```bash
./scripts/rebuild_workspace.sh
```

Start RiskLens:

```bash
./run_app.sh
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

To include AKShare-backed China-market data during setup:

```bash
RISKLENS_WITH_CN_DATA=1 ./scripts/rebuild_workspace.sh
```

## Using RiskLens

### Dashboard

Search by company name or enter tickers directly. A result includes the latest risk view, historical trends, financial statements, covenant checks, and export actions.

Useful local pages:

- Dashboard: `http://127.0.0.1:8000/`
- Service health: `http://127.0.0.1:8000/health`
- Interactive API guide: `http://127.0.0.1:8000/docs`

### Command line

```bash
./run_cli.sh assess AAPL MSFT --data-source yfinance
./run_cli.sh search apple --limit 10
./run_cli.sh covenants AAPL --min-current-ratio 1.2 --max-debt-to-equity 2.0
```

Use `--output path/to/file.json` to save an assessment. Run `./run_cli.sh --help` to see all options.

### API

The primary endpoints are:

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/assess` | Assess one or more companies |
| `GET /api/v1/symbols/search` | Find a listed-company ticker |
| `POST /api/v1/covenants/check` | Check selected covenant limits |
| `POST /api/v1/reports/pdf` | Create a single-company PDF |
| `POST /api/v1/reports/pdf/batch` | Download up to 10 PDFs as a ZIP |

Request and response examples are available in the interactive API guide at `/docs`.

## How to read the result

- **Z-Score** summarizes five balance-sheet and earnings signals into one score.
- **Risk zone** groups the score into Safe, Grey, or Distress.
- **Implied rating** translates the score into familiar credit language for internal screening.
- **Ratios and trends** show what is driving the result over time.
- **Covenant checks** compare actual ratios with limits you choose.
- **Data-quality notes** show where inputs are incomplete or require review.

When a covenant is configured but its underlying data is unavailable, RiskLens marks it as a breach pending manual review. This avoids silently treating missing information as a pass.

## Important limitations

- The implied rating is a RiskLens interpretation, not a rating issued by S&P or another rating agency.
- Public market data may be delayed, restated, incomplete, or mapped differently across accounting standards.
- Historical scores may use current market capitalization when a historical value is unavailable.
- The Altman model is one signal and should be considered alongside industry, ownership, liquidity, and qualitative analysis.
- RiskLens does not provide investment, legal, or lending advice.

## For contributors

Run the main checks before submitting a change:

```bash
pytest
cd web && npm run lint && npm run build && npm run e2e:preflight
```

The primary application is `src/api.py` plus the React app in `web/`. The root `main.py` remains only for compatibility checks.

## Guides

- [How RiskLens works](./docs/architecture/ARCHITECTURE.md)
- [How RiskLens reads credit risk](./docs/methodology/METHODOLOGY.md)
- [Working with Excel exports](./docs/report-workbook/REPORT_WORKBOOK_SPEC.md)
- [Documentation in other languages](./docs/readme/README.md)
- [Release checklist](./docs/review/repository-release-checklist.md)
