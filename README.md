# Credit Analyst Toolkit

*A comprehensive Python toolkit for credit analysis and financial statement analysis.*

## Overview

A modular toolkit for financial statement analysis and credit risk assessment.

## Features

### 🔍 Single Analysis
Enter any stock ticker for instant credit analysis:
- US stocks: AAPL, MSFT, GOOGL, TSLA
- HK stocks: 0700.HK, 9988.HK, 2313.HK
- China stocks: 600519.SS, 000001.SZ

### 📚 Batch Analysis
Analyze multiple companies at once:
- Comma-separated input
- CSV file upload
- Results comparison table

### 📈 Portfolio View
Overview of all analyzed companies:
- Rating distribution
- Risk score comparison
- Sortable data table

### 📊 Visualizations
- Coverage ratio trends
- Leverage comparison charts
- Risk radar charts
- Credit scorecards

### 📥 Export
- Excel reports
- CSV data export

## Quick Start

### Web App (Recommended)

```bash
cd web
streamlit run app.py
```

Then open http://localhost:8501

### Command Line

```bash
python src/main.py --demo
```

## Supported Markets

| Market | Ticker Format | Examples |
|--------|--------------|----------|
| US | Symbol | AAPL, MSFT, GOOGL |
| Hong Kong | Symbol.HK | 0700.HK, 9988.HK |
| China A-Share | Code.SS/SZ | 600519.SS, 000001.SZ |
| UK | Symbol.L | HSBC.L |
| Japan | Symbol.T | 7203.T |

*yfinance handles market-specific data automatically.*

## Project Structure

```
credit-analyst-tools-expanded/
├── src/
│   ├── financial_statement_parser.py
│   ├── ratio_analyzer.py
│   ├── credit_risk_assessment.py
│   ├── credit_visualizer.py
│   └── main.py
├── web/
│   ├── app.py
│   └── requirements.txt
├── requirements.txt
└── README.md
```

## Installation

```bash
pip install -r requirements.txt
```

## Ratios Calculated

### Liquidity
- Current Ratio, Quick Ratio, Cash Ratio, Operating CF Ratio

### Leverage
- Debt to Equity, Debt to Assets, Financial Leverage
- Interest Coverage, Debt/EBITDA

### Profitability
- Gross/Operating/Net Margin
- ROA, ROE

### Efficiency
- Asset Turnover, Receivables/Inventory/Payables Turnover

### Cash Flow
- FCF to Debt, FCF to Revenue

## Dependencies

- pandas, numpy, matplotlib
- yfinance, openpyxl
- streamlit (for web app)

## License

MIT

## Author

Right Leung
