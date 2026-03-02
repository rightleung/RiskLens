# RiskLens Excel Workbook Spec (Current)

Language: [EN](./REPORT_WORKBOOK_SPEC.md) | [简中](./REPORT_WORKBOOK_SPEC_zh-CN.md) | [繁中](./REPORT_WORKBOOK_SPEC_zh-TW.md) | [日本語](./REPORT_WORKBOOK_SPEC_ja.md)

This document describes the actual Excel export behavior implemented in `web/src/App.tsx` (`exportToExcel`).

## 1. Single-Company Export

- Filename: `<TICKER>_Financial_Data.xlsx`
- Trigger: card-level export button in dashboard

### Sheet Layout (localized names)

1. Risk report sheet (`riskText.sheetName`, purple tab)
2. KPI trends sheet (`excelKpiSheet`, blue tab)
3. Financial statements sheet (`excelStatementsSheet`, green tab)

### Risk Report Sheet

For a single company, the sheet contains:
- merged title row with `Company Name (Ticker)`
- summary rows:
  - Ticker
  - Latest Period
  - Currency
  - Altman Z-Score
  - Z-Score Zone
  - Implied Rating
  - Strengths (localized)
  - Watch Items (localized)
- covenant pre-check table:
  - Metric / Actual / Threshold / Status / Signal / Notes
- data quality rows:
  - Breach Count
  - Missing Key Inputs
  - Missing Items

Rules:
- missing covenant actual value is exported as numeric `0`
- missing covenant is treated as `BREACH (DATA MISSING)`

### KPI Trends Sheet

- columns: periods (`FYxx` / `yyQx`) + optional YoY columns for annual pairs
- metrics include:
  - EBIT
  - EBITDA
  - Total Debt
  - Debt / EBITDA
  - Interest Coverage
  - Free Cash Flow
  - FCF / Debt
  - Current Ratio

### Financial Statements Sheet

- rows aggregate line items from income/balance/cash statements
- row order uses standards-first mapping:
  - US tickers -> USGAAP order
  - HK tickers -> IFRS order
  - CN A-share tickers -> CAS order
- synonymous keys are folded under a primary key (frontend modal behavior), while Excel keeps line-item rows based on ordered key collection
- optional YoY columns are generated for annual periods where both values exist

## 2. Multi-Company Export

- Filename: `RiskLens_MultiCompany_Comparison.xlsx`
- Trigger: top-level "Export All" button when multiple companies are present

### Sheet Layout

1. Risk report sheet (`riskText.sheetName`, purple tab)
2. Portfolio KPI comparison (`excelPortfolioKpiSheet`, blue tab)
3. Portfolio statement comparison (`excelPortfolioStatementsSheet`, blue tab)
4. Per-company statement sheet(s): `<CompanyShortName> <excelCompanySheetSuffix>` (green tab)

### Portfolio Risk Sheet

- one section per company
- each section starts with merged, colored title row
- each section includes summary, covenant pre-check table, and data-quality block

### Portfolio KPI / Statement Comparison Sheets

- first selected company is comparison baseline
- for each period block:
  - baseline company value
  - peer company value(s)
  - delta vs baseline
  - `%` vs baseline

## 3. Formatting Conventions

- period header color bands are applied per fiscal period block
- tab colors:
  - risk: purple
  - portfolio comparison: blue
  - statements: green
- columns are auto-fitted from actual cell text length
- number formats:
  - values: `#,##0.00`
  - percentages: `0.00%`

## 4. Localization

Workbook labels support:
- `en`
- `zh-CN`
- `zh-TW`
- `ja`

Localization covers sheet names, risk labels, covenant status text, and translated strengths/watch items.
