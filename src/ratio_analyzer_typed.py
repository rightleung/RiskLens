"""
Credit Analyst Toolkit — Ratio Analyzer
========================================
Calculates and visualizes financial ratios for credit analysis.

Usage:
    from ratio_analyzer import RatioAnalyzer
    analyzer = RatioAnalyzer()
    ratios = analyzer.calculate_all_ratios(income_stmt, balance_sheet, cash_flow)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import (
    Dict, List, Optional, Tuple, Union, 
    Any, TypeVar, Literal, overload
)
from datetime import datetime
import json

# Type aliases for better readability
FinancialDataFrame = pd.DataFrame
RatioDict = Dict[str, Optional[float]]
CategoryDict = Dict[str, str]
ScoreList = List[int]
ReportPath = Path
FormatType = Literal['json', 'csv']

# Type variable for generic type hints
T = TypeVar('T')


@dataclass
class CreditRatioAnalysis:
    """Container for all calculated credit ratios."""
    # Liquidity Ratios
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    cash_ratio: Optional[float] = None
    operating_cf_ratio: Optional[float] = None
    
    # Leverage Ratios
    debt_to_equity: Optional[float] = None
    debt_to_assets: Optional[float] = None
    financial_leverage: Optional[float] = None
    interest_coverage: Optional[float] = None
    debt_to_ebitda: Optional[float] = None
    
    # Profitability Ratios
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roa: Optional[float] = None
    roe: Optional[float] = None
    roic: Optional[float] = None
    
    # Efficiency Ratios
    asset_turnover: Optional[float] = None
    receivables_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None
    payables_turnover: Optional[float] = None
    
    # Cash Flow Ratios
    fcf_to_debt: Optional[float] = None
    fcf_to_revenue: Optional[float] = None
    debt_service_coverage: Optional[float] = None
    
    # Coverage & Quality
    ebitda: Optional[float] = None
    total_debt: Optional[float] = None
    total_equity: Optional[float] = None
    total_assets: Optional[float] = None
    revenue: Optional[float] = None
    
    # Analysis metadata
    analysis_date: Optional[datetime] = None
    fiscal_year: Optional[int] = None
    company_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        data: Dict[str, Any] = self.__dict__.copy()
        data['analysis_date'] = data['analysis_date'].isoformat() if data['analysis_date'] else None
        return data
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to DataFrame for easy viewing."""
        exclude: List[str] = ['analysis_date', 'fiscal_year', 'company_name']
        records: List[Dict[str, Union[str, float]]] = []
        for key, value in self.__dict__.items():
            if key not in exclude and value is not None:
                # Format key for display
                display_key: str = key.replace('_', ' ').title()
                records.append({
                    'Ratio': display_key,
                    'Value': value,
                    'Category': self._get_category(key)
                })
        return pd.DataFrame(records)
    
    def _get_category(self, ratio_name: str) -> str:
        """Get category for a ratio."""
        categories: Dict[str, str] = {
            'current_ratio': 'Liquidity',
            'quick_ratio': 'Liquidity',
            'cash_ratio': 'Liquidity',
            'operating_cf_ratio': 'Liquidity',
            'debt_to_equity': 'Leverage',
            'debt_to_assets': 'Leverage',
            'financial_leverage': 'Leverage',
            'interest_coverage': 'Leverage',
            'debt_to_ebitda': 'Leverage',
            'gross_margin': 'Profitability',
            'operating_margin': 'Profitability',
            'net_margin': 'Profitability',
            'roa': 'Profitability',
            'roe': 'Profitability',
            'roic': 'Profitability',
            'asset_turnover': 'Efficiency',
            'receivables_turnover': 'Efficiency',
            'inventory_turnover': 'Efficiency',
            'payables_turnover': 'Efficiency',
            'fcf_to_debt': 'Cash Flow',
            'fcf_to_revenue': 'Cash Flow',
            'debt_service_coverage': 'Cash Flow',
        }
        return categories.get(ratio_name, 'Other')
    
    def get_rating(self) -> str:
        """
        Generate a simplified credit rating assessment based on key ratios.
        
        This is a basic framework — actual credit ratings require much more analysis.
        """
        scores: List[int] = []
        
        # Interest Coverage (most important for credit)
        if self.interest_coverage:
            if self.interest_coverage > 5:
                scores.append(3)
            elif self.interest_coverage > 3:
                scores.append(2)
            elif self.interest_coverage > 1.5:
                scores.append(1)
            else:
                scores.append(0)
        
        # Debt/EBITDA
        if self.debt_to_ebitda:
            if self.debt_to_ebitda < 2:
                scores.append(3)
            elif self.debt_to_ebitda < 3.5:
                scores.append(2)
            elif self.debt_to_ebitda < 5:
                scores.append(1)
            else:
                scores.append(0)
        
        # Current Ratio
        if self.current_ratio:
            if self.current_ratio > 1.5:
                scores.append(2)
            elif self.current_ratio > 1.0:
                scores.append(1)
            else:
                scores.append(0)
        
        # FCF/Revenue
        if self.fcf_to_revenue:
            if self.fcf_to_revenue > 0.1:
                scores.append(2)
            elif self.fcf_to_revenue > 0:
                scores.append(1)
            else:
                scores.append(0)
        
        if not scores:
            return "Insufficient Data"
        
        avg_score: float = sum(scores) / len(scores)
        
        if avg_score >= 2.2:
            return "Strong (A/AA)"
        elif avg_score >= 1.5:
            return "Moderate (BBB/BB)"
        elif avg_score >= 1.0:
            return "Weak (B/CCC)"
        else:
            return "Distressed (C/D)"


class RatioAnalyzer:
    """
    Calculate financial ratios from financial statements.
    
    Handles:
    - Liquidity analysis
    - Leverage/solvency analysis
    - Profitability analysis
    - Efficiency analysis
    - Cash flow analysis
    
    Example:
        >>> analyzer = RatioAnalyzer()
        >>> ratios = analyzer.calculate_all_ratios(income_stmt, balance_sheet, cash_flow)
        >>> print(ratios.current_ratio)
        >>> print(ratios.get_rating())
    """
    
    def __init__(self, report_dir: str = "../reports") -> None:
        self.report_dir: Path = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True)
    
    def _safe_divide(
        self, 
        numerator: float, 
        denominator: float, 
        default: Optional[float] = None
    ) -> Optional[float]:
        """Safely divide two numbers, handling division by zero."""
        if denominator is None or np.isnan(denominator) or denominator == 0:
            return default
        return numerator / denominator
    
    def calculate_liquidity_ratios(
        self, 
        bs_data: pd.DataFrame
    ) -> Dict[str, Optional[float]]:
        """
        Calculate liquidity ratios from balance sheet data.
        
        Required fields:
        - current_assets, current_liabilities, cash, inventory, 
          accounts_receivable, operating_cf
        """
        ratios: Dict[str, Optional[float]] = {}
        
        # Current Ratio = Current Assets / Current Liabilities
        ca: Optional[float] = self._get_value(bs_data, 'total_current_assets')
        cl: Optional[float] = self._get_value(bs_data, 'total_current_liabilities')
        ratios['current_ratio'] = self._safe_divide(ca, cl)
        
        # Quick Ratio = (Current Assets - Inventory) / Current Liabilities
        inv: Optional[float] = self._get_value(bs_data, 'inventory')
        quick_assets: Optional[float] = (
            self._safe_divide(ca, 1) - self._safe_divide(inv, 1) 
            if ca else None
        )
        ratios['quick_ratio'] = self._safe_divide(quick_assets, cl)
        
        # Cash Ratio = Cash / Current Liabilities
        cash: Optional[float] = self._get_value(bs_data, 'cash')
        ratios['cash_ratio'] = self._safe_divide(cash, cl)
        
        return ratios
    
    def calculate_leverage_ratios(
        self, 
        bs_data: pd.DataFrame, 
        is_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Optional[float]]:
        """
        Calculate leverage/solvency ratios.
        
        Required fields:
        - total_debt, total_equity, total_assets, interest_expense, ebitda
        """
        ratios: Dict[str, Optional[float]] = {}
        
        # Debt to Equity = Total Debt / Total Equity
        debt: Optional[float] = self._get_value(bs_data, 'total_debt')
        equity: Optional[float] = self._get_value(bs_data, 'total_equity')
        ratios['debt_to_equity'] = self._safe_divide(debt, equity)
        
        # Debt to Assets = Total Debt / Total Assets
        assets: Optional[float] = self._get_value(bs_data, 'total_assets')
        ratios['debt_to_assets'] = self._safe_divide(debt, assets)
        
        # Financial Leverage = Total Assets / Total Equity
        ratios['financial_leverage'] = self._safe_divide(assets, equity)
        
        # Interest Coverage = EBIT / Interest Expense
        if is_data is not None:
            ebit: Optional[float] = self._get_value(is_data, 'operating_income')
            interest: Optional[float] = self._get_value(is_data, 'interest_expense')
            ratios['interest_coverage'] = self._safe_divide(ebit, interest)
            
            # EBITDA estimate (approximate)
            ebitda: Optional[float] = ebit  # Would add back depreciation if available
            ratios['debt_to_ebitda'] = self._safe_divide(debt, ebitda)
            ratios['ebitda'] = ebitda
        
        ratios['total_debt'] = debt
        ratios['total_equity'] = equity
        ratios['total_assets'] = assets
        
        return ratios
    
    def calculate_profitability_ratios(
        self, 
        bs_data: pd.DataFrame, 
        is_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Optional[float]]:
        """
        Calculate profitability ratios.
        
        Required fields:
        - gross_profit, operating_income, net_income, revenue, total_assets, total_equity
        """
        ratios: Dict[str, Optional[float]] = {}
        
        if is_data is not None:
            revenue: Optional[float] = self._get_value(is_data, 'revenue')
            gross_profit: Optional[float] = self._get_value(is_data, 'gross_profit')
            operating_income: Optional[float] = self._get_value(is_data, 'operating_income')
            net_income: Optional[float] = self._get_value(is_data, 'net_income')
            
            ratios['gross_margin'] = self._safe_divide(gross_profit, revenue) * 100
            ratios['operating_margin'] = self._safe_divide(operating_income, revenue) * 100
            ratios['net_margin'] = self._safe_divide(net_income, revenue) * 100
            
            ratios['revenue'] = revenue
        
        # Return on Assets = Net Income / Total Assets
        net_income: Optional[float] = (
            self._get_value(is_data, 'net_income') 
            if is_data else None
        )
        assets: Optional[float] = self._get_value(bs_data, 'total_assets')
        ratios['roa'] = self._safe_divide(net_income, assets) * 100
        
        # Return on Equity = Net Income / Total Equity
        equity: Optional[float] = self._get_value(bs_data, 'total_equity')
        ratios['roe'] = self._safe_divide(net_income, equity) * 100
        
        return ratios
    
    def calculate_efficiency_ratios(
        self, 
        bs_data: pd.DataFrame, 
        is_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Optional[float]]:
        """
        Calculate efficiency ratios.
        
        Required fields:
        - revenue, total_assets, accounts_receivable, inventory, 
          accounts_payable, cost_of_revenue
        """
        ratios: Dict[str, Optional[float]] = {}
        
        if is_data is not None:
            revenue: Optional[float] = self._get_value(is_data, 'revenue')
            cogs: Optional[float] = self._get_value(is_data, 'cost_of_revenue')
            
            assets: Optional[float] = self._get_value(bs_data, 'total_assets')
            ar: Optional[float] = self._get_value(bs_data, 'accounts_receivable')
            inv: Optional[float] = self._get_value(bs_data, 'inventory')
            ap: Optional[float] = self._get_value(bs_data, 'accounts_payable')
            
            # Asset Turnover = Revenue / Total Assets
            ratios['asset_turnover'] = self._safe_divide(revenue, assets)
            
            # Receivables Turnover = Revenue / Accounts Receivable
            ratios['receivables_turnover'] = self._safe_divide(revenue, ar)
            
            # Inventory Turnover = COGS / Inventory
            ratios['inventory_turnover'] = self._safe_divide(cogs, inv)
            
            # Payables Turnover = COGS / Accounts Payable
            ratios['payables_turnover'] = self._safe_divide(cogs, ap)
        
        return ratios
    
    def calculate_cash_flow_ratios(
        self, 
        cf_data: pd.DataFrame, 
        bs_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Optional[float]]:
        """
        Calculate cash flow ratios.
        
        Required fields:
        - operating_cf, free_cf, total_debt, revenue
        """
        ratios: Dict[str, Optional[float]] = {}
        
        ocf: Optional[float] = self._get_value(cf_data, 'operating_cf')
        fcf: Optional[float] = self._get_value(cf_data, 'free_cf')
        capex: Optional[float] = self._get_value(cf_data, 'capex')
        debt: Optional[float] = (
            self._get_value(bs_data, 'total_debt') 
            if bs_data else None
        )
        revenue: Optional[float] = self._get_value(cf_data, 'revenue')  # Some CF statements include revenue
        
        # FCF to Debt = Free Cash Flow / Total Debt
        ratios['fcf_to_debt'] = self._safe_divide(fcf, debt)
        
        # FCF to Revenue = Free Cash Flow / Revenue
        ratios['fcf_to_revenue'] = self._safe_divide(fcf, revenue)
        
        # Debt Service Coverage = OCF / (Interest + Principal + Capex)
        # Simplified: just show OCF ratio for now
        ratios['operating_cf_ratio'] = (
            self._safe_divide(ocf, revenue) 
            if revenue else None
        )
        
        return ratios
    
    def calculate_all_ratios(
        self, 
        bs_data: pd.DataFrame, 
        is_data: Optional[pd.DataFrame] = None,
        cf_data: Optional[pd.DataFrame] = None,
        company_name: str = "Unknown",
        fiscal_year: Optional[int] = None
    ) -> CreditRatioAnalysis:
        """
        Calculate all credit ratios from financial statements.
        
        Args:
            bs_data: Balance sheet data (standardized DataFrame)
            is_data: Income statement data (standardized DataFrame)
            cf_data: Cash flow data (standardized DataFrame)
            company_name: Company name for the report
            fiscal_year: Fiscal year being analyzed
        
        Returns:
            CreditRatioAnalysis object with all calculated ratios
        """
        analysis: CreditRatioAnalysis = CreditRatioAnalysis()
        analysis.company_name = company_name
        analysis.fiscal_year = fiscal_year
        analysis.analysis_date = datetime.now()
        
        # Calculate all ratio categories
        liquidity: Dict[str, Optional[float]] = self.calculate_liquidity_ratios(bs_data)
        leverage: Dict[str, Optional[float]] = self.calculate_leverage_ratios(bs_data, is_data)
        profitability: Dict[str, Optional[float]] = self.calculate_profitability_ratios(bs_data, is_data)
        efficiency: Dict[str, Optional[float]] = self.calculate_efficiency_ratios(bs_data, is_data)
        cash_flow: Dict[str, Optional[float]] = self.calculate_cash_flow_ratios(cf_data, bs_data)
        
        # Merge all ratios into the analysis object
        for category in [liquidity, leverage, profitability, efficiency, cash_flow]:
            for key, value in category.items():
                if hasattr(analysis, key):
                    setattr(analysis, key, value)
        
        return analysis
    
    def _get_value(
        self, 
        df: Optional[pd.DataFrame], 
        key: str
    ) -> Optional[float]:
        """Extract a single value from standardized financial data."""
        if df is None or df.empty:
            return None
        if key in df.index:
            value = df.loc[key]
            if hasattr(value, 'iloc'):
                value = value.iloc[0] if len(value) > 0 else None
            return float(value) if value else None
        return None
    
    def export_ratios(
        self, 
        analysis: CreditRatioAnalysis, 
        format: Literal['json', 'csv'] = 'json'
    ) -> str:
        """
        Export ratio analysis to file.
        
        Args:
            analysis: CreditRatioAnalysis object
            format: 'json' or 'csv'
        
        Returns:
            Path to exported file
        """
        if format == 'json':
            output_path: Path = self.report_dir / f"credit_ratios_{analysis.fiscal_year}.json"
            with open(output_path, 'w') as f:
                json.dump(analysis.to_dict(), f, indent=2, default=str)
        elif format == 'csv':
            output_path: Path = self.report_dir / f"credit_ratios_{analysis.fiscal_year}.csv"
            analysis.to_dataframe().to_csv(output_path, index=False)
        
        return str(output_path)


if __name__ == "__main__":
    # Example usage demonstration
    analyzer: RatioAnalyzer = RatioAnalyzer()
    print("Ratio Analyzer initialized.")
    print("Usage: analyzer.calculate_all_ratios(bs_data, is_data, cf_data)")
    print("\nKey ratios calculated:")
    print("- Liquidity: Current, Quick, Cash ratios")
    print("- Leverage: Debt/Equity, Debt/Assets, Interest Coverage")
    print("- Profitability: Margins, ROA, ROE")
    print("- Efficiency: Asset Turnover, Inventory Turnover")
    print("- Cash Flow: FCF/Debt, FCF/Revenue")
