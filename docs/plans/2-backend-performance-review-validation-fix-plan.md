# Backend Performance Review Final Validation Fix Plan

## 目标

覆盖更新此前的验证修复方案，只保留当前验收后仍未完成的代码级修复项。前一轮 P0 blocker 已修复并通过测试，本轮目标是补齐最后两个性能验收缺口，并同步修正文档中的测试结果。

## 当前验收状态

已通过：

- `pytest tests/test_data_fetcher.py -q`：49 passed
- `pytest tests/test_api.py -q`：63 passed
- `pytest tests/test_ratio_analyzer.py tests/test_zscore.py tests/test_rich_assessment_service.py -q`：75 passed
- `pytest tests/test_html_pdf_exporter.py tests/test_pdf_exporter.py -q`：36 passed
- `pytest -q`：272 passed

已确认修复：

- negative cache 命中后 `error_type` 恢复为 `DataFetchErrorType`
- generic yfinance failure 写入 `_error_cache`
- `yfinance_clear_proxy_mode="never"` 不清 proxy
- `FinancialDataFetcher.clear_cache()` 同时清 `_data_cache` 和 `_error_cache`
- `mode="latest"` 代码已按最新可用期选择季度或年度
- `max_pdf_detail_rows` 已应用到 PDF detail rows

仍需一步到位补齐：

1. `mode="latest"` 的直接回归测试。
2. 不同 ticker 冷 miss 不被 proxy lock 串行化的并发测试。
3. `docs/plans/2-backend-performance-review_fix.md` 中测试数量与实际运行结果不一致，需要同步。
4. 可选：将 `docs/prompts/codex-validate-implementation.md` 的流程文档改动从本次性能修复中剥离，除非明确需要保留。

## 修改范围

只修改：

- `tests/test_data_fetcher.py`
- `docs/plans/2-backend-performance-review_fix.md`

可选修改：

- `docs/prompts/codex-validate-implementation.md`

不要修改业务代码，除非新增测试暴露真实 bug。

## Fix 1: 增加 `mode="latest"` 最新季度优先测试

### Severity

Medium

### Related Original Plan Item

P1: Latest-only covenant fetch / latest-only 抓取模式。

### Problem

`src/data_fetcher.py` 当前代码已经实现 `mode="latest"` 对 annual 和 quarterly 第一列日期做比较，并在季度日期更新时返回季度，但现有测试没有直接覆盖这个模式。缺少测试会让后续维护者容易把 latest-only 再次退化为 latest annual。

### Files To Modify

- `tests/test_data_fetcher.py`

### Symbols To Modify

新增测试函数：

- `test_latest_mode_prefers_newer_quarter_over_annual`
- `test_latest_mode_uses_annual_when_quarter_not_newer`

### Required Behavior

当 `FinancialDataFetcher.get_financial_data("AAPL", "yfinance", mode="latest")` 被调用时：

- 只返回一个 `history` period。
- 如果季度报表第一列日期晚于年度报表第一列日期，返回季度 period。
- 如果季度报表为空或季度日期不晚于年度日期，返回年度 period。
- `mode="latest"` 不构造 dashboard 多期 history。

### Exact Test Implementation

在 `tests/test_data_fetcher.py` 末尾新增以下测试。若文件已有 `_build_statement()` helper，则复用；否则用测试内 helper。

```python
def test_latest_mode_prefers_newer_quarter_over_annual(monkeypatch):
    """mode='latest' returns the newest quarter when it is newer than annual."""

    def _stmt(cols, base):
        return pd.DataFrame(
            {
                cols[0]: {
                    "Total Revenue": base + 1,
                    "Total Assets": base + 2,
                    "Total Liabilities Net Minority Interest": base + 3,
                    "Stockholders Equity": base + 4,
                    "Operating Cash Flow": base + 5,
                }
            }
        )

    class _LatestTicker:
        def __init__(self, symbol):
            self.info = {"longName": "Latest Co", "marketCap": 1000}
            self.income_stmt = _stmt([pd.Timestamp("2024-12-31")], 100.0)
            self.balance_sheet = _stmt([pd.Timestamp("2024-12-31")], 200.0)
            self.cashflow = _stmt([pd.Timestamp("2024-12-31")], 300.0)
            self.quarterly_income_stmt = _stmt([pd.Timestamp("2025-09-30")], 400.0)
            self.quarterly_balance_sheet = _stmt([pd.Timestamp("2025-09-30")], 500.0)
            self.quarterly_cashflow = _stmt([pd.Timestamp("2025-09-30")], 600.0)

    monkeypatch.setattr(data_fetcher.yf, "Ticker", _LatestTicker)

    result = FinancialDataFetcher.get_financial_data("AAPL", "yfinance", mode="latest")

    assert result is not None
    assert len(result["history"]) == 1
    period = result["history"][0]
    assert period["year_label"] == "Q3 '25 (U)"
    assert period["is_quarterly"] is True
    assert period["income"].loc["revenue", "Value"] == 401.0
    assert period["balance"].loc["total_assets", "Value"] == 502.0
    assert period["cash"].loc["operating_cf", "Value"] == 605.0
```

第二个测试：

```python
def test_latest_mode_uses_annual_when_quarter_not_newer(monkeypatch):
    """mode='latest' falls back to annual when quarter is absent or not newer."""

    def _stmt(cols, base):
        return pd.DataFrame(
            {
                cols[0]: {
                    "Total Revenue": base + 1,
                    "Total Assets": base + 2,
                    "Total Liabilities Net Minority Interest": base + 3,
                    "Stockholders Equity": base + 4,
                    "Operating Cash Flow": base + 5,
                }
            }
        )

    class _LatestTicker:
        def __init__(self, symbol):
            self.info = {"longName": "Latest Co", "marketCap": 1000}
            self.income_stmt = _stmt([pd.Timestamp("2024-12-31")], 100.0)
            self.balance_sheet = _stmt([pd.Timestamp("2024-12-31")], 200.0)
            self.cashflow = _stmt([pd.Timestamp("2024-12-31")], 300.0)
            self.quarterly_income_stmt = _stmt([pd.Timestamp("2024-09-30")], 400.0)
            self.quarterly_balance_sheet = _stmt([pd.Timestamp("2024-09-30")], 500.0)
            self.quarterly_cashflow = _stmt([pd.Timestamp("2024-09-30")], 600.0)

    monkeypatch.setattr(data_fetcher.yf, "Ticker", _LatestTicker)

    result = FinancialDataFetcher.get_financial_data("AAPL", "yfinance", mode="latest")

    assert result is not None
    assert len(result["history"]) == 1
    period = result["history"][0]
    assert period["year_label"] == "FY24"
    assert period["is_quarterly"] is False
    assert period["income"].loc["revenue", "Value"] == 101.0
    assert period["balance"].loc["total_assets", "Value"] == 202.0
    assert period["cash"].loc["operating_cf", "Value"] == 305.0
```

### Notes

If the exact yfinance metric mapping causes a value mismatch, adjust only the expected mapped keys/values. Do not weaken the core assertions:

- one period only
- quarter is selected when newer
- annual is selected when quarter is not newer

### Verification Command

```bash
./.venv/bin/python -m pytest tests/test_data_fetcher.py -q
```

### Acceptance Condition

`tests/test_data_fetcher.py` passes and includes direct `mode="latest"` coverage for both quarter-newer and annual fallback cases.

## Fix 2: 增加不同 ticker 冷 miss 不串行化测试

### Severity

Medium

### Related Original Plan Item

P0: yfinance 全局锁串行化高频抓取。

### Problem

原计划核心目标是避免不同 ticker 的 yfinance 冷 miss 因 `_PROXY_CLEAR_LOCK` 被串行化。当前已有 proxy mode 单元测试，但没有测试两个不同 ticker 的 upstream 调用可以同时进入。

### Files To Modify

- `tests/test_data_fetcher.py`

### Symbols To Modify

新增测试函数：

- `test_retry_only_allows_different_ticker_cold_misses_to_overlap`

### Required Behavior

在默认 `retry_only` 模式下：

- `get_financial_data("AAA", "yfinance")` 和 `get_financial_data("BBB", "yfinance")` 两个不同 cache key 不应互相等待 `_PROXY_CLEAR_LOCK`。
- 两个线程都应能进入 yfinance upstream mock。
- 测试必须证明第二个 ticker 能在第一个 ticker 释放前进入 upstream。

### Exact Test Implementation

在 `tests/test_data_fetcher.py` 末尾新增：

```python
def test_retry_only_allows_different_ticker_cold_misses_to_overlap(monkeypatch):
    """Different ticker cold misses should not serialize behind proxy lock."""

    entered: list[str] = []
    first_entered = threading.Event()
    release_first = threading.Event()
    lock = threading.Lock()

    def _stmt(base):
        return pd.DataFrame(
            {
                pd.Timestamp("2024-12-31"): {
                    "Total Revenue": base + 1,
                    "Total Assets": base + 2,
                    "Total Liabilities Net Minority Interest": base + 3,
                    "Stockholders Equity": base + 4,
                    "Operating Cash Flow": base + 5,
                }
            }
        )

    class _ConcurrentTicker:
        def __init__(self, symbol):
            with lock:
                entered.append(symbol)
                is_first = len(entered) == 1
            if is_first:
                first_entered.set()
                release_first.wait(timeout=5)
            else:
                first_entered.wait(timeout=5)
            base = 100.0 if symbol == "AAA" else 200.0
            self.info = {"longName": f"{symbol} Co", "marketCap": 1000}
            self.income_stmt = _stmt(base)
            self.balance_sheet = _stmt(base + 1000)
            self.cashflow = _stmt(base + 2000)
            self.quarterly_income_stmt = pd.DataFrame()
            self.quarterly_balance_sheet = pd.DataFrame()
            self.quarterly_cashflow = pd.DataFrame()

    monkeypatch.setattr(data_fetcher.settings, "yfinance_clear_proxy_mode", "retry_only")
    monkeypatch.setattr(data_fetcher.yf, "Ticker", _ConcurrentTicker)

    results: list[tuple[str, str]] = []

    def _fetch(symbol):
        result = FinancialDataFetcher.get_financial_data(symbol, "yfinance")
        results.append((symbol, result["ticker"]))

    t1 = threading.Thread(target=_fetch, args=("AAA",))
    t2 = threading.Thread(target=_fetch, args=("BBB",))
    t1.start()
    first_entered.wait(timeout=5)
    t2.start()

    # If calls are incorrectly serialized behind the proxy lock, BBB cannot enter
    # until AAA finishes. Give BBB a short window to enter while AAA is blocked.
    deadline = time.time() + 1.0
    while time.time() < deadline:
        with lock:
            if len(entered) >= 2:
                break
        time.sleep(0.01)

    with lock:
        entered_while_first_blocked = list(entered)

    release_first.set()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert len(entered_while_first_blocked) == 2, (
        f"Expected both tickers to enter upstream before first released; got {entered_while_first_blocked}"
    )
    assert sorted(symbol for symbol, _ in results) == ["AAA", "BBB"]
```

### Required Imports

If not already imported at the top of `tests/test_data_fetcher.py`, add:

```python
import time
import threading
```

Check first before adding duplicates. `threading` is already likely present because existing tests use it.

### Important Test Isolation

The autouse fixture currently clears `_data_cache`, `_error_cache`, and `_in_flight`. Keep this behavior. This test depends on both tickers being cold misses.

### Verification Command

```bash
./.venv/bin/python -m pytest tests/test_data_fetcher.py -q
```

### Acceptance Condition

The test fails if yfinance calls are serialized behind the proxy lock, and passes when `run_yfinance_call_with_proxy_retry()` allows different ticker cold misses to enter concurrently in `retry_only` mode.

## Fix 3: 更新 handoff 文档测试数量

### Severity

Low

### Related Original Plan Item

Handoff evidence correctness.

### Problem

`docs/plans/2-backend-performance-review_fix.md` 当前 Verification Performed 区域写的单文件测试数量和实际运行结果不一致。

当前实际结果：

- `tests/test_data_fetcher.py -q`：49 passed
- `tests/test_api.py -q`：63 passed
- `tests/test_ratio_analyzer.py tests/test_zscore.py tests/test_rich_assessment_service.py -q`：75 passed
- `tests/test_html_pdf_exporter.py tests/test_pdf_exporter.py -q`：36 passed
- `pytest -q`：272 passed

补完 Fix 1 和 Fix 2 后，`tests/test_data_fetcher.py` 数量会增加 3 个，预期为 52 passed。全量数量会增加 3 个，预期为 275 passed。

### Files To Modify

- `docs/plans/2-backend-performance-review_fix.md`

### Required Behavior

更新 Verification Performed 表，使它反映最终实际运行结果。不要提前硬写数字；先运行测试，再按真实输出更新。

### Required Text Changes

在 `Verification Performed` 表中更新：

- `pytest tests/test_data_fetcher.py -q` 的结果
- `pytest -q` 的结果
- 若 `tests/test_api.py -q` 未变化，保持真实输出

在 `New P1 validation tests added` 列表中追加：

- `test_latest_mode_prefers_newer_quarter_over_annual`
- `test_latest_mode_uses_annual_when_quarter_not_newer`
- `test_retry_only_allows_different_ticker_cold_misses_to_overlap`

并将测试总数从 `12 total` 改成最终真实数量，例如 `15 total`。

### Verification Command

```bash
./.venv/bin/python -m pytest tests/test_data_fetcher.py -q
./.venv/bin/python -m pytest -q
```

### Acceptance Condition

handoff 文件中的测试数量和实际 pytest 输出一致。

## Fix 4: 处理流程文档的无关改动

### Severity

Low

### Related Original Plan Item

Scope control.

### Problem

`docs/prompts/codex-validate-implementation.md` 被修改，但这不是后端性能修复的必要文件。若这是用户有意要求的流程改进，可以保留；否则应撤出本次性能修复，避免范围扩大。

### Files To Inspect

- `docs/prompts/codex-validate-implementation.md`

### Required Decision

二选一：

1. 如果这是有意的 prompt 工作流更新：在最终 handoff 中明确列为 “documentation workflow update, intentionally included”。
2. 如果不是本次任务要求：撤回该文件改动。

### Verification Command

```bash
git diff -- docs/prompts/codex-validate-implementation.md
```

### Acceptance Condition

最终说明中明确该文件改动保留或撤回的理由。

## 执行顺序

1. 修改 `tests/test_data_fetcher.py`，添加 `mode="latest"` 两个测试。
2. 修改 `tests/test_data_fetcher.py`，添加不同 ticker cold miss 并发测试。
3. 运行 `./.venv/bin/python -m pytest tests/test_data_fetcher.py -q`。
4. 若失败，只修测试暴露出的真实问题，不做无关重构。
5. 运行 `./.venv/bin/python -m pytest -q`。
6. 按真实结果更新 `docs/plans/2-backend-performance-review_fix.md`。
7. 决定是否保留 `docs/prompts/codex-validate-implementation.md` 的无关改动，并在 handoff 记录。

## 必跑命令

```bash
./.venv/bin/python -m pytest tests/test_data_fetcher.py -q
./.venv/bin/python -m pytest tests/test_api.py -q
./.venv/bin/python -m pytest tests/test_ratio_analyzer.py tests/test_zscore.py tests/test_rich_assessment_service.py -q
./.venv/bin/python -m pytest tests/test_html_pdf_exporter.py tests/test_pdf_exporter.py -q
./.venv/bin/python -m pytest -q
```

## 最终验收标准

1. `tests/test_data_fetcher.py` 包含 direct latest-mode quarter/annual selection tests。
2. `tests/test_data_fetcher.py` 包含不同 ticker cold miss overlap test。
3. `./.venv/bin/python -m pytest -q` 全部通过。
4. `docs/plans/2-backend-performance-review_fix.md` 测试数量和真实结果一致。
5. 没有新增业务逻辑改动，除非测试暴露真实 bug。
6. 对 `docs/prompts/codex-validate-implementation.md` 的保留/撤回有明确说明。

## 给执行 LLM 的 Prompt

```text
请在 /Users/rightleung/Documents/Python/RiskLens 按 docs/plans/2-backend-performance-review-validation-fix-plan.md 做最后验收修复。

只做以下内容：
1. 在 tests/test_data_fetcher.py 增加 test_latest_mode_prefers_newer_quarter_over_annual。
2. 在 tests/test_data_fetcher.py 增加 test_latest_mode_uses_annual_when_quarter_not_newer。
3. 在 tests/test_data_fetcher.py 增加 test_retry_only_allows_different_ticker_cold_misses_to_overlap。
4. 运行 tests/test_data_fetcher.py 和全量 pytest。
5. 按真实 pytest 输出更新 docs/plans/2-backend-performance-review_fix.md 的 Verification Performed 和新增测试列表。
6. 检查 docs/prompts/codex-validate-implementation.md 是否为有意范围；若不是，撤回；若是，最终说明。

不要改业务代码，除非新增测试暴露真实 bug。
最终回复列出修改文件、测试结果、是否保留 docs/prompts/codex-validate-implementation.md。
```
