"""Custom exception hierarchy for credit risk assessment."""

from typing import Optional


class CreditRiskError(Exception):
    """Base exception for credit risk errors."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.timestamp = __import__('datetime').datetime.now()
    
    def __str__(self):
        return f"{self.__class__.__name__}: {self.message}"


class ValidationError(CreditRiskError):
    """Raised when input validation fails."""
    pass


class InputRangeError(ValidationError):
    """Raised when input value is outside acceptable range."""
    pass


class MissingRequiredFieldError(ValidationError):
    """Raised when required field is missing from input."""
    pass


class CalculationError(CreditRiskError):
    """Raised when calculation fails."""
    pass


class InvalidRatioError(CalculationError):
    """Raised when financial ratio is invalid (e.g., division by zero)."""
    pass


class ConfigurationError(CreditRiskError):
    """Raised when configuration is invalid."""
    pass


class ExportError(CreditRiskError):
    """Raised when export fails."""
    pass
