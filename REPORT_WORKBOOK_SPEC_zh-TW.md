# RiskLens Excel 報告工作簿規格（v1.0）

本文件定義 Excel 匯出會產生的內容，以及各區塊背後的邏輯。

## 1）單公司匯出（`<TICKER>_Risk_Report.xlsx`）

### 工作表命名（統一）
1. `01_Risk_Report`
2. `02_KPI_Trends`
3. `03_Financial_Statements`

### `01_Risk_Report` 內容
- `Executive Summary`
  - Ticker
  - Company Name（在地化）
  - Latest Period
  - Currency
  - Data Source
  - Generated At
  - Altman Z-Score
  - Z-Score Zone
  - Implied Rating
  - Strengths（在地化）
  - Watch Items（在地化）
- `Key Metrics`
  - Interest Coverage
  - Debt / EBITDA
  - FCF / Debt
  - Current Ratio
  - 每個指標包含：
    - Actual
    - Benchmark
    - Signal（`Strong` / `Neutral` / `Watch`）
- `Covenant Pre-Check`
  - Covenant
  - Actual
  - Threshold
  - Status
  - Notes
- `Data Quality`
  - Breach Count
  - Notes（Breach Count 的定義說明）
  - Missing Key Inputs
  - Missing Items
- `Methodology & Boundary`
  - 模型邊界說明（v1.0 僅包含 Altman）
  - 缺失輸入視為 breach（保守控制）
  - 非投資建議免責聲明

### `02_KPI_Trends` 內容
- 核心 KPI 跨期間趨勢表
- 年度期間提供 YoY 欄位（可用時含絕對變化與百分比變化）

### `03_Financial_Statements` 內容
- 原始財務報表項目（損益 / 資產負債 / 現金流量）
- 多期間比較
- 年度期間提供 YoY 欄位（可用時含絕對變化與百分比變化）

## 2）多公司匯出（`RiskLens_MultiCompany_Comparison.xlsx`）

### 工作表命名（統一）
1. `01_Portfolio_Risk_Summary`
2. `02_Portfolio_KPI_Comparison`
3. `03_Portfolio_Statement_Comparison`
4. `04_<TICKER>_Statements`（每家公司一張）

### `01_Portfolio_Risk_Summary` 內容
- 產生時間戳
- 各公司摘要：
  - Ticker
  - Company Name
  - Latest Period
  - Z-Score
  - Implied Rating
  - Breach Count
  - Missing Key Inputs
  - Missing Items
- 邊界說明與 Breach Count 定義

### `02_Portfolio_KPI_Comparison` 內容
- 各公司按期間的 KPI 橫向比較
- 基準公司與同業的 delta 與 delta %

### `03_Portfolio_Statement_Comparison` 內容
- 各公司按期間的報表行項目橫向比較
- 基準公司與同業的 delta 與 delta %

### `04_<TICKER>_Statements` 內容
- 公司層級報表明細
- 期間視圖與 YoY 視圖

## 3）邏輯定義

### Covenant 預檢規則（v1.0 預設）
- Interest Coverage：`>= 3.0`
- Debt / EBITDA：`<= 4.0`
- Current Ratio：`>= 1.2`
- FCF / Debt：`>= 0.05`

### Breach Count 定義
`Breach Count = number of covenant checks flagged as BREACH, including DATA MISSING cases.`

### 缺失項處理
- 缺失的關鍵輸入會在報告輸出中明確列出。
- 缺失的 covenant 指標視為 breach（`BREACH (DATA MISSING)`）。

## 4）在地化行為
- Strengths / Watch Items 透過前端文字翻譯器翻譯。
- Missing Items 優先使用在地化 KPI 標籤，回退為 metric-key prettifier。
- 報告標籤支援 `en`、`zh-CN`、`zh-TW`、`ja`。
