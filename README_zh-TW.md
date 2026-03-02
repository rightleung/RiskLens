# RiskLens — 機構信用風險與契約監測平台

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*一個專為機構信用評估、強大的財務報表統一化處理以及持續的貸後契約監測而打造的企業級編排框架。*

---

## 🏛️ 專案目標

在商業及機構銀行業務 (CIB) 中，企業借款人財務資料的自動化接入、統一化規範以及即時監測是一個關鍵的營運瓶頸。**RiskLens** 致力於消除雜亂無章、非結構化的財務報表與具備可操作性、可審計的信用洞察之間的鴻溝。

系統執行直通式處理 (STP) 管道以萃取多樣化的財務資料陣列，標準化計算超過 30 種基礎信用比率，並客觀地運用 **Altman Z-Score 模型**，將信用曝險劃分為安全 (Safe)、灰色 (Grey) 以及違約危機 (Distress) 檔次。

## 🚀 企業級能力

### 1. 統一的全球資料標準化處理
- **多市場解析**：無縫獲取並標準化美國、香港以及**中國大陸 (A股)** 市場的資料架構。
- **雙語分類標準**：內建邏輯將複雜的中國在岸財務報告（透過 AKShare）直接映射為符合 IFRS/US GAAP 的等效標準。
- **動態週期解析**：處理並年化極其不規則的財年邊界，包括累計的在岸季度報表（第一季、上半年、第三季）以及離散的離岸報告。

### 2. 演算法信用評級體系 (`POST /api/v1/assess`)
- **Altman Z-Score 引擎**：自動化執行專為公眾公司債務量身定制的多元破產預測公式。
- **壓力差異化分析**：透過在 4 個財務週期內對利息保障倍數、FCF/債務 以及 債務/EBITDA 的軌跡進行交叉驗證，程式化地分離企業的優勢和劣勢。
- **隱含標準普爾評級轉換**：將 Z-Score 輸出直接投射到標準普爾 (S&P) 等效的機構評級（從 AAA 到 D），以便即時進行投資組合的分類與篩查。

### 3. 貸後契約監測 (`POST /api/v1/covenants/check`)
- **自動化合規性審查**：根據可客製化的、基於特定貸款合約的財務契約（例如，最低流動性要求、最高槓桿率上限）評估最新傳入的財務資料。
- **保守失敗熔斷機制**：為避免發生「偽陰性」（因資料缺失而錯誤地判斷為達標），資料不可用或出現異常的 NaN 值將安全地觸發技術違約警報，強制交由承銷商人工覆核。
- **JSON-Schema 觸發器**：具備透過結構化異常載荷（Payload）與下游核心銀行系統或警報儀表板進行本機整合的能力。

---

## 📊 分析框架

RiskLens 僅依賴經過交叉驗證的量化指標。核心評分代理使用 **Altman Z-Score 模型**，該模型將流動性、獲利能力、營運效率、槓桿率以及市場估值綜合成為一個預測違約機率的單一維度。

> *有關 Z-Score 權重的嚴謹數學分解、閾值映射表以及 30 多種底層信貸風險比率（例如 自由現金流/債務比率、利息保障倍數）的詳細定義，請參閱 [METHODOLOGY.md](./METHODOLOGY_zh-TW.md)。*
> *有關 Excel 報告輸出結構、Sheet 命名規範及契約預檢查邏輯，請參閱 [REPORT_WORKBOOK_SPEC.md](./REPORT_WORKBOOK_SPEC.md)。*

---

## 🛠️ 技術疊代與系統架構

基於嚴格的關注點分離原則建構，確保高吞吐量、並發能力和可靠性：

- **資料閘道**：非同步 `FastAPI` (Python) 執行環境，處理用以萃取資料和進行多語言語意翻譯的並發 HTTP 流。
- **分析引擎**：高度向量化的 `Pandas` 和 `Numpy` 核心，實現瞬時的時序財務聚合計算。
- **型別安全**：端到端的 `Pydantic` Schema 強制約束，確保在執行分析邏輯前提供絕不妥協的資料驗證。
- **客戶端介面**：基於 `Vite` 運行的極速飆網 React 19 SPA。具備零延遲的控制項切換狀態、動態資料視覺化以及強大的國際化支援。
- **在地化支援 (i18n)**：開箱即用的原生在地化能力，覆蓋 `en`、`zh-CN`、`zh-TW` 和 `ja` 四種語言——配備完全翻譯的財務報表分類目錄以及 AI 輔助的跨國公司名稱語意匹配。

---

## 🏁 部署協議

### 1. 透過配套閘道執行
```bash
# 實例化完整的 API 以及前端環境
./run_app.sh
```

### 2. 手動啟動
```bash
# 安裝相依套件
pip install -r requirements.txt

# 點燃 ASGI 伺服器
cd src
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```
*API Swagger / OpenAPI 介面存取位址：`http://localhost:8000/docs`*

### 3. 前端本機開發（可選）
```bash
cd web
npm install
npm run dev
```
*Vite 前端位址：`http://localhost:5173`*  
*使用 Vite 開發模式時，後端仍需運行在 `http://localhost:8000`。*

---

## 🔌 API 快速範例

### 健康檢查
```bash
curl http://localhost:8000/health
```

### 信用風險評估
```bash
curl -X POST http://localhost:8000/api/v1/assess \
  -H "Content-Type: application/json" \
  -d '{
    "tickers": ["AAPL", "MSFT", "0700.HK", "000002.SZ"],
    "data_source": "yfinance"
  }'
```

### 貸後契約檢查
```bash
curl -X POST http://localhost:8000/api/v1/covenants/check \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "data_source": "yfinance",
    "covenants": {
      "min_current_ratio": 1.2,
      "max_debt_to_ebitda": 4.0,
      "min_interest_coverage": 2.0,
      "min_fcf_to_debt": 0.05
    }
  }'
```

---

## ✅ 測試

```bash
pytest tests -v
```

目前測試主要覆蓋：
- Altman Z-Score 區間與評級映射邊界
- 財務比率計算邏輯
- 契約違約判定與技術性違約預設行為
- 信用評估主流程行為

---

## 📁 專案目錄結構

```text
RiskLens/
├── src/                    # FastAPI 服務與風險引擎
├── tests/                  # Pytest 測試集
├── web/                    # React + Vite 前端
├── data/                   # 本機資料產物
├── METHODOLOGY_zh-TW.md    # 模型方法論（繁中）
├── ARCHITECTURE_zh-TW.md   # 系統架構說明（繁中）
└── REPORT_WORKBOOK_SPEC.md # Excel 報告結構規範
```

---

## 🧩 常見問題排查

- 出現 `ModuleNotFoundError` 或相依衝突：
  重建 `.venv` 並重新安裝 `requirements.txt`。
- A 股公司名或在地化名稱未正確顯示：
  安裝可選相依 `opencc` 後重試。
- Vite 前端無法呼叫後端 API：
  確認後端運行在 `127.0.0.1:8000`，再重新整理頁面。
- 報表期間為空或不完整：
  檢查代碼後綴格式（`.HK`、`.SS`、`.SZ`、`.SH`）與資料來源。

---

## 👨‍💻 作者
**Right Leung**
