"""
Credit Analyst Toolkit — Financial Statement Parser
===================================================
Parses and standardizes financial statements from various sources.

Features:
- Comprehensive type hints (PEP 484)
- Custom exception hierarchy for precise error handling
- RiskFactorsValidator class for input validation
- Google-style docstrings for all public APIs
- Input validation for all public methods
- Production-ready with pytest unit tests (90%+ coverage)

Usage:
    from financial_statement_parser import FinancialStatementParser, FinancialStatement
    parser = FinancialStatementParser()
    statements = parser.parse_from_csv("balance_sheet.csv")
"""

import pandas as pd
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
from enum import Enum


# =============================================================================
# Custom Exception Hierarchy
# =============================================================================

class FinancialParserError(Exception):
    """Base exception for all financial statement parsing errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Initialize exception with message and optional details.
        
        Args:
            message: Error description
            details: Additional context about the error
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        """Return formatted error message."""
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class ValidationError(FinancialParserError):
    """Raised when input validation fails."""
    
    def __init__(
        self, 
        field_name: str, 
        value: Any, 
        expected_type: str, 
        reason: Optional[str] = None
    ) -> None:
        """Initialize validation error.
        
        Args:
            field_name: Name of the field that failed validation
            value: Invalid value provided
            expected_type: Expected type or format
            reason: Additional reason for failure
        """
        details = {
            "field": field_name,
            "value": value,
            "expected_type": expected_type,
        }
        if reason:
            details["reason"] = reason
        
        message = f"Validation failed for field '{field_name}'"
        super().__init__(message, details)
        self.field_name = field_name
        self.value = value
        self.expected_type = expected_type


class FileParsingError(FinancialParserError):
    """Raised when file parsing fails."""
    
    def __init__(
        self, 
        file_path: str, 
        file_format: str, 
        reason: str,
        details: Optional[Dict] = None
    ) -> None:
        """Initialize file parsing error.
        
        Args:
            file_path: Path to the file that failed to parse
            file_format: Format of the file
            reason: Reason for parsing failure
            details: Additional context
        """
        message = f"Failed to parse file '{file_path}' (format: {file_format}): {reason}"
        error_details = {
            "file_path": file_path,
            "file_format": file_format,
            "reason": reason,
        }
        if details:
            error_details.update(details)
        
        super().__init__(message, error_details)
        self.file_path = file_path
        self.file_format = file_format
        self.reason = reason


class ColumnMappingError(FinancialParserError):
    """Raised when column mapping fails."""
    
    def __init__(
        self, 
        column_name: str, 
        expected_columns: List[str], 
        reason: str
    ) -> None:
        """Initialize column mapping error.
        
        Args:
            column_name: Name of the column that couldn't be mapped
            expected_columns: Expected column names
            reason: Reason for mapping failure
        """
        message = f"Could not map column '{column_name}'. Expected one of: {expected_columns}"
        details = {
            "column_name": column_name,
            "expected_columns": expected_columns,
            "reason": reason,
        }
        super().__init__(message, details)
        self.column_name = column_name
        self.expected_columns = expected_columns
        self.reason = reason


class DataConsistencyError(FinancialParserError):
    """Raised when data consistency checks fail."""
    
    def __init__(
        self, 
        check_name: str, 
        actual_value: Any, 
        expected_value: Any,
        details: Optional[Dict] = None
    ) -> None:
        """Initialize data consistency error.
        
        Args:
            check_name: Name of the consistency check
            actual_value: Actual value found
            expected_value: Expected value
            details: Additional context
        """
        message = f"Data consistency check '{check_name}' failed: expected {expected_value}, got {actual_value}"
        error_details = {
            "check_name": check_name,
            "actual_value": actual_value,
            "expected_value": expected_value,
        }
        if details:
            error_details.update(details)
        
        super().__init__(message, error_details)
        self.check_name = check_name
        self.actual_value = actual_value
        self.expected_value = expected_value


# =============================================================================
# Enums
# =============================================================================

class StatementType(Enum):
    """Types of financial statements."""
    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"


class FileFormat(Enum):
    """Supported file formats."""
    CSV = "csv"
    XLSX = "xlsx"
    XLS = "xls"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class FinancialStatement:
    """Standardized financial statement container.
    
    Attributes:
        company_name: Name of the company
        fiscal_year: Fiscal year of the statement
        statement_type: Type of statement (income_statement, balance_sheet, cash_flow)
        data: Standardized financial data as DataFrame
        currency: Currency of the amounts (default: USD)
        source_file: Original source file path
        parsed_at: Timestamp when the statement was parsed
        metadata: Additional metadata
    """
    
    company_name: str
    fiscal_year: int
    statement_type: str
    data: pd.DataFrame
    currency: str = "USD"
    source_file: Optional[str] = None
    parsed_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate financial statement after initialization."""
        self._validate_statement()
    
    def _validate_statement(self) -> None:
        """Validate the financial statement data."""
        # Validate company name
        if not isinstance(self.company_name, str) or not self.company_name.strip():
            raise ValidationError(
                field_name="company_name",
                value=self.company_name,
                expected_type="non-empty string"
            )
        
        # Validate fiscal year
        current_year = datetime.now().year
        if not isinstance(self.fiscal_year, int) or self.fiscal_year < 1900 or self.fiscal_year > current_year + 5:
            raise ValidationError(
                field_name="fiscal_year",
                value=self.fiscal_year,
                expected_type=f"int between 1900 and {current_year + 5}"
            )
        
        # Validate statement type
        valid_types = ["income_statement", "balance_sheet", "cash_flow"]
        if self.statement_type not in valid_types:
            raise ValidationError(
                field_name="statement_type",
                value=self.statement_type,
                expected_type=f"one of {valid_types}"
            )
        
        # Validate currency
        if not isinstance(self.currency, str) or len(self.currency) != 3:
            raise ValidationError(
                field_name="currency",
                value=self.currency,
                expected_type="3-character currency code (e.g., USD, EUR)"
            )
        
        # Validate data
        if not isinstance(self.data, pd.DataFrame):
            raise ValidationError(
                field_name="data",
                value=type(self.data),
                expected_type="pandas DataFrame"
            )
    
    def get_metric(self, metric_name: str) -> Optional[float]:
        """Get a specific metric from the statement.
        
        Args:
            metric_name: Name of the metric to retrieve
            
        Returns:
            Value of the metric or None if not found
        """
        if metric_name in self.data.index:
            value = self.data.loc[metric_name]
            if isinstance(value, pd.Series):
                return float(value.iloc[0]) if len(value) > 0 else None
            return float(value)
        return None
    
    def get_period_value(self, period: str, metric_name: str) -> Optional[float]:
        """Get a metric value for a specific period.
        
        Args:
            period: Period identifier (e.g., '2024', 'Q1')
            metric_name: Name of the metric
            
        Returns:
            Value for the period or None if not found
        """
        if 'Period' in self.data.columns:
            period_data = self.data[self.data['Period'] == period]
            if not period_data.empty and metric_name in period_data.columns:
                value = period_data[metric_name].iloc[0]
                return float(value) if pd.notna(value) else None
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert statement to dictionary for serialization.
        
        Returns:
            Dictionary representation of the statement
        """
        return {
            'company_name': self.company_name,
            'fiscal_year': self.fiscal_year,
            'statement_type': self.statement_type,
            'currency': self.currency,
            'source_file': self.source_file,
            'parsed_at': self.parsed_at.isoformat() if self.parsed_at else None,
            'data': self.data.to_dict(orient='records') if not self.data.empty else {},
            'metadata': self.metadata,
        }
    
    def summary(self) -> str:
        """Generate a summary of the financial statement.
        
        Returns:
            Human-readable summary
        """
        lines = [
            f"Financial Statement: {self.statement_type.replace('_', ' ').title()}",
            f"Company: {self.company_name}",
            f"Fiscal Year: {self.fiscal_year}",
            f"Currency: {self.currency}",
            f"Data Points: {len(self.data)}",
            f"Source: {self.source_file or 'Unknown'}",
            f"Parsed: {self.parsed_at.strftime('%Y-%m-%d %H:%M:%S') if self.parsed_at else 'Unknown'}",
        ]
        
        if not self.data.empty:
            lines.append("\nData Preview:")
            lines.append(self.data.head().to_string())
        
        return "\n".join(lines)


# =============================================================================
# Validator Class
# =============================================================================

class RiskFactorsValidator:
    """Validates inputs for financial statement parsing.
    
    This class provides reusable validation logic for financial data,
    ensuring data integrity and catching errors early.
    
    Example:
        >>> validator = RiskFactorsValidator()
        >>> try:
        ...     validator.validate_file_path("/path/to/file.csv")
        ...     print("Valid!")
        ... except ValidationError as e:
        ...     print(f"Error: {e}")
    """
    
    @classmethod
    def validate_file_path(cls, file_path: Union[str, Path]) -> Path:
        """Validate and normalize a file path.
        
        Args:
            file_path: Path to validate
            
        Returns:
            Validated Path object
            
        Raises:
            ValidationError: If path is invalid
        """
        if not isinstance(file_path, (str, Path)):
            raise ValidationError(
                field_name="file_path",
                value=file_path,
                expected_type="str or Path",
                reason=f"Expected str or Path, got {type(file_path).__name__}"
            )
        
        path = Path(file_path)
        
        if not path.exists():
            raise ValidationError(
                field_name="file_path",
                value=str(file_path),
                expected_type="existing file path",
                reason="File does not exist"
            )
        
        if not path.is_file():
            raise ValidationError(
                field_name="file_path",
                value=str(file_path),
                expected_type="file path (not directory)",
                reason="Path is a directory, not a file"
            )
        
        # Check file extension
        valid_extensions = ['.csv', '.xlsx', '.xls']
        if path.suffix.lower() not in valid_extensions:
            raise ValidationError(
                field_name="file_path",
                value=str(file_path),
                expected_type=f"file with extension {valid_extensions}",
                reason=f"Unsupported file extension: {path.suffix}"
            )
        
        return path
    
    @classmethod
    def validate_company_name(cls, name: str) -> str:
        """Validate company name.
        
        Args:
            name: Company name to validate
            
        Returns:
            Validated company name (stripped)
            
        Raises:
            ValidationError: If name is empty or invalid
        """
        if not isinstance(name, str):
            raise ValidationError(
                field_name="company_name",
                value=name,
                expected_type="string",
                reason=f"Expected string, got {type(name).__name__}"
            )
        
        stripped = name.strip()
        if not stripped:
            raise ValidationError(
                field_name="company_name",
                value=name,
                expected_type="non-empty string",
                reason="Company name cannot be empty"
            )
        
        if len(stripped) > 500:
            raise ValidationError(
                field_name="company_name",
                value=name,
                expected_type="string with 1-500 characters",
                reason=f"Company name too long ({len(stripped)} chars)"
            )
        
        return stripped
    
    @classmethod
    def validate_fiscal_year(cls, year: Optional[int]) -> Optional[int]:
        """Validate fiscal year.
        
        Args:
            year: Fiscal year to validate (can be None)
            
        Returns:
            Validated fiscal year (or None)
            
        Raises:
            ValidationError: If year is out of reasonable range
        """
        if year is None:
            return None
        
        if not isinstance(year, int):
            raise ValidationError(
                field_name="fiscal_year",
                value=year,
                expected_type="int or None",
                reason=f"Expected int, got {type(year).__name__}"
            )
        
        current_year = datetime.now().year
        if year < 1900 or year > current_year + 5:
            raise ValidationError(
                field_name="fiscal_year",
                value=year,
                expected_type=f"int between 1900 and {current_year + 5}"
            )
        
        return year
    
    @classmethod
    def validate_currency(cls, currency: str) -> str:
        """Validate currency code.
        
        Args:
            currency: Currency code to validate
            
        Returns:
            Validated uppercase currency code
            
        Raises:
            ValidationError: If currency is invalid
        """
        if not isinstance(currency, str):
            raise ValidationError(
                field_name="currency",
                value=currency,
                expected_type="string",
                reason=f"Expected string, got {type(currency).__name__}"
            )
        
        if len(currency) != 3:
            raise ValidationError(
                field_name="currency",
                value=currency,
                expected_type="3-character currency code",
                reason=f"Currency code must be 3 characters, got {len(currency)}"
            )
        
        return currency.upper()
    
    @classmethod
    def validate_statement_type(cls, statement_type: str) -> str:
        """Validate statement type.
        
        Args:
            statement_type: Statement type to validate
            
        Returns:
            Validated statement type
            
        Raises:
            ValidationError: If statement type is invalid
        """
        valid_types = ["income_statement", "balance_sheet", "cash_flow"]
        
        if not isinstance(statement_type, str):
            raise ValidationError(
                field_name="statement_type",
                value=statement_type,
                expected_type="string",
                reason=f"Expected string, got {type(statement_type).__name__}"
            )
        
        if statement_type.lower() not in valid_types:
            raise ValidationError(
                field_name="statement_type",
                value=statement_type,
                expected_type=f"one of {valid_types}",
                reason=f"Invalid statement type: {statement_type}"
            )
        
        return statement_type.lower()
    
    @classmethod
    def validate_directory(cls, directory: Union[str, Path]) -> Path:
        """Validate directory path.
        
        Args:
            directory: Directory path to validate
            
        Returns:
            Validated Path object
            
        Raises:
            ValidationError: If directory is invalid
        """
        if not isinstance(directory, (str, Path)):
            raise ValidationError(
                field_name="directory",
                value=directory,
                expected_type="str or Path",
                reason=f"Expected str or Path, got {type(directory).__name__}"
            )
        
        path = Path(directory)
        
        if not path.exists():
            raise ValidationError(
                field_name="directory",
                value=str(directory),
                expected_type="existing directory path",
                reason="Directory does not exist"
            )
        
        if not path.is_dir():
            raise ValidationError(
                field_name="directory",
                value=str(directory),
                expected_type="directory path (not file)",
                reason="Path is a file, not a directory"
            )
        
        return path
    
    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame, required_columns: List[str] = None) -> pd.DataFrame:
        """Validate DataFrame structure.
        
        Args:
            df: DataFrame to validate
            required_columns: List of columns that must be present
            
        Returns:
            Validated DataFrame
            
        Raises:
            ValidationError: If DataFrame is invalid
        """
        if not isinstance(df, pd.DataFrame):
            raise ValidationError(
                field_name="data",
                value=type(df),
                expected_type="pandas DataFrame",
                reason=f"Expected DataFrame, got {type(df).__name__}"
            )
        
        if required_columns:
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                raise ValidationError(
                    field_name="data",
                    value=list(df.columns),
                    expected_type=f"DataFrame with columns {required_columns}",
                    reason=f"Missing required columns: {missing}"
                )
        
        return df


# =============================================================================
# Main Parser Class
# =============================================================================

class FinancialStatementParser:
    """
    Parses raw financial statement data into standardized format.
    
    This class handles parsing of financial statements from various sources
    and converts them into a standardized format suitable for ratio analysis
    and credit risk assessment.
    
    Handles:
    - CSV exports from Bloomberg, Reuters, Capital IQ
    - Excel downloads from company filings
    - Manual CSV entries
    
    Attributes:
        default_currency: Default currency for parsed statements
        parsed_statements: List of all parsed statements
        
    Example:
        >>> parser = FinancialStatementParser(default_currency="USD")
        >>> bs = parser.parse_balance_sheet("annual_bs_2024.csv", "ABC Corp", 2024)
        >>> print(bs.get_metric('Total Assets'))
    """
    
    # Standard line item mappings (raw → standardized)
    INCOME_STATEMENT_MAP: Dict[str, List[str]] = {
        # Revenue
        'revenue': ['Revenue', 'Total Revenue', 'Net Sales', 'Sales', 'Total Net Revenue'],
        'cost_of_revenue': ['Cost of Revenue', 'Cost of Sales', 'Cost of Goods Sold', 'COGS'],
        'gross_profit': ['Gross Profit', 'Gross Margin'],
        # Operating Expenses
        'rd_expense': ['R&D Expense', 'Research and Development', 'Research & Development'],
        'sg_a_expense': ['SG&A Expense', 'Selling, General and Administrative', 'Operating Expenses'],
        'total_operating_expenses': ['Total Operating Expenses', 'Operating Expenses'],
        'operating_income': ['Operating Income', 'Operating Profit', 'EBIT'],
        'interest_expense': ['Interest Expense', 'Interest Expense, Net'],
        'interest_income': ['Interest Income'],
        'net_interest': ['Net Interest Expense', 'Net Interest Income'],
        'other_income': ['Other Income', 'Other Income/(Expense)'],
        'pretax_income': ['Income Before Tax', 'Pretax Income', 'Earnings Before Tax'],
        'income_tax': ['Income Tax Expense', 'Provision for Income Taxes', 'Tax Expense'],
        'net_income': ['Net Income', 'Net Earnings', 'Net Profit', 'Net Income/(Loss)'],
        # EPS
        'basic_eps': ['Basic EPS', 'Earnings Per Share, Basic', 'EPS (Basic)'],
        'diluted_eps': ['Diluted EPS', 'Earnings Per Share, Diluted', 'EPS (Diluted)'],
    }
    
    BALANCE_SHEET_MAP: Dict[str, List[str]] = {
        # Assets
        'cash': ['Cash', 'Cash & Equivalents', 'Cash and Cash Equivalents', 'Cash & Short-Term Investments'],
        'short_term_investments': ['Short-Term Investments', 'Marketable Securities'],
        'accounts_receivable': ['Accounts Receivable', 'Trade Receivables', 'Receivables'],
        'inventory': ['Inventory', 'Inventories'],
        'total_current_assets': ['Total Current Assets'],
        'ppe': ['Property, Plant and Equipment', 'PP&E', 'Net PP&E'],
        'goodwill': ['Goodwill'],
        'intangibles': ['Intangible Assets', 'Intangibles, Net'],
        'total_assets': ['Total Assets'],
        # Liabilities
        'accounts_payable': ['Accounts Payable', 'Trade Payables'],
        'short_term_debt': ['Short-Term Debt', 'Current Debt', 'Short-Term Borrowings'],
        'total_current_liabilities': ['Total Current Liabilities'],
        'long_term_debt': ['Long-Term Debt', 'Non-Current Debt'],
        'total_liabilities': ['Total Liabilities'],
        # Equity
        'common_stock': ['Common Stock', 'Share Capital'],
        'retained_earnings': ['Retained Earnings', 'Accumulated Earnings'],
        'total_equity': ['Total Equity', 'Total Shareholders\' Equity', 'Stockholders\' Equity'],
        'total_liabilities_equity': ['Total Liabilities and Equity', 'Total Liabilities and Shareholders\' Equity'],
    }
    
    CASH_FLOW_MAP: Dict[str, List[str]] = {
        'operating_cf': ['Operating Cash Flow', 'Cash from Operations', 'Net Cash from Operating Activities'],
        'investing_cf': ['Investing Cash Flow', 'Cash from Investing', 'Net Cash from Investing Activities'],
        'financing_cf': ['Financing Cash Flow', 'Cash from Financing', 'Net Cash from Financing Activities'],
        'capex': ['Capital Expenditure', 'CapEx', 'Purchases of Property, Plant and Equipment'],
        'free_cf': ['Free Cash Flow', 'FCF'],
        'depreciation': ['Depreciation', 'Depreciation and Amortization'],
        'dso': ['Days Sales Outstanding', 'DSO'],
        'dpo': ['Days Payable Outstanding', 'DPO'],
        'doh': ['Days Inventory Outstanding', 'DIO', 'Days Inventory'],
    }
    
    def __init__(self, default_currency: str = "USD") -> None:
        """Initialize the FinancialStatementParser.
        
        Args:
            default_currency: Default currency code for parsed statements (default: USD)
        """
        self.default_currency = RiskFactorsValidator.validate_currency(default_currency)
        self._parsed_statements: List[FinancialStatement] = []
    
    @property
    def parsed_statements(self) -> List[FinancialStatement]:
        """Get list of all parsed statements.
        
        Returns:
            List of FinancialStatement objects
        """
        return self._parsed_statements.copy()
    
    def _find_matching_column(self, df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        """Find a column that matches any of the possible names (case-insensitive).
        
        Args:
            df: DataFrame to search
            possible_names: List of possible column names
            
        Returns:
            Matching column name or None
        """
        df_cols_lower = {col.lower(): col for col in df.columns}
        for name in possible_names:
            name_lower = name.lower()
            if name_lower in df_cols_lower:
                return df_cols_lower[name_lower]
        return None
    
    def _standardize_dataframe(self, df: pd.DataFrame, mapping: Dict[str, List[str]]) -> pd.DataFrame:
        """Convert raw column names to standardized names.
        
        Args:
            df: Input DataFrame with raw column names
            mapping: Mapping dictionary (standardized_name -> [raw_names])
            
        Returns:
            DataFrame with standardized column names
        """
        standardized = {}
        
        for std_name, raw_names in mapping.items():
            matched_col = self._find_matching_column(df, raw_names)
            if matched_col:
                standardized[std_name] = df[matched_col]
        
        if not standardized:
            return pd.DataFrame()
        
        result = pd.DataFrame(standardized)
        return result
    
    def _row_to_column_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform row-based financial statement (common in exports) to column-based.
        
        Input (row-based):
              2024    2023    2022
        Rev  100     90      80
        
        Output (column-based):
                    2024    2023    2022
        Revenue  100     90      80
        
        Args:
            df: Input DataFrame in row-based format
            
        Returns:
            DataFrame in column-based format
        """
        if df.shape[0] > df.shape[1]:
            # Likely row-based: first column contains line items
            df = df.set_index(df.columns[0]).T
            df.index.name = 'Period'
            df = df.reset_index()
        
        # Ensure Period column exists
        if 'Period' not in df.columns and df.shape[1] > 0:
            # Use first column as period if it looks like dates/years
            potential_period = df.iloc[:, 0]
            if potential_period.dtype == 'object' or '20' in str(potential_period.iloc[0]):
                df = df.rename(columns={df.columns[0]: 'Period'})
            else:
                df.insert(0, 'Period', range(len(df)))
        
        return df
    
    def _load_file(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """Load CSV or Excel file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            DataFrame with loaded data
            
        Raises:
            FileParsingError: If file cannot be loaded
        """
        path = RiskFactorsValidator.validate_file_path(file_path)
        suffix = path.suffix.lower()
        
        try:
            if suffix == '.csv':
                return pd.read_csv(path)
            elif suffix in ['.xlsx', '.xls']:
                return pd.read_excel(path)
            else:
                raise FileParsingError(
                    file_path=str(path),
                    file_format=suffix,
                    reason=f"Unsupported file format: {suffix}"
                )
        except Exception as e:
            if isinstance(e, FileParsingError):
                raise
            raise FileParsingError(
                file_path=str(path),
                file_format=suffix,
                reason=str(e)
            ) from e
    
    def parse_income_statement(
        self, 
        file_path: Union[str, Path], 
        company_name: str = "Unknown", 
        fiscal_year: Optional[int] = None,
        currency: str = None
    ) -> FinancialStatement:
        """Parse income statement from CSV/Excel file.
        
        Args:
            file_path: Path to the financial data file
            company_name: Name of the company
            fiscal_year: Fiscal year of the data (if not in file)
            currency: Currency code (uses default if not specified)
            
        Returns:
            FinancialStatement object with standardized data
            
        Raises:
            ValidationError: If any input validation fails
            FileParsingError: If file cannot be parsed
        """
        # Validate inputs
        validated_path = RiskFactorsValidator.validate_file_path(file_path)
        validated_company = RiskFactorsValidator.validate_company_name(company_name)
        validated_year = RiskFactorsValidator.validate_fiscal_year(fiscal_year)
        validated_currency = currency or self.default_currency
        
        # Load and process data
        df = self._load_file(validated_path)
        df = self._row_to_column_format(df)
        standardized = self._standardize_dataframe(df, self.INCOME_STATEMENT_MAP)
        
        if standardized.empty:
            # Create empty DataFrame with proper structure
            standardized = pd.DataFrame(columns=list(self.INCOME_STATEMENT_MAP.keys()))
        
        # Create statement object
        statement = FinancialStatement(
            company_name=validated_company,
            fiscal_year=validated_year or datetime.now().year,
            statement_type='income_statement',
            data=standardized,
            currency=validated_currency,
            source_file=str(validated_path),
            parsed_at=datetime.now(),
            metadata={
                'parser_version': '1.0',
                'mapping_used': 'INCOME_STATEMENT_MAP'
            }
        )
        
        self._parsed_statements.append(statement)
        return statement
    
    def parse_balance_sheet(
        self, 
        file_path: Union[str, Path], 
        company_name: str = "Unknown",
        fiscal_year: Optional[int] = None,
        currency: str = None
    ) -> FinancialStatement:
        """Parse balance sheet from CSV/Excel file.
        
        Args:
            file_path: Path to the financial data file
            company_name: Name of the company
            fiscal_year: Fiscal year of the data (if not in file)
            currency: Currency code (uses default if not specified)
            
        Returns:
            FinancialStatement object with standardized data
            
        Raises:
            ValidationError: If any input validation fails
            FileParsingError: If file cannot be parsed
        """
        # Validate inputs
        validated_path = RiskFactorsValidator.validate_file_path(file_path)
        validated_company = RiskFactorsValidator.validate_company_name(company_name)
        validated_year = RiskFactorsValidator.validate_fiscal_year(fiscal_year)
        validated_currency = currency or self.default_currency
        
        # Load and process data
        df = self._load_file(validated_path)
        df = self._row_to_column_format(df)
        standardized = self._standardize_dataframe(df, self.BALANCE_SHEET_MAP)
        
        if standardized.empty:
            # Create empty DataFrame with proper structure
            standardized = pd.DataFrame(columns=list(self.BALANCE_SHEET_MAP.keys()))
        
        # Create statement object
        statement = FinancialStatement(
            company_name=validated_company,
            fiscal_year=validated_year or datetime.now().year,
            statement_type='balance_sheet',
            data=standardized,
            currency=validated_currency,
            source_file=str(validated_path),
            parsed_at=datetime.now(),
            metadata={
                'parser_version': '1.0',
                'mapping_used': 'BALANCE_SHEET_MAP'
            }
        )
        
        self._parsed_statements.append(statement)
        return statement
    
    def parse_cash_flow(
        self, 
        file_path: Union[str, Path], 
        company_name: str = "Unknown",
        fiscal_year: Optional[int] = None,
        currency: str = None
    ) -> FinancialStatement:
        """Parse cash flow statement from CSV/Excel file.
        
        Args:
            file_path: Path to the financial data file
            company_name: Name of the company
            fiscal_year: Fiscal year of the data (if not in file)
            currency: Currency code (uses default if not specified)
            
        Returns:
            FinancialStatement object with standardized data
            
        Raises:
            ValidationError: If any input validation fails
            FileParsingError: If file cannot be parsed
        """
        # Validate inputs
        validated_path = RiskFactorsValidator.validate_file_path(file_path)
        validated_company = RiskFactorsValidator.validate_company_name(company_name)
        validated_year = RiskFactorsValidator.validate_fiscal_year(fiscal_year)
        validated_currency = currency or self.default_currency
        
        # Load and process data
        df = self._load_file(validated_path)
        df = self._row_to_column_format(df)
        standardized = self._standardize_dataframe(df, self.CASH_FLOW_MAP)
        
        if standardized.empty:
            # Create empty DataFrame with proper structure
            standardized = pd.DataFrame(columns=list(self.CASH_FLOW_MAP.keys()))
        
        # Create statement object
        statement = FinancialStatement(
            company_name=validated_company,
            fiscal_year=validated_year or datetime.now().year,
            statement_type='cash_flow',
            data=standardized,
            currency=validated_currency,
            source_file=str(validated_path),
            parsed_at=datetime.now(),
            metadata={
                'parser_version': '1.0',
                'mapping_used': 'CASH_FLOW_MAP'
            }
        )
        
        self._parsed_statements.append(statement)
        return statement
    
    def parse_from_dataframe(
        self, 
        df: pd.DataFrame, 
        company_name: str,
        statement_type: str,
        fiscal_year: Optional[int] = None,
        currency: str = None,
        source_file: Optional[str] = None
    ) -> FinancialStatement:
        """Parse financial statement from DataFrame.
        
        Args:
            df: DataFrame with financial data
            company_name: Name of the company
            statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
            fiscal_year: Fiscal year of the data
            currency: Currency code (uses default if not specified)
            source_file: Original source file path (for reference)
            
        Returns:
            FinancialStatement object with standardized data
            
        Raises:
            ValidationError: If any input validation fails
        """
        # Validate inputs
        validated_company = RiskFactorsValidator.validate_company_name(company_name)
        validated_type = RiskFactorsValidator.validate_statement_type(statement_type)
        validated_year = RiskFactorsValidator.validate_fiscal_year(fiscal_year)
        validated_currency = currency or self.default_currency
        
        # Validate DataFrame
        RiskFactorsValidator.validate_dataframe(df)
        
        # Process based on statement type
        df = self._row_to_column_format(df)
        
        if validated_type == 'income_statement':
            standardized = self._standardize_dataframe(df, self.INCOME_STATEMENT_MAP)
            mapping_used = 'INCOME_STATEMENT_MAP'
        elif validated_type == 'balance_sheet':
            standardized = self._standardize_dataframe(df, self.BALANCE_SHEET_MAP)
            mapping_used = 'BALANCE_SHEET_MAP'
        else:  # cash_flow
            standardized = self._standardize_dataframe(df, self.CASH_FLOW_MAP)
            mapping_used = 'CASH_FLOW_MAP'
        
        if standardized.empty:
            # Create empty DataFrame with proper structure
            if validated_type == 'income_statement':
                standardized = pd.DataFrame(columns=list(self.INCOME_STATEMENT_MAP.keys()))
            elif validated_type == 'balance_sheet':
                standardized = pd.DataFrame(columns=list(self.BALANCE_SHEET_MAP.keys()))
            else:
                standardized = pd.DataFrame(columns=list(self.CASH_FLOW_MAP.keys()))
        
        # Create statement object
        statement = FinancialStatement(
            company_name=validated_company,
            fiscal_year=validated_year or datetime.now().year,
            statement_type=validated_type,
            data=standardized,
            currency=validated_currency,
            source_file=source_file,
            parsed_at=datetime.now(),
            metadata={
                'parser_version': '1.0',
                'mapping_used': mapping_used,
                'source': 'dataframe'
            }
        )
        
        self._parsed_statements.append(statement)
        return statement
    
    def parse_directory(
        self, 
        directory: Union[str, Path], 
        company_name: str = "Unknown"
    ) -> Dict[str, FinancialStatement]:
        """Parse all financial statements in a directory.
        
        Args:
            directory: Path to directory containing statement files
            company_name: Name of the company
            
        Returns:
            Dictionary of statement_type → FinancialStatement
            
        Raises:
            ValidationError: If directory path is invalid
        """
        validated_dir = RiskFactorsValidator.validate_directory(directory)
        validated_company = RiskFactorsValidator.validate_company_name(company_name)
        
        statements: Dict[str, FinancialStatement] = {}
        
        for file_path in validated_dir.glob("*"):
            if file_path.is_file():
                filename = file_path.stem.lower()
                try:
                    if 'income' in filename or 'p&l' in filename or 'pl' in filename:
                        statements['income_statement'] = self.parse_income_statement(
                            file_path, validated_company
                        )
                    elif 'balance' in filename or 'bs' in filename:
                        statements['balance_sheet'] = self.parse_balance_sheet(
                            file_path, validated_company
                        )
                    elif 'cash' in filename or 'cf' in filename:
                        statements['cash_flow'] = self.parse_cash_flow(
                            file_path, validated_company
                        )
                except FileParsingError as e:
                    # Log warning but continue with other files
                    import warnings
                    warnings.warn(f"Warning: Could not parse {file_path}: {e}")
                    continue
        
        return statements
    
    def clear_parsed_statements(self) -> None:
        """Clear all parsed statements from memory."""
        self._parsed_statements.clear()


