# RiskLens — Institutional Credit Risk & Covenant Monitoring Platform

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*An enterprise-grade orchestration framework for institutional credit assessment, robust financial statement harmonization, and continuous post-lending covenant monitoring.*

---

## 🏛️ Project Objective

In Commercial and Institutional Banking (CIB), automated ingestion, harmonization, and real-time monitoring of corporate borrower financials is a critical operational bottleneck. **RiskLens** bridges the gap between raw, unstructured financial statements and actionable, auditable credit insights. 

It executes a straight-through processing (STP) pipeline to extract diverse financial data arrays, standardizes over 30 fundamental credit ratios, and objectively applies the **Altman Z-Score Model** to segment credit exposure into Safe, Grey, and Distress tranches.

## 🚀 Enterprise Capabilities

### 1. Unified Global Data Harmonization 
- **Multi-Market Parsing**: Seamlessly acquires and standardizes structures across the US, Hong Kong, and **Mainland China (A-Shares)** markets.
- **Bilingual Taxonomies**: Embedded logic maps complex Chinese onshore reporting (via AKShare) directly into IFRS/US GAAP-aligned equivalents.
- **Dynamic Period Resolution**: Handles and annualizes highly irregular fiscal boundaries, including cumulative onshore quarters (Q1, H1, Q3) and discrete offshore reporting.

### 2. Algorithmic Credit Grading (`POST /api/v1/assess`)
- **Altman Z-Score Engine**: Automates the exact multivariate bankruptcy prediction formula tailored for public corporate debt.
- **Stress Differentiation**: Programmatically isolates strengths and weaknesses by cross-validating Interest Coverage, FCF/Debt, and Debt/EBITDA trajectories across 4 fiscal periods.
- **Implied S&P Rating Translation**: Projects Z-Score outputs onto standard S&P-equivalent agency ratings (AAA through D) for immediate portfolio triage.

### 3. Post-Lending Covenant Surveillance (`POST /api/v1/covenants/check`)
- **Automated Compliance Checks**: Evaluates incoming financials against customizable, loan-specific financial covenants (e.g., minimum liquidity, maximum leverage).
- **Conservative Default Protocols**: Data unavailability or anomalous NaN values safely trigger technical breach alerts rather than false-positive passes.
- **JSON-Schema Triggers**: Capable of integrating natively with downstream core banking systems or alerting dashboards via structured exception payloads.

---

## 📊 Analytics Framework

RiskLens relies exclusively on verified quantitative metrics. The primary scoring agent utilizes the **Altman Z-Score Model**, which synthesizes liquidity, profitability, operating efficiency, leverage, and market valuation into a single dimension of default probability.

> *For a rigorous mathematical breakdown of the Z-Score weights, threshold mappings, and definitions behind the 30+ underlying credit ratios (e.g., FCF-to-Debt, Interest Coverage), refer to [METHODOLOGY.md](./METHODOLOGY.md).*

**1.0 Scope Note:** The live API pipeline uses Altman Z-Score as the sole scoring model. The module `src/credit_risk_assessment.py` is a legacy/experimental framework and is not invoked by the FastAPI service.

---

## 🛠️ Technology Stack & Architecture

Built with a strict separation of concerns, ensuring high throughput, concurrency, and reliability:

- **Data Gateway**: Asynchronous `FastAPI` Python execution handling concurrent HTTP streams for data retrieval and multi-language semantic translation.
- **Analysis Engine**: Highly vectorized `Pandas` and `Numpy` core for instantaneous time-series financial aggregation.
- **Type Safety**: End-to-end `Pydantic` schema enforcement guaranteeing uncompromised data validation before analytical execution.
- **Client Interface**: Ultra-responsive React 19 SPA running on `Vite` featuring zero-latency toggle states, dynamic data visualizations, and robust internationalization.
- **Localization (i18n)**: Out-of-the-box native localization traversing `en`, `zh-CN`, `zh-TW`, and `ja`—complete with fully translated statement taxonomies and AI-assisted cross-border semantic matching for company names.

---

## 🏁 Deployment Protocol

### 1. Execution via Provided Gateway
```bash
# Instantiate the complete API and Frontend environments
./run_app.sh
```

### 2. Manual Bootstrapping
```bash
# Install dependencies
pip install -r requirements.txt

# Ignite ASGI Server
cd src
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```
*API Swagger / OpenAPI Interface available at: `http://localhost:8000/docs`*

### 3. Post-Migration (Linux to macOS)
```bash
# 1) Recreate Python environment to avoid cross-platform binaries
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# 2) Reinstall frontend dependencies
cd web
npm ci
```

---

## 👨‍💻 Maintainer
**Right Leung**
