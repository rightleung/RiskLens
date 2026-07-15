# How RiskLens reads credit risk

Language: [EN](./METHODOLOGY.md) | [简中](./METHODOLOGY_zh-CN.md) | [繁中](./METHODOLOGY_zh-TW.md) | [日本語](./METHODOLOGY_ja.md)

RiskLens combines a familiar distress-screening model with financial ratios, trend analysis, covenant checks, and data-quality warnings. The goal is to make review faster while keeping the underlying signals visible.

The result is an internal screening view. It is not an agency credit rating, a probability of default, or a lending recommendation.

## The headline signal: Altman Z-Score

RiskLens uses the public-company form of the Altman Z-Score:

`Z = 1.2 × X1 + 1.4 × X2 + 3.3 × X3 + 0.6 × X4 + 1.0 × X5`

| Term | Calculation | What it helps show |
|---|---|---|
| X1 | Working capital / Total assets | Short-term financial cushion |
| X2 | Retained earnings / Total assets | Accumulated profitability |
| X3 | EBIT / Total assets | Operating return on assets |
| X4 | Market value of equity / Total liabilities | Market-value coverage of liabilities |
| X5 | Sales / Total assets | Asset turnover |

## Risk zones and implied ratings

| Z-Score | RiskLens zone | Implied rating |
|---:|---|---|
| 4.50 or above | Safe | AAA |
| 3.50–4.49 | Safe | AA |
| 2.99–3.49 | Safe | A |
| 2.50–2.98 | Grey | BBB |
| 1.81–2.49 | Grey | BB |
| 1.20–1.80 | Distress | B |
| 0.50–1.19 | Distress | CCC |
| Below 0.50 | Distress | D |

The implied rating is a RiskLens display scale. It uses familiar rating labels to make relative risk easier to read; it is not issued or endorsed by S&P.

## What sits behind the headline

RiskLens also calculates 40+ indicators across:

- liquidity and short-term coverage;
- leverage and debt capacity;
- profitability and operating performance;
- cash generation and free cash flow;
- asset and working-capital efficiency.

Period trends and peer comparisons help show whether the headline score is improving, weakening, or being driven by a single input.

## Covenant checks

Users can set limits for interest coverage, debt/EBITDA, debt/equity, current ratio, quick ratio, and free-cash-flow/debt.

Each configured covenant is shown as pass or breach. If the required value cannot be calculated, RiskLens treats it as a breach pending manual review. Unconfigured covenants are skipped.

## How missing data is handled

- Missing total assets, total liabilities, EBIT, sales, or working capital produces an `N/A` Z-Score.
- Missing retained earnings or market capitalization contributes zero in the current implementation.
- Historical market capitalization is not always available, so historical periods may use the current market value.
- `NaN` and infinite values are removed before results are returned.

These choices are surfaced as data-quality limitations and should be considered during review.

## When to use extra care

Z-Score can be less representative for financial institutions, early-stage companies, unusual capital structures, and businesses whose accounting or industry economics differ from the original model assumptions. Always combine the output with source statements, industry context, liquidity, ownership, and qualitative analysis.
