# RiskLens 项目重构 - 剩余任务

## 已完成 ✅

- **Phase 1**: 删除死代码 (225 行不可达代码)
- **Phase 2**: 归档 Legacy 代码 (src/legacy/, tests/legacy/)
- **Phase 3**: 提取共享工具函数 (~50 行重复代码消除)
- **Phase 4**: 改善异常处理 (10+ 个裸 except 收窄)
- **Phase 5**: Python 打包 (pyproject.toml, conftest.py, sys.path 清理)
- **Phase 6**: 仓库清理 (部分完成: 构建产物已删除, .gitignore 已更新, shim 文件已移除, akshare 已下放为 optional extra)
- **Phase 7**: 测试覆盖补充 (101 tests, 0 failures)

**当前状态**: 101 passed, 0 failed (all green)

---

## Phase 5: Python 打包 ✅

> **已完成** — `pyproject.toml`、`tests/conftest.py`、`sys.path` 清理均已落地。

<details>
<summary>原始计划（已完成）</summary>

### 目标
消除所有 `sys.path.insert(0, ...)` 调用，创建标准 Python 包结构。

### 步骤

#### 5.1 创建 pyproject.toml

```toml
[build-system]
requires = ["setuptools>=75", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "risklens"
version = "1.1.0"
description = "Institutional Credit Risk Assessment Platform"
requires-python = ">=3.12"
dependencies = [
    "numpy>=2.4",
    "pandas>=3.0",
    "yfinance>=1.2",
    "reportlab>=4,<5",
    "fastapi>=0.133",
    "uvicorn>=0.41",
    "pydantic>=2.12",
    "sentry-sdk>=2.53",
]

[project.optional-dependencies]
dev = ["pytest>=9", "httpx>=0.28"]
cn = ["opencc"]
cn-data = ["akshare>=1.18"]

[tool.setuptools.packages.find]
where = ["."]
include = ["src*", "fastapi*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

#### 5.2 创建 tests/conftest.py

```python
"""Pytest configuration - single source of path setup."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

#### 5.3 删除所有测试文件中的 sys.path.insert

需要清理的文件（15 处）：
- `tests/test_api.py` (lines 17-18)
- `tests/test_data_fetcher.py` (line 12)
- `tests/test_ratio_analyzer.py` (line 12)
- `tests/test_zscore.py` (line 11)
- `tests/test_cli.py` (line 10)
- `tests/test_covenant_monitor.py` (line 10)
- `tests/test_html_pdf_exporter.py` (lines 11-12)
- `tests/test_main_mvp.py` (line 9)
- `tests/test_pdf_exporter.py` (lines 16-17)
- `tests/test_rich_assessment_service.py` (line 8)
- `tests/test_aapl_real_pdf.py` (lines 15-16)

#### 5.4 更新根目录脚本

同样删除这些文件中的 `sys.path.insert`:
- `sitecustomize.py`
- `generate_audit_pdf.py`
- `generate_real_pdf.py`
- `dump_payload.py`
- `test_methodology.py`
- `scripts/compare_aapl_real_pdf.py`

#### 5.5 验证

```bash
pip install -e ".[dev]"
python -m pytest tests/ --ignore=tests/legacy/ -q
python -c "from services import RichAssessmentService; print('OK')"
```

</details>

---

## Phase 6: 仓库清理 ✅ (部分完成)

> **已完成**: 构建产物删除、.gitignore 更新、根目录 shim 文件移除、akshare 下放为 optional extra
> **剩余**: `.venv_fetcher/` 检查（如不需则可删除）

<details>
<summary>原始计划</summary>

### 6.1 删除跟踪的构建产物

```bash
git rm --cached RiskLens_Latest_Report.pdf
git rm --cached RiskLens_Latest_Report_en_test.pdf
git rm --cached RiskLens_Latest_Report_zhCN.pdf
git rm --cached msft.json
git rm --cached msft_payload.json
```

### 6.2 更新 .gitignore

添加：
```gitignore
# Generated artifacts
*.pdf
*_payload.json
scratch_*.json
```

### 6.3 删除根目录多余的 shim 文件

这些是单行 re-export，没有实际用途：
- `pdf_exporter.py` (55 bytes)
- `reportlab_pdf_exporter.py` (60 bytes)

```bash
git rm pdf_exporter.py reportlab_pdf_exporter.py
```

### 6.4 检查两个虚拟环境

- `.venv/` - 主环境
- `.venv_fetcher/` - 检查是否仍需要，如果不需要则删除

### 6.5 可选：移动根目录 api.py

根目录的 `api.py` (75 lines) 是 MVP 兼容 API，考虑：
- **选项 A**: 移动到 `tests/compat_api.py`（推荐）
- **选项 B**: 重命名为 `smoke_test_api.py`

---

</details>

---

## Phase 7: 测试覆盖补充 ✅

> **已完成** — 当前 101 tests, 0 failures。RichAssessmentService.analyze()、data_fetcher 边缘测试均已覆盖。

<details>
<summary>原始计划</summary>

### 7.1 为 RichAssessmentService.analyze() 添加测试

**文件**: `tests/test_rich_assessment_service.py`

当前只有 22 行，1 个测试。需要添加：

```python
def test_analyze_with_demo_source():
    """Test analyze with demo data source."""
    service = RichAssessmentService()
    result = service.analyze(ticker="DEMO", data_source="demo")
    
    assert result["ticker"] == "DEMO"
    assert "company_name" in result
    assert "currency" in result
    assert "history" in result
    assert len(result["history"]) > 0
    
    # Verify history structure
    for period in result["history"]:
        assert "fiscal_year" in period
        assert "is_quarterly" in period
        assert "assessment" in period
        assert "ratios" in period
        assert "raw_metrics" in period
        assert "statements" in period


def test_analyze_with_invalid_ticker():
    """Test analyze with invalid ticker raises 404."""
    service = RichAssessmentService()
    with pytest.raises(AssessmentServiceError) as exc_info:
        service.analyze(ticker="INVALID_TICKER_XYZ", data_source="yfinance")
    assert exc_info.value.status_code == 404


def test_analyze_with_empty_ticker():
    """Test analyze with empty ticker raises 422."""
    service = RichAssessmentService()
    with pytest.raises(AssessmentServiceError) as exc_info:
        service.analyze(ticker="", data_source="demo")
    assert exc_info.value.status_code == 422


def test_analyze_invalid_source():
    """Test analyze with invalid data source raises 422."""
    service = RichAssessmentService()
    with pytest.raises(AssessmentServiceError) as exc_info:
        service.analyze(ticker="DEMO", data_source="invalid_source")
    assert exc_info.value.status_code == 422


def test_analyze_history_structure():
    """Test that history contains all required fields."""
    service = RichAssessmentService()
    result = service.analyze(ticker="DEMO", data_source="demo")
    
    for period in result["history"]:
        # Check assessment structure
        if period.get("assessment"):
            assert "risk_score" in period["assessment"]
            assert "overall_rating" in period["assessment"]
            assert "implied_rating" in period["assessment"]
            assert "strengths" in period["assessment"]
            assert "weaknesses" in period["assessment"]
        
        # Check ratios structure
        assert isinstance(period["ratios"], dict)
        
        # Check statements structure
        assert "income" in period["statements"]
        assert "balance" in period["statements"]
        assert "cash" in period["statements"]


def test_analyze_quarterly_fallback():
    """Test that quarterly periods with N/A ratings fall back to latest FY."""
    service = RichAssessmentService()
    result = service.analyze(ticker="DEMO", data_source="demo")
    
    # Find latest FY assessment
    latest_fy = None
    for period in result["history"]:
        if not period.get("is_quarterly") and period.get("assessment"):
            if period["assessment"].get("overall_rating") != "N/A":
                latest_fy = period["assessment"]
                break
    
    # Check quarterly periods use FY fallback
    if latest_fy:
        for period in result["history"]:
            if period.get("is_quarterly") and period.get("assessment"):
                if period["assessment"].get("overall_rating") != "N/A":
                    # Should have same rating as FY
                    assert period["assessment"]["overall_rating"] == latest_fy["overall_rating"]
```

### 7.2 为 data_fetcher 添加边缘测试

**文件**: `tests/test_data_fetcher.py`

添加：
- 空响应处理测试
- 部分数据（缺失报表）测试
- 网络超时模拟测试

</details>

---

## Phase 8: 拆分单体文件（远期）

⚠️ **高风险**：只在 Phase 1-7 全部落地并在生产环境验证后再考虑。

### 目标文件

| 文件 | 行数 | 拆分策略 |
|------|------|----------|
| `src/html_pdf_exporter.py` | 1,609 | 提取 HTML 模板到 `src/templates/`；按语言拆分渲染模块 |
| `src/reportlab_pdf_renderer.py` | 1,135 | 按页面类型拆分：`pdf_sections/cover.py`, `pdf_sections/ratios.py`, `pdf_sections/zscore.py`, `pdf_sections/covenant.py` |
| `src/ratio_analyzer.py` | 1,135 | 按比率类别拆分 mixin：`ratios/liquidity.py`, `ratios/solvency.py`, `ratios/profitability.py`, `ratios/efficiency.py` |
| `src/data_fetcher.py` | 1,121 | 按数据源拆分：`fetchers/yfinance.py`, `fetchers/akshare.py`, `fetchers/demo.py` + 共享基类 |
| `src/api.py` | ~730 (Phase 1 后) | 提取公司名本地化到 `src/services/company_name.py` |
| `web/src/App.tsx` | 3,817 | React 组件分解（非 Python 范畴） |

### 拆分原则

1. **保持向后兼容**：原文件保留为 facade，re-export 新模块
2. **增量拆分**：一次拆一个文件，每次拆分后跑全量测试
3. **测试先行**：拆分前确保该模块有充分的测试覆盖

---

## 验证清单

每个 Phase 完成后运行：

```bash
# 1. 测试套件
source .venv/bin/activate
python -m pytest tests/ --ignore=tests/legacy/ -q

# 2. 模块导入
python -c "from src.api import app; print('✓ API import OK')"
python -c "from services import RichAssessmentService; print('✓ Service import OK')"

# 3. 启动服务
bash run_app.sh &
sleep 3
curl http://localhost:8000/health
pkill -f "uvicorn src.api:app"
```

---

## 提交规范

每个 Phase 完成后创建独立 commit：

```bash
git add <changed-files>
git commit -m "Refactor: <Phase 名称> (Phase N)

<详细说明>

Tests: X passed, Y failed

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 预期收益

完成 Phase 5-7 后：
- ✅ 标准 Python 包结构
- ✅ 干净的 git 仓库
- ✅ 核心模块测试覆盖 >80%
- ✅ 零 sys.path hack
- ✅ 可 pip 安装

完成 Phase 8 后：
- ✅ 所有文件 <500 行
- ✅ 单一职责原则
- ✅ 易于维护和扩展
