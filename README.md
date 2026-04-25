# RiskLens

Language: [English](./README.md) | [简体中文](./docs/readme/README_zh-CN.md) | [繁體中文](./docs/readme/README_zh-TW.md) | [日本語](./docs/readme/README_ja.md)

## 1. Runtime Paths

RiskLens currently exposes two runnable backend paths for different purposes:

1. Dashboard path (default)
- Launcher: `./run_app.sh`
- Backend entrypoint: `src/api.py` (`uvicorn src.api:app`)
- Frontend: `web/` (React + Vite build served by FastAPI static routes)
- Primary APIs: `/api/v1/assess`, `/api/v1/symbols/search`, `/api/v1/covenants/check`

2. MVP compatibility path (kept for legacy)
- Backend entrypoint: `main.py`
- APIs: `/api/assess`, `/api/v1/assess`
- Mainly used for backward compatibility and `smoke_test.sh` (currently verifies `/api/assess`)

## 2. Feature Scope (Dashboard Path)

- `GET /`: dashboard UI
- `GET /health`: health endpoint
- `GET /docs`: OpenAPI docs
- `POST /api/v1/assess`: single or multi-ticker risk assessment
- `GET /api/v1/symbols/search`: company/ticker search (equity-focused filtering)
- `POST /api/v1/covenants/check`: covenant pre-check
- Company finder in the frontend: search by company name, multi-select, write back to ticker input

## 3. Project Structure

```text
RiskLens/
├── run_app.sh
├── run_cli.sh
├── smoke_test.sh
├── rollback.sh
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
│   ├── akshare_data.py
│   ├── reportlab_pdf_exporter.py
│   ├── reportlab_pdf_renderer.py
│   ├── html_pdf_exporter.py
│   ├── pdf_report_core.py
│   ├── services/
│   └── legacy/
├── web/
│   ├── src/App.tsx
│   └── dist/
├── docs/
│   ├── architecture/
│   ├── methodology/
│   ├── pdf-template/
│   ├── readme/
│   └── report-workbook/
├── main.py           (MVP compat)
└── *.md
```

## 4. Quick Start

### 4.1 Dashboard Path (recommended)

```bash
./run_app.sh
```

Open:
- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

### 4.2 Rebuild a Clean Workspace

If you want to shrink the local workspace or recover from missing local artifacts, use:

```bash
./scripts/rebuild_workspace.sh
```

This recreates `.venv`, restores `web/node_modules`, and rebuilds `web/dist/`.

If you also need AKShare-backed Chinese market data, set:

```bash
RISKLENS_WITH_CN_DATA=1 ./scripts/rebuild_workspace.sh
```

That installs the `cn-data` extra.

### 4.3 MVP Compatibility Path (`/api/assess`)

```bash
./.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 18000
./smoke_test.sh http://127.0.0.1:18000
```

### 4.4 CLI Command (`risklens`) One-Time Setup

Run once in the project root (`RiskLens/`):

```bash
mkdir -p ~/.local/bin
ln -sf "$(pwd)/risklens" ~/.local/bin/risklens
grep -q 'export PATH="$HOME/.local/bin:$PATH"' ~/.zshrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Verify:

```bash
risklens version
```

Basic commands:

- `risklens assess AAPL MSFT --data-source yfinance`
- `risklens search apple --limit 10`
- `risklens covenants AAPL --min-current-ratio 1.2 --max-debt-to-equity 2.0`
- `risklens sources`
- `risklens version`

## 5. API Examples (Dashboard Path)

### 5.1 Risk Assessment

```bash
curl -X POST http://127.0.0.1:8000/api/v1/assess \
  -H "Content-Type: application/json" \
  -d '{"tickers":["AAPL","0700.HK"],"data_source":"yfinance"}'
```

### 5.2 Company Finder Search

```bash
curl "http://127.0.0.1:8000/api/v1/symbols/search?q=apple&limit=20"
```

### 5.3 Covenant Check

```bash
curl -X POST http://127.0.0.1:8000/api/v1/covenants/check \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","data_source":"yfinance","covenants":{"min_current_ratio":1.2}}'
```

## 6. Documentation Layers

Keep these docs because each has a different ownership boundary:

- [ARCHITECTURE.md](./docs/architecture/ARCHITECTURE.md): runtime boundaries and component ownership (translations: [zh-CN](./docs/architecture/ARCHITECTURE_zh-CN.md), [zh-TW](./docs/architecture/ARCHITECTURE_zh-TW.md), [ja](./docs/architecture/ARCHITECTURE_ja.md))
- [METHODOLOGY.md](./docs/methodology/METHODOLOGY.md): scoring and risk-layer methodology (translations: [zh-CN](./docs/methodology/METHODOLOGY_zh-CN.md), [zh-TW](./docs/methodology/METHODOLOGY_zh-TW.md), [ja](./docs/methodology/METHODOLOGY_ja.md))
- [REPORT_WORKBOOK_SPEC.md](./docs/report-workbook/REPORT_WORKBOOK_SPEC.md): Excel output contract and field rules (translations: [zh-CN](./docs/report-workbook/REPORT_WORKBOOK_SPEC_zh-CN.md), [zh-TW](./docs/report-workbook/REPORT_WORKBOOK_SPEC_zh-TW.md), [ja](./docs/report-workbook/REPORT_WORKBOOK_SPEC_ja.md))
- [REPORT_PDF_TEMPLATE_DRAFT_zh-CN.md](./docs/pdf-template/REPORT_PDF_TEMPLATE_DRAFT_zh-CN.md): Full PDF desktop-first draft template and wireframe
- README translations: [zh-CN](./docs/readme/README_zh-CN.md), [zh-TW](./docs/readme/README_zh-TW.md), [ja](./docs/readme/README_ja.md)

Responsibilities:
- README: onboarding and runbook
- Architecture: system design and deployment/runtime truth
- Methodology: risk/scoring policy
- Workbook Spec: reporting contract between frontend and business users
- PDF Template Draft: full-report page structure and export layout baseline

## 7. Documentation Maintenance Policy

- All four language docs provide full content.
- If any wording conflicts, English docs prevail.
