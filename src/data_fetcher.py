"""
Data Fetcher Module
====================
Extracts financial data using yfinance (and optionally akshare).

Produces DataFrames with metric names as the **index** and a single
value column — the format expected by RatioAnalyzer._get_value().
"""

import pandas as pd
import numpy as np
import yfinance as yf
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)


# ── Simple In-Memory Cache with TTL ──────────────────────────────────────────

class SimpleCache:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self, default_ttl: int = 600):
        """Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 600 = 10 minutes)
        """
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
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
                # Expired, remove from cache
                del self._cache[key]
                self._misses += 1
                return None

            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl if ttl is not None else self._default_ttl
        expiry = datetime.now() + timedelta(seconds=ttl)
        with self._lock:
            self._cache[key] = (value, expiry)

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, int]:
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


# Global cache instance (10-minute TTL)
_data_cache = SimpleCache(default_ttl=600)


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
    retriable_errors: tuple = (Exception,)
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

    def __init__(self, message: str, error_type: DataFetchErrorType, ticker: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.ticker = ticker
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.message,
            "error_type": self.error_type.value,
            "ticker": self.ticker,
            "details": self.details
        }

# Optional AKShare integration (akshare_data.py is a legacy module)
try:
    from akshare_data import get_financial_data as akshare_get_data
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


def _extract_single_column(df: Optional[pd.DataFrame], col_idx: int) -> pd.DataFrame:
    """Extract a single column (period) from a yfinance statement DataFrame and 
    standardize the index. Format: index = metric names, single 'Value' column."""
    if df is None or df.empty or col_idx >= len(df.columns):
        return pd.DataFrame()

    target_col = df.iloc[:, col_idx]

    # Build a new Series with standardized index names
    records: Dict[str, float] = {}
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
    if 'short_term_debt' in records or 'long_term_debt' in records:
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
            all_row_keys = set(str(k) for k in row.index) if hasattr(row, 'index') else set()
            mapped_cn_keys = set(field_map.keys())
            unmatched = all_row_keys - mapped_cn_keys
            if unmatched and len(unmatched) < 50:  # avoid logging noise
                logger.debug(f"AKShare unmapped fields: {unmatched}")
        return pd.DataFrame()
    return pd.DataFrame.from_dict(records, orient='index', columns=['Value'])


@retry_with_backoff(
    max_retries=2,
    initial_delay=1.5,
    backoff_factor=2.0,
    retriable_errors=(Exception,)
)
def _fetch_a_share_akshare(ticker: str) -> Optional[Dict[str, Any]]:
    """Fetch A-share data from AKShare's Sina Finance API.
    
    Returns the same dict format as the yfinance path:
        { ticker, company_name, market_cap, history: [...] }
    """
    try:
        import akshare as ak
    except ImportError:
        return None
    
    try:
        # Fetch all 3 statements
        logger.info(f"Fetching AKShare data for {ticker}")
        company_name = ticker

        # Get company info first
        try:
            stock_info = ak.stock_individual_info_em(symbol=ticker)
            if stock_info is not None and not stock_info.empty:
                for col in ['股票简称', '公司名称', '名称', 'name']:
                    if col in stock_info['item'].values:
                        company_name = stock_info[stock_info['item'] == col]['value'].values[0]
                        break
        except Exception as e:
            logger.warning(f"AKShare individual info error for {ticker}: {e}")

        inc_df = ak.stock_financial_report_sina(stock=ticker, symbol='利润表')
        bal_df = ak.stock_financial_report_sina(stock=ticker, symbol='资产负债表')
        cf_df = ak.stock_financial_report_sina(stock=ticker, symbol='现金流量表')
        logger.debug(f"AKShare {ticker} statement sizes: income={len(inc_df) if inc_df is not None else 0}, balance={len(bal_df) if bal_df is not None else 0}, cashflow={len(cf_df) if cf_df is not None else 0}")
    except Exception as e:
        logger.error(f"AKShare Sina API error for {ticker}: {e}")
        return None

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
    annual_dates = [d for d in dates_inc if _date_digits(d).endswith('1231')]
    quarterly_dates = [d for d in dates_inc if not _date_digits(d).endswith('1231')]

    # Take latest 3 annual
    annual_dates = annual_dates[:3]
    latest_annual_year = int(_date_digits(annual_dates[0])[:4]) if annual_dates else 0

    # Only keep quarterly dates with year > latest annual year
    quarterly_dates = [d for d in quarterly_dates if int(_date_digits(d)[:4]) > latest_annual_year]

    def _find_row(df, date_val):
        """Find the row matching a report date."""
        if df is None or df.empty:
            return None
        matches = df[df['报告日'] == date_val]
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
    try:
        yf_ticker = ticker + ('.SS' if ticker.startswith('6') else '.SZ')
        yf_stock = yf.Ticker(yf_ticker)
        info_yf = yf_stock.info or {}
        market_cap = info_yf.get('marketCap', 0)
        
        # Only fallback to yfinance name if AKShare didn't find one
        if company_name == ticker:
            yf_name = info_yf.get('longName', info_yf.get('shortName', ''))
            if yf_name:
                company_name = yf_name
        
        # Supplement EBITDA from yfinance income statement
        yf_inc = yf_stock.income_stmt
        if yf_inc is not None and not yf_inc.empty:
            # Build a map: year -> (ebitda, d&a) from yfinance
            yf_ebitda_map = {}
            for col_idx in range(len(yf_inc.columns)):
                col_date = str(yf_inc.columns[col_idx])[:4]  # e.g. '2024'
                ebitda_val = None
                da_val = None
                if 'EBITDA' in yf_inc.index:
                    try: ebitda_val = float(yf_inc.loc['EBITDA'].iloc[col_idx])
                    except: pass
                if 'Reconciled Depreciation' in yf_inc.index:
                    try: da_val = float(yf_inc.loc['Reconciled Depreciation'].iloc[col_idx])
                    except: pass
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
        'history': history,
    }


class FinancialDataFetcher:
    """Fetches financial statements from external sources."""

    @staticmethod
    @retry_with_backoff(
        max_retries=3,
        initial_delay=1.0,
        backoff_factor=2.0,
        retriable_errors=(Exception,)
    )
    def get_financial_data(ticker: str, data_source: str = 'auto') -> Optional[Dict[str, Any]]:
        """
        Fetch financial data with auto-detection of market.

        Routing:
            - 6-digit numbers (e.g. 600519) → A股 → AKShare (Sina), fallback yfinance
            - .HK suffix (e.g. 0700.HK)    → 港股 → yfinance
            - Letters (e.g. AAPL)           → 美股 → yfinance

        Returns a dict with keys:
            ticker, company_name, market_cap, history
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

        # Build cache key: ticker + data_source
        cache_key = f"{ticker.upper()}:{source}"

        # Check cache first
        cached_result = _data_cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for {cache_key}")
            return cached_result

        logger.debug(f"Cache miss for {cache_key}, fetching from source...")

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
                result = _fetch_a_share_akshare(ticker)
                if result and result.get('history'):
                    # Cache successful AKShare result
                    _data_cache.set(cache_key, result)
                    logger.debug(f"Cached AKShare result for {cache_key}")
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
        try:
            stock = yf.Ticker(ticker)
            # Rate-limit: brief pause to avoid Yahoo Finance throttling
            time.sleep(0.3)
            info = stock.info or {}

            inc = stock.income_stmt
            bal = stock.balance_sheet
            cf = stock.cashflow

            history = []
            
            # 1. Fetch Annual Data first (Up to 3 Years) — establishes the cutoff
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
            
            # 2. Fetch Quarterly Data — only keep quarters NEWER than latest annual
            inc_q = stock.quarterly_income_stmt
            bal_q = stock.quarterly_balance_sheet
            cf_q = stock.quarterly_cashflow
            
            cols_count_q = 0
            for stmt in [inc_q, bal_q, cf_q]:
                if stmt is not None and not stmt.empty:
                    cols_count_q = max(cols_count_q, len(stmt.columns))
            cols_count_q = min(cols_count_q, 12)  # safety cap
            
            quarterly_entries = []
            for i in range(cols_count_q):
                col_date_str = None
                year_label = f"Q{i+1} Unaudited"
                for stmt in [inc_q, bal_q, cf_q]:
                    if stmt is not None and not stmt.empty and i < len(stmt.columns):
                        col_date_str = str(stmt.columns[i])[:10]
                        if len(col_date_str) >= 10:
                            m = int(col_date_str[5:7])
                            q = (m - 1) // 3 + 1
                            year_label = f"Q{q} '{col_date_str[2:4]} (U)"
                        break
                
                # Skip quarters in the same year or earlier than the latest annual FY
                if latest_annual_date and col_date_str:
                    annual_year = int(latest_annual_date[:4])
                    quarter_year = int(col_date_str[:4])
                    if quarter_year <= annual_year:
                        continue
                        
                quarterly_entries.append({
                    'year_label': year_label,
                    'is_quarterly': True,
                    'income': _extract_single_column(inc_q, i),
                    'balance': _extract_single_column(bal_q, i),
                    'cash': _extract_single_column(cf_q, i),
                })
            
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
                'company_name': info.get('longName', info.get('shortName', ticker)),
                'market_cap': info.get('marketCap'),
                'history': history
            }

            # Cache successful result
            _data_cache.set(cache_key, result)
            logger.debug(f"Cached result for {cache_key}")

            return result
        except DataFetchError:
            # Re-raise our custom exceptions
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
            raise DataFetchError(message, error_type=error_type, ticker=ticker, details={"original_error": str(e)})

    @staticmethod
    def get_cache_stats() -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dict with hits, misses, size, and hit_rate percentage
        """
        return _data_cache.stats()

    @staticmethod
    def clear_cache() -> None:
        """Clear all cached data."""
        _data_cache.clear()
        logger.info("Data cache cleared")
