# Plan Implementation Handoff (Revised)

## Original Plan
- **Plan path**: `docs/plans/backend_security_reliability_review.md`
- **Plan title**: 后端安全与可靠性修复计划 (Backend Security & Reliability Fix Plan)
- **External Review**: "Needs fixes" — findings 1, 3, 6 + new issue + test insufficiency
- **Fix executor**: Claude Code (Opus 4.7)
- **Fix date**: 2026-05-02

## Working Tree Summary
- **Branch**: `main`
- **Last commit**: `4d006b3c` — "Refactor assessment pipeline and dashboard data flow"
- **Uncommitted changes (this fix session)**: `tests/test_api.py`, `tests/test_data_fetcher.py` (new tests only)
- **Source changes committed in** `4d006b3c`: `src/api.py`, `src/config.py`, `src/data_fetcher.py`, `src/covenant_monitor.py`, `src/reportlab_pdf_exporter.py`, `src/services/rich_assessment_service.py`

## Fixes Applied (per External Review)

### Finding 1: 不可取消线程 → 容量隔离 + 明确降级
- Added `UpstreamCapacityError` exception class in `src/api.py`.
- Added `_FETCH_CAPACITY = threading.BoundedSemaphore(settings.upstream_max_workers)` for capacity gating.
- `_run_in_fetch_executor()` now acquires the semaphore non-blocking; raises `UpstreamCapacityError` if full; releases in `finally`.
- All 4 endpoints (`run_credit_assessment`, `search_symbols`, `check_covenants`, `export_full_pdf`) catch `UpstreamCapacityError` and return **503** with `error_type: "upstream_busy"`.
- `upstream_busy` added to `_priority_status_for_all_fail` → 503.
- Comments explicitly state: `asyncio.wait_for` is a *request wait timeout*; the OS thread may continue running. The bounded executor + semaphore prevent abandoned work from saturating the pool.
- `src/config.py` added: `upstream_max_workers: int = 12`.
- `_FETCH_EXECUTOR` uses `settings.upstream_max_workers`.

### Finding 3: 所有 yfinance 调用走同一个 proxy-safe wrapper
- Replaced `_clear_proxy_env()` context manager with `run_yfinance_call(fn, *, clear_proxy: bool = True)` in `src/data_fetcher.py`.
- `run_yfinance_call` always holds `_PROXY_CLEAR_LOCK`. When `clear_proxy=True`, it also clears/restores `os.environ`. When `clear_proxy=False`, it still holds the lock (preventing races with concurrent clear-proxy calls).
- All yfinance network sites now go through `run_yfinance_call`:
  - `get_financial_data()` main path: `_do_yfinance_calls` closure passed to `run_yfinance_call(clear_proxy=True)`.
  - `_fetch_a_share_akshare()` yfinance supplement: `_do_aks_yfinance_calls` closure passed to `run_yfinance_call(clear_proxy=True)`.
  - `api._search_tickers()`: both search attempts go through `run_yfinance_call(clear_proxy=attempt==1)`. First attempt holds lock without clearing; second holds lock with clearing.
- Removed `_clear_proxy_env` import from `src/api.py`. API layer no longer manipulates `os.environ` directly.

### Finding 6: localized cache + 配置
- `_LOCALIZED_NAME_CACHE` now uses `SimpleCache(default_ttl=86400, maxsize=settings.localized_name_cache_maxsize)`.
- `_data_cache` in data_fetcher.py uses `settings.data_cache_maxsize`.
- `src/config.py` added: `data_cache_maxsize: int = 1000`, `localized_name_cache_maxsize: int = 500`.
- `SimpleCache.__init__` uses `max(1, maxsize)` to prevent zero-size cache.

### New must-fix: internal_error + test assertions
- `"internal_error"` → 500 in `_priority_status_for_all_fail` (kept from previous fix).
- `test_unhandled_exception_in_process_ticker_isolated` asserts exact `500` (not a range).
- Added response body assertions: no raw exception strings (`"confidential db password"`, `"secret internal path"`, `"AttributeError"`, `"RuntimeError"`) in error responses.

### Test Insufficiency: fixed
- **single-flight test**: Rewrote `test_single_flight_coalesces_concurrent_misses` to count real `yf.Ticker()` constructor calls via `_CountingTicker`. Uses `threading.Event` to ensure thread 1 starts before thread 2. Asserts `ticker_call_count[0] == 1` exactly.
- **Capacity exhaustion tests**: 4 tests (assess 503, search 503, covenant 503, pdf 503).
- **Executor isolation tests**: 2 tests verifying `_run_in_fetch_executor` is used by assess and search.
- **Error content tests**: 2 tests verifying no raw strings in 500/503 responses.
- **`run_yfinance_call` wrapper tests**: 2 tests counting wrapper invocations (main path + AKShare supplement path).
- **Localized cache eviction test**: fills cache past maxsize, verifies LRU eviction.

## Plan-External Files (Pre-existing Changes)

The following files were changed in commit `4d006b3c` alongside the plan implementation. They are **not** part of the backend security/reliability plan:

| File | Status |
|---|---|
| `pyproject.toml` | Pre-existing (committed) |
| `src/ratio_analyzer.py` | Pre-existing (committed) |
| `src/services/assessment_service.py` | Pre-existing (committed) |
| `src/zscore.py` | Pre-existing (committed) |
| `tests/test_ratio_analyzer.py` | Pre-existing (committed) |
| `tests/test_zscore.py` | Pre-existing (committed) |
| `tests/test_covenant_monitor.py` | Pre-existing (committed) |
| `tests/test_rich_assessment_service.py` | Pre-existing (committed) |
| `web/src/App.tsx` | Pre-existing (committed) |
| `web/src/index.css` | Pre-existing (committed) |
| `docs/prompts/*` | Pre-existing (committed) |
| `docs/plans/README.md` | Pre-existing (committed) |

These can be verified with: `git diff 17f49f45..4d006b3c -- <file>`

## Files Changed (This Implementation + Fix)

| File | Reason |
|---|---|
| `src/api.py` | Input validation, error sanitization, capacity isolation, proxy via `run_yfinance_call`, PDF hardening |
| `src/config.py` | `upstream_max_workers`, `data_cache_maxsize`, `localized_name_cache_maxsize` |
| `src/covenant_monitor.py` | Threshold `gt=0`, NaN/Inf rejection |
| `src/data_fetcher.py` | `run_yfinance_call` wrapper, cache maxsize+LRU, single-flight, narrowed retry |
| `src/reportlab_pdf_exporter.py` | History size/string length limits |
| `src/services/rich_assessment_service.py` | `data_quality` metadata, safe reason codes |
| `tests/test_api.py` | Validation, sanitization, capacity isolation, executor isolation, localized cache |
| `tests/test_data_fetcher.py` | Cache eviction, single-flight (exact assert), `run_yfinance_call` wrapper |
| `tests/test_rich_assessment_service.py` | `data_quality` partial/complete |
| `docs/plans/backend_security_reliability_review_fix.md` | This handoff document |

## Verification Performed

| Command | Result |
|---|---|
| `./.venv/bin/python -m pytest tests/test_api.py tests/test_data_fetcher.py tests/test_rich_assessment_service.py tests/test_covenant_monitor.py -q` | **138 passed** |
| `./.venv/bin/python -m pytest -q` (full suite) | **260 passed** in 11.04s |

## Deviations From Original Plan

1. **Thread cancellation**: Plan implied `wait_for` could cancel underlying threads. Clarified that Python threads cannot be forcibly killed. Mitigation: bounded executor + capacity semaphore prevent resource exhaustion from abandoned (timed-out) work.

2. **Proxy handling**: Plan said "per-call proxy config". yfinance has no such API. Implemented `run_yfinance_call()` wrapper that holds a lock for ALL yfinance calls (both clear-proxy and non-clear-proxy), ensuring no concurrent os.environ races.

3. **Retry scope**: Narrowed from `(Exception,)` to `(ConnectionError, TimeoutError, OSError)`. Plan said "only 429/network" — OSError covers network errors; the existing DataFetchError INVALID_TICKER/NO_DATA_AVAILABLE non-retry check was already in place.

4. **PDF async wrapper**: Switched from `generate_full_pdf_async` to `generate_full_pdf` + `_run_in_fetch_executor` because the async wrapper was a no-op.

## Known Issues / Remaining Risks

1. **`asyncio.wait_for` cannot cancel the underlying OS thread.** This is a Python limitation. The bounded executor + semaphore prevent thread pool saturation but do not stop in-flight network calls after timeout.

2. **`run_yfinance_call` holds `_PROXY_CLEAR_LOCK` for the entire yfinance call duration.** Non-clear-proxy calls also hold the lock, which serializes ALL yfinance operations. This is correct for safety but limits concurrency of symbol search + data fetch when both are active.

3. **Cache sizes are configurable via `Settings` but not runtime-tunable.** Requires process restart to change.

## Suggested Prompt For Reviewer

```
Re-validate the implementation against docs/plans/backend_security_reliability_review.md.

All findings from the previous review (Findings 1, 3, 6) have been addressed:
- Finding 1: bounded executor + capacity semaphore + 503 upstream_busy
- Finding 3: run_yfinance_call wrapper covering all yfinance call sites
- Finding 6: localized cache bounded, both caches use settings

Return: Accepted / Needs fixes / Blocked
```
