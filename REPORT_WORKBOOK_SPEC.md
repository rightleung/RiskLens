# RiskLens Excel Report Workbook Spec (v1.0)

This document defines what the Excel export generates and the logic behind each section.

## 1) Single-company export (`<TICKER>_Risk_Report.xlsx`)

### Sheet naming (unified)
1. `01_Risk_Report`
2. `02_KPI_Trends`
3. `03_Financial_Statements`

### `01_Risk_Report` content
- `Executive Summary`
  - Ticker
  - Company Name (localized)
  - Latest Period
  - Currency
  - Data Source
  - Generated At
  - Altman Z-Score
  - Z-Score Zone
  - Implied Rating
  - Strengths (localized)
  - Watch Items (localized)
- `Key Metrics`
  - Interest Coverage
  - Debt / EBITDA
  - FCF / Debt
  - Current Ratio
  - For each metric:
    - Actual
    - Benchmark
    - Signal (`Strong` / `Neutral` / `Watch`)
- `Covenant Pre-Check`
  - Covenant
  - Actual
  - Threshold
  - Status
  - Notes
- `Data Quality`
  - Breach Count
  - Notes (definition of breach count)
  - Missing Key Inputs
  - Missing Items
- `Methodology & Boundary`
  - Model scope note (Altman only in v1.0)
  - Missing input treated as breach (conservative control)
  - Non-investment-advice disclaimer

### `02_KPI_Trends` content
- Core KPI trend table across periods
- YoY columns for annual periods (absolute and % change where available)

### `03_Financial_Statements` content
- Raw financial statement items (income / balance / cash)
- Multi-period comparison
- YoY columns for annual periods (absolute and % change where available)

## 2) Multi-company export (`RiskLens_MultiCompany_Comparison.xlsx`)

### Sheet naming (unified)
1. `01_Portfolio_Risk_Summary`
2. `02_Portfolio_KPI_Comparison`
3. `03_Portfolio_Statement_Comparison`
4. `04_<TICKER>_Statements` (one per company)

### `01_Portfolio_Risk_Summary` content
- Generated timestamp
- Per-company summary:
  - Ticker
  - Company Name
  - Latest Period
  - Z-Score
  - Implied Rating
  - Breach Count
  - Missing Key Inputs
  - Missing Items
- Boundary notes and breach-count definition

### `02_Portfolio_KPI_Comparison` content
- Cross-company KPI comparison per period
- Base company vs peers delta and delta %

### `03_Portfolio_Statement_Comparison` content
- Cross-company statement line-item comparison per period
- Base company vs peers delta and delta %

### `04_<TICKER>_Statements` content
- Company-level statement details
- Period and YoY views

## 3) Logic Definitions

### Covenant pre-check rules (default v1.0)
- Interest Coverage: `>= 3.0`
- Debt / EBITDA: `<= 4.0`
- Current Ratio: `>= 1.2`
- FCF / Debt: `>= 0.05`

### Breach Count definition
`Breach Count = number of covenant checks flagged as BREACH, including DATA MISSING cases.`

### Missing item handling
- Missing key inputs are listed explicitly in report output.
- Missing covenant metric is treated as breach (`BREACH (DATA MISSING)`).

## 4) Localization behavior
- Strengths / Watch Items are translated via frontend text translator.
- Missing Items use localized KPI labels first; fallback to metric-key prettifier.
- Report labels support `en`, `zh-CN`, `zh-TW`, `ja`.
