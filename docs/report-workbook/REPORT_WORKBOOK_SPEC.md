# Working with RiskLens Excel exports

Language: [EN](./REPORT_WORKBOOK_SPEC.md) | [简中](./REPORT_WORKBOOK_SPEC_zh-CN.md) | [繁中](./REPORT_WORKBOOK_SPEC_zh-TW.md) | [日本語](./REPORT_WORKBOOK_SPEC_ja.md)

Excel exports turn the dashboard result into a workbook that can be reviewed, shared, or used as a starting point for further analysis.

## Single-company workbook

From a company card, choose the Excel export action. The file is named `<TICKER>_Financial_Data.xlsx` and contains three views.

### Risk overview

The first sheet brings together the latest period, currency, Altman Z-Score, risk zone, implied rating, strengths, watch items, covenant results, and data-quality notes.

### KPI trends

The trend sheet shows key measures across available annual and quarterly periods, including EBIT, EBITDA, total debt, leverage, interest coverage, free cash flow, FCF/debt, and current ratio.

When a suitable comparison period exists, the workbook adds year-over-year changes. Quarterly results are compared with the same quarter of the previous year; annual results are compared with the previous available year.

### Financial statements

Income statement, balance-sheet, and cash-flow items are arranged in a consistent order. RiskLens uses US GAAP, IFRS, or CAS label mappings where applicable so that similar line items are easier to follow across markets.

## Multi-company workbook

When several companies are assessed, choose **Export All**. The file is named `RiskLens_MultiCompany_Comparison.xlsx` and includes:

- a portfolio risk overview with one section per company;
- a cross-company KPI comparison;
- a cross-company financial-statement comparison;
- a separate statement sheet for each company.

The first selected company is used as the comparison baseline. Other companies show both the absolute difference and percentage difference from that baseline where calculation is possible.

## Reading the workbook

- Purple identifies risk-overview content.
- Blue identifies portfolio and KPI comparisons.
- Green identifies financial statements.
- Numbers use consistent decimal and percentage formats.
- Column widths adapt to the displayed content.
- Missing covenant inputs require review and are treated as breaches rather than passes.

## Languages

Sheet names, risk labels, covenant status, strengths, and watch items follow the language selected in RiskLens: English, Simplified Chinese, Traditional Chinese, or Japanese.

The workbook reflects the data available at export time. Always review data-quality notes before relying on a comparison or covenant result.
