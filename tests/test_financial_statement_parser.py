"""
Test suite for financial_statement_parser module.

Tests cover:
- FileParsingError exception
- FinancialStatement dataclass
- FinancialStatementParser class

Run with: pytest tests/test_financial_statement_parser.py -v
"""

import pytest
from datetime import datetime
import pandas as pd

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from financial_statement_parser import (
    FileParsingError,
    FinancialStatement,
    FinancialStatementParser,
    RiskFactorsValidator,
)


class TestFileParsingError:
    """Tests for FileParsingError exception."""
    
    def test_error_creation(self):
        error = FileParsingError(
            file_path="/path/to/file.csv",
            file_format="CSV",
            reason="Parse failed"
        )
        assert "/path/to/file.csv" in str(error)
        assert "CSV" in str(error)


class TestFinancialStatement:
    """Tests for FinancialStatement dataclass."""
    
    def test_statement_creation(self):
        df = pd.DataFrame({'A': [1, 2, 3]})
        statement = FinancialStatement(
            company_name="Test Corp",
            fiscal_year=2024,
            statement_type="balance_sheet",
            data=df
        )
        assert statement.company_name == "Test Corp"
        assert statement.fiscal_year == 2024
        assert statement.statement_type == "balance_sheet"
        assert isinstance(statement.data, pd.DataFrame)
    
    def test_statement_with_defaults(self):
        df = pd.DataFrame({'A': [1]})
        statement = FinancialStatement(
            company_name="Test",
            fiscal_year=2024,
            statement_type="income_statement",
            data=df
        )
        assert statement.currency == "USD"
        assert statement.metadata == {}
    
    def test_statement_to_dict(self):
        df = pd.DataFrame({'A': [1]})
        statement = FinancialStatement(
            company_name="Test Corp",
            fiscal_year=2024,
            statement_type="balance_sheet",
            data=df
        )
        data = statement.to_dict()
        assert data['company_name'] == "Test Corp"
        assert data['fiscal_year'] == 2024


class TestFinancialStatementParser:
    """Tests for FinancialStatementParser class."""
    
    def test_parser_initialization(self):
        parser = FinancialStatementParser()
        assert parser is not None
        assert hasattr(parser, 'parsed_statements')
    
    def test_parsed_statements_empty(self):
        parser = FinancialStatementParser()
        statements = parser.parsed_statements
        assert isinstance(statements, list)
        assert len(statements) == 0


class TestParserValidation:
    """Tests for parser validation."""
    
    def test_validate_company_name(self):
        result = RiskFactorsValidator.validate_company_name("  Test Corp  ")
        assert result == "Test Corp"
    
    def test_validate_fiscal_year(self):
        assert RiskFactorsValidator.validate_fiscal_year(2024) == 2024
        assert RiskFactorsValidator.validate_fiscal_year(None) is None
    
    def test_validate_currency(self):
        assert RiskFactorsValidator.validate_currency("USD") == "USD"
    
    def test_validate_statement_type(self):
        assert RiskFactorsValidator.validate_statement_type("income_statement") == "income_statement"
        assert RiskFactorsValidator.validate_statement_type("balance_sheet") == "balance_sheet"
        assert RiskFactorsValidator.validate_statement_type("cash_flow") == "cash_flow"
    
    def test_validate_statement_type_invalid(self):
        with pytest.raises(Exception):  # May raise various exceptions
            RiskFactorsValidator.validate_statement_type("invalid")


class TestIntegration:
    """Integration tests."""
    
    def test_full_parse_workflow(self):
        """Test complete parsing workflow."""
        # Create sample data
        data = pd.DataFrame({
            'Period': ['2024', '2023'],
            'revenue': [100000, 90000],
            'net_income': [24800, 21760]
        })
        
        parser = FinancialStatementParser()
        
        statement = parser.parse_from_dataframe(
            data,
            statement_type="income_statement",
            company_name="Test Corp",
            fiscal_year=2024
        )
        
        assert statement.company_name == "Test Corp"
        assert statement.fiscal_year == 2024
        assert statement.statement_type == "income_statement"
        assert len(parser.parsed_statements) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
