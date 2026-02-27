# RiskLens 架构概览

RiskLens 是基于现代解耦架构构建的，专为处理机构级信贷风险分析而设计。系统被拆分为高性能的 Python 分析后端和响应式的 React 前端，两者通过 RESTful JSON API 连接。

## 系统架构

### 1. 后端网关 (FastAPI)
后端使用 **FastAPI** 构建，提供高吞吐量的异步执行、自动化的 OpenAPI 文档以及严格的数据验证。
- **`api.py` (编排器)**：暴露 `POST /api/v1/assess` 端点。它接收股票代码数组，并编排数据获取和翻译流程。
- **并发执行**：为了大幅降低响应延迟，多语言语义匹配（Google 翻译）使用 Python 的 `concurrent.futures.ThreadPoolExecutor` 动态执行，从而可以并行获取英语、简体中文、繁体中文和日语的公司名称。

### 2. 数据接入层 (`data_fetcher.py`)
该层负责从外部 API 物理获取财务数据集。它实现了稳健的降级（Fallback）方法：
- **AKShare (中国 A 股及港股)**：在岸中国股票（如 `600673.SS`）的主数据管道。直接查询内地 API (`stock_financial_report_sina`, `stock_individual_info_em`)，处理复杂的中国会计准则 (GAAP) 分类，并将不规则的报告期（Q1、H1、Q3）转换为年化的标准格式。
- **yFinance (全球/美国)**：作为美国/欧洲市场的主引擎，当在岸 API 限制连接时，它还作为安全的回退数据源。

### 3. 分析与监测引擎
- **`ratio_analyzer.py`**：一个纯粹的数学引擎，将抓取的原始数据数组处理为 30 多种高级信用比率（流动比率、FCF/债务、营业利润率等）。
- **Altman Z-Score 模型（`zscore.py`）**：最终计算出的比率被送入 Z-Score 引擎，生成最终的概率评估（安全、灰色、违约危机区）。这是 1.0 的唯一评分模型。
- **`covenant_monitor.py`**：一个专门的模块，根据严格的预定义约束（例如 债务/EBITDA < 3.5x）评估计算出的比率。至关重要的是，该系统奉行保守失败原则——如果所需的指标缺失 (`null`)，它会触发技术性违约警报，而不是默认通过。

### 4. 前端客户端 (React 19 + Vite)
- **状态管理**：构建为利用函数式 React Hooks 的单页应用程序 (SPA)。包含暗黑模式 (`useTheme`)、当前激活的公司数据集以及响应式财务模态框的集中状态逻辑。
- **UI/UX**：在 `Tailwind CSS` 中进行了广泛的样式设计，利用玻璃态 (glassmorphism) 实用类（`glass-panel`，`glass-header`）建立了一个高级且具有机构感的视觉美学。
- **本地化 (i18n)**：由 `translations.ts` 决定，该文件映射了 650 多个本地化术语。UI 会根据用户当前激活的语言选择（`zh-CN`, `zh-TW`, `en`, `ja`）动态地重新渲染整个界面——从整体布局到具体的财务行项目。

## 数据流图

```mermaid
graph TD
    A[客户端请求 (React)] -->|POST /api/v1/assess| B(FastAPI 路由器)
    
    B --> C{股票类型?}
    C -->|A 股/港股| D[AKShare 接入]
    C -->|美国/全球数据| E[yFinance 接入]
    
    D --> F[数据标准化]
    E --> F
    
    F --> G[比率分析器]
    G --> H[Altman Z-Score 引擎]
    H --> I[隐含评级映射]
    
    B --> J[多语言并发翻译器]
    J -->|ThreadPoolExecutor| K[Google 翻译 API]
    K -->|多语言字典| L[响应聚合器]
    
    I --> L
    L -->|JSON Payload| A
```

## 关键架构决策

| 决策点 | 理论依据 |
|----------|-----------|
| **异步 FastAPI + Pydantic** | 为传入请求提供高吞吐量并发和自动类型强制转换，在分析引擎运行之前确保数据结构的合法性。 |
| **双语分类学映射** | 这对于将 AKShare 中的中国 GAAP 术语正确映射为标准化的全球结构 (IFRS/US GAAP) 以实现有效的同业比较至关重要。 |
| **信贷评估与契约隔离** | 贷后监测（契约）独立于违约概率评分 (Z-Score) 运行，允许为每个借款人设置不同的阈值。 |
| **实时语义翻译** | 使用 `ThreadPoolExecutor` 可确保公司名称在日/中市场获得准确翻译，且不会延迟庞大的数据抓取负载。 |
