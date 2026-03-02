# RiskLens Excel 工作簿规范（当前实现）

语言: [EN](./REPORT_WORKBOOK_SPEC.md) | [简中](./REPORT_WORKBOOK_SPEC_zh-CN.md) | [繁中](./REPORT_WORKBOOK_SPEC_zh-TW.md) | [日本語](./REPORT_WORKBOOK_SPEC_ja.md)

本文档描述 `web/src/App.tsx` 中 `exportToExcel` 的实际导出行为。

## 1. 单公司导出

- 文件名：`<TICKER>_Financial_Data.xlsx`
- 触发方式：Dashboard 公司卡片级导出按钮

### Sheet 布局（本地化名称）

1. 风险报告页（`riskText.sheetName`，紫色标签）
2. KPI 趋势页（`excelKpiSheet`，蓝色标签）
3. 财务报表页（`excelStatementsSheet`，绿色标签）

### 风险报告页

单公司风险页包含：
- 合并标题行：`公司名 (Ticker)`
- 摘要行：
  - Ticker
  - Latest Period
  - Currency
  - Altman Z-Score
  - Z-Score Zone
  - Implied Rating
  - Strengths（本地化）
  - Watch Items（本地化）
- 契约预检表：
  - Metric / Actual / Threshold / Status / Signal / Notes
- 数据质量区域：
  - Breach Count
  - Missing Key Inputs
  - Missing Items

规则：
- 契约实际值缺失时导出为数值 `0`
- 缺失契约按 `BREACH (DATA MISSING)` 处理

### KPI 趋势页

- 列结构：期间列（`FYxx` / `yyQx`）+ 年度区间可选 YoY 列
- 指标包含：
  - EBIT
  - EBITDA
  - Total Debt
  - Debt / EBITDA
  - Interest Coverage
  - Free Cash Flow
  - FCF / Debt
  - Current Ratio

### 财务报表页

- 行来自利润表/资产负债表/现金流表的科目聚合
- 排序按会计准则优先映射：
  - 美股 ticker -> USGAAP 顺序
  - 港股 ticker -> IFRS 顺序
  - A 股 ticker -> CAS 顺序
- 同义科目在前端弹窗里折叠到主科目；Excel 里仍按有序键集合输出行
- 年度区间在存在成对数据时可生成 YoY 列

## 2. 多公司导出

- 文件名：`RiskLens_MultiCompany_Comparison.xlsx`
- 触发方式：多公司结果时顶部 `Export All` 按钮

### Sheet 布局

1. 风险报告页（`riskText.sheetName`，紫色标签）
2. 组合 KPI 对比页（`excelPortfolioKpiSheet`，蓝色标签）
3. 组合报表对比页（`excelPortfolioStatementsSheet`，蓝色标签）
4. 公司报表分表：`<CompanyShortName> <excelCompanySheetSuffix>`（绿色标签）

### 组合风险页

- 每家公司一个区块
- 每个区块由合并且着色的标题行开始
- 每个区块包含摘要区、契约预检表、数据质量区

### 组合 KPI / 报表对比页

- 首家选中公司作为对比基准
- 每个期间块包含：
  - 基准公司值
  - 同行公司值
  - 相对基准的差值
  - 相对基准的 `%`

## 3. 格式约定

- 每个期间块应用独立表头色带
- 标签色：
  - risk：紫色
  - portfolio comparison：蓝色
  - statements：绿色
- 列宽按单元格真实文本自动拟合
- 数字格式：
  - 数值：`#,##0.00`
  - 百分比：`0.00%`

## 4. 多语言

工作簿标签支持：
- `en`
- `zh-CN`
- `zh-TW`
- `ja`

本地化覆盖 sheet 名、风险标签、契约状态文本，以及 strengths/watch items 翻译。
