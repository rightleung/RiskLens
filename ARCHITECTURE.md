# RiskLens Architecture Overview

RiskLens is built on a modern, decoupled architecture designed to handle institutional credit risk analysis. The system is split into a high-performance Python analytics backend and a responsive React frontend, connected via a RESTful JSON API.

## System Architecture

### 1. The Backend Gateway (FastAPI)
The backend is built with **FastAPI**, providing high-throughput asynchronous execution, automatic OpenAPI documentation, and strict data validation.
- **`api.py` (The Orchestrator)**: Exposes the `POST /api/v1/assess` endpoint. It receives an array of ticker symbols and orchestrates the data fetching and translation processes.
- **Concurrent Execution**: To dramatically reduce response latency, multi-language semantic matching (Google Translate) is executed dynamically using Python's `concurrent.futures.ThreadPoolExecutor`, allowing English, Simplified Chinese, Traditional Chinese, and Japanese names to be fetched in parallel.

### 2. The Data Ingestion Layer (`data_fetcher.py`)
This layer handles the physical retrieval of financial datasets from external APIs. It implements a robust fallback methodology:
- **AKShare (China A-Shares & HK)**: Primary pipeline for onshore Chinese equities (e.g., `600673.SS`). Directly queries Mainland APIs (`stock_financial_report_sina`, `stock_individual_info_em`) handling complex Chinese GAAP taxonomy and converting irregular reporting periods (Q1, H1, Q3) into annualized standard formats.
- **yFinance (Global/US)**: Serves as the primary engine for US/European markets and acts as a safety fallback if onshore APIs throttle connections.

### 3. The Analytics & Surveillance Engines
- **`ratio_analyzer.py`**: A pure mathematical engine that processes raw ingested arrays into 30+ sophisticated credit ratios (Current Ratio, FCF/Debt, Operating Margin).
- **Altman Z-Score Model (`zscore.py`)**: The finalized ratios are fed into the Z-Score engine to generate the final probabilistic assessment (Safe, Grey, Distress). This is the sole scoring model in 1.0.
- **`covenant_monitor.py`**: A specialized module that evaluates the calculated ratios against strict predefined constraints (e.g., Debt/EBITDA < 3.5x). Crucially, the system fails conservatively—if a required metric is missing (`null`), it triggers a technical breach alert rather than defaulting to a pass.

### 4. The Frontend Client (React 19 + Vite)
- **State Management**: Built as a Single Page Application (SPA) utilizing functional React Hooks. Contains centralized state logic for dark mode (`useTheme`), active company datasets, and responsive financial modals.
- **UI/UX**: Styled extensively with `Tailwind CSS`, utilizing glassmorphism utilities (`glass-panel`, `glass-header`) to establish a premium, institutional aesthetics.
- **Localization (i18n)**: Dictated by `translations.ts`, which maps over 650 localized terms. The UI dynamically re-renders the entire interface—from overarching layouts down to specific financial row items—based on the user's active language selection (`zh-CN`, `zh-TW`, `en`, `ja`).

## Data Flow Diagram

```mermaid
graph TD
    A[Client Request (React)] -->|POST /api/v1/assess| B(FastAPI Router)
    
    B --> C{Ticker Type?}
    C -->|A-Share/HK| D[AKShare Ingestion]
    C -->|US/Global Data| E[yFinance Ingestion]
    
    D --> F[Data Normalization]
    E --> F
    
    F --> G[Ratio Analyzer]
    G --> H[Altman Z-Score Engine]
    H --> I[Implied Rating Mapping]
    
    B --> J[Concurrent Translator]
    J -->|ThreadPoolExecutor| K[Google Translate API]
    K -->|Multi-lang dict| L[Response Aggregator]
    
    I --> L
    L -->|JSON Payload| A
```

## Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| **Asynchronous FastAPI + Pydantic** | Provides high-throughput concurrency and automatic type coercion for incoming requests, guaranteeing data structures before the analysis engine runs. |
| **Bilingual Taxonomy Matching** | Essential for accurately mapping Chinese GAAP terms from AKShare into standardized global structures (IFRS/US GAAP) for valid peer comparisons. |
| **Separation of Assessment and Covenants** | Post-lending surveillance (Covenants) operates independently from probability of default scoring (Z-Score), allowing different thresholds per borrower. |
| **Real-time Semantic Translation** | Using `ThreadPoolExecutor` ensures company names are correctly rendered in JS/ZH markets without delaying the massive ingestion payload. |
