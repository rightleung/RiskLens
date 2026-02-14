"""
Credit Analyst Toolkit — Web Application
=========================================
Multi-language support: English, 简体中文, 繁體中文
Themes: Light, Dark, Blue, Green

Usage:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import io

# Import toolkit modules
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ratio_analyzer import RatioAnalyzer, CreditRatioAnalysis
from credit_risk_assessment import CreditRiskAssessor, CreditRiskAssessment
from credit_visualizer import CreditVisualizer

# Import AKShare data fetcher (optional)
try:
    from akshare_data import get_financial_data as akshare_get_data
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False


# ==================== Language / Theme Config ====================
TRANSLATIONS = {
    'en': {
        'title': 'Credit Analyst Toolkit',
        'subtitle': 'Financial statement analysis & credit risk assessment',
        'tab_single': '🔍 Single Analysis',
        'tab_batch': '📚 Batch Analysis',
        'tab_portfolio': '📈 Portfolio View',
        'ticker_placeholder': 'Enter stock ticker (e.g., AAPL, 0700.HK, 600519.SS)',
        'analyze': '🔍 Analyze',
        'company_info': 'Company Info',
        'rating': 'Credit Rating',
        'outlook': 'Outlook',
        'risk_score': 'Risk Score',
        'strengths': '✅ Strengths',
        'weaknesses': '⚠️ Weaknesses',
        'all_ratios': '📋 All Financial Ratios',
        'export': '📥 Export Full Report',
        'key_metrics': 'Key Credit Metrics',
        'interest_coverage': 'Interest Coverage',
        'debt_ebitda': 'Debt/EBITDA',
        'fcf_debt': 'FCF/Debt',
        'current_ratio': 'Current Ratio',
        'net_margin': 'Net Margin',
        'batch_input': 'Enter tickers (comma-separated)',
        'batch_upload': 'Upload CSV with ticker column',
        'analyze_companies': '🔍 Analyze {n} Companies',
        'companies_analyzed': 'Analyzed {n} companies',
        'download_csv': '📥 Download Results (CSV)',
        'portfolio_summary': 'Portfolio Summary',
        'companies_count': 'Companies Analyzed',
        'avg_risk': 'Avg Risk Score',
        'strong_ratings': 'Strong Ratings (A+)',
        'weak_ratings': 'Weak Ratings (B-)',
        'rating_dist': 'Rating Distribution',
        'risk_dist': 'Risk Score Distribution',
        'all_companies': 'All Companies',
        'settings': '⚙️ Settings',
        'language': 'Language',
        'theme': 'Theme',
        'data_source': 'Data Source',
        'about': 'About',
        'about_text': '''This tool analyzes credit risk using:
- Liquidity ratios
- Leverage metrics
- Coverage analysis
- Cash flow generation

⚠️ For educational purposes only. Not financial advice.''',
        'settings_default_ticker': 'Default Ticker',
        'settings_fiscal_year': 'Fiscal Year',
        'settings_export': 'Export Format',
        'strong': 'Strong', 'moderate': 'Moderate', 'weak': 'Weak', 'distress': 'Distress',
    },
    'zh': {
        'title': '信用分析工具箱',
        'subtitle': '财务报表分析与信用风险评估',
        'tab_single': '🔍 单股分析',
        'tab_batch': '📚 批量分析',
        'tab_portfolio': '📈 组合视图',
        'ticker_placeholder': '输入股票代码 (例如: AAPL, 0700.HK, 600519.SS)',
        'analyze': '🔍 分析',
        'company_info': '公司信息',
        'rating': '信用评级',
        'outlook': '展望',
        'risk_score': '风险评分',
        'strengths': '✅ 优势',
        'weaknesses': '⚠️ 劣势',
        'all_ratios': '📋 全部财务比率',
        'export': '📥 导出完整报告',
        'key_metrics': '关键信用指标',
        'interest_coverage': '利息保障倍数',
        'debt_ebitda': '债务/EBITDA',
        'fcf_debt': '自由现金流/债务',
        'current_ratio': '流动比率',
        'net_margin': '净利润率',
        'batch_input': '输入股票代码 (逗号分隔)',
        'batch_upload': '上传含股票代码的CSV',
        'analyze_companies': '🔍 分析 {n} 家公司',
        'companies_analyzed': '已分析 {n} 家公司',
        'download_csv': '📥 下载结果 (CSV)',
        'portfolio_summary': '组合摘要',
        'companies_count': '分析公司数',
        'avg_risk': '平均风险评分',
        'strong_ratings': '高评级 (A以上)',
        'weak_ratings': '低评级 (B以下)',
        'rating_dist': '评级分布',
        'risk_dist': '风险评分分布',
        'all_companies': '全部公司',
        'settings': '⚙️ 设置',
        'language': '语言',
        'theme': '主题',
        'data_source': '数据来源',
        'about': '关于',
        'about_text': '''本工具分析信用风险使用：
- 流动性比率
- 杠杆指标
- 偿付能力分析
- 现金流生成能力

⚠️ 仅供学习参考，不构成投资建议。''',
        'settings_default_ticker': '默认股票代码',
        'settings_fiscal_year': '财年',
        'settings_export': '导出格式',
        'strong': '强', 'moderate': '中', 'weak': '弱', 'distress': '危',
    },
    'tw': {
        'title': '信用分析工具箱',
        'subtitle': '財務報表分析與信用風險評估',
        'tab_single': '🔍 單股分析',
        'tab_batch': '📚 批次分析',
        'tab_portfolio': '📈 組合視圖',
        'ticker_placeholder': '輸入股票代碼 (例如: AAPL, 0700.HK, 600519.SS)',
        'analyze': '🔍 分析',
        'company_info': '公司資訊',
        'rating': '信用評級',
        'outlook': '展望',
        'risk_score': '風險評分',
        'strengths': '✅ 優勢',
        'weaknesses': '⚠️ 劣勢',
        'all_ratios': '📋 全部財務比率',
        'export': '📥 導出完整報告',
        'key_metrics': '關鍵信用指標',
        'interest_coverage': '利息保障倍數',
        'debt_ebitda': '債務/EBITDA',
        'fcf_debt': '自由現金流/債務',
        'current_ratio': '流動比率',
        'net_margin': '淨利潤率',
        'batch_input': '輸入股票代碼 (逗號分隔)',
        'batch_upload': '上傳含股票代碼的CSV',
        'analyze_companies': '🔍 分析 {n} 家公司',
        'companies_analyzed': '已分析 {n} 家公司',
        'download_csv': '📥 下載結果 (CSV)',
        'portfolio_summary': '組合摘要',
        'companies_count': '分析公司數',
        'avg_risk': '平均風險評分',
        'strong_ratings': '高評級 (A以上)',
        'weak_ratings': '低評級 (B以下)',
        'rating_dist': '評級分佈',
        'risk_dist': '風險評分分佈',
        'all_companies': '全部公司',
        'settings': '⚙️ 設置',
        'language': '語言',
        'theme': '主題',
        'data_source': '數據來源',
        'about': '關於',
        'about_text': '''本工具分析信用風險使用：
- 流動性比率
- 槓桿指標
- 償付能力分析
- 現金流生成能力

⚠️ 僅供學習參考，不構成投資建議。''',
        'settings_default_ticker': '默認股票代碼',
        'settings_fiscal_year': '財年',
        'settings_export': '導出格式',
        'strong': '強', 'moderate': '中', 'weak': '弱', 'distress': '危',
    }
}

THEMES = {
    'light': {
        'primary': '#1a5fb4',      # Darker blue for better contrast on light
        'secondary': '#1a5fb4',
        'bg': '#ffffff',
        'text': '#1c1c1c',         # Not pure black, easier on eyes
        'card_bg': '#f8f9fa',
        'border': '#dee2e6',
        'success': '#1a7f37',
        'error': '#cf222e',
        'warning': '#9a6700',
    },
    'dark': {
        'primary': '#4fc1ff',      # Bright blue for dark mode
        'secondary': '#79c0ff',
        'bg': '#0d1117',
        'text': '#f0f6fc',
        'card_bg': '#161b22',
        'border': '#30363d',
        'success': '#3fb950',
        'error': '#ff7b72',
        'warning': '#d29922',
    },
    'blue': {
        'primary': '#58a6ff',      # Bright blue
        'secondary': '#79c0ff',
        'bg': '#0d1b2a',
        'text': '#e0f7fa',
        'card_bg': '#1b2d3e',
        'border': '#304c5d',
        'success': '#7ee787',
        'error': '#ff9b8a',
        'warning': '#d29922',
    },
    'green': {
        'primary': '#7ee787',      # Bright green
        'secondary': '#a5d6a7',
        'bg': '#0f1f0f',
        'text': '#e8f5e9',
        'card_bg': '#1a2e1a',
        'border': '#3d5c3d',
        'success': '#7ee787',
        'error': '#ff8a8a',
        'warning': '#ffd54f',
    },
}


def get_text(key, lang='en'):
    """Get translated text."""
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)


def apply_theme(theme_name):
    """Apply theme CSS."""
    theme = THEMES.get(theme_name, THEMES['light'])
    st.markdown(f"""
    <style>
        /* Main app background and text */
        .stApp {{
            background-color: {theme['bg']};
            color: {theme['text']};
        }}
        
        /* Headings */
        h1, h2, h3, h4, h5, h6 {{
            color: {theme['primary']} !important;
        }}
        
        /* Metrics */
        .metric-value {{
            color: {theme['primary']} !important;
        }}
        
        /* Cards and containers */
        div[data-testid="stMetric"],
        div[data-testid="stExpander"] {{
            background-color: {theme['card_bg']};
            border: 1px solid {theme['border']};
            border-radius: 8px;
            padding: 12px;
        }}
        
        /* Buttons */
        div.stButton > button {{
            background-color: {theme['primary']};
            color: {theme['bg']};
            border: none;
            border-radius: 6px;
        }}
        
        /* Success/Error/Warning messages */
        div[data-testid="stSuccess"] {{
            background-color: {theme['success']}20;
            color: {theme['success']};
            border: 1px solid {theme['success']};
        }}
        div[data-testid="stError"] {{
            background-color: {theme['error']}20;
            color: {theme['error']};
            border: 1px solid {theme['error']};
        }}
        div[data-testid="stWarning"] {{
            background-color: {theme['warning']}20;
            color: {theme['warning']};
            border: 1px solid {theme['warning']};
        }}
        
        /* Input fields */
        .stTextInput > div > div,
        .stSelectbox > div > div {{
            background-color: {theme['card_bg']};
            color: {theme['text']};
        }}
        
        /* Tables */
        div[data-testid="stDataFrame"] {{
            background-color: {theme['card_bg']};
        }}
        
        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background-color: {theme['card_bg']};
        }}
        
        /* Links */
        a {{
            color: {theme['primary']};
        }}
    </style>
    """, unsafe_allow_html=True)


# ==================== Page Config ====================
st.set_page_config(
    page_title="Credit Analyst Toolkit",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==================== Main App ====================
def main():
    # Initialize session state
    if 'lang' not in st.session_state:
        st.session_state['lang'] = 'en'
    if 'theme' not in st.session_state:
        st.session_state['theme'] = 'light'
    if 'ratios' not in st.session_state:
        st.session_state['ratios'] = None
    if 'assessment' not in st.session_state:
        st.session_state['assessment'] = None
    
    # Apply theme
    apply_theme(st.session_state['theme'])
    
    t = lambda k: get_text(k, st.session_state['lang'])
    
    # Sidebar settings
    with st.sidebar:
        st.header(t('settings'))
        
        # Language
        st.subheader(t('language'))
        st.session_state['lang'] = st.selectbox(
            '', ['en', 'zh', 'tw'], 
            format_func=lambda x: {'en': 'English', 'zh': '简体中文', 'tw': '繁體中文'}[x],
            index=['en', 'zh', 'tw'].index(st.session_state['lang'])
        )
        
        # Theme
        st.subheader(t('theme'))
        st.session_state['theme'] = st.selectbox(
            '', ['light', 'dark', 'blue', 'green'],
            format_func=lambda x: {'light': '☀️ Light', 'dark': '🌙 Dark', 'blue': '🔵 Blue', 'green': '🟢 Green'}[x],
            index=['light', 'dark', 'blue', 'green'].index(st.session_state['theme'])
        )
        
        # Data Source
        st.subheader(t('data_source'))
        data_source_options = ['yfinance']
        if AKSHARE_AVAILABLE:
            data_source_options.append('akshare')
        st.session_state['data_source'] = st.radio(
            '',
            data_source_options,
            format_func=lambda x: '🇨🇳 AKShare (A股/港股)' if x == 'akshare' else '🌍 yfinance (US/全球)',
            index=data_source_options.index(st.session_state.get('data_source', 'yfinance')) if st.session_state.get('data_source') in data_source_options else 0
        )
        
        st.divider()
        st.subheader(t('about'))
        st.info(t('about_text'))
    
    # Main content
    st.title(t('title'))
    st.markdown(f"*{t('subtitle')}*")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs([t('tab_single'), t('tab_batch'), t('tab_portfolio')])
    
    with tab1:
        single_analysis(t)
    
    with tab2:
        batch_analysis(t)
    
    with tab3:
        portfolio_view(t)


def single_analysis(t):
    """Single company analysis."""
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader(t('company_info'))
        ticker = st.text_input('', placeholder=t('ticker_placeholder'), key='single_ticker').upper()
        
        if st.button(t('analyze'), type='primary'):
            if ticker:
                with st.spinner(f"Analyzing {ticker}..."):
                    data = get_financial_data(ticker)
                    if data:
                        st.session_state['current_data'] = data
                        st.session_state['ratios'] = None
                        st.session_state['assessment'] = None
    
    with col2:
        if 'current_data' in st.session_state:
            data = st.session_state['current_data']
            ticker = data['ticker']
            
            st.subheader(f"🏢 {data['company_name']} ({ticker})")
            st.caption(f"Fiscal Year: {data['fiscal_year']}")
            
            # Calculate ratios
            if st.session_state['ratios'] is None:
                with st.spinner("Calculating..."):
                    ratios = calculate_ratios(data)
                    st.session_state['ratios'] = ratios
                    st.session_state['assessment'] = assess_risk(data['company_name'], ratios)
            
            display_analysis_results(t)


def batch_analysis(t):
    """Batch analysis."""
    st.subheader(t('tab_batch'))
    
    input_method = st.radio('', ['Comma-separated', 'CSV Upload'])
    
    tickers = []
    
    if input_method == 'Comma-separated':
        ticker_input = st.text_area(t('batch_input'), placeholder="AAPL, MSFT, GOOGL")
        tickers = [t.strip().upper() for t in ticker_input.split(',') if t.strip()]
    else:
        uploaded = st.file_uploader(t('batch_upload'), type=['csv'])
        if uploaded:
            df = pd.read_csv(uploaded)
            if 'ticker' in df.columns:
                tickers = df['ticker'].str.upper().tolist()
    
    if tickers and st.button(t('analyze_companies').format(n=len(tickers)), type='primary'):
        results = []
        progress = st.progress(0)
        
        for i, ticker in enumerate(tickers):
            progress.progress((i + 1) / len(tickers))
            data = get_financial_data(ticker)
            if data:
                ratios = calculate_ratios(data)
                results.append({
                    'Ticker': ticker,
                    'Company': data['company_name'],
                    'Rating': assess_risk(data['company_name'], ratios).overall_rating,
                    'Risk Score': assess_risk(data['company_name'], ratios).risk_score,
                    'Interest Cov.': ratios.interest_coverage,
                    'Debt/EBITDA': ratios.debt_to_ebitda,
                })
        
        if results:
            st.success(t('companies_analyzed').format(n=len(results)))
            results_df = pd.DataFrame(results)
            st.session_state['batch_results'] = results_df
            st.dataframe(results_df, use_container_width=True)
            
            csv = results_df.to_csv(index=False)
            st.download_button(t('download_csv'), csv, "credit_analysis_batch.csv", "text/csv")
    
    if 'batch_results' in st.session_state:
        st.dataframe(st.session_state['batch_results'], use_container_width=True)


def portfolio_view(t):
    """Portfolio overview."""
    st.subheader(t('portfolio_summary'))
    
    if 'batch_results' not in st.session_state:
        st.info("Run batch analysis first.")
        return
    
    df = st.session_state['batch_results']
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric(t('companies_count'), len(df))
    with c2: st.metric(t('avg_risk'), f"{df['Risk Score'].mean():.1f}/100")
    with c3: st.metric(t('strong_ratings'), len(df[df['Rating'].isin(['AAA', 'AA', 'A'])]))
    with c4: st.metric(t('weak_ratings'), len(df[df['Rating'].isin(['B', 'CCC', 'CC', 'C', 'D'])]))
    
    st.subheader(t('rating_dist'))
    rating_counts = df['Rating'].value_counts()
    st.bar_chart(rating_counts)
    
    st.subheader(t('all_companies'))
    st.dataframe(df.sort_values('Risk Score'), use_container_width=True)


def get_financial_data(ticker: str, data_source: str = None):
    """Fetch financial data from Yahoo Finance or AKShare."""
    # Use session state if not specified
    if data_source is None:
        data_source = st.session_state.get('data_source', 'yfinance')
    
    # Use AKShare for Chinese stocks if akshare is selected
    if data_source == 'akshare' and AKSHARE_AVAILABLE:
        return akshare_get_data(ticker)
    
    # Default to yfinance
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        def standardize_columns(name: str) -> str:
            """Convert yfinance column names to snake_case."""
            # Map common yfinance names to expected names
            mapping = {
                'Total Assets': 'total_assets',
                'Total Liabilities': 'total_liabilities',
                'Total Stockholder Equity': 'total_equity',
                'Common Stock': 'common_stock',
                'Retained Earnings': 'retained_earnings',
                'Cash': 'cash',
                'Short Term Investments': 'short_term_investments',
                'Accounts Receivable': 'accounts_receivable',
                'Inventory': 'inventory',
                'Total Current Assets': 'total_current_assets',
                'Property Plant Equipment': 'property_plant_equipment',
                'Goodwill': 'goodwill',
                'Intangible Assets': 'intangible_assets',
                'Accounts Payable': 'accounts_payable',
                'Short Term Debt': 'short_term_debt',
                'Total Current Liabilities': 'total_current_liabilities',
                'Long Term Debt': 'long_term_debt',
                'Revenue': 'revenue',
                'Gross Profit': 'gross_profit',
                'Operating Income': 'operating_income',
                'Net Income': 'net_income',
                'Interest Expense': 'interest_expense',
                'Income Before Tax': 'income_before_tax',
                'Income Tax Expense': 'income_tax_expense',
                'Operating Cash Flow': 'operating_cf',
                'Capital Expenditures': 'capital_expenditures',
                'Net Change In Cash': 'net_change_in_cash',
            }
            return mapping.get(name, name.lower().replace(' ', '_').replace('&', 'and'))
        
        def prepare_data(df):
            """Convert yfinance format to ratio analyzer format."""
            if df is None or df.empty:
                return pd.DataFrame()
            # yfinance: rows=metrics, cols=periods → transpose to: cols=metrics, rows=periods
            df_t = df.T
            df_t.index.name = 'Period'
            df_t = df_t.reset_index()
            # Standardize column names
            df_t.columns = [standardize_columns(c) if i > 0 else c for i, c in enumerate(df_t.columns)]
            return df_t
        
        return {
            'ticker': ticker,
            'company_name': info.get('longName', info.get('shortName', ticker)),
            'fiscal_year': datetime.now().year,
            'income': prepare_data(stock.income_stmt),
            'balance': prepare_data(stock.balance_sheet),
            'cash': prepare_data(stock.cashflow),
        }
    except Exception as e:
        st.error(f"Error fetching {ticker}: {e}")
        return None


def calculate_ratios(data):
    """Calculate financial ratios."""
    analyzer = RatioAnalyzer()
    return analyzer.calculate_all_ratios(
        bs_data=data['balance'],
        is_data=data['income'],
        cf_data=data['cash'],
        company_name=data['company_name'],
        fiscal_year=data['fiscal_year']
    )


def assess_risk(company_name: str, ratios):
    """Assess credit risk."""
    assessor = CreditRiskAssessor()
    return assessor.assess_credit(
        company_name=company_name,
        ratios=ratios,
        industry='general',
        fiscal_year=datetime.now().year
    )


def display_analysis_results(t):
    """Display analysis results."""
    ratios = st.session_state['ratios']
    assessment = st.session_state['assessment']
    
    if not ratios or not assessment:
        return
    
    # Rating
    rating_class = {'Strong': 'rating-strong', 'Moderate': 'rating-moderate', 
                   'Weak': 'rating-weak', 'Distress': 'rating-distress'}.get(
        assessment.overall_rating[:2] if assessment.overall_rating.startswith('A') 
        else assessment.overall_rating[0], 'rating-moderate')
    
    st.markdown(f"""
    <div class="credit-rating {rating_class}">
        {assessment.overall_rating}
    </div>
    <p style="text-align: center; color: #666;">{t('outlook')}: {assessment.outlook}</p>
    <p style="text-align: center; color: #666;">{t('risk_score')}: {assessment.risk_score:.0f}/100</p>
    """, unsafe_allow_html=True)
    
    # Key metrics
    st.subheader(t('key_metrics'))
    m1, m2, m3, m4 = st.columns(4)
    
    with m1: st.metric(t('interest_coverage'), f"{ratios.interest_coverage:.1f}x" if ratios.interest_coverage else "N/A")
    with m2: st.metric(t('debt_ebitda'), f"{ratios.debt_to_ebitda:.1f}" if ratios.debt_to_ebitda else "N/A")
    with m3: st.metric(t('fcf_debt'), f"{ratios.fcf_to_debt*100:.1f}%" if ratios.fcf_to_debt else "N/A")
    with m4: st.metric(t('current_ratio'), f"{ratios.current_ratio:.2f}" if ratios.current_ratio else "N/A")
    
    # Strengths/Weaknesses
    c1, c2 = st.columns(2)
    with c1:
        st.subheader(t('strengths'))
        for s in assessment.strengths:
            st.success(s)
    with c2:
        st.subheader(t('weaknesses'))
        for w in assessment.weaknesses:
            st.warning(w)
    
    # All ratios
    with st.expander(t('all_ratios')):
        ratio_df = ratios.to_dataframe()
        st.dataframe(ratio_df, use_container_width=True)


if __name__ == "__main__":
    main()
