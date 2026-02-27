# RiskLens 架構概覽

RiskLens 是基於現代解耦架構建構的，專為處理機構級信用風險分析而設計。系統被拆分為高效能的 Python 分析後端和響應式的 React 前端，兩者透過 RESTful JSON API 連接。

## 系統架構

### 1. 後端閘道 (FastAPI)
後端使用 **FastAPI** 建構，提供高吞吐量的非同步執行、自動化的 OpenAPI 文件以及嚴格的資料驗證。
- **`api.py` (編排器)**：暴露 `POST /api/v1/assess` 端點。它接收股票代碼陣列，並編排資料獲取和翻譯流程。
- **並發執行**：為了大幅降低回應延遲，多語言語意匹配（Google 翻譯）使用 Python 的 `concurrent.futures.ThreadPoolExecutor` 動態執行，從而可以平行獲取英語、簡體中文、繁體中文和日語的公司名稱。

### 2. 資料接入層 (`data_fetcher.py`)
該層負責從外部 API 物理獲取財務資料集。它實現了穩健的降級（Fallback）方法：
- **AKShare (中國 A 股及港股)**：在岸中國股票（如 `600673.SS`）的主資料管道。直接查詢內地 API (`stock_financial_report_sina`, `stock_individual_info_em`)，處理複雜的中國會計準則 (GAAP) 分類，並將不規則的報告期（Q1、H1、Q3）轉換為年化的標準格式。
- **yFinance (全球/美國)**：作為美國/歐洲市場的主引擎，當在岸 API 限制連線時，它還作為安全的回退資料源。

### 3. 分析與監測引擎
- **`ratio_analyzer.py`**：一個純粹的數學引擎，將抓取的原始資料陣列處理為 30 多種進階信用比率（流動比率、FCF/債務、營業利潤率等）。
- **Altman Z-Score 模型**：最終計算出的比率被送入 Z-Score 引擎，生成最終的機率評估（安全、灰色、違約危機區）。
- **`covenant_monitor.py`**：一個專門的模組，根據嚴格的預定義約束（例如 債務/EBITDA < 3.5x）評估計算出的比率。至關重要的是，該系統奉行保守失敗原則——如果所需的指標缺失 (`null`)，它會觸發技術性違約警報，而不是預設通過。

### 4. 前端客戶端 (React 19 + Vite)
- **狀態管理**：建構為利用函數式 React Hooks 的單頁應用程式 (SPA)。包含深色模式 (`useTheme`)、當前啟用的公司資料集以及響應式財務模態框的集中狀態邏輯。
- **UI/UX**：在 `Tailwind CSS` 中進行了廣泛的樣式設計，利用玻璃態 (glassmorphism) 實用類別（`glass-panel`，`glass-header`）建立了一個高階且具有機構感的視覺美學。
- **在地化 (i18n)**：由 `translations.ts` 決定，該文件映射了 650 多個在地化術語。UI 會根據用戶當前啟用的語言選擇（`zh-CN`, `zh-TW`, `en`, `ja`）動態地重新渲染整個介面——從整體佈局到具體的財務行項目。

## 資料流圖

```mermaid
graph TD
    A[客戶端請求 (React)] -->|POST /api/v1/assess| B(FastAPI 路由器)
    
    B --> C{股票類型?}
    C -->|A 股/港股| D[AKShare 接入]
    C -->|美國/全球資料| E[yFinance 接入]
    
    D --> F[資料標準化]
    E --> F
    
    F --> G[比率分析器]
    G --> H[Altman Z-Score 引擎]
    H --> I[隱含評級映射]
    
    B --> J[多語言並行翻譯器]
    J -->|ThreadPoolExecutor| K[Google 翻譯 API]
    K -->|多語言字典| L[回應聚合器]
    
    I --> L
    L -->|JSON Payload| A
```

## 關鍵架構決策

| 決策點 | 理論依據 |
|----------|-----------|
| **非同步 FastAPI + Pydantic** | 為傳入請求提供高吞吐量並發和自動類型強制轉換，在分析引擎運行之前確保資料結構的合法性。 |
| **雙語分類學映射** | 這對於將 AKShare 中的中國 GAAP 術語正確映射為標準化的全球結構 (IFRS/US GAAP) 以實現有效的同業比較至關重要。 |
| **信貸評估與契約隔離** | 貸後監測（契約）獨立於違約機率評分 (Z-Score) 運行，允許為每個借款人設置不同的閾值。 |
| **即時語意翻譯** | 使用 `ThreadPoolExecutor` 可確保公司名稱在日/中市場獲得準確翻譯，且不會延遲龐大的資料抓取負載。 |
