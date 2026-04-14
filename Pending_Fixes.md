# RiskLens PDF 真实数据最终排错与修复指令

在前面几轮针对真实数据的结构和排版优化后（包括调整了 YoY 显示、重构了 Page 1/Page 2 布局、修正了脚注和徽章排版），我们发现系统中还存在**最后 2 个遗留的数据绑定错误**。它们导致了：
1. 首页 Z-Score 进度条数据全空（显示 `--`）
2. KPI 趋势表格中 `Free CF` 和 `FCF / Debt` 数据全空

为了彻底解决这两个问题，请严格根据以下 `[Old String]` 和 `[New String]` 的对比，对代码进行精确的逐行级替换：

---

## 1. 修复 Z-Score Breakdown (图表因子) 数据为空
**文件**: `src/html_pdf_exporter.py`
**问题原因**: 真实数据的资产负债表嵌套在 `statements` 字典下，提取因子的代码层级错误。

**[Old String]**
```python
def _build_altman_breakdown(entry: dict[str, Any], lang: str) -> list[dict[str, Any]]:
    raw_metrics = _mapping(entry.get('raw_metrics'))
    balance = _mapping(entry.get('balance') or entry.get('balance_sheet') or entry.get('bs'))
    income = _mapping(entry.get('income') or entry.get('income_statement') or entry.get('pnl'))

    total_assets = _safe_number(_pick(raw_metrics, ('total_assets',))) or _safe_number(_pick(balance, ('total_assets',)))
```

**[New String]**
```python
def _build_altman_breakdown(entry: dict[str, Any], lang: str) -> list[dict[str, Any]]:
    statements = _mapping(entry.get('statements', {}))
    raw_metrics = _mapping(entry.get('raw_metrics'))
    balance = _mapping(entry.get('balance') or entry.get('balance_sheet') or entry.get('bs') or statements.get('balance'))
    income = _mapping(entry.get('income') or entry.get('income_statement') or entry.get('pnl') or statements.get('income'))

    total_assets = _safe_number(_pick(raw_metrics, ('total_assets',))) or _safe_number(_pick(balance, ('total_assets',)))
```

---

## 2. 修复 KPI Trends 中 Free CF 及其派生指标无数据
**文件**: `src/html_pdf_exporter.py`
**问题原因**: `KPI_SPECS` 别名不全，未配置真实 JSON 中的键名 `free_cf` 和 `fcf_to_debt`。

**[Old String]**
```python
KPI_SPECS = [
    ('EBIT', ('ebit',)),
    ('EBITDA', ('ebitda',)),
    ('Total Debt', ('total_debt', 'gross_debt', 'debt_total')),
    ('Debt / EBITDA', ('debt_ebitda', 'debt_to_ebitda')),
    ('Interest Coverage', ('interest_coverage', 'ebit_interest_coverage')),
    ('Free CF', ('free_cash_flow', 'fcf')),
    ('FCF / Debt', ('fcf_debt',)),
    ('Current Ratio', ('current_ratio',)),
]
```

**[New String]**
```python
KPI_SPECS = [
    ('EBIT', ('ebit',)),
    ('EBITDA', ('ebitda',)),
    ('Total Debt', ('total_debt', 'gross_debt', 'debt_total')),
    ('Debt / EBITDA', ('debt_ebitda', 'debt_to_ebitda')),
    ('Interest Coverage', ('interest_coverage', 'ebit_interest_coverage')),
    ('Free CF', ('free_cash_flow', 'fcf', 'free_cf')),
    ('FCF / Debt', ('fcf_debt', 'fcf_to_debt')),
    ('Current Ratio', ('current_ratio',)),
]
```
