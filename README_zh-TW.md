# RiskLens

語言: [English](./README.md) | [简体中文](./README_zh-CN.md) | [繁體中文](./README_zh-TW.md) | [日本語](./README_ja.md)

## 1. 執行路徑

RiskLens 目前提供兩條後端執行路徑，對應不同用途：

1. Dashboard 路徑（預設）
- 啟動腳本：`./run_app.sh`
- 後端入口：`src/api.py`（`uvicorn api:app`）
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
├── smoke_test.sh
├── src/
│   ├── api.py
│   ├── data_fetcher.py
│   ├── ratio_analyzer.py
│   ├── covenant_monitor.py
│   └── zscore.py
├── web/
│   ├── src/App.tsx
│   └── dist/
├── main.py
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

### 4.2 MVP 相容路徑（`/api/assess`）

```bash
./.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 18000
./smoke_test.sh http://127.0.0.1:18000
```

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

建議保留以下三份文件，因為各自負責不同邊界：

- [ARCHITECTURE.md](./ARCHITECTURE.md)：執行邊界與元件職責
- [METHODOLOGY.md](./METHODOLOGY.md)：評分方法與風險分層口徑
- [REPORT_WORKBOOK_SPEC.md](./REPORT_WORKBOOK_SPEC.md)：Excel 匯出契約與欄位規則

職責劃分：
- README：上手與執行
- Architecture：系統設計與執行邊界
- Methodology：模型與風險口徑
- Workbook Spec：報表輸出契約

## 7. 多語文件維護策略

- 四語文件均提供完整內容。
- 如有描述衝突，以英文版本為準。
