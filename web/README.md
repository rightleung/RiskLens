# Credit Analysis Web App

*Interactive web interface for credit analysis, powered by Credit Analyst Toolkit.*

## Overview

A Streamlit-based web application that provides:
- Real-time credit analysis for public companies
- Batch processing for multiple tickers
- Portfolio credit overview
- Excel report export

## Setup

```bash
# 1. Install dependencies
pip install streamlit yfinance pandas numpy openpyxl

# 2. Make sure credit-analyst-tools-expanded/ is in the parent directory
#    (required for the core analysis modules)

# 3. Launch the app
streamlit run app.py
```

## Features

### 🔍 Single Analysis
Enter a stock ticker (AAPL, MSFT, GOOGL) for instant credit analysis:
- Interest coverage, Debt/EBITDA, FCF/Debt, Current Ratio
- Credit rating (AAA to D)
- Strengths and weaknesses analysis
- Full ratio table

### 📚 Batch Analysis
Analyze multiple companies at once:
- Comma-separated input (AAPL, MSFT, GOOGL)
- CSV file upload
- Results table with all metrics
- Export to CSV

### 📈 Portfolio View
Overview of all analyzed companies:
- Average risk score
- Rating distribution chart
- Sortable data table

## Data Source

Uses Yahoo Finance for real-time financial data.

## Requirements

- Python 3.8+
- Streamlit
- yfinance
- pandas
- numpy
- openpyxl

Also requires `credit-analyst-tools-expanded/` in the parent directory for core analysis modules.

## License

MIT
