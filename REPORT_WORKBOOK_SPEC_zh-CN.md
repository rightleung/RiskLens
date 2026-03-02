# RiskLens Excel 报告工作簿规范（v1.0）

本文档定义 Excel 导出将生成的内容，以及各部分背后的逻辑。

## 1）单公司导出（`<TICKER>_Risk_Report.xlsx`）

### 工作表命名（统一）
1. `01_Risk_Report`
2. `02_KPI_Trends`
3. `03_Financial_Statements`

### `01_Risk_Report` 内容
- `Executive Summary`
  - Ticker
  - Company Name（本地化）
  - Latest Period
  - Currency
  - Data Source
  - Generated At
  - Altman Z-Score
  - Z-Score Zone
  - Implied Rating
  - Strengths（本地化）
  - Watch Items（本地化）
- `Key Metrics`
  - Interest Coverage
  - Debt / EBITDA
  - FCF / Debt
  - Current Ratio
  - 对于每个指标：
    - Actual
    - Benchmark
    - Signal（`Strong` / `Neutral` / `Watch`）
- `Covenant Pre-Check`
  - Covenant
  - Actual
  - Threshold
  - Status
  - Notes
- `Data Quality`
  - Breach Count
  - Notes（Breach Count 的定义说明）
  - Missing Key Inputs
  - Missing Items
- `Methodology & Boundary`
  - 模型边界说明（v1.0 仅包含 Altman）
  - 缺失输入按 breach 处理（保守控制）
  - 非投资建议免责声明

### `02_KPI_Trends` 内容
- 核心 KPI 跨期趋势表
- 年度期间提供 YoY 列（在可用时包含绝对值变化与百分比变化）

### `03_Financial_Statements` 内容
- 原始财务报表条目（利润表 / 资产负债表 / 现金流量表）
- 多期间对比
- 年度期间提供 YoY 列（在可用时包含绝对值变化与百分比变化）

## 2）多公司导出（`RiskLens_MultiCompany_Comparison.xlsx`）

### 工作表命名（统一）
1. `01_Portfolio_Risk_Summary`
2. `02_Portfolio_KPI_Comparison`
3. `03_Portfolio_Statement_Comparison`
4. `04_<TICKER>_Statements`（每家公司一张）

### `01_Portfolio_Risk_Summary` 内容
- 生成时间戳
- 各公司汇总：
  - Ticker
  - Company Name
  - Latest Period
  - Z-Score
  - Implied Rating
  - Breach Count
  - Missing Key Inputs
  - Missing Items
- 边界说明与 Breach Count 定义

### `02_Portfolio_KPI_Comparison` 内容
- 各公司按期间的 KPI 横向对比
- 基准公司与同业的 delta 与 delta %

### `03_Portfolio_Statement_Comparison` 内容
- 各公司按期间的报表行项目横向对比
- 基准公司与同业的 delta 与 delta %

### `04_<TICKER>_Statements` 内容
- 公司级报表明细
- 期间视图与 YoY 视图

## 3）逻辑定义

### Covenant 预检查规则（v1.0 默认）
- Interest Coverage：`>= 3.0`
- Debt / EBITDA：`<= 4.0`
- Current Ratio：`>= 1.2`
- FCF / Debt：`>= 0.05`

### Breach Count 定义
`Breach Count = number of covenant checks flagged as BREACH, including DATA MISSING cases.`

### 缺失项处理
- 缺失的关键输入会在报告输出中显式列出。
- 缺失的 covenant 指标按 breach 处理（`BREACH (DATA MISSING)`）。

## 4）本地化行为
- Strengths / Watch Items 通过前端文本翻译器进行翻译。
- Missing Items 优先使用本地化 KPI 标签，回退为 metric-key prettifier。
- 报告标签支持 `en`、`zh-CN`、`zh-TW`、`ja`。
