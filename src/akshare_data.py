"""
AKShare Data Fetcher for Credit Analyst Toolkit
==============================================
Alternative to yfinance for Chinese A-shares and other markets.

Usage:
    from akshare_data import get_financial_data
    data = get_financial_data("600519")  # 贵州茅台
"""

import akshare as ak
import pandas as pd
from datetime import datetime
from typing import Dict, Optional


def get_financial_data(ticker: str) -> Optional[Dict]:
    """
    Fetch financial data from AKShare.
    
    Args:
        ticker: Stock ticker
            - A股: 600519, 000001 (without .SS/.SZ)
            - HK: 0700, 9988
            - US: AAPL, MSFT
    
    Returns:
        Dict with company_name, income, balance, cashflow
    """
    # 判断市场
    ticker_upper = ticker.upper()
    
    # A股 (6位数字)
    if ticker.isdigit() and len(ticker) == 6:
        return get_a_stock_data(ticker)
    # HK股 (5位数字)
    elif ticker.isdigit() and len(ticker) == 5:
        return get_hk_stock_data(ticker)
    # 美股 (字母)
    else:
        # 美股用 yfinance
        return get_us_stock_data(ticker)


def get_a_stock_data(ticker: str) -> Optional[Dict]:
    """获取A股数据 (via AKShare Sina Finance API)"""
    try:
        import akshare as ak

        # RA-003: Replaced deprecated ak.stock_balance_sheet/profit_statement/cashflow_statement
        # with the current Sina Finance report API used by data_fetcher._fetch_a_share_akshare().
        stock_info = ak.stock_individual_info_em(symbol=ticker)
        company_name = _extract_company_name(stock_info)

        # Current Sina Finance API (matches data_fetcher.py usage)
        income_stmt = ak.stock_financial_report_sina(stock=ticker, symbol='利润表')
        balance_sheet = ak.stock_financial_report_sina(stock=ticker, symbol='资产负债表')
        cashflow = ak.stock_financial_report_sina(stock=ticker, symbol='现金流量表')

        return {
            'ticker': ticker,
            'company_name': company_name,
            'fiscal_year': datetime.now().year,
            'income': _prepare_financial_df(income_stmt),
            'balance': _prepare_financial_df(balance_sheet),
            'cash': _prepare_financial_df(cashflow),
        }
    except Exception as e:
        print(f"Error fetching A-share {ticker}: {e}")
        return None


def get_hk_stock_data(ticker: str) -> Optional[Dict]:
    """获取港股数据"""
    try:
        # 港股用 akshare
        stock_info = ak.stock_individual_info_em(symbol=ticker)
        company_name = _extract_company_name(stock_info)
        
        # 港股财务报表
        balance_sheet = ak.stock_balance_sheet_hk(symbol=ticker)
        income_stmt = ak.stock_profit_statement_hk(symbol=ticker)
        cashflow = ak.stock_cashflow_statement_hk(symbol=ticker)
        
        return {
            'ticker': ticker,
            'company_name': company_name,
            'fiscal_year': datetime.now().year,
            'income': _prepare_financial_df(income_stmt),
            'balance': _prepare_financial_df(balance_sheet),
            'cash': _prepare_financial_df(cashflow),
        }
    except Exception as e:
        print(f"Error fetching HK stock {ticker}: {e}")
        return None


def get_us_stock_data(ticker: str) -> Optional[Dict]:
    """获取美股数据 - 暂时用 yfinance"""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            'ticker': ticker,
            'company_name': info.get('longName', info.get('shortName', ticker)),
            'fiscal_year': datetime.now().year,
            'income': _prepare_financial_df_yf(stock.income_stmt),
            'balance': _prepare_financial_df_yf(stock.balance_sheet),
            'cash': _prepare_financial_df_yf(stock.cashflow),
        }
    except Exception as e:
        print(f"Error fetching US stock {ticker}: {e}")
        return None


def _extract_company_name(stock_info) -> str:
    """从股票信息中提取公司名称"""
    if stock_info is None or stock_info.empty:
        return "Unknown"
    
    # 尝试从不同字段获取公司名
    for col in ['股票简称', '公司名称', '名称', 'name']:
        if col in stock_info['item'].values:
            return stock_info[stock_info['item'] == col]['value'].values[0]
    
    return stock_info.iloc[0]['value'] if 'value' in stock_info.columns else "Unknown"


def _prepare_financial_df(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare AKShare financial data for ratio analyzer"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    # AKShare: rows=periods, cols=metrics
    # Need to transpose and format for ratio analyzer
    df_t = df.T
    df_t.index.name = 'Period'
    df_t = df_t.reset_index()
    
    # 重命名列
    df_t.columns = [str(c) for c in df_t.columns]
    
    return df_t


def _prepare_financial_df_yf(df) -> pd.DataFrame:
    """Prepare yfinance data for ratio analyzer (existing format)"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    df_t = df.T
    df_t.index.name = 'Period'
    df_t = df_t.reset_index()
    df_t.columns = [str(c) for c in df_t.columns]
    
    return df_t


# 快速测试
if __name__ == "__main__":
    # 测试 A股
    print("Testing A-share (600519 - 贵州茅台)...")
    data = get_financial_data("600519")
    if data:
        print(f"Company: {data['company_name']}")
        print(f"Income statement shape: {data['income'].shape if data['income'] is not None else 'None'}")
    else:
        print("Failed to fetch data")
