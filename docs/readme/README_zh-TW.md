# RiskLens

語言: [English](../README.md) | [简体中文](./README_zh-CN.md) | [繁體中文](./README_zh-TW.md) | [日本語](./README_ja.md)

## 1. 執行路徑

RiskLens 目前提供兩條後端執行路徑，對應不同用途：

1. Dashboard 路徑（預設）
- 啟動腳本：`./run_app.sh`
- 後端入口：`src/api.py`（`uvicorn src.api:app`）
- 前端：`web/`（React + Vite 產物由 FastAPI 靜態路由提供）
- 主要 API：`/api/v1/assess`、`/api/v1/symbols/search`、`/api/v1/covenants/check`

2. MVP 相容路徑（保留）
- 後端入口：`main.py`
- API：`/api/assess`、`/api/v1/assess`
- 主要用於歷史相容與 `smoke_test.sh`（目前驗證 `/api/assess`）

## 2. 功能範圍（Dashboard 路徑）

- `GET /`：Dashboard 介面
- `GET /health`：健康檢查
- `GET /docs`：OpenAPI 文件
- `POST /api/v1/assess`：單一/多 ticker 風險評估
- `GET /api/v1/symbols/search`：公司/代碼搜尋（以股票標的為主）
- `POST /api/v1/covenants/check`：契約預檢
- 前端公司搜尋器：可依公司名搜尋、多選並回填 ticker 輸入框

## 3. 專案結構

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
├── main.py           (MVP 相容)
└── *.md
```

## 4. 快速啟動

### 4.1 Dashboard 路徑（建議）

```bash
./run_app.sh
```

存取：
- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

### 4.2 重建開發環境

如須從頭重建本機工作區或恢復缺失的建置產物：

```bash
./scripts/rebuild_workspace.sh
```

這會重建 `.venv`、恢復 `web/node_modules`，並重新建置 `web/dist/`。

如果需要 AKShare 中國市場資料支援：

```bash
RISKLENS_WITH_CN_DATA=1 ./scripts/rebuild_workspace.sh
```

### 4.3 MVP 相容路徑（`/api/assess`）

```bash
./.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 18000
./smoke_test.sh http://127.0.0.1:18000
```

### 4.4 CLI 指令（`risklens`）一次性設定

在專案根目錄（`RiskLens/`）執行一次：

```bash
mkdir -p ~/.local/bin
ln -sf "$(pwd)/risklens" ~/.local/bin/risklens
grep -q 'export PATH="$HOME/.local/bin:$PATH"' ~/.zshrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

驗證：

```bash
risklens version
```

基礎指令：

- `risklens assess AAPL MSFT --data-source yfinance`
- `risklens search apple --limit 10`
- `risklens covenants AAPL --min-current-ratio 1.2 --max-debt-to-equity 2.0`
- `risklens sources`
- `risklens version`

## 5. API 範例（Dashboard 路徑）

### 5.1 風險評估

```bash
curl -X POST http://127.0.0.1:8000/api/v1/assess \
  -H "Content-Type: application/json" \
  -d '{"tickers":["AAPL","0700.HK"],"data_source":"yfinance"}'
```

### 5.2 公司搜尋

```bash
curl "http://127.0.0.1:8000/api/v1/symbols/search?q=apple&limit=20"
```

### 5.3 契約檢查

```bash
curl -X POST http://127.0.0.1:8000/api/v1/covenants/check \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","data_source":"yfinance","covenants":{"min_current_ratio":1.2}}'
```

## 6. 文件分層

以下文件各自對應不同職責邊界，建議保留：

- [ARCHITECTURE.md](../architecture/ARCHITECTURE.md)：執行邊界與元件職責（多語言：[簡中](../architecture/ARCHITECTURE_zh-CN.md)、[繁中](../architecture/ARCHITECTURE_zh-TW.md)、[日文](../architecture/ARCHITECTURE_ja.md)）
- [METHODOLOGY.md](../methodology/METHODOLOGY.md)：評分方法與風險分層口徑（多語言：[簡中](../methodology/METHODOLOGY_zh-CN.md)、[繁中](../methodology/METHODOLOGY_zh-TW.md)、[日文](../methodology/METHODOLOGY_ja.md)）
- [REPORT_WORKBOOK_SPEC.md](../report-workbook/REPORT_WORKBOOK_SPEC.md)：Excel 匯出契約與欄位規則（多語言：[簡中](../report-workbook/REPORT_WORKBOOK_SPEC_zh-CN.md)、[繁中](../report-workbook/REPORT_WORKBOOK_SPEC_zh-TW.md)、[日文](../report-workbook/REPORT_WORKBOOK_SPEC_ja.md)）
- [REPORT_PDF_TEMPLATE_DRAFT_zh-CN.md](../pdf-template/REPORT_PDF_TEMPLATE_DRAFT_zh-CN.md)：完整 PDF 報告樣板與草圖
- 其他語言版本已統一收納到對應目錄（如 `docs/readme/` 與 `docs/architecture/`），方便保持根目錄整潔。

職責劃分：
- README：上手與執行
- Architecture：系統設計與執行邊界
- Methodology：模型與風險口徑
- Workbook Spec：報表輸出契約
- PDF Template：全報告頁面結構與匯出佈局基準

## 7. 多語文件維護策略

- 四語文件均提供完整內容。
- 如有描述衝突，以英文版本為準。
