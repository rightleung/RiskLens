# RiskLens Credit Rating Methodology

Language: [EN](./METHODOLOGY.md) | [简中](./METHODOLOGY_zh-CN.md) | [繁中](./METHODOLOGY_zh-TW.md) | [日本語](./METHODOLOGY_ja.md)

This document outlines the quantitative framework used by RiskLens to generate internal credit ratings and risk scores. The methodology bridges classic multivariate bankruptcy prediction (the **Altman Z-Score Model**) with modern, continuous post-lending covenant monitoring.

---

## 1. Primary Scoring Architecture: The Altman Z-Score

RiskLens relies heavily on the **Altman Z-Score** as its core algorithmic engine for public companies. The Z-Score is a multivariate formula that synthesizes five distinct dimensions of a firm's financial health into a single predictive score.

**1.0 Scope Note:** The live API pipeline uses Altman Z-Score as the sole scoring model. The legacy scoring framework in `src/credit_risk_assessment.py` is not invoked by the FastAPI service.

### The Z-Score Formula
`Z = 1.2(X1) + 1.4(X2) + 3.3(X3) + 0.6(X4) + 1.0(X5)`

Where:
- **X1 (Working Capital / Total Assets)**: Evaluates short-term liquidity and buffer.
- **X2 (Retained Earnings / Total Assets)**: Measures cumulative profitability over time, penalizing newly established or chronically unprofitable firms.
- **X3 (EBIT / Total Assets)**: A pure metric of operating efficiency and asset productivity, isolated from tax and leverage effects.
- **X4 (Market Value of Equity / Total Liabilities)**: Introduces market capitalization to assess the market's perception of solvency relative to book debt.
- **X5 (Sales / Total Assets)**: Measures the asset turnover and capital intensity of the business model.

### Z-Score Zone Classification
The raw Z-Score is translated into three distinct risk tranches:
1. **Safe Zone (Z ≥ 2.99)**: Implies robust financial health; bankruptcy likelihood within 2 years is statistically negligible.
2. **Grey Zone (1.81 ≤ Z < 2.99)**: Indicates moderate distress risk; warrants heightened monitoring and potential credit tightening.
3. **Distress Zone (Z < 1.81)**: High probability of default or severe financial restructuring within 24 months.

---

## 2. Implied Rating Mapping Scale

To translate the raw Z-Score into an institutional language compatible with standard credit policy, RiskLens maps the zones to an S&P-equivalent implied rating.

| Z-Score Range | Zone | Implied Rating | Risk Category | Description |
| :--- | :--- | :--- | :--- | :--- |
| ≥ 4.50 | Safe | **AAA / AA** | Prime | Exceptionally strong capacity to meet obligations. |
| 2.99 - 4.49 | Safe | **A** | Upper Medium | Strong capacity, but susceptible to adverse changes. |
| 2.50 - 2.98 | Grey | **BBB** | Lower Medium | Adequate capacity; moderate protection parameters. |
| 1.81 - 2.49 | Grey | **BB** | Speculative | Less vulnerable in the near term, but faces uncertainty. |
| 1.20 - 1.80 | Distress | **B**| Highly Speculative| Vulnerable to adverse business/financial conditions. |
| < 1.20 | Distress | **CCC / D**| Substantial Risk | Currently vulnerable; dependent on favorable conditions. |

---

## 3. Post-Lending Covenant Surveillance

While the Z-Score provides point-in-time default probability, covenants act as an ongoing "early warning system." RiskLens actively monitors these metrics to trigger alerts before a technical default materializes.

### Standard Monitored Covenants:
1. **Leverage Test**: `Debt / EBITDA < [Threshold]` — Prevents the borrower from over-leveraging organically or via acquisition.
2. **Coverage Test**: `EBITDA / Interest Expense > [Threshold]` — Ensures sufficient operating cash remains to satisfy debt servicing costs.
3. **Liquidity Test**: `Current Assets / Current Liabilities > [Threshold]` — Ensures adequate short-term asset coverage for impending liabilities.

*Note: RiskLens treats `null` or missing values conservatively in post-lending surveillance, triggering an automatic assumption of BREACH to enforce manual underwriter review rather than silently passing the covenant.*

---

## 4. Financial Data Normalization

RiskLens performs strict ontological data cleaning across borders to feed the scoring engines accurately:
- **US / Global Models (yFinance)**: Harmonizes standard SEC XBRL tags into RiskLens primary variables.
- **Chinese A-Shares (AKShare)**: Dynamically maps Mainland Chinese GAAP taxonomy (e.g., *长期借款* to Long Term Debt, *营业总收入* to Total Revenue) into identical mathematical structures, ensuring ratings remain completely comparable regardless of geographical origin.
