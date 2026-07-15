# RiskLens

語言: [English](../../README.md) | [简体中文](./README_zh-CN.md) | [繁體中文](./README_zh-TW.md) | [日本語](./README_ja.md)

RiskLens 是面向機構授信風險評估的平台。它會為上市公司取得財務資料，計算 40+ 信用與營運比率，將 Altman Z-Score 映射為類 S&P 信用評級，檢查貸後契約，並輸出 Dashboard、JSON、Excel 和 PDF 報告。

## 功能範圍

- 透過 FastAPI + React Dashboard 進行多 ticker 信用評估。
- 透過 `yfinance` 取得財務資料，並可選接入 AKShare 中國市場資料。
- 覆蓋流動性、償債能力、盈利能力、營運效率與現金流比率。
- Altman Z-Score 風險區間與類 S&P 評級映射。
- 契約閾值檢查；當設定了閾值但資料缺失時，按盡調安全原則預設視為 breach。
- 前端術語支援英文、簡體中文、繁體中文和日文。
- 支援 API JSON、前端工作簿匯出和完整 PDF 匯出。

## 執行路徑

RiskLens 有兩條後端路徑：

| 路徑 | 入口 | 用途 |
|------|------|------|
| Dashboard | `./run_app.sh` -> `src/api.py` | 主要 FastAPI API 與 React SPA，執行於 `http://127.0.0.1:8000` |
| MVP 相容 | `main.py` | 保留舊版 `/api/assess` 相容與 smoke 檢查 |

Dashboard 路徑會從 `web/dist/` 提供 React 建置產物。執行 `./run_app.sh` 前需先建置前端。

## 環境需求

- Python 3.12+
- 用於前端的 Node.js 和 npm
- 即時 `yfinance`/AKShare 資料需要網路存取

## 快速開始

重建完整本機環境：

```bash
./scripts/rebuild_workspace.sh
```

該腳本會重建 `.venv`，安裝 Python dev 依賴，執行 `npm ci`，並建置 `web/dist/`。

如需 AKShare 中國市場資料支援：

```bash
RISKLENS_WITH_CN_DATA=1 ./scripts/rebuild_workspace.sh
```

啟動 Dashboard：

```bash
./run_app.sh
```

訪問：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## 手動安裝

後端：

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e ".[dev]"
```

前端：

```bash
cd web
npm ci
npm run build
```

前端開發伺服器：

```bash
cd web
npm run dev
```

## CLI

在倉庫根目錄使用啟動器：

```bash
./run_cli.sh assess AAPL MSFT --data-source yfinance
./run_cli.sh search apple --limit 10
./run_cli.sh covenants AAPL --min-current-ratio 1.2 --max-debt-to-equity 2.0
./run_cli.sh sources
./run_cli.sh version
```

CLI 在適用位置支援 `auto`、`yfinance`、`akshare` 和 `demo` 資料源。使用 `--output path/to/file.json` 可寫入 JSON 檔案，使用 `--compact` 可輸出緊湊 JSON。

可選 shell 捷徑：

```bash
mkdir -p ~/.local/bin
ln -sf "$(pwd)/risklens" ~/.local/bin/risklens
```

之後可執行：

```bash
risklens assess NVDA AMD --data-source yfinance
```

## API 範例

### 信用評估

```bash
curl -X POST http://127.0.0.1:8000/api/v1/assess \
  -H "Content-Type: application/json" \
  -d '{"tickers":["NVDA","0700.HK"],"data_source":"yfinance","include_suggestions":true}'
```

### 公司搜尋

```bash
curl "http://127.0.0.1:8000/api/v1/symbols/search?q=apple&limit=20"
```

### 契約檢查

```bash
curl -X POST http://127.0.0.1:8000/api/v1/covenants/check \
  -H "Content-Type: application/json" \
  -d '{"ticker":"NVDA","data_source":"yfinance","covenants":{"min_current_ratio":1.2,"max_debt_to_equity":2.0}}'
```

### PDF 匯出

`POST /api/v1/reports/pdf` 接收 `/api/v1/assess` 回傳的單公司評估 payload。節選結構：

```json
{
  "report": { "ticker": "NVDA" },
  "lang": "zh-TW",
  "theme": "dark"
}
```

支援語言：`en`、`zh-CN`、`zh-TW`、`ja`。支援主題：`dark`、`light`。

## 測試

執行後端測試：

```bash
pytest
```

執行單一測試檔：

```bash
pytest tests/test_zscore.py
```

執行前端檢查：

```bash
cd web
npm run lint
npm run build
npm run e2e:preflight
```

針對 MVP 相容應用執行 legacy smoke 檢查：

```bash
./.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 18000
./smoke_test.sh http://127.0.0.1:18000
```

## 專案結構

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

## 關鍵模組

| 模組 | 職責 |
|------|------|
| `src/api.py` | Dashboard FastAPI 應用、API 路由、SPA 靜態託管、並發限制 |
| `src/services/rich_assessment_service.py` | Dashboard 多期間評估流程 |
| `src/services/assessment_service.py` | Legacy MVP/CLI 單期間評估流程 |
| `src/data_fetcher.py` | 財務資料取得與快取 |
| `src/ratio_analyzer.py` | 40+ 財務比率計算 |
| `src/zscore.py` | Altman Z-Score 與評級映射 |
| `src/covenant_monitor.py` | 契約閾值檢查 |
| `src/reportlab_pdf_exporter.py` | 完整 PDF 報告生成入口 |
| `web/src/App.tsx` | React Dashboard 主介面 |

## 設定

設定來自環境變數和可選 `.env` 檔案。建立本機設定時可從 `.env.example` 開始。

常用設定：

| 變數 | 預設值 | 用途 |
|------|--------|------|
| `APP_PORT` | `8000` | 本機 Dashboard 連接埠 |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 前端開發來源 |
| `ASSESS_MAX_CONCURRENCY` | `8` | 並發 ticker 評估數 |
| `ASSESS_TICKER_TIMEOUT_SECONDS` | `20` | 單 ticker 評估逾時 |
| `SYMBOL_SEARCH_TIMEOUT_SECONDS` | `8` | 公司搜尋逾時 |
| `CACHE_TTL_SECONDS` | `600` | 財務資料快取 TTL |
| `SENTRY_DSN` | 空 | 僅設定後啟用 Sentry |
| `API_REPORT_DIR` | `/tmp/credit_api_reports` | Dashboard 比率/報告產物目錄 |

## 文件

- [Architecture](../architecture/ARCHITECTURE.md)
- [Methodology](../methodology/METHODOLOGY.md)
- [Report workbook spec](../report-workbook/REPORT_WORKBOOK_SPEC.md)
- [Release review checklist](../review/repository-release-checklist.md)
- README 翻譯：[zh-CN](./README_zh-CN.md)、[zh-TW](./README_zh-TW.md)、[ja](./README_ja.md)

如果翻譯內容與英文文件衝突，以英文文件為準。
