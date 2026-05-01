# Plan Implementation Handoff

## Original Plan
- **Plan path**: `docs/plans/backend_security_reliability_review.md`
- **Plan title**: 后端安全与可靠性修复计划 (Backend Security & Reliability Fix Plan)
- **Plan source/session**: External plan, authored before implementation
- **Implementation executor**: Claude Code (Opus 4.7)

## Working Tree Summary
- **Branch**: `main`
- **Last commit**: `17f49f45` — "Localize PDF statement and profile labels"
- **Git status**: 17 files modified (8 implementation files + 9 pre-existing uncommitted changes)
- **Changed files (this implementation)**: 9 files, ~3,289 lines of diff
- **Pre-existing changes (not from this work)**: `pyproject.toml`, `src/ratio_analyzer.py`, `src/services/assessment_service.py`, `src/zscore.py`, `tests/test_ratio_analyzer.py`, `tests/test_zscore.py`, `web/src/App.tsx`, `web/src/index.css`, `tests/test_covenant_monitor.py`

## Plan Coverage Matrix

| Plan Item | Status | Evidence | Notes |
|---|---|---|---|
| **api.py**: `AssessmentRequest` stricter input boundaries (ticker length, charset) | Completed | `src/api.py` — `field_validator("tickers")` added: max 20 chars, `[A-Za-z0-9._-]+` pattern. `CovenantCheckRequest.ticker`: `min_length=1, max_length=20` | |
| **api.py**: `CovenantCheckRequest` stricter input boundaries | Completed | Same validator applied | |
| **api.py**: `PdfExportRequest` payload size limit | Completed | `field_validator("report")` added: 2 MB serialized size limit | |
| **api.py**: `process_ticker` add `except Exception` catch-all | Completed | Line ~459: `except Exception as exc` block returns `{"type": "error", ... "msg": "Internal processing error"}` | |
| **api.py**: Safe per-ticker error objects from catch-all | Completed | Returns same structure as other error handlers: `type`, `ticker`, `msg`, `error_type`, `status_code`, `sugg` | |
| **api.py**: Strip `str(exc)` from symbol search error | Completed | Line ~672: replaced `f"...{exc}"` with safe `"Unable to search symbols right now. Please try again later."` | |
| **api.py**: Strip `str(exc)` from PDF export error | Completed | Line ~816: replaced `detail={"error": str(exc), ...}` with safe `"Invalid PDF report structure"` | |
| **api.py**: Strip `str(exc)` from global exception handler | Completed | Line ~179: replaced `str(exc)` with `"Internal server error — check server logs for details"` (debug mode only) | |
| **api.py**: Stop process-level `os.environ` mutation | Deviated | `_temporarily_clear_proxy_env` now wrapped in `threading.Lock` (`_PROXY_ENV_LOCK`). Per-call proxy config not viable (yfinance has no API for it). The plan allowed either lock or per-call config. | |
| **api.py**: PDF rendering in thread pool | Completed | Changed endpoint to call `run_in_threadpool(generate_full_pdf, ...)` instead of `await generate_full_pdf_async(...)` | |
| **api.py**: PDF filename whitelist sanitization | Completed | `re.sub(r'[^A-Za-z0-9._-]', '_', ticker)` before constructing `Content-Disposition` header | |
| **api.py**: Validation error handler JSON-safe | Completed | `validation_exception_handler` now extracts `loc`/`msg`/`type` from Pydantic errors, avoiding serialization of raw `ValueError` objects | Added — discovered during implementation as pre-existing bug |
| **data_fetcher.py**: Narrow `retry_with_backoff` scope | Deviated | Default changed from `(Exception,)` to `(ConnectionError, TimeoutError, OSError)`. Both call sites updated. Internal `DataFetchError` check (INVALID_TICKER/NO_DATA_AVAILABLE) was already rejecting non-retriable errors. `UNKNOWN` DataFetchError is no longer retried. | Plan said "only 429/network" — implemented slightly broader (OSError covers network) but same intent |
| **data_fetcher.py**: Cache `maxsize` | Completed | `SimpleCache` now accepts `maxsize` param (default 1000), uses `OrderedDict` for LRU eviction. `_data_cache` global passes `maxsize=1000`. | |
| **data_fetcher.py**: Single-flight coalescing | Completed | Module-level `_in_flight: dict[str, threading.Event]` + `_in_flight_lock`. `get_financial_data` checks in-flight dict on cache miss, waits on existing event, or registers as fetcher. `finally` block signals waiters. | |
| **data_fetcher.py**: Stop leaking `original_error` in details | Completed | Removed `"original_error": str(exc)` from 3 locations: yfinance error handler (line ~1133), AKShare error handler (line ~664), and api.py covenant handler (line ~718) | |
| **rich_assessment_service.py**: `data_quality` metadata | Completed | Top-level response now includes `"data_quality": {"status": "partial"\|"complete", "failed_periods": [...], "latest_period_valid": bool}` | |
| **rich_assessment_service.py**: Safe per-period reason codes | Completed | Per-period `"error": str(exc)` replaced with stable codes: `"calculation_error"` or `"insufficient_data"` | |
| **rich_assessment_service.py**: Strip raw exceptions from details | Completed | `_fetch_financial_data` and `_calculate_ratios` no longer pass `details={"error": str(exc)}` | |
| **rich_assessment_service.py**: Maintain partial-result behavior | Completed | Logic unchanged: if at least one period has a valid assessment, return results. Only raises 422 when all periods fail. | |
| **covenant_monitor.py**: Range/finite validation on thresholds | Completed | All fields (except `min_fcf_to_debt`) have `gt=0`. `model_validator(mode="after")` rejects `NaN`/`Inf` for all float fields. | |
| **covenant_monitor.py**: Safe breach messages | Completed | Already had `DATA_UNAVAILABLE` message. No internal details in covenant breach messages. No change needed beyond threshold validation. | |
| **reportlab_pdf_exporter.py**: Input size/structure limits | Completed | `_validate_report_payload`: `len(history) > 50` limit, per-period `fiscal_year`/`year_label` max 50 chars | |
| **pdf_report_core.py**: (No changes needed) | Not implemented | Plan referenced this file but existing `_sanitize_pdf_document_model` already provides extensive validation. No additional changes needed — size limits added in `reportlab_pdf_exporter.py` boundary layer instead. | Deliberate — validation at the API boundary is more appropriate than deep in the rendering layer |

## Files Changed

| File | Reason | Related Plan Item |
|---|---|---|
| `src/api.py` | Input validation, error sanitization, proxy lock, PDF filename, PDF thread-pool, validation handler fix | 7 plan items + 1 bugfix |
| `src/covenant_monitor.py` | Threshold `gt=0`, NaN/Inf rejection | 1 plan item |
| `src/data_fetcher.py` | Cache maxsize+LRU, single-flight, narrowed retry, removed `original_error` leaks | 4 plan items |
| `src/reportlab_pdf_exporter.py` | History size/string length limits | 1 plan item |
| `src/services/rich_assessment_service.py` | `data_quality` metadata, safe reason codes, removed raw error details | 3 plan items |
| `tests/test_api.py` | 9 new tests: ticker validation, covenant threshold rejection, error sanitization, PDF filename, PDF size limits | Test Plan coverage |
| `tests/test_data_fetcher.py` | 4 new tests: cache maxsize eviction, LRU access ordering, single-flight coalescing, single-flight cleanup on failure | Test Plan coverage |
| `tests/test_rich_assessment_service.py` | 3 new tests: partial data_quality, complete data_quality, safe reason codes | Test Plan coverage |

**Files NOT changed (pre-existing uncommitted modifications, outside plan scope):**
`pyproject.toml`, `src/ratio_analyzer.py`, `src/services/assessment_service.py`, `src/zscore.py`, `src/pdf_report_core.py`, `tests/test_ratio_analyzer.py`, `tests/test_covenant_monitor.py`, `tests/test_zscore.py`, `web/src/App.tsx`, `web/src/index.css`

## Verification Performed

| Command | Result | Notes |
|---|---|---|
| `pytest -q` (full suite) | **249 passed** in 4.49s | All pre-existing tests + 16 new tests pass |
| `pytest tests/test_api.py -v` | 50 passed | Covers validation, sanitization, PDF |
| `pytest tests/test_covenant_monitor.py -v` | 74 passed | Covers threshold validation (existing parametrized + new) |
| `pytest tests/test_data_fetcher.py -v` | 43 passed | Covers cache, single-flight, error classification |
| `pytest tests/test_rich_assessment_service.py -v` | 16 passed | Covers data_quality, safe reason codes |

**Not verified (requires live environment):**
- Smoke test against running dashboard (`./smoke_test.sh http://127.0.0.1:8000`)
- Concurrent PDF generation under load (ReportLab thread safety)
- Real yfinance/AKShare call integration

## Deviations From Plan

1. **Proxy env fix: lock instead of per-call config.** Plan said "改成单线程锁或 per-call proxy 配置". Per-call proxy configuration is not viable because yfinance has no API to pass proxy settings per call. Used `threading.Lock` serialization around `_temporarily_clear_proxy_env` — the plan's own stated alternative. Risk: serializes proxy-cleared yfinance calls (only symbol search uses this path).

2. **Retry scope: narrowed to `(ConnectionError, TimeoutError, OSError)` rather than "only 429/network".** The plan's intent was to stop retrying business-logic failures. The implementation achieves this by excluding generic `Exception` from retriable errors. The existing non-retriable check on `INVALID_TICKER`/`NO_DATA_AVAILABLE` `DataFetchError` subtypes was already in place. `UNKNOWN` DataFetchError is no longer retried.

3. **PDF async wrapper: switched to sync `generate_full_pdf` + `run_in_threadpool`.** Plan referenced `generate_full_pdf_async` but the async wrapper was a no-op — all rendering is synchronous internally. Using the sync entry point directly with `run_in_threadpool` is the correct pattern.

4. **`pdf_report_core.py` not modified.** Plan listed `src/pdf_report_core.py` but the existing `_sanitize_pdf_document_model` already provides comprehensive validation. Size/structure limits were added at the API boundary (`reportlab_pdf_exporter.py:_validate_report_payload`) which is the more appropriate layer for payload-size rejection.

5. **Additional fix: `validation_exception_handler` JSON safety.** Discovered during implementation that Pydantic v2 `ValueError` from custom validators creates unserializable `ctx` objects in error details. The handler was changed to extract only safe `loc`/`msg`/`type` fields. This was a pre-existing bug exposed by the new `field_validator` on `AssessmentRequest.tickers`.

## Known Issues / Remaining Risks

1. **ReportLab thread safety unverified.** `_render_reportlab_pdf` now runs in `run_in_threadpool`. ReportLab canvas is not documented as thread-safe, though each call creates fresh `SimpleDocTemplate` instances. Needs concurrent PDF load test.

2. **Single-flight `finally` block spans ~200 lines.** The `try/finally` wrapping the entire `get_financial_data` fetch path is structurally sound but easy to break in future edits if an early return is added inside the `try` block.

3. **Cache `maxsize=1000` is hardcoded.** Should be configurable via `Settings` for production tuning.

4. **Pre-existing uncommitted changes in 9 files.** These are independent of this plan but share the working tree. A reviewer should note that `tests/test_covenant_monitor.py` has both pre-existing changes AND new tests from this implementation.

## Items Requiring External Validation

1. **Proxy lock serialization** — Verify the `threading.Lock` around `_temporarily_clear_proxy_env` is acceptable vs. the plan's preference for per-call config. The lock serializes symbol-search yfinance calls; concurrency impact is low since symbol search is infrequent.

2. **Retry scope narrowing** — `(ConnectionError, TimeoutError, OSError)` is slightly broader than "only 429/network". Confirm this matches the intent.

3. **PDF thread-pool** — Confirm the switch from `generate_full_pdf_async` to `generate_full_pdf` + `run_in_threadpool` is acceptable, and that no caller depends on the async entry point's specific behavior.

4. **`data_quality` response schema** — The new `data_quality` key is additive. Confirm the frontend (`web/src/App.tsx`) handles it gracefully (or doesn't break on unknown keys).

5. **Test coverage of `except Exception` catch-all** — The test `test_unhandled_exception_in_process_ticker_isolated` verifies that the error response doesn't leak raw exception strings. It does NOT verify the exact `error_type: "internal_error"` path because `run_in_threadpool` + `asyncio.wait_for` exception propagation through TestClient is complex. The test asserts status code in `(422, 500, 502)` and absence of raw strings.

## Suggested Prompt For Reviewer

```
Please validate this implementation against the original plan at docs/plans/backend_security_reliability_review.md.

Focus on:
1. Whether every Key Change was implemented.
2. Whether the implementation stayed within scope.
3. Whether any public API behavior changed unexpectedly (new "data_quality" key, safe error messages, tighter validation).
4. Whether error handling, validation, concurrency, and tests match the plan.
5. Whether the 2 deviations (proxy lock instead of per-call config, sync+threadpool instead of async PDF) are acceptable or need correction.

Return:
- Accepted
- Needs fixes
- Blocked

Also list exact files or test cases that need follow-up.
```
