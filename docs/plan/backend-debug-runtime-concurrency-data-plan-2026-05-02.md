# 后端 Debug 与故障定位修复计划（2026-05-02）

## 调试范围与当前结论

- 范围：仅检查后端代码，重点覆盖 `src/api.py`、`src/data_fetcher.py`、`src/ratio_analyzer.py`、`src/services/rich_assessment_service.py`、`src/html_pdf_exporter.py`、`src/pdf_report_core.py` 与后端测试。
- 未收到外部报错日志、堆栈或复现步骤，因此以下结论基于当前仓库代码、现有测试、dirty diff 和补充复现命令。
- 直接执行 `pytest -q` 失败：`zsh:1: command not found: pytest`。这是本地 PATH/虚拟环境问题，不是后端业务代码失败。
- 使用仓库虚拟环境执行后端全量测试通过：`./.venv/bin/pytest -q` -> `272 passed in 4.80s`。
- 当前测试通过不代表没有运行期缺陷；本次定位到的最高优先级问题属于超时、并发容量、代理环境和数据缺失类风险，现有测试未覆盖这些边界。

## P0 已确认根因：API executor capacity 在请求超时后提前释放

### 问题现象

`/api/v1/assess`、`/api/v1/covenants/check`、`/api/v1/symbols/search` 在 `asyncio.wait_for` 超时后会向客户端返回 timeout 或降级结果，但底层 `ThreadPoolExecutor` 中的阻塞任务仍在运行。当前代码会在包装协程被取消时立刻释放 capacity semaphore，导致新请求继续进入 executor 队列，长期运行时会出现请求堆积、线程池排队、超时放大和 503/504 不稳定。

补充复现已确认：

```bash
./.venv/bin/python -c $'import asyncio, time\nimport src.api as api\nstart = api._FETCH_CAPACITY._value\nasync def main():\n    try:\n        await asyncio.wait_for(api._run_in_fetch_executor(time.sleep, 0.4), timeout=0.05)\n    except TimeoutError:\n        pass\n    print("start", start, "after_timeout", api._FETCH_CAPACITY._value)\n    await asyncio.sleep(0.5)\n    print("after_worker_done", api._FETCH_CAPACITY._value)\nasyncio.run(main())'
```

输出为 `start 12 after_timeout 12`，说明 timeout 后 worker 仍在 sleep，但 capacity 已恢复到满值。

### 根因分析

- 文件：`src/api.py`
- 直接代码路径：
  - `_run_in_fetch_executor()` 获取 `_FETCH_CAPACITY`：`src/api.py:210-223`
  - `_release_after()` 在 `finally` 释放 semaphore：`src/api.py:224-230`
  - `_run_in_pdf_executor()` 存在同类释放逻辑：`src/api.py:233-247`
  - `_run_in_search_executor()` 存在同类释放逻辑：`src/api.py:250-270`
  - `/api/v1/assess` 用 `asyncio.wait_for(..., timeout=per_ticker_timeout)` 包裹：`src/api.py:518-523`
  - `/api/v1/covenants/check` 用 `asyncio.wait_for(..., timeout=per_ticker_timeout)` 包裹：`src/api.py:925-927`
  - `/api/v1/symbols/search` 用 `asyncio.wait_for(..., timeout=timeout_seconds)` 包裹：`src/api.py:801-805`

### 触发条件

- 任一阻塞函数运行时间超过 endpoint timeout，例如 yfinance、AKShare、ratio pipeline、symbol search 或未来 PDF 渲染。
- `asyncio.wait_for` 取消 `_release_after(fut)` 包装协程。

### 为什么会发生

`asyncio.wait_for` 超时时会取消被等待的 coroutine。`_release_after()` 的 `finally` 会在取消时执行，因此 semaphore 被提前释放。但 `loop.run_in_executor()` 已提交到 OS 线程的函数不会被取消，仍继续运行。当前注释 `src/api.py:187-192` 已指出 wait_for 不能取消运行中的 OS thread，但实现和注释目标相反，capacity 没有绑定到 worker 实际完成时间。

### 代码级修复方案

1. 在 `src/api.py` 增加一个共享 helper，例如 `_submit_with_capacity(executor, capacity, busy_message, func, *args)`。
2. helper 内部流程：
   - `capacity.acquire(blocking=False)` 失败时抛 `UpstreamCapacityError(busy_message)`。
   - 调用 `loop.run_in_executor(executor, func, *args)` 后，立刻给 future 注册 `add_done_callback(release_once)`。
   - `release_once` 内部用 `threading.Lock()` 或闭包布尔值确保 semaphore 只释放一次。
   - 包装 coroutine 只 `return await fut`，不要在 coroutine cancellation 的 `finally` 中释放 capacity。
   - 如果 `run_in_executor` 提交本身抛异常，需要同步释放 capacity 后再抛出。
3. 用 helper 替换：
   - `_run_in_fetch_executor()`：`src/api.py:210-230`
   - `_run_in_pdf_executor()`：`src/api.py:233-247`
   - `_run_in_search_executor()`：`src/api.py:250-270`
4. 新增测试：
   - `tests/test_api.py` 新增 `test_fetch_capacity_not_released_until_worker_done_after_timeout`。
   - 用短 sleep worker + `asyncio.wait_for(..., timeout=0.01)` 触发取消。
   - 断言 timeout 后 `_FETCH_CAPACITY` 未恢复，worker 完成后才恢复。
   - 同类测试覆盖 `_run_in_pdf_executor` 或至少共享 helper。

### 验收标准

- timeout 后 capacity 不提前恢复；worker 实际完成后才恢复。
- 现有 capacity exhaustion 测试仍通过。
- `./.venv/bin/pytest -q` 全量通过。

### 回归风险

- 修复后 timeout 请求会继续占用 capacity 直到底层线程实际结束，这是正确的背压行为，但在上游长期卡死时更容易返回 503。需要和 P3 single-flight 等待超时、真实上游 timeout 配合处理。

## P1 已确认设计缺陷：PDF 导出没有请求级 timeout

### 问题现象

`/api/v1/reports/pdf` 如果遇到大 payload、复杂 ReportLab 布局、字体问题或渲染卡住，会一直等待 `_run_in_pdf_executor()` 返回。当前已有独立 `_PDF_EXECUTOR` 和 `_PDF_CAPACITY`，但没有请求等待上限，用户侧会表现为接口长时间挂起。

### 根因分析

- 文件：`src/api.py`
- 直接代码路径：
  - PDF executor 定义：`src/api.py:199-203`
  - PDF 导出直接 await executor：`src/api.py:976-978`
  - 只捕获 `UpstreamCapacityError`、`ValueError`、通用 `Exception`：`src/api.py:978-994`
- 配置文件 `src/config.py` 目前没有 `pdf_export_timeout_seconds`：`src/config.py:24-44`

### 触发条件

- `generate_full_pdf(report, lang, theme)` 渲染耗时明显超过普通请求窗口。
- PDF payload 接近 2MB 上限，或者 statement/detail rows 多，ReportLab pagination 复杂。

### 为什么会发生

assess、symbol search、covenant 都在 endpoint 层使用 `asyncio.wait_for`，但 PDF route 没有同等超时保护。即使 P0 修复后 capacity 能正确背压，缺少 PDF timeout 仍会导致调用方无限等待。

### 代码级修复方案

1. 在 `src/config.py` 新增：
   - `pdf_export_timeout_seconds: float = 20.0`
2. 在 `src/api.py:976-978` 改为：
   - `pdf_bytes = await asyncio.wait_for(_run_in_pdf_executor(generate_full_pdf, report, lang, theme), timeout=max(1.0, settings.pdf_export_timeout_seconds))`
   - 需要在 `export_full_pdf()` 内引入 `asyncio`。
3. 在 `src/api.py:978-994` 新增 `except TimeoutError` 分支，返回：
   - status code: `504`
   - detail: `{"error": "PDF export timed out", "error_type": "timeout", "ticker": ticker}`
4. 新增测试：
   - `tests/test_api.py::test_pdf_export_timeout_returns_504`
   - monkeypatch `_run_in_pdf_executor` 或 `asyncio.wait_for` 模拟 timeout。

### 验收标准

- PDF 超时返回 504，`error_type == "timeout"`。
- PDF capacity exhausted 仍返回 503。
- 正常 PDF 导出仍返回 `application/pdf`、`X-PDF-SHA256`、`X-PDF-Bytes`。

### 回归风险

- timeout 只限制请求等待，不会杀死已进入 ReportLab 的 OS thread。必须先修 P0，避免 timeout 后 capacity 被提前释放。

## P2 高概率根因：retry_only 代理清理会和并发 yfinance 调用竞争全局 os.environ

### 问题现象

并发请求 yfinance 时，一个请求遇到 proxy/curl/SSL 异常后会执行清代理重试。清代理通过临时修改进程级 `os.environ` 实现；当前默认 `retry_only` 模式下，其他 yfinance 调用不会持有同一把锁，可能在代理变量被临时删除时启动网络请求，造成偶发网络错误、走错代理、认证失败或公司网络下表现不稳定。

### 根因分析

- 文件：`src/data_fetcher.py`
- 直接代码路径：
  - `_clear_proxy_env()` 删除进程级代理变量：`src/data_fetcher.py:55-60`
  - `_run_with_cleared_proxy()` 持有 `_PROXY_CLEAR_LOCK` 并修改/恢复环境：`src/data_fetcher.py:78-85`
  - `run_yfinance_call()` 在 `retry_only` 且 `clear_proxy=False` 时直接 `return fn()`，不加锁：`src/data_fetcher.py:109-112`
  - `run_yfinance_call_with_proxy_retry()` 默认第一次直接 `return fn()`，不加锁：`src/data_fetcher.py:129-135`
  - yfinance 主路径使用该 wrapper：`src/data_fetcher.py:1194-1211`
  - AKShare 补充 yfinance 也使用该 wrapper：`src/data_fetcher.py:962-968`
- 当前新增测试还固化了“不加锁”行为：`tests/test_data_fetcher.py:831-843`

### 触发条件

- 环境变量中存在 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY` 等代理设置。
- 至少两个线程并发执行 yfinance。
- 其中一个线程第一次失败并进入 `_run_with_cleared_proxy()`，另一个线程同时执行无锁的 yfinance 调用。

### 为什么会发生

`os.environ` 是进程级共享状态，不是线程局部变量。只有清理代理的线程持有 `_PROXY_CLEAR_LOCK` 不够，其他读环境/启动请求的 yfinance 调用也必须和清理操作互斥，否则会观察到被临时修改的环境。

### 代码级修复方案

1. 在 `src/data_fetcher.py` 新增 `_run_with_proxy_lock(fn)`：
   - `with _PROXY_CLEAR_LOCK: return fn()`
   - 不清理代理，只保证和清理代理互斥。
2. 修改 `run_yfinance_call()`：
   - `mode == "never"`：保持 `return fn()`。
   - `mode == "always"`：`clear_proxy=True` 走 `_run_with_cleared_proxy(fn)`，`clear_proxy=False` 走 `_run_with_proxy_lock(fn)`。
   - `mode == "retry_only"`：`clear_proxy=True` 走 `_run_with_cleared_proxy(fn)`，`clear_proxy=False` 走 `_run_with_proxy_lock(fn)`。
3. 修改 `run_yfinance_call_with_proxy_retry()`：
   - `mode == "retry_only"` 第一次尝试走 `_run_with_proxy_lock(fn)`。
   - proxy 相关异常时第二次走 `_run_with_cleared_proxy(fn)`。
4. 更新测试：
   - 删除或改写 `tests/test_data_fetcher.py:831-843` 中“no lock”的断言。
   - 新增并发测试：一个线程进入 `_run_with_cleared_proxy()` 时，另一个 `run_yfinance_call(..., clear_proxy=False)` 必须等待锁释放后执行。

### 验收标准

- 代理清理期间没有其他 yfinance wrapper 执行 `fn()`。
- proxy retry 行为仍保留：第一次 proxy 异常后第二次清代理成功。
- 全量测试通过。

### 回归风险

- 默认 `retry_only` 模式下 yfinance 调用会被串行化到同一把代理锁，吞吐会下降。若要兼顾吞吐，需要后续改为不修改全局环境的 yfinance/session 级代理控制；当前最小修复优先保证正确性。

## P3 高概率根因：single-flight waiter 无超时，leader 卡死会放大线程耗尽

### 问题现象

同一个 ticker/source/mode 并发请求时，第一个请求作为 leader 访问上游，后续请求在 `_InFlightEntry.event.wait()` 等待 leader 结果。如果 leader 卡在 yfinance/AKShare 调用中，waiter 会无限阻塞在 worker thread 内。API 层 timeout 只取消 asyncio 等待，不会终止 worker thread。

### 根因分析

- 文件：`src/data_fetcher.py`
- 直接代码路径：
  - `_InFlightEntry` 定义：`src/data_fetcher.py:228-243`
  - waiter 无 timeout 等待：`src/data_fetcher.py:1125-1131`
  - leader finally 才 `event.set()` 并删除 `_in_flight`：`src/data_fetcher.py:1446-1452`
- 关联问题：P0 当前会提前释放 API capacity，导致更多 waiter 被放进线程池。

### 触发条件

- 同一 cache key 被并发请求。
- leader 上游调用长时间不返回或卡死。
- waiter 进入 `event.wait()`。

### 为什么会发生

single-flight 只做了击穿保护，没有等待时限、stale entry 判断或 leader 健康状态。API timeout 无法中断正在运行或正在 `event.wait()` 的 worker thread。

### 代码级修复方案

1. 在 `src/config.py` 新增：
   - `single_flight_wait_timeout_seconds: float = 20.0`
2. 在 `src/data_fetcher.py:1125-1131` 改为：
   - `completed = in_flight_entry.event.wait(timeout=max(0.1, settings.single_flight_wait_timeout_seconds))`
   - `completed == False` 时抛 `DataFetchError(..., error_type=DataFetchErrorType.NETWORK_ERROR, details={"reason": "single_flight_timeout", "cache_key": cache_key})`
3. 不要由 waiter 删除 `_in_flight`，仍由 leader finally 清理，避免破坏 leader 状态传播。
4. 新增测试：
   - leader mock 阻塞，waiter 使用很短 single-flight timeout。
   - waiter 抛 `DataFetchError`，`error_type == NETWORK_ERROR`，details reason 为 `single_flight_timeout`。
   - 现有 `test_single_flight_reuses_failure_for_waiters` 仍通过。

### 验收标准

- waiter 不会无限等待。
- leader 正常成功/失败时仍能复用结果/异常。
- 与 P0 一起验证超时后不会无限放大线程占用。

### 回归风险

- 超时后的 waiter 会返回网络错误，而 leader 可能随后成功并写入缓存；这是可接受的请求级降级。响应文案应说明是等待上游并发请求超时。

## P4 高概率根因：AKShare statement 日期精确匹配导致跨表数据缺失

### 问题现象

AKShare 三张报表中，如果 `报告日` 的格式不完全一致，例如 income 是 `20250930`，balance/cash 是 `2025-09-30`，当前代码能识别季度/年度日期，却在取 balance/cash 行时匹配失败，导致该 period 的 balance/cash DataFrame 为空。下游会出现 ratio 缺失、Z-Score N/A、covenant 默认 breach 或整期 calculation_failed。

### 根因分析

- 文件：`src/data_fetcher.py`
- 直接代码路径：
  - `_date_digits()` 已用于归一化日期：`src/data_fetcher.py:859-863`
  - annual/quarter 分类基于 income dates：`src/data_fetcher.py:864-866`
  - `_find_row()` 却用原始值精确比较：`src/data_fetcher.py:906-911`
  - quarterly entries 依赖 `_find_row()`：`src/data_fetcher.py:924-933`
  - annual entries 依赖 `_find_row()`：`src/data_fetcher.py:943-952`

### 触发条件

- AKShare 返回的三张表 `报告日` 类型或格式不同。
- 其中 income 表有目标日期，但 balance/cash 表等价日期不是同一个原始字符串。

### 为什么会发生

代码前半段已经承认日期可能是 `YYYY-12-31` 或 `YYYYMMDD`，但 `_find_row()` 没复用 `_date_digits()`。分类和查找使用了两套不一致的日期语义。

### 代码级修复方案

1. 在 `_fetch_a_share_akshare()` 内替换 `_find_row()`：
   - 先判断 `df is None or df.empty or '报告日' not in df.columns`。
   - `target_digits = _date_digits(date_val)`。
   - 用 `df['报告日'].map(_date_digits) == target_digits` 匹配。
2. 可选优化：为 inc/bal/cf 分别预建 `{date_digits: row}` map，避免循环中重复 map。
3. 同时将 `dates_inc` 按 `_date_digits` 倒序排序，避免 AKShare 返回顺序变化时 latest 逻辑错误。
4. 新增测试：
   - fake AKShare income dates 用 `20250930`，balance/cash dates 用 `2025-09-30`。
   - 断言同一 history period 中 income/balance/cash 均非空。

### 验收标准

- 不同日期格式的三张表能合并到同一个 period。
- A-share quarterly + annual history 现有测试仍通过。

### 回归风险

- 如果同一表存在多个原始 `报告日` 归一化到同一天，只取第一行。应在测试中明确保持 newest-first 或排序后取第一。

## P5 高概率根因：total_debt 派生逻辑不完整，导致杠杆/现金流比率错误缺失

### 问题现象

如果数据源缺少显式 `total_debt`，但有 `short_term_debt`、`long_term_debt`、`current_portion_lt_debt`、`bonds_payable` 等组成项，`debt_to_assets`、`debt_to_ebitda`、`fcf_to_debt` 会返回 `None`，下游 covenant 可能默认 breach，PDF/JSON 也会显示关键债务指标缺失。

### 根因分析

- 文件：`src/data_fetcher.py`、`src/ratio_analyzer.py`
- 直接代码路径：
  - yfinance 映射保留 `short_term_debt`、`long_term_debt`：`src/data_fetcher.py:478-485`
  - AKShare 映射保留 `bonds_payable`、`current_portion_lt_debt`：`src/data_fetcher.py:590-593`
  - AKShare 派生 total debt 只在 short/long debt 存在时触发，忽略只有 current portion/bonds 的情况：`src/data_fetcher.py:628-634`
  - ratio 层只读取 `total_debt`：`src/ratio_analyzer.py:799-812`
  - cash-flow ratio 也只读取 `total_debt`：`src/ratio_analyzer.py:979-989`

### 触发条件

- yfinance statement 没有 `Total Debt`，但有短债/长债字段。
- AKShare statement 只有 `一年内到期的非流动负债` 或 `应付债券`，没有短期借款/长期借款。

### 为什么会发生

字段标准化层和 ratio 层的职责不一致：上游保留了债务组成项，但只有 AKShare 局部做了不完整派生；yfinance 路径完全没有总债派生，ratio 层也没有兜底。

### 代码级修复方案

1. 在 `src/ratio_analyzer.py` 新增 helper：
   - `_derive_total_debt_from_map(bs_map: dict[str, float]) -> float | None`
   - 优先返回 `bs_map.get("total_debt")`。
   - 缺失时汇总 `short_term_debt`、`long_term_debt`、`current_portion_lt_debt`、`bonds_payable` 中存在的值。
   - 所有组成项都缺失时返回 `None`。
2. 在 `calculate_leverage_ratios()` 的 `src/ratio_analyzer.py:799-812` 使用该 helper。
3. 在 `calculate_cash_flow_ratios()` 的 `src/ratio_analyzer.py:979-989` 使用同一 helper。
4. 在 `src/data_fetcher.py:628-634` 把 AKShare 派生条件改成任一债务组成项存在即派生。
5. 新增测试：
   - `tests/test_ratio_analyzer.py`：只有 short/long debt 时 `debt_to_assets`、`debt_to_ebitda`、`fcf_to_debt` 正常计算。
   - `tests/test_data_fetcher.py`：只有 `应付债券` 或 `一年内到期的非流动负债` 时 `_akshare_row_to_df()` 生成 `total_debt`。

### 验收标准

- 缺失显式 `total_debt` 时，债务组成项可驱动杠杆与现金流比率。
- 显式 `total_debt` 存在时优先使用显式值，避免重复计算。

### 回归风险

- 不同数据源对 debt component 的包含关系可能不同。必须坚持“显式 total_debt 优先”，只有缺失时才汇总组成项，降低重复计算风险。

## P6 低概率推测：关键运行配置缺少下限校验，错误环境变量可导致启动或容量异常

### 问题现象

如果环境变量把 `UPSTREAM_MAX_WORKERS`、`PDF_MAX_WORKERS`、`SEARCH_MAX_WORKERS`、timeout 或 cache size 配成 0/负数，应用可能在 import 阶段崩溃，或创建不可用的 semaphore/executor。

### 根因分析

- 文件：`src/config.py`
- 当前设置均是裸类型，没有 `Field(gt=0)` 或 `ge=1` 约束：`src/config.py:24-38`
- `src/api.py` 直接把 `settings.upstream_max_workers` 传给 `threading.BoundedSemaphore`：`src/api.py:197`
- `src/api.py` 直接把 `settings.pdf_max_workers` 传给 `threading.BoundedSemaphore`：`src/api.py:203`

### 触发条件

- `.env` 或部署环境中配置了 0/负数 worker 或 timeout。

### 为什么会发生

Pydantic settings 会完成类型转换，但当前没有数值范围约束。部分调用处有 `max(1, ...)`，部分没有。

### 代码级修复方案

1. 在 `src/config.py` 引入 `Field`。
2. 给 worker/cache/timeout 配置添加边界：
   - worker/cache/maxsize 使用 `Field(default, ge=1)`。
   - timeout 使用 `Field(default, gt=0)`。
3. 保留 endpoint 内部 `max(...)` 防御，但不要依赖它修复 import-time semaphore。
4. 新增配置测试或最小 import 测试，验证非法设置会在 settings 层失败，而不是 API import 阶段异常。

### 验收标准

- 非法环境配置报错位置清晰。
- 合法默认配置不变。

### 回归风险

- 如果现有部署曾用 0 表示禁用某功能，会被拒绝。当前代码没有支持 0=disabled 的语义，因此应优先修正部署配置。

## 修改顺序

1. 先修 P0：重写 executor capacity 释放机制，并加 timeout cancellation 回归测试。
2. 修 P1：给 PDF 导出加配置化 timeout 和 504 分支。
3. 修 P2：恢复 yfinance proxy lock 对全局 `os.environ` 修改的互斥保护，并更新既有测试。
4. 修 P3：给 single-flight waiter 加 timeout，避免同 ticker 卡死放大。
5. 修 P4：统一 AKShare `报告日` 归一化匹配，并补跨格式日期测试。
6. 修 P5：补 total_debt 派生 helper 和 ratio/data_fetcher 测试。
7. 修 P6：为运行配置加 Pydantic 数值约束。
8. 运行 `./.venv/bin/pytest -q`，必要时再跑 `./smoke_test.sh http://127.0.0.1:8000`（需先启动后端且前端 dist 存在）。

## 总体验收标准

- `./.venv/bin/pytest -q` 全量通过。
- executor capacity 在 `asyncio.wait_for` timeout 后不会提前释放。
- PDF 渲染超时返回 504，不无限等待。
- yfinance 清代理重试期间不会有其他 yfinance wrapper 并发观察到被修改的 `os.environ`。
- single-flight waiter 不会无限阻塞。
- AKShare 不同日期格式能正确合并三张 statement。
- 缺失显式 `total_debt` 但存在债务组成项时，杠杆/现金流比率不再错误缺失。

## 后续 LLM 可直接执行的修改 prompt

请在 `/Users/rightleung/Documents/Python/RiskLens` 中只修改后端代码和后端测试，不改前端。按以下顺序实现，并确保每一步后可运行相关测试。

1. 修改 `src/api.py` 的 executor helper：
   - 新增 `_submit_with_capacity(executor, capacity, busy_message, func, *args)`，统一封装 `_FETCH_EXECUTOR`、`_PDF_EXECUTOR`、`_SEARCH_CAPACITY` 的提交逻辑。
   - capacity acquire 成功后，`run_in_executor` 返回的 future 必须注册 `add_done_callback(release_once)`，只有 future 实际 done 后释放 semaphore。
   - wrapper coroutine 不要在 cancellation 的 `finally` 中释放 semaphore。
   - `run_in_executor` 提交失败时必须同步释放 capacity。
   - 用该 helper 替换 `_run_in_fetch_executor()`、`_run_in_pdf_executor()`、`_run_in_search_executor()`。

2. 修改 `src/config.py`：
   - 引入 `Field`。
   - 新增 `pdf_export_timeout_seconds: float = Field(20.0, gt=0)`。
   - 新增 `single_flight_wait_timeout_seconds: float = Field(20.0, gt=0)`。
   - 给 `assess_max_concurrency`、`upstream_max_workers`、`pdf_max_workers`、`search_max_workers`、`data_cache_maxsize`、`localized_name_cache_maxsize`、`cache_ttl_seconds`、`negative_cache_ttl_seconds`、`max_pdf_periods`、`max_pdf_detail_rows` 添加合理的 `ge=1` 或 `gt=0` 约束。

3. 修改 `src/api.py` 的 PDF route：
   - 在 `export_full_pdf()` 中用 `asyncio.wait_for(_run_in_pdf_executor(...), timeout=max(1.0, settings.pdf_export_timeout_seconds))` 包裹 PDF 生成。
   - 捕获 `TimeoutError`，返回 HTTP 504，detail 至少包含 `error_type="timeout"` 和 `ticker`。

4. 修改 `src/data_fetcher.py` 的 yfinance proxy wrapper：
   - 新增 `_run_with_proxy_lock(fn)`，只持有 `_PROXY_CLEAR_LOCK`，不清理环境。
   - `run_yfinance_call()` 在 `always`/`retry_only` 且 `clear_proxy=False` 时走 `_run_with_proxy_lock(fn)`。
   - `run_yfinance_call_with_proxy_retry()` 在 `retry_only` 第一次尝试走 `_run_with_proxy_lock(fn)`，proxy 相关异常后第二次走 `_run_with_cleared_proxy(fn)`。
   - 更新测试，不再断言 retry_only+clear_proxy=False 无锁。

5. 修改 `src/data_fetcher.py` 的 single-flight waiter：
   - 将 `in_flight_entry.event.wait()` 改成带 `settings.single_flight_wait_timeout_seconds` 的 timeout。
   - wait 超时抛 `DataFetchError("Timed out waiting for in-flight fetch", error_type=DataFetchErrorType.NETWORK_ERROR, ticker=ticker, details={"reason": "single_flight_timeout", "cache_key": cache_key})`。
   - waiter 不删除 `_in_flight`，leader finally 保持现有清理职责。

6. 修改 `src/data_fetcher.py` 的 AKShare 日期匹配：
   - `_find_row()` 用 `_date_digits()` 比较 `报告日`，不要原始字符串精确匹配。
   - 对 `annual_dates` 和 `quarterly_dates_raw` 按 `_date_digits` 倒序排序。
   - `_akshare_row_to_df()` 的 total debt 派生条件改为任一债务组成项存在即派生。

7. 修改 `src/ratio_analyzer.py`：
   - 新增 `_derive_total_debt_from_map(bs_map)`。
   - `calculate_leverage_ratios()` 和 `calculate_cash_flow_ratios()` 都使用该 helper。
   - 显式 `total_debt` 优先；缺失时汇总 `short_term_debt`、`long_term_debt`、`current_portion_lt_debt`、`bonds_payable`。

8. 增加/更新测试：
   - `tests/test_api.py`：executor timeout cancellation 后 capacity 不提前释放；PDF timeout 返回 504。
   - `tests/test_data_fetcher.py`：proxy lock 互斥；single-flight waiter timeout；AKShare 跨日期格式匹配；AKShare 仅 current portion/bonds 时派生 total_debt。
   - `tests/test_ratio_analyzer.py`：缺失显式 `total_debt` 但有债务组成项时，debt ratios 和 fcf_to_debt 正常计算。

9. 验收：
   - 运行 `./.venv/bin/pytest -q`。
   - 若测试失败，优先修测试暴露的真实行为问题，不要放宽断言掩盖 P0/P2/P3 的并发语义。
