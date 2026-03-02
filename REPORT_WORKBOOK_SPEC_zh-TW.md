# RiskLens Excel 工作簿規格（目前實作）

語言: [EN](./REPORT_WORKBOOK_SPEC.md) | [简中](./REPORT_WORKBOOK_SPEC_zh-CN.md) | [繁中](./REPORT_WORKBOOK_SPEC_zh-TW.md) | [日本語](./REPORT_WORKBOOK_SPEC_ja.md)

本文描述 `web/src/App.tsx` 中 `exportToExcel` 的實際匯出行為。

## 1. 單一公司匯出

- 檔名：`<TICKER>_Financial_Data.xlsx`
- 觸發方式：Dashboard 公司卡片匯出按鈕

### Sheet 版面（多語名稱）

1. 風險報告頁（`riskText.sheetName`，紫色標籤）
2. KPI 趨勢頁（`excelKpiSheet`，藍色標籤）
3. 財務報表頁（`excelStatementsSheet`，綠色標籤）

### 風險報告頁

單一公司風險頁包含：
- 合併標題列：`公司名稱 (Ticker)`
- 摘要列：
  - Ticker
  - Latest Period
  - Currency
  - Altman Z-Score
  - Z-Score Zone
  - Implied Rating
  - Strengths（多語）
  - Watch Items（多語）
- 契約預檢表：
  - Metric / Actual / Threshold / Status / Signal / Notes
- 資料品質區：
  - Breach Count
  - Missing Key Inputs
  - Missing Items

規則：
- 契約實際值缺失時，匯出為數值 `0`
- 缺失契約一律視為 `BREACH (DATA MISSING)`

### KPI 趨勢頁

- 欄位：期間欄（`FYxx` / `yyQx`）+ 年度可選 YoY 欄
- 指標包含：
  - EBIT
  - EBITDA
  - Total Debt
  - Debt / EBITDA
  - Interest Coverage
  - Free Cash Flow
  - FCF / Debt
  - Current Ratio

### 財務報表頁

- 行資料來自損益表/資產負債表/現金流量表彙整
- 排序採準則優先映射：
  - 美股 ticker -> USGAAP 順序
  - 港股 ticker -> IFRS 順序
  - A 股 ticker -> CAS 順序
- 同義科目在前端彈窗折疊為主科目；Excel 仍依有序鍵集合輸出行
- 年度區間在資料成對存在時可輸出 YoY 欄

## 2. 多公司匯出

- 檔名：`RiskLens_MultiCompany_Comparison.xlsx`
- 觸發方式：多公司結果時頂部 `Export All` 按鈕

### Sheet 版面

1. 風險報告頁（`riskText.sheetName`，紫色標籤）
2. 組合 KPI 對比頁（`excelPortfolioKpiSheet`，藍色標籤）
3. 組合報表對比頁（`excelPortfolioStatementsSheet`，藍色標籤）
4. 公司分表：`<CompanyShortName> <excelCompanySheetSuffix>`（綠色標籤）

### 組合風險頁

- 每家公司一個區塊
- 每個區塊由合併且著色標題列開始
- 每個區塊含摘要區、契約預檢表、資料品質區

### 組合 KPI / 報表對比頁

- 第一家選中公司作為比較基準
- 每個期間區塊包含：
  - 基準公司值
  - 同行公司值
  - 相對基準差值
  - 相對基準 `%`

## 3. 格式慣例

- 每個期間區塊使用獨立表頭色帶
- 標籤色：
  - risk：紫色
  - portfolio comparison：藍色
  - statements：綠色
- 欄寬依實際儲存格文字自動調整
- 數字格式：
  - 數值：`#,##0.00`
  - 百分比：`0.00%`

## 4. 多語系

工作簿標籤支援：
- `en`
- `zh-CN`
- `zh-TW`
- `ja`

在地化覆蓋 sheet 名稱、風險標籤、契約狀態文字與 strengths/watch items 翻譯。
