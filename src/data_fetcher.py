"""
Data Fetcher Module
====================
Extracts financial data using yfinance (and optionally akshare).

Produces DataFrames with metric names as the **index** and a single
value column — the format expected by RatioAnalyzer._get_value().
"""

from __future__ import annotations

import pandas as pd
import numpy as np
import yfinance as yf
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Any
from collections.abc import Callable
from enum import Enum
from functools import wraps

from src.config import settings

logger = logging.getLogger(__name__)


# ── Proxy-Safe yfinance Call Wrapper ──────────────────────────────────────

import os as _os

_PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)

_PROXY_ENV_ERROR_TOKENS = (
    "proxy",
    "curl",
    "ProxyError",
    "SSLError",
    "ssl",
    "CONNECT",
    "tunnel",
)

_PROXY_CLEAR_LOCK = threading.Lock()


def _clear_proxy_env():
    """Remove proxy env vars and return a backup dict for restoration."""
    backup = {k: _os.environ.get(k) for k in _PROXY_ENV_KEYS}
    for k in _PROXY_ENV_KEYS:
        _os.environ.pop(k, None)
    return backup


def _restore_proxy_env(backup):
    """Restore proxy env vars from a backup dict."""
    for k, v in backup.items():
        if v is None:
            _os.environ.pop(k, None)
        else:
            _os.environ[k] = v


def _is_proxy_related_error(exc: Exception) -> bool:
    """Return True if the exception suggests a proxy or TLS/curl problem."""
    msg = str(exc).lower()
    return any(token.lower() in msg for token in _PROXY_ENV_ERROR_TOKENS)


def _run_with_cleared_proxy(fn):
    """Execute *fn* with proxy env vars temporarily removed, holding the lock."""
    with _PROXY_CLEAR_LOCK:
        backup = _clear_proxy_env()
        try:
            return fn()
        finally:
            _restore_proxy_env(backup)


def _run_with_proxy_lock(fn):
    """Execute *fn* while holding the proxy lock, without clearing the environment.

    This ensures mutual exclusion with any concurrent ``_run_with_cleared_proxy``
    call so that no thread observes an inconsistent ``os.environ`` state.
    """
    with _PROXY_CLEAR_LOCK:
        return fn()


def run_yfinance_call(fn, *, clear_proxy: bool = True):
    """Execute a yfinance call under the proxy-safety lock.

    All yfinance network operations (Ticker, Search, info, statement lookups)
    MUST go through this wrapper so that no concurrent thread sees an
    inconsistent os.environ state.

    When *clear_proxy* is True the proxy env vars are temporarily removed
    for the duration of the call (the default for all primary fetches).
    When False the call runs with the current environment untouched but
    still holds the lock, preventing races with a concurrent clear-proxy
    call.
    """
    mode = settings.yfinance_clear_proxy_mode

    if mode == "never":
        return fn()

    if mode == "always":
        return _run_with_cleared_proxy(fn) if clear_proxy else _run_with_proxy_lock(fn)

    if clear_proxy:
        return _run_with_cleared_proxy(fn)
    return _run_with_proxy_lock(fn)


def run_yfinance_call_with_proxy_retry(fn):
    """Execute *fn* under the proxy lock; retry with cleared proxy on proxy error.

    In 'retry_only' mode (the default), the first attempt holds
    ``_PROXY_CLEAR_LOCK`` without clearing the environment so that no
    concurrent thread sees an inconsistent ``os.environ`` during a
    clear-proxy retry.  If the first attempt fails with a proxy-looking
    error, the retry clears proxy vars inside the same lock.
    """
    mode = settings.yfinance_clear_proxy_mode

    if mode == "always":
        return _run_with_cleared_proxy(fn)
    if mode == "never":
        return fn()

    try:
        return _run_with_proxy_lock(fn)
    except Exception as exc:
        if _is_proxy_related_error(exc):
            logger.debug("Proxy-related error on first attempt, retrying with cleared proxy: %s", exc)
            return _run_with_cleared_proxy(fn)
        raise


# ── Simple In-Memory Cache with TTL ──────────────────────────────────────────

class SimpleCache:
    """Thread-safe in-memory cache with TTL and LRU eviction."""

    def __init__(self, default_ttl: int = 600, maxsize: int = 1000):
        """Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 600 = 10 minutes)
            maxsize: Maximum number of entries (LRU eviction when exceeded)
        """
        from collections import OrderedDict
        self._cache: OrderedDict[str, tuple[Any, datetime]] = OrderedDict()
        self._default_ttl = default_ttl
        self._maxsize = max(1, maxsize)  # never allow zero-size cache
        self._hits = 0
        self._misses = 0
        self._lock = threading.RLock()

    def get(self, key: str) -> Any | None:
        """Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value if exists and not expired, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, expiry = self._cache[key]
            if datetime.now() > expiry:
                del self._cache[key]
                self._misses += 1
                return None

            # LRU: move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl if ttl is not None else self._default_ttl
        expiry = datetime.now() + timedelta(seconds=ttl)
        with self._lock:
            # LRU eviction: remove oldest entries if at capacity
            while len(self._cache) >= self._maxsize:
                self._cache.popitem(last=False)
            self._cache[key] = (value, expiry)
            self._cache.move_to_end(key)

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dict with hits, misses, size, and hit_rate
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._cache),
                "hit_rate": round(hit_rate, 2)
            }


# Global cache instance
_data_cache = SimpleCache(default_ttl=settings.cache_ttl_seconds, maxsize=settings.data_cache_maxsize)

# Single-flight coalescing: prevents concurrent cache misses for the same key
class _InFlightEntry:
    """Holds state for a single-flight upstream request.

    The leader thread populates result or exception after the upstream call
    completes; waiter threads block on *event* then read the outcome.
    """
    __slots__ = ("event", "result", "exception")

    def __init__(self):
        self.event = threading.Event()
        self.result: Any | None = None
        self.exception: BaseException | None = None


_in_flight: dict[str, _InFlightEntry] = {}
_in_flight_lock = threading.Lock()

# Negative cache: caches failures to avoid repeated upstream requests.
_error_cache = SimpleCache(
    default_ttl=settings.negative_cache_ttl_seconds,
    maxsize=max(200, settings.data_cache_maxsize // 2),
)


# ── Ticker Normalization ─────────────────────────────────────────────────────

def _normalize_ticker(ticker: str) -> str:
    """Normalize ticker format for better compatibility.

    Handles special cases:
    - BRK.B → BRK-B (Berkshire Hathaway Class B)
    - BF.B → BF-B (Brown-Forman Class B)
    - Removes extra whitespace
    - Converts to uppercase

    Args:
        ticker: Raw ticker string

    Returns:
        Normalized ticker string
    """
    ticker = ticker.strip().upper()

    # Special handling for Class B shares with dot notation
    # yfinance uses hyphen (-) not dot (.) for share classes
    if ticker.endswith('.B'):
        ticker = ticker[:-2] + '-B'
        logger.debug(f"Normalized Class B ticker: {ticker}")
    elif ticker.endswith('.A'):
        ticker = ticker[:-2] + '-A'
        logger.debug(f"Normalized Class A ticker: {ticker}")

    return ticker


# ── Retry Mechanism with Exponential Backoff ────────────────────────────────

def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 10.0,
    retriable_errors: tuple = (ConnectionError, TimeoutError, OSError)
):
    """Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        backoff_factor: Multiplier for delay after each retry (default: 2.0)
        max_delay: Maximum delay between retries in seconds (default: 10.0)
        retriable_errors: Tuple of exception types to retry on

    Returns:
        Decorated function that retries on failure
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retriable_errors as e:
                    last_exception = e

                    # Don't retry on invalid ticker or no data errors
                    if isinstance(e, DataFetchError):
                        if e.error_type in (DataFetchErrorType.INVALID_TICKER,
                                           DataFetchErrorType.NO_DATA_AVAILABLE):
                            logger.debug(f"Non-retriable error for {func.__name__}: {e.error_type.value}")
                            raise

                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        logger.error(f"All {max_retries} retries exhausted for {func.__name__}")
                        raise

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


# ── Custom Exceptions ────────────────────────────────────────────────────────

class DataFetchErrorType(Enum):
    """Types of data fetching errors."""
    INVALID_TICKER = "invalid_ticker"
    NO_DATA_AVAILABLE = "no_data_available"
    RATE_LIMIT = "rate_limit"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


class DataFetchError(Exception):
    """Custom exception for data fetching errors with detailed error types."""

    def __init__(self, message: str, error_type: DataFetchErrorType, ticker: str = None, details: dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.ticker = ticker
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.message,
            "error_type": self.error_type.value,
            "ticker": self.ticker,
            "details": self.details
        }


_NEGATIVE_CACHE_TTLS: dict[str, int] = {
    DataFetchErrorType.INVALID_TICKER.value: 900,
    DataFetchErrorType.NO_DATA_AVAILABLE.value: 300,
    DataFetchErrorType.RATE_LIMIT.value: 60,
    DataFetchErrorType.NETWORK_ERROR.value: 10,
}


def _coerce_error_type(value: Any) -> DataFetchErrorType:
    """Convert a cached error_type value back to a DataFetchErrorType enum."""
    if isinstance(value, DataFetchErrorType):
        return value
    if isinstance(value, str):
        try:
            return DataFetchErrorType(value)
        except ValueError:
            return DataFetchErrorType.UNKNOWN
    return DataFetchErrorType.UNKNOWN


def _cache_data_fetch_error(cache_key: str, exc: DataFetchError) -> None:
    """Cache a DataFetchError in _error_cache with type-specific TTL."""
    ttl = _NEGATIVE_CACHE_TTLS.get(exc.error_type.value, settings.negative_cache_ttl_seconds)
    _error_cache.set(
        cache_key,
        {
            "message": exc.message,
            "error_type": exc.error_type.value,
            "ticker": exc.ticker,
            "details": exc.details,
        },
        ttl=ttl,
    )


# Optional AKShare integration (akshare_data.py is a legacy module)
try:
    from src.akshare_data import get_financial_data as akshare_get_data
except ImportError:
    akshare_get_data = None


# ── Column name mapping ──────────────────────────────────────────────────────

_YFINANCE_MAP = {
    # ── Balance Sheet ────────────────────────────────────────────────────
    'Total Assets': 'total_assets',
    'TotalAssets': 'total_assets',

    'Total Liabilities Net Minority Interest': 'total_liabilities',
    'Total Liabilities': 'total_liabilities',
    'TotalLiabilitiesNetMinorityInterest': 'total_liabilities',

    # Equity — yfinance uses 'Stockholders Equity' (plural, no "Total")
    'Stockholders Equity': 'total_equity',
    'StockholdersEquity': 'total_equity',
    'Total Stockholder Equity': 'total_equity',
    'Common Stock Equity': 'total_equity',
    'CommonStockEquity': 'total_equity',
    'Total Equity Gross Minority Interest': 'total_equity',

    'Common Stock': 'common_stock',
    'CommonStock': 'common_stock',
    'Capital Stock': 'common_stock',
    'Retained Earnings': 'retained_earnings',
    'RetainedEarnings': 'retained_earnings',

    # Cash
    'Cash And Cash Equivalents': 'cash',
    'CashAndCashEquivalents': 'cash',
    'Cash Cash Equivalents And Short Term Investments': 'cash',
    'CashCashEquivalentsAndShortTermInvestments': 'cash',
    'Cash Financial': 'cash',
    'Cash': 'cash',
    'Other Short Term Investments': 'short_term_investments',
    'OtherShortTermInvestments': 'short_term_investments',

    # Receivables / Inventory
    'Accounts Receivable': 'accounts_receivable',
    'AccountsReceivable': 'accounts_receivable',
    'Receivables': 'accounts_receivable',
    'Inventory': 'inventory',

    # Current Assets / Liabilities — yfinance uses 'Current Assets' not 'Total Current Assets'
    'Current Assets': 'total_current_assets',
    'CurrentAssets': 'total_current_assets',
    'Total Current Assets': 'total_current_assets',

    'Current Liabilities': 'total_current_liabilities',
    'CurrentLiabilities': 'total_current_liabilities',
    'Total Current Liabilities': 'total_current_liabilities',

    # PP&E
    'Net PPE': 'property_plant_equipment',
    'NetPPE': 'property_plant_equipment',
    'Property Plant Equipment': 'property_plant_equipment',
    'Goodwill': 'goodwill',
    'GoodwillAndOtherIntangibleAssets': 'intangible_assets',
    'Intangible Assets': 'intangible_assets',

    # Payables
    'Accounts Payable': 'accounts_payable',
    'AccountsPayable': 'accounts_payable',

    # Debt
    'Current Debt': 'short_term_debt',
    'CurrentDebt': 'short_term_debt',
    'Short Term Debt': 'short_term_debt',
    'Commercial Paper': 'short_term_debt',
    'Long Term Debt': 'long_term_debt',
    'LongTermDebt': 'long_term_debt',
    'Total Debt': 'total_debt',
    'TotalDebt': 'total_debt',

    # ── Income Statement ─────────────────────────────────────────────────
    'Total Revenue': 'revenue',
    'TotalRevenue': 'revenue',
    'Revenue': 'revenue',
    'Cost Of Revenue': 'cost_of_revenue',
    'CostOfRevenue': 'cost_of_revenue',
    'Gross Profit': 'gross_profit',
    'GrossProfit': 'gross_profit',
    'Operating Income': 'operating_income',
    'OperatingIncome': 'operating_income',
    'Net Income': 'net_income',
    'NetIncome': 'net_income',
    'Interest Expense': 'interest_expense',
    'InterestExpense': 'interest_expense',
    'Pretax Income': 'income_before_tax',
    'PretaxIncome': 'income_before_tax',
    'Income Before Tax': 'income_before_tax',
    'Tax Provision': 'income_tax_expense',
    'TaxProvision': 'income_tax_expense',
    'Income Tax Expense': 'income_tax_expense',
    'EBITDA': 'ebitda',

    # ── Cash Flow Statement ──────────────────────────────────────────────
    'Operating Cash Flow': 'operating_cf',
    'OperatingCashFlow': 'operating_cf',
    'Free Cash Flow': 'free_cf',
    'FreeCashFlow': 'free_cf',
    'Capital Expenditure': 'capital_expenditures',
    'CapitalExpenditure': 'capital_expenditures',
    'Capital Expenditures': 'capital_expenditures',
    'Change In Cash': 'net_change_in_cash',
    'ChangeInCash': 'net_change_in_cash',
    'Net Change In Cash': 'net_change_in_cash',
}



def _standardize_name(name: str) -> str:
    """Map a yfinance metric name to the snake_case key used by RatioAnalyzer."""
    if name in _YFINANCE_MAP:
        return _YFINANCE_MAP[name]
    # Fallback: convert CamelCase / Title Case to snake_case
    return name.lower().replace(' ', '_').replace('&', 'and')


def _extract_single_column(df: pd.DataFrame | None, col_idx: int) -> pd.DataFrame:
    """Extract a single column (period) from a yfinance statement DataFrame and
    standardize the index. Format: index = metric names, single 'Value' column."""
    if df is None or df.empty or col_idx >= len(df.columns):
        return pd.DataFrame()

    target_col = df.iloc[:, col_idx]

    # Build a new Series with standardized index names
    records: dict[str, float] = {}
    for raw_name, value in target_col.items():
        key = _standardize_name(str(raw_name))
        if key in records:
            continue  # first valid value wins
        try:
            val = float(value)
            if not np.isnan(val):
                records[key] = val
        except (TypeError, ValueError):
            continue

    result = pd.DataFrame.from_dict(records, orient='index', columns=['Value'])
    return result


# ── AKShare Sina Finance mapping (Chinese → standardized English) ──────────

_SINA_INCOME_MAP = {
    '营业总收入': 'revenue',
    '营业收入': 'revenue',
    '营业成本': 'cost_of_revenue',
    '营业利润': 'operating_income',
    '利润总额': 'income_before_tax',
    '净利润': 'net_income',
    '归属于母公司所有者的净利润': 'net_income',
    '财务费用': 'interest_expense',
    '利息费用': 'interest_expense',
    '销售费用': 'selling_expense',
    '管理费用': 'admin_expense',
    '研发费用': 'research_development',
    '营业税金及附加': 'taxes_and_surcharges',
    '资产减值损失': 'asset_impairment_loss',
    '信用减值损失': 'credit_impairment_loss',
    '投资收益': 'investment_income',
    '公允价值变动收益': 'fair_value_change',
    '营业总成本': 'total_operating_cost',
}

_SINA_BALANCE_MAP = {
    '资产总计': 'total_assets',
    '负债合计': 'total_liabilities',
    '所有者权益(或股东权益)合计': 'total_equity',
    '归属于母公司股东权益合计': 'total_equity',
    '流动资产合计': 'total_current_assets',
    '流动负债合计': 'total_current_liabilities',
    '货币资金': 'cash',
    '应收账款': 'accounts_receivable',
    '存货': 'inventory',
    '短期借款': 'short_term_debt',
    '长期借款': 'long_term_debt',
    '应付债券': 'bonds_payable',
    '一年内到期的非流动负债': 'current_portion_lt_debt',
    '未分配利润': 'retained_earnings',
    '应付账款': 'accounts_payable',
    '非流动负债合计': 'non_current_liabilities',
    '固定资产净额': 'property_plant_equipment',
    '无形资产': 'intangible_assets',
    '商誉': 'goodwill',
}

_SINA_CASHFLOW_MAP = {
    '经营活动产生的现金流量净额': 'operating_cf',
    '投资活动产生的现金流量净额': 'investing_cf',
    '筹资活动产生的现金流量净额': 'financing_cf',
    '购建固定资产、无形资产和其他长期资产所支付的现金': 'capital_expenditures',
    '现金及现金等价物净增加额': 'net_change_in_cash',
    '固定资产折旧、油气资产折耗、生产性生物资产折旧': 'depreciation',
    '无形资产摊销': 'amortization',
    '期末现金及现金等价物余额': 'cash_end',
}


def _akshare_row_to_df(row: pd.Series, field_map: dict) -> pd.DataFrame:
    """Convert a single AKShare row to our standard DataFrame format (index=metric name, col='Value')."""
    records = {}
    for cn_name, en_name in field_map.items():
        val = row.get(cn_name)
        if val is not None and str(val) not in ('nan', 'NaN', '', 'None'):
            try:
                fval = float(val)
                if not np.isnan(fval):
                    if en_name not in records:
                        records[en_name] = fval
            except (TypeError, ValueError):
                continue

    # Compute derived fields
    _debt_keys = ('short_term_debt', 'long_term_debt', 'current_portion_lt_debt', 'bonds_payable')
    if any(k in records for k in _debt_keys):
        st = records.get('short_term_debt', 0)
        lt = records.get('long_term_debt', 0)
        cp = records.get('current_portion_lt_debt', 0)
        bp = records.get('bonds_payable', 0)
        records['total_debt'] = st + lt + cp + bp

    if 'operating_cf' in records and 'capital_expenditures' in records:
        records['free_cf'] = records['operating_cf'] - abs(records['capital_expenditures'])

    # Note: EBITDA derivation is done after both income+cash DFs are built
    # (see _fetch_a_share_akshare post-processing)

    if not records:
        # Log which Chinese field names were NOT matched
        if field_map:
            all_row_keys = {str(k) for k in row.index} if hasattr(row, 'index') else set()
            mapped_cn_keys = set(field_map.keys())
            unmatched = all_row_keys - mapped_cn_keys
            if unmatched and len(unmatched) < 50:  # avoid logging noise
                logger.debug(f"AKShare unmapped fields: {unmatched}")
        return pd.DataFrame()
    return pd.DataFrame.from_dict(records, orient='index', columns=['Value'])


def _normalize_profile_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "--", "-"}:
        return None
    return text


def _normalize_profile_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _build_company_profile_from_yfinance_info(info: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(info, dict):
        return {}
    return {
        "description": _normalize_profile_text(info.get("longBusinessSummary") or info.get("description")),
        "sector": _normalize_profile_text(info.get("sectorDisp") or info.get("sector")),
        "industry": _normalize_profile_text(info.get("industryDisp") or info.get("industry")),
        "website": _normalize_profile_text(info.get("website")),
        "country": _normalize_profile_text(info.get("country")),
        "employees": _normalize_profile_int(info.get("fullTimeEmployees")),
        "products": [],
    }


def _merge_company_profiles(primary: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    merged = dict(primary or {})
    fb = fallback or {}
    for key in ("description", "sector", "industry", "website", "country", "employees"):
        if not merged.get(key) and fb.get(key):
            merged[key] = fb[key]
    primary_products = merged.get("products") if isinstance(merged.get("products"), list) else []
    fallback_products = fb.get("products") if isinstance(fb.get("products"), list) else []
    combined = []
    seen = set()
    for value in primary_products + fallback_products:
        cleaned = _normalize_profile_text(value)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            combined.append(cleaned)
    merged["products"] = combined
    return merged


@retry_with_backoff(
    max_retries=2,
    initial_delay=1.5,
    backoff_factor=2.0,
    retriable_errors=(DataFetchError, ConnectionError, TimeoutError, OSError)
)
def _fetch_a_share_akshare(ticker: str, *, include_profile: bool = True, include_supplement: bool = True) -> dict[str, Any] | None:
    """Fetch A-share data from AKShare's Sina Finance API.

    Parameters:
        include_profile:  Fetch company info, profile, and product mix from AKShare.
        include_supplement:  Fetch yfinance supplement for market cap / EBITDA.

    Returns the same dict format as the yfinance path:
        { ticker, company_name, market_cap, company_profile, history: [...] }
    """
    try:
        import akshare as ak
    except ImportError:
        return None

    try:
        # Fetch all 3 statements
        logger.info(f"Fetching AKShare data for {ticker}")
        company_name = ticker
        company_profile: dict[str, Any] = {
            "description": None,
            "sector": None,
            "industry": None,
            "website": None,
            "country": "China",
            "employees": None,
            "products": [],
        }

        # Get company info first
        try:
            stock_info = ak.stock_individual_info_em(symbol=ticker) if include_profile else None
            if stock_info is not None and not stock_info.empty:
                stock_info_map: dict[str, Any] = {}
                if {'item', 'value'}.issubset(set(stock_info.columns)):
                    for _, row in stock_info.iterrows():
                        key = str(row.get('item', '')).strip()
                        if key:
                            stock_info_map[key] = row.get('value')

                for col in ['股票简称', '公司名称', '名称', 'name']:
                    if col in stock_info_map and _normalize_profile_text(stock_info_map[col]):
                        company_name = _normalize_profile_text(stock_info_map[col]) or company_name
                        break
                for col in ['行业', '所属行业', '证监会行业', '申万行业']:
                    if col in stock_info_map and _normalize_profile_text(stock_info_map[col]):
                        company_profile["industry"] = _normalize_profile_text(stock_info_map[col])
                        if not company_profile["sector"]:
                            company_profile["sector"] = company_profile["industry"]
                        break
                for col in ['网址', '公司网站', '官方网站']:
                    if col in stock_info_map and _normalize_profile_text(stock_info_map[col]):
                        company_profile["website"] = _normalize_profile_text(stock_info_map[col])
                        break
                for col in ['员工人数', '员工总数', '在职员工人数']:
                    if col in stock_info_map and _normalize_profile_int(stock_info_map[col]) is not None:
                        company_profile["employees"] = _normalize_profile_int(stock_info_map[col])
                        break
                for col in ['公司简介', '主营业务', '经营范围', '公司业务']:
                    if col in stock_info_map and _normalize_profile_text(stock_info_map[col]):
                        company_profile["description"] = _normalize_profile_text(stock_info_map[col])
                        break
        except Exception as e:
            logger.warning(f"AKShare individual info error for {ticker}: {e}")

        try:
            profile_df = ak.stock_profile_cninfo(symbol=ticker) if include_profile else None
            if profile_df is not None and not profile_df.empty:
                row_dict = profile_df.iloc[0].to_dict()
                for key, value in row_dict.items():
                    key_text = str(key)
                    normalized_value = _normalize_profile_text(value)
                    if normalized_value is None:
                        continue
                    if company_profile["description"] is None and any(token in key_text for token in ("主营", "业务", "简介", "经营范围")):
                        company_profile["description"] = normalized_value
                    elif company_profile["website"] is None and any(token in key_text for token in ("网址", "网站", "homepage", "website")):
                        company_profile["website"] = normalized_value
                    elif company_profile["industry"] is None and any(token in key_text for token in ("行业", "industry")):
                        company_profile["industry"] = normalized_value
                        if not company_profile["sector"]:
                            company_profile["sector"] = normalized_value
                    elif company_profile["country"] is None and any(token in key_text for token in ("国家", "地区", "country")):
                        company_profile["country"] = normalized_value
                    elif company_profile["employees"] is None and any(token in key_text for token in ("员工", "雇员", "employees")):
                        parsed_emp = _normalize_profile_int(normalized_value)
                        if parsed_emp is not None:
                            company_profile["employees"] = parsed_emp
        except Exception as e:
            logger.debug(f"AKShare profile fetch error for {ticker}: {e}")

        try:
            market_prefix = 'SH' if ticker.startswith('6') else 'SZ'
            zygc_symbol = f"{market_prefix}{ticker}"
            zygc_df = ak.stock_zygc_em(symbol=zygc_symbol) if include_profile else None
            if zygc_df is not None and not zygc_df.empty:
                data_df = zygc_df
                if '分类方向' in data_df.columns:
                    product_rows = data_df[data_df['分类方向'].astype(str).str.contains('产品', na=False)]
                    if not product_rows.empty:
                        data_df = product_rows
                name_col = next(
                    (col for col in ['主营构成', '分类名称', '分类类型', '产品名称', '项目名称', '业务名称'] if col in data_df.columns),
                    None
                )
                if name_col is not None:
                    products: list[str] = []
                    seen_products = set()
                    for raw_value in data_df[name_col].tolist():
                        cleaned = _normalize_profile_text(raw_value)
                        if cleaned and cleaned not in seen_products:
                            seen_products.add(cleaned)
                            products.append(cleaned)
                        if len(products) >= 8:
                            break
                    company_profile["products"] = products
        except Exception as e:
            logger.debug(f"AKShare product mix fetch error for {ticker}: {e}")

        inc_df = ak.stock_financial_report_sina(stock=ticker, symbol='利润表')
        bal_df = ak.stock_financial_report_sina(stock=ticker, symbol='资产负债表')
        cf_df = ak.stock_financial_report_sina(stock=ticker, symbol='现金流量表')
        logger.debug(f"AKShare {ticker} statement sizes: income={len(inc_df) if inc_df is not None else 0}, balance={len(bal_df) if bal_df is not None else 0}, cashflow={len(cf_df) if cf_df is not None else 0}")
    except DataFetchError:
        raise
    except Exception as e:
        logger.error(f"AKShare Sina API error for {ticker}: {e}")
        raise DataFetchError(
            f"AKShare statement fetch failed for '{ticker}': {e}",
            error_type=DataFetchErrorType.NETWORK_ERROR,
            ticker=ticker,
            details={"source": "akshare"},
        ) from e

    if inc_df is None or inc_df.empty:
        logger.warning(f"AKShare income statement is empty for {ticker}")
        return None

    # Company name fetch attempted above; market cap fetched from yfinance at the end

    # Build date index: each row in inc_df is a report period (sorted newest first)
    dates_inc = inc_df['报告日'].tolist()
    dates_bal = bal_df['报告日'].tolist() if bal_df is not None and not bal_df.empty else []
    dates_cf = cf_df['报告日'].tolist() if cf_df is not None and not cf_df.empty else []

    # Normalize date strings (handles "YYYY-12-31" and "YYYYMMDD")
    import re as _re
    def _date_digits(date_val: Any) -> str:
        return _re.sub(r'\D', '', str(date_val))

    # Identify annual vs quarterly: annual = ends with 1231
    annual_dates = sorted(
        [d for d in dates_inc if _date_digits(d).endswith('1231')],
        key=_date_digits, reverse=True,
    )
    quarterly_dates_raw = sorted(
        [d for d in dates_inc if not _date_digits(d).endswith('1231')],
        key=_date_digits, reverse=True,
    )

    # Take latest 3 annual
    annual_dates = annual_dates[:3]
    latest_annual_year = int(_date_digits(annual_dates[0])[:4]) if annual_dates else 0

    def _year_quarter(date_val: Any) -> tuple[int, int] | None:
        ds = _date_digits(date_val)
        if len(ds) < 6:
            return None
        year = int(ds[:4])
        month = int(ds[4:6])
        quarter = (month - 1) // 3 + 1
        return year, quarter

    # Keep quarters newer than the latest annual FY, plus the prior-year same quarter
    # for the latest quarter to support YoY quarter comparisons (e.g., 25Q3 vs 24Q3).
    latest_quarter_meta = _year_quarter(quarterly_dates_raw[0]) if quarterly_dates_raw else None
    prior_year_same_quarter = None
    latest_quarter_is_displayed = (
        latest_quarter_meta is not None
        and (latest_annual_year == 0 or latest_quarter_meta[0] > latest_annual_year)
    )
    if latest_quarter_is_displayed:
        prior_year_same_quarter = (latest_quarter_meta[0] - 1, latest_quarter_meta[1])

    quarterly_dates: list[Any] = []
    seen_quarters: set[tuple[int, int]] = set()
    for d in quarterly_dates_raw:
        yq = _year_quarter(d)
        if yq is None:
            continue
        quarter_year = yq[0]
        keep = latest_annual_year == 0 or quarter_year > latest_annual_year
        if prior_year_same_quarter is not None and yq == prior_year_same_quarter:
            keep = True
        if keep and yq not in seen_quarters:
            quarterly_dates.append(d)
            seen_quarters.add(yq)

    def _find_row(df, date_val):
        """Find the row matching a report date, normalising date formats."""
        if df is None or df.empty or '报告日' not in df.columns:
            return None
        target_digits = _date_digits(date_val)
        matches = df[df['报告日'].map(_date_digits) == target_digits]
        return matches.iloc[0] if len(matches) > 0 else None

    history = []

    # Quarterly entries (newest first)
    for d in quarterly_dates:
        ds = _date_digits(d)
        if len(ds) < 6:
            continue
        m = int(ds[4:6])
        q = (m - 1) // 3 + 1
        year_label = f"Q{q} '{ds[2:4]} (U)"

        inc_row = _find_row(inc_df, d)
        bal_row = _find_row(bal_df, d)
        cf_row = _find_row(cf_df, d)

        history.append({
            'year_label': year_label,
            'is_quarterly': True,
            'income': _akshare_row_to_df(inc_row, _SINA_INCOME_MAP) if inc_row is not None else pd.DataFrame(),
            'balance': _akshare_row_to_df(bal_row, _SINA_BALANCE_MAP) if bal_row is not None else pd.DataFrame(),
            'cash': _akshare_row_to_df(cf_row, _SINA_CASHFLOW_MAP) if cf_row is not None else pd.DataFrame(),
        })

    # Annual entries (newest first)
    for d in annual_dates:
        ds = _date_digits(d)
        if len(ds) < 4:
            continue
        year_label = f"FY{ds[2:4]}"

        inc_row = _find_row(inc_df, d)
        bal_row = _find_row(bal_df, d)
        cf_row = _find_row(cf_df, d)

        history.append({
            'year_label': year_label,
            'is_quarterly': False,
            'income': _akshare_row_to_df(inc_row, _SINA_INCOME_MAP) if inc_row is not None else pd.DataFrame(),
            'balance': _akshare_row_to_df(bal_row, _SINA_BALANCE_MAP) if bal_row is not None else pd.DataFrame(),
            'cash': _akshare_row_to_df(cf_row, _SINA_CASHFLOW_MAP) if cf_row is not None else pd.DataFrame(),
        })

    # Get market cap and EBITDA/D&A from yfinance (AKShare Sina lacks D&A)
    market_cap = 0
    # company_name defaults to ticker, might have been updated by akshare above
    if include_supplement:
        try:
            yf_ticker = ticker + ('.SS' if ticker.startswith('6') else '.SZ')

            def _do_aks_yfinance_calls():
                _yf_stock = yf.Ticker(yf_ticker)
                _info_yf = _yf_stock.info or {}
                _yf_inc = _yf_stock.income_stmt
                return _yf_stock, _info_yf, _yf_inc

            yf_stock, info_yf, yf_inc = run_yfinance_call_with_proxy_retry(_do_aks_yfinance_calls)
            yf_profile = _build_company_profile_from_yfinance_info(info_yf)
            company_profile = _merge_company_profiles(company_profile, yf_profile)
            market_cap = info_yf.get('marketCap', 0)

            # Only fallback to yfinance name if AKShare didn't find one
            if company_name == ticker:
                yf_name = info_yf.get('longName', info_yf.get('shortName', ''))
                if yf_name:
                    company_name = yf_name

            # Supplement EBITDA from yfinance income statement (already fetched above)
            if yf_inc is not None and not yf_inc.empty:
                # Build a map: year -> (ebitda, d&a) from yfinance
                yf_ebitda_map = {}
                for col_idx in range(len(yf_inc.columns)):
                    col_date = str(yf_inc.columns[col_idx])[:4]  # e.g. '2024'
                    ebitda_val = None
                    da_val = None
                    if 'EBITDA' in yf_inc.index:
                        try:
                            ebitda_val = float(yf_inc.loc['EBITDA'].iloc[col_idx])
                        except (TypeError, ValueError, KeyError, IndexError):
                            pass
                    if 'Reconciled Depreciation' in yf_inc.index:
                        try:
                            da_val = float(yf_inc.loc['Reconciled Depreciation'].iloc[col_idx])
                        except (TypeError, ValueError, KeyError, IndexError):
                            pass
                    if ebitda_val is not None:
                        yf_ebitda_map[col_date] = (ebitda_val, da_val)

                # Apply to history entries — process annuals first to establish D&A ratio
                latest_da_ratio = None
                annual_entries_h = [e for e in history if not e.get('is_quarterly')]
                quarterly_entries_h = [e for e in history if e.get('is_quarterly')]

                for entry in annual_entries_h + quarterly_entries_h:
                    inc_e = entry.get('income')
                    if inc_e is None or inc_e.empty or 'ebitda' in inc_e.index:
                        continue
                    ebit = inc_e.loc['operating_income', 'Value'] if 'operating_income' in inc_e.index else None
                    if ebit is None:
                        continue

                    # Try to match by FY year label
                    label = entry.get('year_label', '')
                    year_2d = ''.join(c for c in label if c.isdigit())[-2:]
                    year_4d = '20' + year_2d if year_2d else ''

                    if year_4d in yf_ebitda_map:
                        ebitda_val, da_val = yf_ebitda_map[year_4d]
                        inc_e.loc['ebitda', 'Value'] = ebitda_val
                        if da_val is not None:
                            inc_e.loc['reconciled_depreciation', 'Value'] = da_val
                            if ebit != 0:
                                latest_da_ratio = abs(da_val) / abs(ebit)
                    elif latest_da_ratio is not None and entry.get('is_quarterly'):
                        # Estimate quarterly EBITDA using latest D&A ratio
                        est_da = abs(ebit) * latest_da_ratio
                        inc_e.loc['ebitda', 'Value'] = ebit + est_da
                        inc_e.loc['reconciled_depreciation', 'Value'] = est_da
        except Exception as e:
            logger.warning(f"yfinance EBITDA supplement error for {ticker}: {e}")

    return {
        'ticker': ticker,
        'company_name': company_name,
        'market_cap': market_cap,
        'company_profile': company_profile,
        'history': history,
    }


class FinancialDataFetcher:
    """Fetches financial statements from external sources."""

    @staticmethod
    def get_financial_data(
        ticker: str,
        data_source: str = 'auto',
        *,
        mode: str = 'dashboard',
        include_profile: bool = True,
        include_supplement: bool = True,
    ) -> dict[str, Any] | None:
        """
        Fetch financial data with auto-detection of market.

        Routing:
            - 6-digit numbers (e.g. 600519) → A股 → AKShare (Sina), fallback yfinance
            - .HK suffix (e.g. 0700.HK)    → 港股 → yfinance
            - Letters (e.g. NVDA)           → 美股 → yfinance

        Modes:
            - 'dashboard': full multi-period history with quarterly + annual.
            - 'latest': only the most recent period (for covenant checks).

        Parameters:
            include_profile:  Fetch company profile (Ticker.info / AKShare info).
            include_supplement:  Fetch yfinance supplement for A-share (market cap, EBITDA).

        Returns a dict with keys:
            ticker, company_name, market_cap, company_profile, history
        where history is a list of period dicts.

        Results are cached for 10 minutes to reduce API calls.
        """
        ticker = ticker.strip()
        if not ticker:
            raise DataFetchError(
                "Ticker cannot be empty",
                error_type=DataFetchErrorType.INVALID_TICKER,
                ticker=ticker,
                details={"reason": "Empty ticker string"}
            )

        source = (data_source or "auto").strip().lower()
        if source not in ("auto", "yfinance", "akshare"):
            source = "auto"

        # Normalize special ticker formats
        ticker = _normalize_ticker(ticker)

        # Build cache key: ticker + data_source + mode + profile/supplement flags
        _flag_suffix = f"{'p' if include_profile else 'n'}{'s' if include_supplement else 'n'}"
        cache_key = f"{ticker.upper()}:{source}:{mode}:{_flag_suffix}"

        # Check positive cache first
        cached_result = _data_cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for {cache_key}")
            return cached_result

        # Check negative cache (failures with type-specific TTL)
        cached_error = _error_cache.get(cache_key)
        if cached_error is not None:
            logger.debug(f"Negative cache hit for {cache_key}: {cached_error}")
            raise DataFetchError(
                cached_error.get("message", "Cached upstream failure"),
                error_type=_coerce_error_type(cached_error.get("error_type")),
                ticker=cached_error.get("ticker", ticker),
                details=cached_error.get("details") or {},
            )

        # Single-flight coalescing: only one upstream call per cache key.
        in_flight_entry: _InFlightEntry | None = None
        is_leader = False
        with _in_flight_lock:
            existing = _in_flight.get(cache_key)
            if existing is not None:
                in_flight_entry = existing
            else:
                in_flight_entry = _InFlightEntry()
                _in_flight[cache_key] = in_flight_entry
                is_leader = True

        if not is_leader:
            logger.debug(f"Waiting for in-flight fetch of {cache_key}")
            completed = in_flight_entry.event.wait(
                timeout=max(0.1, settings.single_flight_wait_timeout_seconds),
            )
            if not completed:
                raise DataFetchError(
                    "Timed out waiting for in-flight fetch",
                    error_type=DataFetchErrorType.NETWORK_ERROR,
                    ticker=ticker,
                    details={"reason": "single_flight_timeout", "cache_key": cache_key},
                )
            if in_flight_entry.result is not None:
                return in_flight_entry.result
            if in_flight_entry.exception is not None:
                raise in_flight_entry.exception

        logger.debug(f"Cache miss for {cache_key}, fetching from source...")

        try:
            # OR-004: Strip A-share exchange suffixes before routing detection.
            # Handles copy-pasted formats like "600519.SS", "000002.SZ", "000002.SH"
            _raw = ticker.upper()
            for _suffix in ('.SS', '.SZ', '.SH'):
                if _raw.endswith(_suffix):
                    ticker = ticker[: -len(_suffix)]
                    break

            # Auto-detect A-share: 6-digit number → AKShare first, fallback yfinance
            if ticker.isdigit() and len(ticker) == 6:
                if source in ("auto", "akshare"):
                    try:
                        result = _fetch_a_share_akshare(ticker, include_profile=include_profile, include_supplement=include_supplement)
                    except DataFetchError as exc:
                        if source == "akshare":
                            raise
                        logger.warning(
                            "AKShare failed for %s in auto mode, falling back to yfinance: %s",
                            ticker,
                            exc,
                        )
                        result = None

                    if result and result.get('history'):
                        # Cache successful AKShare result
                        _data_cache.set(cache_key, result)
                        logger.debug(f"Cached AKShare result for {cache_key}")
                        with _in_flight_lock:
                            entry = _in_flight.get(cache_key)
                            if entry is not None:
                                entry.result = result
                        return result
                    if source == "akshare":
                        # Caller explicitly requested AKShare; surface explicit failure.
                        logger.warning(f"AKShare failed for {ticker} (akshare requested)")
                        raise DataFetchError(
                            f"No financial data available from AKShare for '{ticker}'",
                            error_type=DataFetchErrorType.NO_DATA_AVAILABLE,
                            ticker=ticker,
                            details={"source": "akshare"},
                        )
                    # Fallback to yfinance for auto mode
                    logger.info(f"AKShare failed for {ticker}, falling back to yfinance")
                suffix = '.SS' if ticker.startswith('6') else '.SZ'
                ticker = ticker + suffix

            # ── yfinance (US / HK / A-share) ──
            # Rate-limit before upstream I/O to avoid Yahoo Finance throttling.
            # In retry_only mode (default) the proxy lock is only acquired on a
            # proxy/curl-related retry, letting concurrent yfinance misses run in
            # parallel rather than serialising behind _PROXY_CLEAR_LOCK.
            try:
                _stock = None
                _info = None
                _inc = _bal = _cf = None
                _inc_q = _bal_q = _cf_q = None
                _is_latest = (mode == 'latest')

                def _do_yfinance_calls():
                    nonlocal _stock, _info, _inc, _bal, _cf, _inc_q, _bal_q, _cf_q
                    _stock = yf.Ticker(ticker)
                    if include_profile:
                        _info = _stock.info or {}
                    else:
                        _info = {}
                    _inc = _stock.income_stmt
                    _bal = _stock.balance_sheet
                    _cf = _stock.cashflow
                    # In latest mode we still need quarterly to compare
                    # dates and pick the truly most recent period.
                    _inc_q = _stock.quarterly_income_stmt
                    _bal_q = _stock.quarterly_balance_sheet
                    _cf_q = _stock.quarterly_cashflow

                time.sleep(0.3)
                run_yfinance_call_with_proxy_retry(_do_yfinance_calls)
                stock, info = _stock, _info
                inc, bal, cf = _inc, _bal, _cf
                inc_q, bal_q, cf_q = _inc_q, _bal_q, _cf_q

                if _is_latest:
                    # Latest-only mode: single most recent period.
                    # Prefer the latest quarter over the latest annual when
                    # the quarter date is newer, preserving "最新可用期" semantics.
                    def _first_cell_date(*statements: pd.DataFrame | None) -> str | None:
                        for s in statements:
                            if s is not None and not s.empty and len(s.columns) > 0:
                                d = str(s.columns[0])[:10]
                                if len(d) >= 10:
                                    return d
                        return None

                    annual_date = _first_cell_date(inc, bal, cf)
                    quarter_date = _first_cell_date(inc_q, bal_q, cf_q)

                    use_quarter = False
                    if quarter_date and annual_date:
                        use_quarter = quarter_date > annual_date
                    elif quarter_date and not annual_date:
                        use_quarter = True

                    if use_quarter:
                        m = int(quarter_date[5:7])
                        q = (m - 1) // 3 + 1
                        year_label = f"Q{q} '{quarter_date[2:4]} (U)"
                        history = [{
                            'year_label': year_label,
                            'is_quarterly': True,
                            'income': _extract_single_column(inc_q, 0),
                            'balance': _extract_single_column(bal_q, 0),
                            'cash': _extract_single_column(cf_q, 0),
                        }]
                    else:
                        year_label = "Latest"
                        if annual_date:
                            year_label = f"FY{annual_date[2:4]}"
                        history = [{
                            'year_label': year_label,
                            'is_quarterly': False,
                            'income': _extract_single_column(inc, 0),
                            'balance': _extract_single_column(bal, 0),
                            'cash': _extract_single_column(cf, 0),
                        }]
                else:
                    history = []

                # 1. Fetch Annual Data first (Up to 3 Years) — establishes the cutoff
                if not _is_latest:
                    cols_count = 0
                    for stmt in [inc, bal, cf]:
                        if stmt is not None and not stmt.empty:
                            cols_count = max(cols_count, len(stmt.columns))
                    cols_count = min(3, cols_count)

                    latest_annual_date = None
                    annual_entries = []
                    for i in range(cols_count):
                        year_label = f"Year {i+1}"
                        col_date_str = None
                        for stmt in [inc, bal, cf]:
                            if stmt is not None and not stmt.empty and i < len(stmt.columns):
                                col_date_str = str(stmt.columns[i])[:10]
                                if len(col_date_str) >= 10:
                                    year_label = f"FY{col_date_str[2:4]}"
                                break

                        annual_entries.append({
                            'year_label': year_label,
                            'is_quarterly': False,
                            'income': _extract_single_column(inc, i),
                            'balance': _extract_single_column(bal, i),
                            'cash': _extract_single_column(cf, i),
                        })
                        # Track latest annual date (first column = most recent)
                        if i == 0 and col_date_str and len(col_date_str) >= 10:
                            latest_annual_date = col_date_str

                    # 2. Process Quarterly Data — keep quarters newer than latest annual
                    # plus latest-quarter YoY baseline (same quarter last year).

                    cols_count_q = 0
                    for stmt in [inc_q, bal_q, cf_q]:
                        if stmt is not None and not stmt.empty:
                            cols_count_q = max(cols_count_q, len(stmt.columns))
                    cols_count_q = min(cols_count_q, 12)  # safety cap

                    quarterly_candidates = []
                    for i in range(cols_count_q):
                        col_date_str = None
                        year_label = f"Q{i+1} Unaudited"
                        quarter_meta = None
                        for stmt in [inc_q, bal_q, cf_q]:
                            if stmt is not None and not stmt.empty and i < len(stmt.columns):
                                col_date_str = str(stmt.columns[i])[:10]
                                if len(col_date_str) >= 10:
                                    m = int(col_date_str[5:7])
                                    q = (m - 1) // 3 + 1
                                    quarter_meta = (int(col_date_str[:4]), q)
                                    year_label = f"Q{q} '{col_date_str[2:4]} (U)"
                                break

                        quarterly_candidates.append({
                            'year_label': year_label,
                            'is_quarterly': True,
                            'income': _extract_single_column(inc_q, i),
                            'balance': _extract_single_column(bal_q, i),
                            'cash': _extract_single_column(cf_q, i),
                            '_quarter_meta': quarter_meta,
                        })

                    latest_quarter_meta = None
                    for candidate in quarterly_candidates:
                        candidate_meta = candidate.get('_quarter_meta')
                        if candidate_meta is not None:
                            latest_quarter_meta = candidate_meta
                            break

                    annual_year = int(latest_annual_date[:4]) if latest_annual_date else None
                    prior_year_same_quarter = None
                    latest_quarter_is_displayed = (
                        latest_quarter_meta is not None
                        and (annual_year is None or latest_quarter_meta[0] > annual_year)
                    )
                    if latest_quarter_is_displayed:
                        prior_year_same_quarter = (latest_quarter_meta[0] - 1, latest_quarter_meta[1])

                    quarterly_entries = []
                    seen_quarters = set()
                    for candidate in quarterly_candidates:
                        candidate_meta = candidate.get('_quarter_meta')
                        keep = True
                        if annual_year is not None and candidate_meta is not None:
                            keep = candidate_meta[0] > annual_year
                            if prior_year_same_quarter is not None and candidate_meta == prior_year_same_quarter:
                                keep = True
                        if not keep:
                            continue
                        if candidate_meta is not None and candidate_meta in seen_quarters:
                            continue
                        if candidate_meta is not None:
                            seen_quarters.add(candidate_meta)
                        candidate.pop('_quarter_meta', None)
                        quarterly_entries.append(candidate)

                    # Final order: quarterly (newest first) then annual (newest first)
                    history = quarterly_entries + annual_entries

                # Validate that we have actual financial data before returning success
                if not history:
                    logger.warning(f"No financial history available for {ticker}")
                    raise DataFetchError(
                        f"No financial data available for ticker '{ticker}'",
                        error_type=DataFetchErrorType.NO_DATA_AVAILABLE,
                        ticker=ticker,
                        details={"reason": "Empty history after fetching statements"}
                    )

                result = {
                    'ticker': ticker,
                    'company_name': info.get('longName', info.get('shortName', ticker)) if info else ticker,
                    'market_cap': info.get('marketCap') if info else None,
                    'company_profile': _build_company_profile_from_yfinance_info(info) if include_profile else {},
                    'history': history
                }

                # Cache successful result
                _data_cache.set(cache_key, result)
                logger.debug(f"Cached result for {cache_key}")
                with _in_flight_lock:
                    entry = _in_flight.get(cache_key)
                    if entry is not None:
                        entry.result = result

                return result
            except DataFetchError as exc:
                _cache_data_fetch_error(cache_key, exc)
                with _in_flight_lock:
                    entry = _in_flight.get(cache_key)
                    if entry is not None:
                        entry.exception = exc
                raise
            except Exception as e:
                error_msg = str(e).lower()

                # Classify error type based on error message and provide helpful suggestions
                if "404" in error_msg or "not found" in error_msg:
                    error_type = DataFetchErrorType.INVALID_TICKER
                    suggestions = []

                    # Provide helpful suggestions based on ticker format
                    if '.' in ticker and not ticker.endswith(('.HK', '.SS', '.SZ', '.SH')):
                        suggestions.append(f"Try using hyphen instead: {ticker.replace('.', '-')}")
                    if ticker.endswith('.B'):
                        suggestions.append(f"Class B shares should use hyphen: {ticker[:-2]}-B")
                    if ticker.isdigit() and len(ticker) == 6:
                        suggestions.append(f"A-share tickers need exchange suffix: {ticker}.SS or {ticker}.SZ")

                    message = f"Ticker '{ticker}' not found in data source"
                    if suggestions:
                        message += f". Suggestions: {'; '.join(suggestions)}"

                elif "429" in error_msg or "rate limit" in error_msg or "too many requests" in error_msg:
                    error_type = DataFetchErrorType.RATE_LIMIT
                    message = f"Rate limit exceeded for '{ticker}'. Please wait a moment and try again."
                elif any(
                    token in error_msg
                    for token in (
                        "timeout",
                        "connection",
                        "network",
                        "proxy",
                        "failed to connect",
                        "could not connect",
                        "curl: (7)",
                    )
                ):
                    error_type = DataFetchErrorType.NETWORK_ERROR
                    message = f"Network error when fetching '{ticker}'. Check your internet connection."
                else:
                    error_type = DataFetchErrorType.UNKNOWN
                    message = f"Error fetching data for '{ticker}': {e}"

                logger.error(f"yfinance error for {ticker}: {e}")
                exc_to_raise = DataFetchError(message, error_type=error_type, ticker=ticker)
                _cache_data_fetch_error(cache_key, exc_to_raise)
                with _in_flight_lock:
                    entry = _in_flight.get(cache_key)
                    if entry is not None:
                        entry.exception = exc_to_raise
                raise exc_to_raise
        finally:
            # Signal any waiters that this in-flight request has completed.
            with _in_flight_lock:
                entry = _in_flight.get(cache_key)
                if entry is not None:
                    entry.event.set()
                    del _in_flight[cache_key]

    @staticmethod
    def get_cache_stats() -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dict with hits, misses, size, and hit_rate percentage
        """
        return _data_cache.stats()

    @staticmethod
    def clear_cache() -> None:
        """Clear all cached financial data and cached failures."""
        _data_cache.clear()
        _error_cache.clear()
        logger.info("Data cache cleared")
