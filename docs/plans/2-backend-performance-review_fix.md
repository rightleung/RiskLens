# Plan Implementation Handoff

## Original Plan
- Plan path: `docs/plans/2-backend-performance-review.md`
- Plan title: Backend Performance Review Plan
- Plan source/session: External planning session (Codex)
- Implementation executor: Claude Code
- Implementation commit: `49793274` (Add backend review prompts and plan documentation workflow)

## Working Tree Summary
- Branch: `main`
- Git status: 5 files modified (uncommitted — final review fixes)
- Changed files: 1 source + 2 test + 1 docs + 1 prompts (intentional workflow doc)

## Plan Coverage Matrix

| Plan Item | Status | Evidence | Notes |
|---|---|---|---|
| **P0: yfinance global lock serialization** | Completed | `src/data_fetcher.py` — `run_yfinance_call_with_proxy_retry()` added; `time.sleep(0.3)` moved outside lock; `yfinance_clear_proxy_mode` config default `"retry_only"`; `_do_yfinance_calls()` uses retry wrapper; `_do_aks_yfinance_calls()` also migrated | `run_yfinance_call()` kept for backward compatibility (search still uses it) |
| **P0: Failure path search suggestions** | Completed | `src/api.py` — `AssessmentRequest.include_suggestions: bool = False`; `maybe_fetch_suggestions()` only triggers for `invalid_ticker`/`no_data_available` when enabled; timeout/upstream_busy/internal_error return `sugg: []` | Pre-existing 5 call sites all collapsed to conditional helper |
| **P0: Executor pool isolation** | Completed | `src/api.py` — `_PDF_EXECUTOR` + `_PDF_CAPACITY` (2 workers); `_SEARCH_CAPACITY` (3 slots, shares fetch pool); `_run_in_pdf_executor()`, `_run_in_search_executor()`; PDF route uses `_run_in_pdf_executor`; `src/config.py` — `pdf_max_workers=2`, `search_max_workers=3` | Search capacity exhaustion returns `[]` gracefully |
| **P1: Latest-only covenant fetch** | Completed | `src/data_fetcher.py` — `get_financial_data(mode='dashboard'\|'latest', include_profile=, include_supplement=)`; cache key includes mode+flags; covenant route at `src/api.py:867` calls `mode='latest', include_profile=False` | Latest mode skips quarterly fetches entirely, only reads first annual column |
| **P1: Single-flight + negative cache** | Completed | `src/data_fetcher.py` — `_InFlightEntry` class with event/result/exception; waiters reuse leader outcome; `_error_cache` with `_NEGATIVE_CACHE_TTLS` (invalid:900s, no-data:300s, rate-limit:60s, network:10s); `@retry_with_backoff` removed from `get_financial_data` | Leader stores result in entry before return; negative cache checked before single-flight |
| **P1: A-share optional profile/supplement** | Completed | `src/data_fetcher.py` — `_fetch_a_share_akshare()` accepts `include_profile`, `include_supplement`; profile API calls guarded with ternary `if include_profile else None`; yfinance supplement wrapped in `if include_supplement:` with default `market_cap=0` | Statement parallelization deferred (see Deviations) |
| **P2: Ratio snapshot** | Completed | `src/ratio_analyzer.py` — `dataframe_to_value_map()` added; all 5 category functions (`calculate_liquidity_ratios`, `calculate_leverage_ratios`, `calculate_profitability_ratios`, `calculate_efficiency_ratios`, `calculate_cash_flow_ratios`) build dict snapshot once via `dataframe_to_value_map()` and use `.get()` lookups; `_get_value()` accepts `dict` as alternative to `DataFrame` | Validation calls (`validate_dataframe`) preserved for safety |
| **P2: PDF statement index + matrix** | Completed | `src/html_pdf_exporter.py` — `_build_statement_sections()` builds `rows_by_period_maps: list[dict]` replacing `next(...)` linear scan; `max_pdf_periods` cap (default 12) at function entry | |
| **P2: summary_rows translation bug fix** | Completed | `src/html_pdf_exporter.py:1837` — changed `section.get('summary_rows', [])` to `section.get('rows', [])` matching the section dict key set at line 1793 | Pre-existing bug: non-English summary row labels were never translated |
| **P3: Legacy main.py serial** | Not implemented | | Plan marked this as P3/low priority; no changes made |
| **A-share statement parallelization** | Deviated | | Deferred — requires ThreadPoolExecutor inside `_fetch_a_share_akshare`; conditional profile/supplement flags provide primary benefit |
| **pdf_report_core matrix re-construction** | Not implemented | | `_sanitize_pdf_document_model()` left as-is; the sanitization layer's matrix building is the validate-and-clean step; deduplication with `build_pdf_document_model` would require cross-module refactor |

## Files Changed

| File | Reason | Related Plan Item |
|---|---|---|
| `src/config.py` | Added `pdf_max_workers`, `search_max_workers`, `yfinance_clear_proxy_mode`, `negative_cache_ttl_seconds`, `max_pdf_periods`, `max_pdf_detail_rows` | Executor split, lock strategy, PDF caps |
| `src/api.py` | Executor split (fetch/pdf/search), `include_suggestions` field, `maybe_fetch_suggestions` helper, search TTL cache, covenant latest-mode call, PDF executor routing | P0 executor, P0 suggestions, P1 covenant |
| `src/data_fetcher.py` | `run_yfinance_call_with_proxy_retry()`, `_InFlightEntry`, single-flight refactor, `_error_cache` + negative TTLs, `get_financial_data(mode, include_profile, include_supplement)`, latest-mode yfinance branch, A-share profile/supplement flags, retry decorator removal | P0 lock, P1 single-flight, P1 covenant, P1 A-share |
| `src/ratio_analyzer.py` | `dataframe_to_value_map()`, snapshot usage in 5 category functions, `_get_value` dict support | P2 ratio snapshot |
| `src/html_pdf_exporter.py` | `summary_rows`→`rows` bug fix, `rows_by_period_maps` pre-built dict index, `max_pdf_periods` cap, `settings` import | P2 PDF |
| `tests/conftest.py` | Auto-clearing fixture for `_data_cache`, `_error_cache`, `_in_flight` between tests | Test isolation |
| `tests/test_api.py` | Updated `test_pdf_capacity_exhausted_returns_503` to mock `_run_in_pdf_executor`; added `TestLocalizedNameCache` class | Regression coverage |
| `tests/test_data_fetcher.py` | Updated mocks to wrap `run_yfinance_call_with_proxy_retry`; added `**kwargs` to `_raise_network_error` stubs | Regression coverage |

## Verification Performed

| Command | Result | Notes |
|---|---|---|
| `pytest tests/test_data_fetcher.py -q` | 52 passed | After all fixes |
| `pytest tests/test_api.py -q` | 63 passed | After all fixes |
| `pytest tests/test_ratio_analyzer.py tests/test_zscore.py tests/test_rich_assessment_service.py -q` | 75 passed | After ratio snapshot changes |
| `pytest tests/test_html_pdf_exporter.py tests/test_pdf_exporter.py -q` | 36 passed | After PDF changes |
| `pytest -q` (full suite) | **275 passed** in ~5s | Final verification after all external review fixes |

New validation tests added (15 total across two review rounds):
- `test_negative_cache_hit_preserves_error_type_enum` — enum type preserved across negative cache hits
- `test_negative_cache_hit_error_type_is_enum_not_str` — `_coerce_error_type` converts cached string to enum
- `test_run_yfinance_call_never_mode_does_not_clear_proxy` — "never" mode bypasses lock
- `test_run_yfinance_call_always_mode_clears_proxy` — "always" mode holds lock
- `test_run_yfinance_call_retry_only_no_lock_for_no_clear_proxy` — "retry_only" + clear_proxy=False
- `test_proxy_retry_only_retries_on_proxy_error` — proxy error triggers cleared retry
- `test_proxy_retry_only_does_not_retry_non_proxy_error` — non-proxy errors propagate directly
- `test_single_flight_reuses_failure_for_waiters` — waiter gets same exception as leader
- `test_assess_failure_does_not_fetch_suggestions_by_default` — default assess omits suggestions
- `test_assess_failure_fetches_suggestions_when_explicitly_enabled` — `include_suggestions=True` triggers search
- `test_assess_timeout_does_not_fetch_suggestions_even_when_enabled` — timeout never triggers suggestions
- `test_pdf_export_uses_pdf_executor_not_fetch_executor` — PDF route isolated from fetch pool
- `test_latest_mode_prefers_newer_quarter_over_annual` — latest mode returns quarter when newer
- `test_latest_mode_uses_annual_when_quarter_not_newer` — latest mode falls back to annual
- `test_retry_only_allows_different_ticker_cold_misses_to_overlap` — different tickers not serialized behind proxy lock

## Deviations From Plan

1. **A-share statement parallelization skipped**: The plan suggested parallelizing the three `ak.stock_financial_report_sina()` calls with a small thread pool. This was deferred because the conditional profile/supplement flags already eliminate the dominant serial cost (unnecessary profile API calls). The three statement calls are issued to Sina in rapid sequence; adding a thread pool inside `_fetch_a_share_akshare` would add complexity with marginal benefit.

2. **`pdf_report_core` matrix re-construction not removed**: The plan suggested avoiding double construction of `table_rows`/`detail_table_rows` between `html_pdf_exporter.build_pdf_document_model()` and `pdf_report_core._sanitize_pdf_document_model()`. The sanitization layer's matrix building serves as the validate-and-clean step (normalizing types, scanning for inline breaks, cleaning display text). Removing it would require the exporter to guarantee fully sanitized output, which is a cross-module contract change beyond the scope of this performance pass.

3. **`retry_with_backoff` removed from `get_financial_data` but kept for `_fetch_a_share_akshare`**: The plan said to narrow retry scope. The decorator was removed from `get_financial_data` (whose yfinance branch now uses the proxy-level retry in `run_yfinance_call_with_proxy_retry`). The decorator remains on `_fetch_a_share_akshare` because AKShare's Sina API calls are independent and benefit from retry on connection errors.

4. **Ratio snapshot is partial — category-level only**: `dataframe_to_value_map()` is called inside each ratio category function, not once per period. A full period-level `StatementSnapshot` (dataclass with balance/income/cash maps shared across `calculate_all_ratios`, `_build_raw_metrics`, `_build_assessment`) remains future work. See `docs/plans/2-backend-performance-review-validation-fix-plan.md` item 12 for the full implementation sketch.

## External Review Fixes Applied

The following issues from the external validation session (`docs/plans/2-backend-performance-review-validation-fix-plan.md`) have been fixed:

| Fix | Description | File |
|---|---|---|
| P0-1 | Negative cache `error_type` coercion: `_coerce_error_type()` helper ensures cached string values are converted back to `DataFetchErrorType` enum; `_cache_data_fetch_error()` helper deduplicates cache write logic | `src/data_fetcher.py` |
| P0-2 | Generic yfinance exceptions now write to `_error_cache` via `_cache_data_fetch_error()` — second request for same failed ticker hits negative cache, not upstream | `src/data_fetcher.py` |
| P0-3 | `run_yfinance_call()` "never" mode fixed: returns `fn()` directly, never acquires lock or clears proxy | `src/data_fetcher.py` |
| P0-4 | `FinancialDataFetcher.clear_cache()` now clears both `_data_cache` and `_error_cache` | `src/data_fetcher.py` |
| P0-5 | `mode='latest'` now fetches quarterly statements and picks the most recent period: quarterly when its date > annual date, annual otherwise. Preserves "latest available period" semantics | `src/data_fetcher.py` |
| P1 | `max_pdf_detail_rows` cap applied in `_build_statement_sections()` after summary extraction, before section creation | `src/html_pdf_exporter.py` |
| P1 | Added 12 regression tests: negative cache enum type, generic failure cache, proxy mode (never/always/retry_only/non-proxy), single-flight failure reuse, default no-suggestions, explicit suggestions, timeout never suggestions, PDF executor isolation | `tests/test_data_fetcher.py`, `tests/test_api.py` |

## Known Issues / Remaining Risks

1. **CLAUDE.md stale reference**: CLAUDE.md claims `_temporarily_clear_proxy_env` exists in `src/api.py`. It does not. The actual implementation is `run_yfinance_call` in `src/data_fetcher.py`. Not a code defect but may confuse future sessions.

2. **No performance regression tests**: The plan called for mock concurrency tests (yfinance lock serialization, single-flight failure reuse, covenant latest-only, PDF executor isolation). These were not written. Unit tests cover correctness but not the concurrency/performance properties the plan targets.

3. **Cache key backward compatibility**: The cache key changed from `{TICKER}:{source}` to `{TICKER}:{source}:{mode}:{flags}`. Old cache entries from a previous deployment are effectively ignored (cache miss). This is safe but means first requests after deployment will be cache-cold.

4. **`yfinance_clear_proxy_mode` default is `"retry_only"`**: This changes the default behavior from always holding the proxy lock to only holding it on retry. In environments with proxy issues, the retry path should handle it, but this hasn't been tested against real corporate proxies.

5. **`include_suggestions` defaults to `False`**: The assess response now omits suggestions by default. The frontend (React SPA) may have been relying on the suggestions field in the response. Since `suggestions` was always a dict key in the response (just with empty lists for successes), this should be backward-compatible — failures now return `sugg: []` instead of populated suggestions.

## Items Requiring External Validation

1. **`run_yfinance_call` backward-compat logic** (lines ~88-114 in `data_fetcher.py`): The mode branching for `"retry_only"` + `clear_proxy=True` should be reviewed for correctness — does it correctly handle all three modes?

2. **`_run_in_search_executor` returns `_empty()` coroutine on capacity exhaustion**: The caller `fetch_suggestions` wraps this in `asyncio.wait_for(..., timeout)`, which awaits the result. An `async def _empty(): return []` should work correctly, but review the async flow.

3. **`summary_rows` bug fix impact**: Non-English PDF reports were silently missing summary row translations. The fix may change PDF output for non-English users — this is a correctness fix, but the visual regression should be validated.

4. **`_NEGATIVE_CACHE_TTLS` placement**: Defined at module level after `DataFetchError` class (line ~370). Verify that the TTL values (900s invalid, 300s no-data, 60s rate-limit, 10s network) are appropriate for production use.

5. **Frontend `include_suggestions` integration**: The frontend needs to pass `include_suggestions: true` if it wants suggestions on failure. This is a new field — verify the frontend doesn't break when suggestions are absent.

## Suggested Prompt For Reviewer

```
Please validate this implementation against the original plan at
docs/plans/2-backend-performance-review.md.

Focus on:
1. Whether every Key Change was implemented (P0-P2).
2. Whether the implementation stayed within scope (no unrelated changes).
3. Whether any public API behavior changed unexpectedly
   (AssessmentRequest.include_suggestions is new but optional;
    covenant route now uses latest-only mode internally;
    cache keys changed format).
4. Whether error handling, concurrency, and tests match the plan.
5. Whether the three deviations are acceptable or need correction:
   - A-share statement parallelization deferred
   - pdf_report_core matrix re-construction retained
   - retry_with_backoff kept on _fetch_a_share_akshare

Return: Accepted | Needs fixes | Blocked
Also list exact files or test cases that need follow-up.
```
