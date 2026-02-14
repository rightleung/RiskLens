"""
Test suite for ratio_analyzer module - Basic smoke tests.

Run with: pytest tests/test_ratio_analyzer.py -v
"""

import pytest
import pandas as pd

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ratio_analyzer import (
    CreditRatioAnalysis,
    RatioAnalyzer,
)


class TestCreditRatioAnalysis:
    """Basic tests for CreditRatioAnalysis class."""
    
    def test_creation(self):
        """Test creating a ratio analysis."""
        analysis = CreditRatioAnalysis()
        analysis.current_ratio = 3.0
        analysis.debt_to_equity = 0.5
        analysis.company_name = "Test Corp"
        
        assert analysis.company_name == "Test Corp"
        assert analysis.current_ratio == 3.0
    
    def test_defaults(self):
        """Test default values."""
        analysis = CreditRatioAnalysis()
        assert analysis.current_ratio is None
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        analysis = CreditRatioAnalysis()
        analysis.current_ratio = 2.5
        
        data = analysis.to_dict()
        assert isinstance(data, dict)
        assert 'current_ratio' in data
    
    def test_to_dataframe(self):
        """Test conversion to DataFrame."""
        analysis = CreditRatioAnalysis()
        analysis.current_ratio = 2.5
        analysis.debt_to_equity = 0.8
        
        df = analysis.to_dataframe()
        assert isinstance(df, pd.DataFrame)


class TestRatioAnalyzer:
    """Basic tests for RatioAnalyzer class."""
    
    def test_initialization(self, tmp_path):
        """Test analyzer initialization."""
        analyzer = RatioAnalyzer(str(tmp_path))
        assert analyzer is not None
    
    def test_calculate_liquidity_ratios(self):
        """Test liquidity ratio calculations - smoke test."""
        # Create indexed DataFrame for _get_value method
        data = pd.DataFrame({
            'value': [15000, 5000, 8000, 6000, 45000, 12000]
        }, index=['cash', 'short_term_investments', 'accounts_receivable', 
                  'inventory', 'total_current_assets', 'total_current_liabilities'])
        
        analyzer = RatioAnalyzer("/tmp")
        ratios = analyzer.calculate_liquidity_ratios(data)
        
        assert isinstance(ratios, dict)
        assert 'current_ratio' in ratios
    
    def test_calculate_leverage_ratios(self):
        """Test leverage ratio calculations - smoke test."""
        bs_data = pd.DataFrame({
            'value': [37000, 53000, 90000, 15000, 6000]
        }, index=['total_liabilities', 'total_equity', 'total_assets',
                  'cash', 'inventory'])
        
        is_data = pd.DataFrame({
            'value': [33000, 2000]
        }, index=['operating_income', 'interest_expense'])
        
        analyzer = RatioAnalyzer("/tmp")
        ratios = analyzer.calculate_leverage_ratios(bs_data, is_data)
        
        assert isinstance(ratios, dict)
        assert 'debt_to_equity' in ratios
    
    def test_calculate_efficiency_ratios(self):
        """Test efficiency ratio calculations - smoke test."""
        bs_data = pd.DataFrame({
            'value': [100000, 25000, 8000, 6000, 40000]
        }, index=['revenue', 'property_plant_equipment', 'accounts_receivable',
                  'inventory', 'cost_of_revenue'])
        
        analyzer = RatioAnalyzer("/tmp")
        ratios = analyzer.calculate_efficiency_ratios(bs_data)
        
        assert isinstance(ratios, dict)


class TestExport:
    """Export functionality tests."""
    
    def test_export_json(self, tmp_path):
        """Test exporting ratios to JSON."""
        analyzer = RatioAnalyzer(str(tmp_path))
        
        # Create CreditRatioAnalysis object
        analysis = CreditRatioAnalysis()
        analysis.current_ratio = 2.5
        analysis.debt_to_equity = 0.65
        
        result = analyzer.export_ratios(analysis, format='json')
        
        # Should return a path in the output directory
        assert result.endswith('.json')
        assert 'test' in result or 'credit' in result
    
    def test_export_csv(self, tmp_path):
        """Test exporting ratios to CSV."""
        analyzer = RatioAnalyzer(str(tmp_path))
        
        analysis = CreditRatioAnalysis()
        analysis.current_ratio = 2.5
        analysis.debt_to_equity = 0.65
        
        result = analyzer.export_ratios(analysis, format='csv')
        
        # Should return a path in the output directory
        assert result.endswith('.csv')
        assert 'test' in result or 'credit' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
