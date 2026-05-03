# Required Fixes: Backend Runtime Concurrency/Data Implementation

## Verdict

Needs fixes

## Critical

### Fix 1: Make the full backend test suite deterministic and remove live upstream background work from timeout tests

- Severity: Critical
- Related original plan item: P0 executor capacity release, verification
- Problem: `./.venv/bin/pytest -q` currently fails with `1 failed, 294 passed`. The failing test is `tests/test_api.py::TestExecutorCapacityAfterTimeout::test_fetch_capacity_not_released_until_worker_done_after_timeout`.
- Missing, partial, or incorrect implementation: Earlier timeout tests monkeypatch `asyncio.wait_for` to raise immediately after `_run_in_fetch_executor()` has already submitted real `_analyze_single_ticker()` work to `_FETCH_EXECUTOR`. Those background workers call yfinance for real tickers (`AAPL`, `A`, `B`), continue after the test returns, and mutate `_FETCH_CAPACITY` while later capacity tests are running. The failing assertion saw `cap_before=8` and `cap_after_done=12`, proving cross-test leakage.
- Files to modify:
  - `tests/test_api.py`
- Symbols/tests to modify:
  - `TestAssessEndpoint.test_assess_timeout_returns_504`
  - `TestAssessEndpoint.test_all_fail_timeout_plus_invalid_returns_504`
  - `TestSearchSymbols.test_symbol_search_timeout_returns_504`
  - `TestCovenantsEndpoint.test_covenant_timeout_returns_504`
  - `TestExecutorCapacityAfterTimeout.test_fetch_capacity_not_released_until_worker_done_after_timeout`
  - `TestExecutorCapacityAfterTimeout.test_pdf_capacity_not_released_until_worker_done_after_timeout`
- Required behavior:
  - Timeout tests must not submit real yfinance/AKShare/API work to the shared production executors.
  - Tests that intentionally exercise `_submit_with_capacity()` must isolate executor and semaphore state from global `_FETCH_EXECUTOR`, `_FETCH_CAPACITY`, `_PDF_EXECUTOR`, and `_PDF_CAPACITY`, or they must wait for/drain all intentionally submitted work before returning.
  - Full test suite must be order-independent and deterministic.
- Required code-level changes:
  1. In endpoint timeout tests that monkeypatch `asyncio.wait_for`, also monkeypatch the executor wrapper before issuing the request:
     - For `/api/v1/assess`, set `api._run_in_fetch_executor` to a function that returns a controlled awaitable/future and does not call `_analyze_single_ticker`.
     - For `/api/v1/symbols/search`, set `api._run_in_fetch_executor` to a controlled awaitable/future and do not call `_search_tickers`.
     - For `/api/v1/covenants/check`, set `api._run_in_fetch_executor` to a controlled awaitable/future and do not call `fetcher.get_financial_data`.
  2. Replace the P0 tests' direct use of `api._FETCH_CAPACITY` and `api._PDF_CAPACITY` with local `threading.BoundedSemaphore` instances and local `ThreadPoolExecutor` instances passed to `api._submit_with_capacity()`. Example expected shape:
     - create `cap = threading.BoundedSemaphore(1)`
     - create `ex = ThreadPoolExecutor(max_workers=1)`
     - call `await asyncio.wait_for(api._submit_with_capacity(ex, cap, "busy", _slow_worker), timeout=0.01)`
     - assert `cap._value == 0` while worker is running
     - wait for worker completion and assert `cap._value == 1`
     - shut down the local executor with `ex.shutdown(wait=True)`
  3. If any test must use the global executors, add explicit worker completion synchronization and avoid comparing against a global semaphore baseline that may be affected by other tests.
- Tests to add or update:
  - Update existing timeout tests so they do not emit yfinance DNS/curl logs.
  - Update P0 capacity tests to use local executor/semaphore and prove the shared helper behavior directly.
- Verification command:
  - `./.venv/bin/pytest -q`
  - `./.venv/bin/pytest tests/test_api.py -q`
- Acceptance condition:
  - Full suite passes.
  - No test in `tests/test_api.py` starts real yfinance work when simulating timeout via monkeypatched `asyncio.wait_for`.
  - P0 capacity tests pass in isolation and in full-suite order.

## High

### Fix 2: Make AKShare cross-format date matching test exercise production code, not a copied local helper

- Severity: High
- Related original plan item: P4 AKShare statement date matching
- Problem: `tests/test_data_fetcher.py::test_akshare_date_digits_cross_format_matching` copies a local `_date_digits()` and `_find_row()` inside the test. It verifies the copied test helper, not `_fetch_a_share_akshare()` or the production `_find_row()` nested inside it.
- Missing, partial, or incorrect implementation: The implementation in `src/data_fetcher.py` may be correct, but the test would still pass if production `_find_row()` regressed to raw string matching again.
- Files to modify:
  - `tests/test_data_fetcher.py`
- Symbols/tests to modify:
  - Replace `test_akshare_date_digits_cross_format_matching`
- Required behavior:
  - The test must monkeypatch fake AKShare APIs and call `FinancialDataFetcher.get_financial_data("600000", "akshare", include_profile=False, include_supplement=False)` or `_fetch_a_share_akshare(...)` directly.
  - Fake income statement dates should use compact format such as `20250930`.
  - Fake balance/cashflow statement dates should use dashed format such as `2025-09-30`.
  - The returned `history` entry for `Q3 '25 (U)` must have non-empty `income`, `balance`, and `cash` DataFrames with expected mapped values.
- Required code-level changes:
  1. Build fake `ak` module with `stock_financial_report_sina(stock, symbol)` returning three DataFrames:
     - `利润表`: `报告日` values like `["20250930", "20241231", "20231231"]`
     - `资产负债表`: matching dates like `["2025-09-30", "2024-12-31", "2023-12-31"]`
     - `现金流量表`: matching dashed dates
  2. Monkeypatch import path used by `_fetch_a_share_akshare()` so `import akshare as ak` resolves to the fake module.
  3. Call production fetch with `include_profile=False, include_supplement=False` to avoid network.
  4. Assert the first quarterly period includes expected balance/cash values, not empty frames.
- Tests to add or update:
  - Replace the copied-helper test with a production-path test.
- Verification command:
  - `./.venv/bin/pytest tests/test_data_fetcher.py -q`
- Acceptance condition:
  - The test fails if `src/data_fetcher.py::_fetch_a_share_akshare()` returns to raw `df['报告日'] == date_val` matching.

### Fix 3: Make AKShare total debt derivation tests actually cover missing short/long debt keys

- Severity: High
- Related original plan item: P5 total debt derivation
- Problem: `test_akshare_total_debt_derived_when_only_bonds_payable_present` and `test_akshare_total_debt_derived_when_only_current_portion_present` include `'短期借款': 0` and `'长期借款': 0`. Because `_akshare_row_to_df()` stores zero values, the old pre-fix condition `if 'short_term_debt' in records or 'long_term_debt' in records` would still pass. These tests do not catch the intended regression.
- Missing, partial, or incorrect implementation: Test inputs contradict test names and the original bug condition.
- Files to modify:
  - `tests/test_data_fetcher.py`
- Symbols/tests to modify:
  - `test_akshare_total_debt_derived_when_only_bonds_payable_present`
  - `test_akshare_total_debt_derived_when_only_current_portion_present`
- Required behavior:
  - The “only bonds payable” test must omit `短期借款` and `长期借款` entirely, or set them to values that `_akshare_row_to_df()` ignores as missing (`None`/`""`/`"nan"`).
  - The “only current portion” test must omit `短期借款` and `长期借款` entirely, or set them to missing values.
  - The tests must fail against the old condition and pass with the new `any(k in records for k in _debt_keys)` condition.
- Required code-level changes:
  1. Remove `'短期借款': 0` and `'长期借款': 0` from both test rows.
  2. Keep only the target component:
     - bonds test: include `'应付债券': 150`; optionally include `'一年内到期的非流动负债': None`
     - current portion test: include `'一年内到期的非流动负债': 80`; optionally include `'应付债券': None`
  3. Assert `total_debt` equals only the target component.
- Tests to add or update:
  - Update the two existing tests.
- Verification command:
  - `./.venv/bin/pytest tests/test_data_fetcher.py -q`
- Acceptance condition:
  - Both tests fail on the old short/long-only condition and pass on the new any-component condition.

## Medium

### Fix 4: Avoid leaking coroutine warnings in PDF timeout tests

- Severity: Medium
- Related original plan item: P1 PDF export timeout
- Problem: `tests/test_api.py::TestPdfExportTimeout.test_pdf_export_timeout_returns_504` monkeypatches `asyncio.wait_for` to raise before awaiting the awaitable returned by `_run_in_pdf_executor`. The current test uses a completed wrapped future to avoid coroutine warnings, which is acceptable, but the same pattern should be applied consistently in other timeout tests that pass coroutine objects.
- Missing, partial, or incorrect implementation: Some timeout tests close/cancel whatever object they receive, but after the executor refactor they may receive wrapped futures tied to real submitted work.
- Files to modify:
  - `tests/test_api.py`
- Symbols/tests to modify:
  - Same endpoint timeout tests listed in Fix 1.
- Required behavior:
  - Fake `wait_for` should not leave unawaited coroutine warnings.
  - Fake executor wrappers used in timeout tests should return futures, not coroutine objects, unless the fake `wait_for` explicitly closes the coroutine.
- Tests to add or update:
  - Covered by Fix 1 updates.
- Verification command:
  - `./.venv/bin/pytest tests/test_api.py -q`
- Acceptance condition:
  - No RuntimeWarning about unawaited coroutines or pending tasks.

## Low

- none

## What Claude Code Did Not Finish

- It did not leave the repository in a passing test state: `./.venv/bin/pytest -q` fails.
- It did not isolate timeout tests from production executors and live yfinance calls.
- It did not make the AKShare cross-format date test exercise the actual production fetch path.
- It did not make the AKShare “only bonds/current portion” tests cover absence of short/long debt keys.

## Scope / Deviation Review

- Main implementation scope is aligned with the plan: P0-P6 were attempted in the intended files.
- The executor implementation direction is acceptable: capacity release is tied to a `concurrent.futures.Future` callback rather than an asyncio cancellation `finally`.
- The PDF timeout implementation is in scope.
- The proxy-lock implementation intentionally serializes yfinance calls for correctness. This matches the required fix plan, though it is a throughput tradeoff.
- The main blocker is verification quality and test isolation, not broad scope drift.

## Test Coverage Review

- API timeout/capacity coverage exists but is currently order-dependent and fails in the full suite.
- Data-fetcher P4/P5 tests need to be rewritten so they fail against the old bug.
- Ratio analyzer P5 tests are directionally correct and can remain after the full suite is fixed.

## Verification Commands

```bash
./.venv/bin/pytest -q
./.venv/bin/pytest tests/test_api.py -q
./.venv/bin/pytest tests/test_data_fetcher.py -q
./.venv/bin/pytest tests/test_ratio_analyzer.py -q
```

## Claude Code Fix Prompt

```text
/user:fix-external-review
Original plan: docs/plan/backend-debug-runtime-concurrency-data-plan-2026-05-02.md

External review:
The implementation is close but cannot be accepted because the full backend suite fails and several new tests do not cover the production paths they claim to validate.

Required fixes:
1. Fix tests/test_api.py timeout tests so they do not submit real yfinance/AKShare work to shared production executors. Endpoint timeout tests that monkeypatch asyncio.wait_for must also monkeypatch api._run_in_fetch_executor or api._run_in_pdf_executor to return controlled awaitables/futures. Do not let tests start real _analyze_single_ticker, _search_tickers, or fetcher.get_financial_data when simulating timeout.
2. Rewrite TestExecutorCapacityAfterTimeout to call api._submit_with_capacity() with local ThreadPoolExecutor and local BoundedSemaphore instances. Assert local semaphore remains consumed until the worker finishes, then returns to full capacity. Do not compare against api._FETCH_CAPACITY._value or api._PDF_CAPACITY._value.
3. Replace tests/test_data_fetcher.py::test_akshare_date_digits_cross_format_matching with a production-path fake-AKShare test that calls FinancialDataFetcher.get_financial_data(..., "akshare", include_profile=False, include_supplement=False) or _fetch_a_share_akshare(), and asserts cross-format income/balance/cash report dates merge into non-empty period frames.
4. Fix the two AKShare total_debt derivation tests so short/long debt keys are absent or missing, not present as zero. The tests must fail against the old short/long-only derivation condition.
5. Run ./.venv/bin/pytest -q and ensure it passes without yfinance DNS/curl logs caused by timeout tests.

Required fix plan file:
docs/reviews/backend-debug-runtime-concurrency-data_required_fixes.md
```
