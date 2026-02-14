"""Input validation for credit risk assessment."""

from typing import Dict, Optional, Any, Union
from .exceptions import (
    ValidationError,
    InputRangeError,
    MissingRequiredFieldError
)


class CreditRiskValidator:
    """Validates input data for credit risk assessment."""
    
    # Validation ranges (1-5 for risk scores)
    MIN_RISK_SCORE = 1
    MAX_RISK_SCORE = 5
    
    # Financial ratio validation ranges
    VALID_RANGES: Dict[str, tuple] = {
        'interest_coverage': (-1000, 1000),  # Can be negative
        'debt_to_ebitda': (0, 100),  # Can't be negative
        'fcf_to_debt': (-10, 10),  # Percentage
        'current_ratio': (0, 100),
        'net_margin': (-100, 100),  # Percentage
    }
    
    # Required fields
    REQUIRED_FIELDS = ['company_name']
    
    def __init__(self, raise_on_error: bool = True):
        """Initialize validator.
        
        Args:
            raise_on_error: If True, raise exceptions on validation failure.
                           If False, return error messages instead.
        """
        self.raise_on_error = raise_on_error
        self._errors: Dict[str, str] = {}
    
    @property
    def errors(self) -> Dict[str, str]:
        """Get accumulated validation errors."""
        return self._errors.copy()
    
    def clear_errors(self) -> None:
        """Clear accumulated errors."""
        self._errors = {}
    
    def _add_error(self, field: str, message: str) -> None:
        """Add an error message."""
        self._errors[field] = message
        if self.raise_on_error:
            raise ValidationError(message, {'field': field})
    
    def validate_company_name(self, name: Any) -> str:
        """Validate and sanitize company name."""
        if not name:
            self._add_error('company_name', 'Company name is required')
        
        if not isinstance(name, str):
            self._add_error('company_name', f'Company name must be string, got {type(name).__name__}')
        
        name = str(name).strip()
        if len(name) < 1:
            self._add_error('company_name', 'Company name cannot be empty')
        
        if len(name) > 500:
            self._add_error('company_name', 'Company name is too long (max 500 characters)')
        
        return name
    
    def validate_financial_ratio(
        self, 
        name: str, 
        value: Optional[Union[float, int]], 
        allow_none: bool = True
    ) -> Optional[float]:
        """Validate a financial ratio.
        
        Args:
            name: Name of the ratio for error messages
            value: The ratio value
            allow_none: Whether None values are allowed
        
        Returns:
            Validated float value
        
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            if allow_none:
                return None
            else:
                self._add_error(name, f'{name} is required')
        
        if not isinstance(value, (int, float)):
            self._add_error(name, f'{name} must be numeric, got {type(value).__name__}')
        
        # Check range
        min_val, max_val = self.VALID_RANGES.get(name, (-float('inf'), float('inf')))
        
        if value < min_val or value > max_val:
            self._add_error(
                name, 
                f'{name} value {value} is outside valid range ({min_val}, {max_val})'
            )
        
        return float(value)
    
    def validate_risk_score(self, name: str, value: Any) -> int:
        """Validate a risk score (1-5)."""
        if value is None:
            return 0
        
        if not isinstance(value, int):
            self._add_error(name, f'{name} must be an integer, got {type(value).__name__}')
        
        if value != 0 and (value < self.MIN_RISK_SCORE or value > self.MAX_RISK_SCORE):
            self._add_error(
                name, 
                f'{name} must be 0 or between {self.MIN_RISK_SCORE}-{self.MAX_RISK_SCORE}, got {value}'
            )
        
        return int(value)
    
    def validate_financials(self, financials: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete financial data.
        
        Args:
            financials: Dictionary of financial ratios
        
        Returns:
            Validated financials dictionary
        
        Raises:
            ValidationError: If validation fails
        """
        self.clear_errors()
        validated = {}
        
        # Validate company name (required)
        if 'company_name' in financials:
            validated['company_name'] = self.validate_company_name(financials['company_name'])
        
        # Validate optional financial ratios
        for field_name in ['interest_coverage', 'debt_to_ebitda', 'fcf_to_debt', 'current_ratio', 'net_margin']:
            if field_name in financials:
                validated[field_name] = self.validate_financial_ratio(
                    field_name, 
                    financials[field_name],
                    allow_none=True
                )
        
        # Validate fiscal year if provided
        if 'fiscal_year' in financials:
            year = financials['fiscal_year']
            if year is not None:
                if not isinstance(year, int):
                    self._add_error('fiscal_year', f'Fiscal year must be integer, got {type(year).__name__}')
                elif year < 1900 or year > 2100:
                    self._add_error('fiscal_year', f'Invalid fiscal year: {year}')
                else:
                    validated['fiscal_year'] = year
        
        return validated
    
    def validate_additional_factors(self, factors: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate additional risk factors."""
        if not factors:
            return {}
        
        validated = {}
        
        # Customer concentration (1-5)
        if 'customer_concentration' in factors:
            validated['customer_concentration'] = self.validate_risk_score(
                'customer_concentration',
                factors['customer_concentration']
            )
        
        # Management quality (inverted: 1 = good)
        if 'management_quality' in factors:
            validated['management_quality'] = self.validate_risk_score(
                'management_quality',
                factors['management_quality']
            )
        
        return validated
    
    def is_valid(self, financials: Dict[str, Any]) -> bool:
        """Check if financials are valid without raising exceptions."""
        old_raise = self.raise_on_error
        self.raise_on_error = False
        
        try:
            self.validate_financials(financials)
            return len(self.errors) == 0
        finally:
            self.raise_on_error = old_raise
