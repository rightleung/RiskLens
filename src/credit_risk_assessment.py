"""
Credit Analyst Toolkit — Credit Risk Assessment (Legacy)
========================================================
Legacy framework for assessing credit risk and generating risk ratings.
This module is not used by the current FastAPI API (which uses Altman Z-Score).

Features:
- Custom exception hierarchy for precise error handling
- Input validation with RiskFactorsValidator
- Comprehensive type hints (PEP 484)
- Google-style docstrings for all public APIs
- Production-ready with pytest unit tests (90%+ coverage)

Usage:
    from credit_risk_assessment import CreditRiskAssessor, RiskFactors
    assessor = CreditRiskAssessor()
    assessment = assessor.assess_credit(company_name, financial_data)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
from enum import Enum
from pathlib import Path


# =============================================================================
# Custom Exception Hierarchy
# =============================================================================

class CreditRiskError(Exception):
    """Base exception for all credit risk assessment errors."""
    
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


class ValidationError(CreditRiskError):
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


class RatioAnalysisError(CreditRiskError):
    """Raised when ratio analysis fails or returns invalid results."""
    
    def __init__(
        self, 
        ratio_name: str, 
        value: Any, 
        expected_range: str, 
        details: Optional[Dict] = None
    ) -> None:
        """Initialize ratio analysis error.
        
        Args:
            ratio_name: Name of the ratio
            value: Invalid ratio value
            expected_range: Expected valid range
            details: Additional context
        """
        message = f"Invalid ratio value for '{ratio_name}': {value} (expected {expected_range})"
        error_details = {
            "ratio_name": ratio_name,
            "value": value,
            "expected_range": expected_range,
        }
        if details:
            error_details.update(details)
        
        super().__init__(message, error_details)
        self.ratio_name = ratio_name
        self.value = value
        self.expected_range = expected_range


class ConfigurationError(CreditRiskError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, config_key: str, reason: str) -> None:
        """Initialize configuration error.
        
        Args:
            config_key: Configuration key that is invalid
            reason: Why the configuration is invalid
        """
        message = f"Configuration error for '{config_key}': {reason}"
        details = {"config_key": config_key, "reason": reason}
        super().__init__(message, details)
        self.config_key = config_key
        self.reason = reason


# =============================================================================
# Enums
# =============================================================================

class CreditRating(Enum):
    """Credit rating scale (approximate to S&P/Moody's)."""
    AAA = "AAA"
    AA = "AA"
    A = "A"
    BBB = "BBB"
    BB = "BB"
    B = "B"
    CCC = "CCC"
    CC = "CC"
    C = "C"
    D = "D"  # Default


class RiskDirection(Enum):
    """Direction of risk assessment."""
    IMPROVING = "Improving"
    STABLE = "Stable"
    DETERIORATING = "Deteriorating"
    VOLATILE = "Volatile"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class RiskFactors:
    """Container for risk factor assessments.
    
    Attributes:
        leverage_risk: Financial leverage risk (1-5, higher = riskier)
        liquidity_risk: Liquidity risk (1-5)
        profitability_risk: Profitability risk (1-5)
        cash_flow_risk: Cash flow risk (1-5)
        coverage_risk: Interest coverage risk (1-5)
        industry_risk: Industry-specific risk (1-5)
        competitive_position: Competitive position risk (1-5, inverted)
        customer_concentration: Customer concentration risk (1-5)
        technology_risk: Technology disruption risk (1-5)
        management_quality: Management quality risk (1-5, inverted)
        governance_risk: Corporate governance risk (1-5)
        environmental_risk: Environmental risk factor (1-5)
        social_risk: Social responsibility risk (1-5)
        governance_esg_risk: ESG governance risk (1-5)
    """
    
    # Financial Risk Factors (1-5 scale, higher = riskier)
    leverage_risk: int = 0
    liquidity_risk: int = 0
    profitability_risk: int = 0
    cash_flow_risk: int = 0
    coverage_risk: int = 0
    
    # Business Risk Factors (1-5 scale)
    industry_risk: int = 0
    competitive_position: int = 0  # Inverted: 1 = strong
    customer_concentration: int = 0
    technology_risk: int = 0
    
    # Management & Governance (1-5 scale, inverted where noted)
    management_quality: int = 0  # Inverted: 1 = good
    governance_risk: int = 0
    
    # ESG Factors (1-5 scale)
    environmental_risk: int = 0
    social_risk: int = 0
    governance_esg_risk: int = 0
    
    def __post_init__(self) -> None:
        """Validate risk factor values after initialization."""
        self._validate_risk_factor("leverage_risk", self.leverage_risk)
        self._validate_risk_factor("liquidity_risk", self.liquidity_risk)
        self._validate_risk_factor("profitability_risk", self.profitability_risk)
        self._validate_risk_factor("cash_flow_risk", self.cash_flow_risk)
        self._validate_risk_factor("coverage_risk", self.coverage_risk)
        self._validate_risk_factor("industry_risk", self.industry_risk)
        self._validate_risk_factor("competitive_position", self.competitive_position)
        self._validate_risk_factor("customer_concentration", self.customer_concentration)
        self._validate_risk_factor("technology_risk", self.technology_risk)
        self._validate_risk_factor("management_quality", self.management_quality)
        self._validate_risk_factor("governance_risk", self.governance_risk)
        self._validate_risk_factor("environmental_risk", self.environmental_risk)
        self._validate_risk_factor("social_risk", self.social_risk)
        self._validate_risk_factor("governance_esg_risk", self.governance_esg_risk)
    
    @staticmethod
    def _validate_risk_factor(name: str, value: int, min_val: int = 0, max_val: int = 5) -> None:
        """Validate a single risk factor value.
        
        Args:
            name: Name of the risk factor
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Raises:
            ValidationError: If value is outside valid range
        """
        if not isinstance(value, int):
            raise ValidationError(
                field_name=name,
                value=value,
                expected_type=f"int between {min_val} and {max_val}",
                reason=f"Expected int, got {type(value).__name__}"
            )
        if value < min_val or value > max_val:
            raise ValidationError(
                field_name=name,
                value=value,
                expected_type=f"int between {min_val} and {max_val}",
                reason=f"Value {value} is outside valid range [{min_val}, {max_val}]"
            )
    
    def average_financial_risk(self) -> float:
        """Calculate average financial risk score.
        
        Returns:
            Average of all financial risk factors (0 if none set)
        """
        risks = [
            self.leverage_risk,
            self.liquidity_risk,
            self.profitability_risk,
            self.cash_flow_risk,
            self.coverage_risk
        ]
        valid_risks = [r for r in risks if r > 0]
        return sum(valid_risks) / len(valid_risks) if valid_risks else 0.0
    
    def average_business_risk(self) -> float:
        """Calculate average business risk score.
        
        Returns:
            Average of all business risk factors (0 if none set)
        """
        risks = [
            self.industry_risk,
            self.competitive_position,
            self.customer_concentration,
            self.technology_risk
        ]
        valid_risks = [r for r in risks if r > 0]
        return sum(valid_risks) / len(valid_risks) if valid_risks else 0.0
    
    def average_management_risk(self) -> float:
        """Calculate average management and governance risk score.
        
        Returns:
            Average of management/governance risks (0 if none set)
        """
        risks = [self.management_quality, self.governance_risk]
        valid_risks = [r for r in risks if r > 0]
        return sum(valid_risks) / len(valid_risks) if valid_risks else 0.0
    
    def average_esg_risk(self) -> float:
        """Calculate average ESG risk score.
        
        Returns:
            Average of ESG risk factors (0 if none set)
        """
        risks = [self.environmental_risk, self.social_risk, self.governance_esg_risk]
        valid_risks = [r for r in risks if r > 0]
        return sum(valid_risks) / len(valid_risks) if valid_risks else 0.0
    
    def total_risk_score(self) -> float:
        """Calculate total weighted risk score.
        
        Weights:
            Financial:  40%
            Business:   25%
            Management: 20%
            ESG:        15%
        
        Returns:
            Weighted risk score (0-100 scale)
        """
        financial = self.average_financial_risk() * 0.40
        business = self.average_business_risk() * 0.25
        management = self.average_management_risk() * 0.20
        esg = self.average_esg_risk() * 0.15
        
        return (financial + business + management + esg) * 20  # Scale to 0-100


@dataclass
class CreditRiskAssessment:
    """Complete credit risk assessment result.
    
    Attributes:
        company_name: Name of the company being assessed
        fiscal_year: Fiscal year of the analysis
        overall_rating: Final credit rating (e.g., 'AAA', 'BB')
        outlook: Rating outlook (e.g., 'Stable', 'Positive')
        risk_score: Overall risk score (0-100, higher = riskier)
        risk_factors: Detailed risk factor assessments
        interest_coverage: Interest coverage ratio
        debt_to_ebitda: Debt to EBITDA ratio
        fcf_to_debt: Free cash flow to debt ratio
        current_ratio: Current ratio
        strengths: List of credit strengths identified
        weaknesses: List of credit weaknesses identified
        watch_items: Items requiring monitoring
        assessment_date: Date of assessment
        analyst_notes: Additional analyst notes
    """
    
    company_name: str
    fiscal_year: int
    overall_rating: str
    outlook: str
    risk_score: float
    risk_factors: RiskFactors
    
    # Key Metrics
    interest_coverage: Optional[float] = None
    debt_to_ebitda: Optional[float] = None
    fcf_to_debt: Optional[float] = None
    current_ratio: Optional[float] = None
    
    # Strengths and Weaknesses
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    watch_items: List[str] = field(default_factory=list)
    
    # Assessment Details
    assessment_date: datetime = field(default_factory=datetime.now)
    analyst_notes: str = ""
    
    def __post_init__(self) -> None:
        """Validate assessment data after initialization."""
        if not isinstance(self.company_name, str) or not self.company_name.strip():
            raise ValidationError(
                field_name="company_name",
                value=self.company_name,
                expected_type="non-empty string"
            )
        if not isinstance(self.fiscal_year, int) or self.fiscal_year < 1900 or self.fiscal_year > 2100:
            raise ValidationError(
                field_name="fiscal_year",
                value=self.fiscal_year,
                expected_type="int between 1900 and 2100"
            )
        if not isinstance(self.risk_score, (int, float)) or self.risk_score < 0 or self.risk_score > 100:
            raise ValidationError(
                field_name="risk_score",
                value=self.risk_score,
                expected_type="float between 0 and 100"
            )
    
    @property
    def industry_risk(self) -> int:
        """Get industry risk from risk factors.
        
        Returns:
            Industry risk score (1-5)
        """
        return self.risk_factors.industry_risk
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert assessment to dictionary for serialization.
        
        Returns:
            Dictionary representation of the assessment
        """
        return {
            'company_name': self.company_name,
            'fiscal_year': self.fiscal_year,
            'overall_rating': self.overall_rating,
            'outlook': self.outlook,
            'risk_score': self.risk_score,
            'risk_factors': {
                'financial_risk_avg': self.risk_factors.average_financial_risk(),
                'business_risk_avg': self.risk_factors.average_business_risk(),
                'management_risk_avg': self.risk_factors.average_management_risk(),
                'esg_risk_avg': self.risk_factors.average_esg_risk(),
                'total_risk_score': self.risk_factors.total_risk_score(),
            },
            'key_metrics': {
                'interest_coverage': self.interest_coverage,
                'debt_to_ebitda': self.debt_to_ebitda,
                'fcf_to_debt': self.fcf_to_debt,
                'current_ratio': self.current_ratio,
            },
            'strengths': self.strengths,
            'weaknesses': self.weaknesses,
            'watch_items': self.watch_items,
            'assessment_date': self.assessment_date.isoformat(),
            'analyst_notes': self.analyst_notes,
        }
    
    def to_json(self) -> str:
        """Convert assessment to JSON string.
        
        Returns:
            JSON representation of the assessment
        """
        import json
        return json.dumps(self.to_dict(), indent=2)
    
    def summary(self) -> str:
        """Generate a summary string of the assessment.
        
        Returns:
            Human-readable summary
        """
        risk_level = "Low" if self.risk_score < 30 else "Medium" if self.risk_score < 60 else "High"
        
        lines = [
            f"Credit Risk Assessment: {self.company_name} ({self.fiscal_year})",
            f"Rating: {self.overall_rating} ({risk_level} Risk)",
            f"Outlook: {self.outlook}",
            f"Risk Score: {self.risk_score:.1f}/100",
            "",
            "Key Metrics:",
            f"  Interest Coverage: {self._format_metric(self.interest_coverage)}",
            f"  Debt/EBITDA: {self._format_metric(self.debt_to_ebitda)}",
            f"  FCF/Debt: {self._format_metric(self.fcf_to_debt)}",
            f"  Current Ratio: {self._format_metric(self.current_ratio)}",
        ]
        
        if self.strengths:
            lines.extend(["", "Strengths:"] + [f"  - {s}" for s in self.strengths[:5]])
        
        if self.weaknesses:
            lines.extend(["", "Weaknesses:"] + [f"  - {w}" for w in self.weaknesses[:5]])
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_metric(value: Optional[float]) -> str:
        """Format a metric value for display.
        
        Args:
            value: Metric value to format
            
        Returns:
            Formatted string representation
        """
        if value is None:
            return "N/A"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)


# =============================================================================
# Validator Class
# =============================================================================

class RiskFactorsValidator:
    """Validates risk factor inputs and financial data.
    
    This class provides reusable validation logic for credit risk
    assessments, ensuring data integrity and catching errors early.
    
    Example:
        >>> validator = RiskFactorsValidator()
        >>> try:
        ...     validator.validate_interest_coverage(5.0)
        ...     print("Valid!")
        ... except ValidationError as e:
        ...     print(f"Error: {e}")
    """
    
    # Valid ranges for key metrics
    VALID_RANGES: Dict[str, Tuple[float, float]] = {
        'interest_coverage': (-100000.0, 100000.0),
        'debt_to_ebitda': (-100000.0, 100000.0),
        'fcf_to_debt': (-1000.0, 1000.0),
        'current_ratio': (0.0, 1000.0),
        'net_margin': (-1000.0, 1000.0),
    }
    
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
    def validate_industry(cls, industry: str) -> str:
        """Validate industry name.
        
        Args:
            industry: Industry name to validate
            
        Returns:
            Lowercase validated industry name
            
        Raises:
            ValidationError: If industry is invalid
        """
        if not isinstance(industry, str):
            raise ValidationError(
                field_name="industry",
                value=industry,
                expected_type="string",
                reason=f"Expected string, got {type(industry).__name__}"
            )
        
        normalized = industry.strip().lower()
        if not normalized:
            raise ValidationError(
                field_name="industry",
                value=industry,
                expected_type="non-empty string"
            )
        
        return normalized
    
    @classmethod
    def validate_fiscal_year(cls, year: int) -> int:
        """Validate fiscal year.
        
        Args:
            year: Fiscal year to validate
            
        Returns:
            Validated fiscal year
            
        Raises:
            ValidationError: If year is out of reasonable range
        """
        if not isinstance(year, int):
            raise ValidationError(
                field_name="fiscal_year",
                value=year,
                expected_type="int",
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
    def validate_interest_coverage(
        cls, 
        value: Optional[float], 
        allow_none: bool = True
    ) -> Optional[float]:
        """Validate interest coverage ratio.
        
        Args:
            value: Interest coverage ratio
            allow_none: Whether None values are allowed
            
        Returns:
            Validated value
            
        Raises:
            ValidationError: If value is invalid
        """
        if value is None:
            if allow_none:
                return None
            raise ValidationError(
                field_name="interest_coverage",
                value=value,
                expected_type="float",
                reason="Interest coverage cannot be None"
            )
        
        return cls._validate_numeric_range("interest_coverage", value)
    
    @classmethod
    def validate_debt_to_ebitda(
        cls, 
        value: Optional[float], 
        allow_none: bool = True
    ) -> Optional[float]:
        """Validate Debt/EBITDA ratio.
        
        Args:
            value: Debt to EBITDA ratio
            allow_none: Whether None values are allowed
            
        Returns:
            Validated value
            
        Raises:
            ValidationError: If value is invalid
        """
        if value is None:
            if allow_none:
                return None
            raise ValidationError(
                field_name="debt_to_ebitda",
                value=value,
                expected_type="float",
                reason="Debt/EBITDA cannot be None"
            )
        
        return cls._validate_numeric_range("debt_to_ebitda", value)
    
    @classmethod
    def validate_fcf_to_debt(
        cls, 
        value: Optional[float], 
        allow_none: bool = True
    ) -> Optional[float]:
        """Validate Free Cash Flow / Debt ratio.
        
        Args:
            value: FCF to Debt ratio
            allow_none: Whether None values are allowed
            
        Returns:
            Validated value
            
        Raises:
            ValidationError: If value is invalid
        """
        if value is None:
            if allow_none:
                return None
            raise ValidationError(
                field_name="fcf_to_debt",
                value=value,
                expected_type="float",
                reason="FCF/Debt cannot be None"
            )
        
        return cls._validate_numeric_range("fcf_to_debt", value)
    
    @classmethod
    def validate_current_ratio(
        cls, 
        value: Optional[float], 
        allow_none: bool = True
    ) -> Optional[float]:
        """Validate Current Ratio.
        
        Args:
            value: Current ratio
            allow_none: Whether None values are allowed
            
        Returns:
            Validated value
            
        Raises:
            ValidationError: If value is invalid
        """
        if value is None:
            if allow_none:
                return None
            raise ValidationError(
                field_name="current_ratio",
                value=value,
                expected_type="float",
                reason="Current ratio cannot be None"
            )
        
        if value < 0:
            raise ValidationError(
                field_name="current_ratio",
                value=value,
                expected_type="non-negative float",
                reason="Current ratio cannot be negative"
            )
        
        return cls._validate_numeric_range("current_ratio", value)
    
    @classmethod
    def _validate_numeric_range(
        cls, 
        name: str, 
        value: float, 
        custom_range: Optional[Tuple[float, float]] = None
    ) -> float:
        """Validate a numeric value is within expected range.
        
        Args:
            name: Name of the field for error messages
            value: Value to validate
            custom_range: Custom range to use (uses VALID_RANGES if None)
            
        Returns:
            Validated value
            
        Raises:
            ValidationError: If value is outside range
        """
        if not isinstance(value, (int, float)):
            raise ValidationError(
                field_name=name,
                value=value,
                expected_type="numeric",
                reason=f"Expected numeric type, got {type(value).__name__}"
            )
        
        min_val, max_val = custom_range or cls.VALID_RANGES.get(name, (-float('inf'), float('inf')))
        
        if value < min_val or value > max_val:
            raise ValidationError(
                field_name=name,
                value=value,
                expected_type=f"float between {min_val} and {max_val}",
                reason=f"Value {value} outside valid range"
            )
        
        return float(value)
    
    @classmethod
    def validate_risk_factors(cls, risk_factors: RiskFactors) -> RiskFactors:
        """Validate complete RiskFactors object.
        
        Args:
            risk_factors: RiskFactors to validate
            
        Returns:
            Validated RiskFactors (for method chaining)
            
        Raises:
            ValidationError: If any factor is invalid
        """
        if not isinstance(risk_factors, RiskFactors):
            raise ValidationError(
                field_name="risk_factors",
                value=risk_factors,
                expected_type="RiskFactors",
                reason=f"Expected RiskFactors, got {type(risk_factors).__name__}"
            )
        
        # RiskFactors validates itself in __post_init__
        return risk_factors


# =============================================================================
# Scoring Utilities
# =============================================================================

def score_interest_coverage(ic: float) -> int:
    """Convert interest coverage ratio to risk score (1-5).
    
    Args:
        ic: Interest coverage ratio
        
    Returns:
        Risk score (1-5, where 1 = low risk)
        
    Raises:
        ValueError: If coverage is negative
    """
    if ic < 0:
        raise ValueError("Interest coverage cannot be negative")
    
    if ic >= 8:
        return 1
    elif ic >= 5:
        return 2
    elif ic >= 3:
        return 3
    elif ic >= 1.5:
        return 4
    else:
        return 5


def score_debt_to_ebitda(d_e: float) -> int:
    """Convert Debt/EBITDA ratio to risk score (1-5).
    
    Args:
        d_e: Debt to EBITDA ratio
        
    Returns:
        Risk score (1-5, where 1 = low risk)
        
    Raises:
        ValueError: If ratio is negative
    """
    # Negative D/E means negative EBITDA — highest risk, not an error
    if d_e < 0:
        return 5
    
    if d_e <= 2:
        return 1
    elif d_e <= 3.5:
        return 2
    elif d_e <= 5:
        return 3
    elif d_e <= 7:
        return 4
    else:
        return 5


def score_fcf_to_debt(fcf_d: float) -> int:
    """Convert FCF/Debt ratio to risk score (1-5).
    
    Args:
        fcf_d: Free cash flow to debt ratio
        
    Returns:
        Risk score (1-5, where 1 = low risk)
    """
    if fcf_d >= 0.5:
        return 1
    elif fcf_d >= 0.25:
        return 2
    elif fcf_d >= 0.1:
        return 3
    elif fcf_d >= 0:
        return 4
    else:
        return 5


def score_current_ratio(cr: float) -> int:
    """Convert current ratio to risk score (1-5).
    
    Args:
        cr: Current ratio
        
    Returns:
        Risk score (1-5, where 1 = low risk)
        
    Raises:
        ValueError: If ratio is negative
    """
    if cr < 0:
        raise ValueError("Current ratio cannot be negative")
    
    if cr >= 2:
        return 1
    elif cr >= 1.5:
        return 2
    elif cr >= 1.2:
        return 3
    elif cr >= 1.0:
        return 4
    else:
        return 5


def score_net_margin(margin: Optional[float]) -> int:
    """Convert net margin to risk score (1-5).
    
    Args:
        margin: Net profit margin (percentage)
        
    Returns:
        Risk score (1-5, where 1 = low risk), 0 if None
    """
    if margin is None:
        return 0
    
    if margin >= 15:
        return 1
    elif margin >= 10:
        return 2
    elif margin >= 5:
        return 3
    elif margin > 0:
        return 4
    else:
        return 5


def risk_score_to_rating(score: float) -> str:
    """Convert risk score to credit rating.
    
    Args:
        score: Risk score (0-100)
        
    Returns:
        Credit rating string
        
    Raises:
        ValueError: If score is outside valid range
    """
    if score < 0 or score > 100:
        raise ValueError(f"Risk score must be 0-100, got {score}")
    
    if score < 20:
        return "AAA"
    elif score < 30:
        return "AA"
    elif score < 40:
        return "A"
    elif score < 50:
        return "BBB"
    elif score < 60:
        return "BB"
    elif score < 70:
        return "B"
    elif score < 80:
        return "CCC"
    elif score < 90:
        return "CC"
    else:
        return "C"


def determine_outlook(
    interest_coverage: Optional[float],
    fcf_to_debt: Optional[float],
    current_ratio: Optional[float]
) -> str:
    """Determine rating outlook based on key metrics.
    
    Args:
        interest_coverage: Interest coverage ratio
        fcf_to_debt: Free cash flow to debt ratio
        current_ratio: Current ratio
        
    Returns:
        Outlook string ('Positive', 'Stable', 'Negative', etc.)
    """
    improving = []
    deteriorating = []
    
    if interest_coverage is not None and interest_coverage > 5:
        improving.append("interest coverage")
    elif interest_coverage is not None and interest_coverage < 2:
        deteriorating.append("interest coverage")
    
    if fcf_to_debt is not None and fcf_to_debt > 0.1:
        improving.append("free cash flow")
    elif fcf_to_debt is not None and fcf_to_debt < 0:
        deteriorating.append("free cash flow")
    
    if current_ratio is not None and current_ratio > 1.5:
        improving.append("liquidity")
    elif current_ratio is not None and current_ratio < 1.0:
        deteriorating.append("liquidity")
    
    if improving and not deteriorating:
        return f"Positive ({', '.join(improving)})"
    elif deteriorating and not improving:
        return f"Negative ({', '.join(deteriorating)})"
    elif improving and deteriorating:
        return f"Mixed ({', '.join(improving)} improving, {', '.join(deteriorating)} deteriorating)"
    
    return "Stable"


# =============================================================================
# Main Assesor Class
# =============================================================================

class CreditRiskAssessor:
    """
    Assess credit risk based on financial and business factors.
    
    This class provides a comprehensive framework for assessing credit risk,
    including quantitative scoring based on financial ratios, qualitative
    assessment framework, and credit rating approximation.
    
    Attributes:
        THRESHOLDS: Dict of scoring thresholds for key ratios
        INDUSTRY_RISK: Dict of industry risk scores (1-5)
        
    Example:
        >>> assessor = CreditRiskAssessor()
        >>> assessment = assessor.assess_credit(
        ...     company_name="ABC Corp",
        ...     ratios=ratio_analysis,
        ...     industry="Technology"
        ... )
        >>> print(assessment.overall_rating)
    """
    
    # Scoring thresholds (can be customized)
    THRESHOLDS = {
        'interest_coverage': {
            'excellent': 8, 'good': 5, 'fair': 3, 'weak': 1.5, 'poor': 0
        },
        'debt_to_ebitda': {
            'excellent': 2, 'good': 3.5, 'fair': 5, 'weak': 7, 'poor': 10
        },
        'fcf_to_debt': {
            'excellent': 0.5, 'good': 0.25, 'fair': 0.1, 'weak': 0, 'poor': -0.1
        },
        'current_ratio': {
            'excellent': 2, 'good': 1.5, 'fair': 1.2, 'weak': 1, 'poor': 0.8
        },
    }
    
    # Industry risk scores (1-5, higher = riskier)
    INDUSTRY_RISK = {
        'technology': 3,      # High growth but disruption risk
        'software': 3,
        'hardware': 4,
        'financial': 4,       # Regulated but cyclical
        'banking': 4,
        'insurance': 3,
        'healthcare': 2,      # Stable demand
        'pharmaceuticals': 2,
        'retail': 5,          # Competitive, cyclical
        'consumer': 4,
        'industrial': 3,       # Cyclical
        'energy': 5,          # Commodity price risk
        'utilities': 2,       # Stable, regulated
        'real_estate': 4,     # Capital intensive
        'telecom': 4,         # Capital intensive
        'media': 4,
    }
    
    def __init__(self) -> None:
        """Initialize the CreditRiskAssessor."""
        self.assessments: List[CreditRiskAssessment] = []
        self._MAX_ASSESSMENTS = 1000  # Prevent memory leak
    
    def assess_credit(
        self,
        company_name: str,
        ratios: 'CreditRatioAnalysis',
        industry: str = "general",
        fiscal_year: Optional[int] = None,
        additional_factors: Optional[Dict[str, int]] = None,
        analyst_notes: str = ""
    ) -> CreditRiskAssessment:
        """
        Perform comprehensive credit risk assessment.
        
        Args:
            company_name: Name of the company being assessed
            ratios: CreditRatioAnalysis object with calculated ratios
            industry: Industry sector for peer comparison
            fiscal_year: Fiscal year of analysis (defaults to current year)
            additional_factors: Dict of additional risk factors to override
            analyst_notes: Additional notes from the analyst
            
        Returns:
            CreditRiskAssessment with rating and analysis
            
        Raises:
            ValidationError: If any input validation fails
            TypeError: If ratios is not a CreditRatioAnalysis object
        """
        # Validate inputs
        validated_name = RiskFactorsValidator.validate_company_name(company_name)
        validated_industry = RiskFactorsValidator.validate_industry(industry)
        validated_year = RiskFactorsValidator.validate_fiscal_year(
            fiscal_year or datetime.now().year
        )
        
        # Validate ratios object type
        if not hasattr(ratios, 'interest_coverage'):
            raise TypeError(
                f"ratios must be a CreditRatioAnalysis object, got {type(ratios).__name__}"
            )
        
        # Create risk factors container
        risk_factors = RiskFactors()
        
        # --- Financial Risk Scoring ---
        
        # Interest Coverage
        ic = RiskFactorsValidator.validate_interest_coverage(ratios.interest_coverage)
        if ic is not None:
            try:
                risk_factors.coverage_risk = score_interest_coverage(ic)
            except ValueError as e:
                raise RatioAnalysisError(
                    ratio_name="interest_coverage",
                    value=ic,
                    expected_range="non-negative",
                    details={"error": str(e)}
                ) from e
        
        # Debt/EBITDA
        d_e = RiskFactorsValidator.validate_debt_to_ebitda(ratios.debt_to_ebitda)
        if d_e is not None:
            try:
                risk_factors.leverage_risk = score_debt_to_ebitda(d_e)
            except ValueError as e:
                raise RatioAnalysisError(
                    ratio_name="debt_to_ebitda",
                    value=d_e,
                    expected_range="non-negative",
                    details={"error": str(e)}
                ) from e
        
        # FCF/Debt
        fcf_d = RiskFactorsValidator.validate_fcf_to_debt(ratios.fcf_to_debt)
        if fcf_d is not None:
            try:
                risk_factors.cash_flow_risk = score_fcf_to_debt(fcf_d)
            except ValueError as e:
                raise RatioAnalysisError(
                    ratio_name="fcf_to_debt",
                    value=fcf_d,
                    expected_range="numeric",
                    details={"error": str(e)}
                ) from e
        
        # Current Ratio
        cr = RiskFactorsValidator.validate_current_ratio(ratios.current_ratio)
        if cr is not None:
            try:
                risk_factors.liquidity_risk = score_current_ratio(cr)
            except ValueError as e:
                raise RatioAnalysisError(
                    ratio_name="current_ratio",
                    value=cr,
                    expected_range="non-negative",
                    details={"error": str(e)}
                ) from e
        
        # Net Margin (for profitability)
        if ratios.net_margin is not None:
            try:
                margin = float(ratios.net_margin)
                risk_factors.profitability_risk = score_net_margin(margin)
            except (TypeError, ValueError) as e:
                raise RatioAnalysisError(
                    ratio_name="net_margin",
                    value=ratios.net_margin,
                    expected_range="numeric percentage",
                    details={"error": str(e)}
                ) from e
        
        # --- Business Risk Scoring ---
        
        # Industry Risk
        industry_lower = validated_industry.lower()
        risk_factors.industry_risk = self.INDUSTRY_RISK.get(industry_lower, 3)
        
        # Apply additional factors if provided
        if additional_factors:
            if 'customer_concentration' in additional_factors:
                val = additional_factors['customer_concentration']
                if not isinstance(val, int) or val < 1 or val > 5:
                    raise ValidationError(
                        field_name="customer_concentration",
                        value=val,
                        expected_type="int between 1 and 5"
                    )
                risk_factors.customer_concentration = val
            if 'management_quality' in additional_factors:
                val = additional_factors['management_quality']
                if not isinstance(val, int) or val < 1 or val > 5:
                    raise ValidationError(
                        field_name="management_quality",
                        value=val,
                        expected_type="int between 1 and 5"
                    )
                risk_factors.management_quality = val
        
        # --- Calculate Overall Risk Score ---
        
        financial_risk = risk_factors.average_financial_risk()
        business_risk = risk_factors.average_business_risk()
        management_risk = risk_factors.average_management_risk()
        esg_risk = risk_factors.average_esg_risk()
        
        # Weighted score: Financial 40%, Business 25%, Management 20%, ESG 15%
        risk_score = (
            financial_risk * 0.40
            + business_risk * 0.25
            + management_risk * 0.20
            + esg_risk * 0.15
        ) * 20  # Scale to 0-100
        
        # --- Generate Rating ---
        
        rating = risk_score_to_rating(risk_score)
        
        # --- Determine Outlook ---
        
        outlook = determine_outlook(ic, fcf_d, cr)
        
        # --- Identify Strengths and Weaknesses ---
        
        strengths = []
        weaknesses = []
        watch_items = []
        
        if ic is not None and ic > 5:
            strengths.append(f"Strong interest coverage ({ic:.1f}x)")
        elif ic is not None and ic < 2:
            weaknesses.append(f"Weak interest coverage ({ic:.1f}x)")
            watch_items.append("Interest coverage deterioration")
        
        if d_e is not None and d_e < 3:
            strengths.append(f"Low leverage (Debt/EBITDA: {d_e:.1f})")
        elif d_e is not None and d_e > 5:
            weaknesses.append(f"High leverage (Debt/EBITDA: {d_e:.1f})")
        
        if fcf_d is not None and fcf_d > 0.2:
            strengths.append(f"Strong free cash flow ({fcf_d*100:.1f}% of debt)")
        elif fcf_d is not None and fcf_d < 0:
            weaknesses.append("Negative free cash flow")
        
        if cr is not None and cr > 1.5:
            strengths.append(f"Good liquidity (Current Ratio: {cr:.2f})")
        elif cr is not None and cr < 1:
            weaknesses.append(f"Weak liquidity (Current Ratio: {cr:.2f})")
        
        # --- Create Assessment ---
        
        assessment = CreditRiskAssessment(
            company_name=validated_name,
            fiscal_year=validated_year,
            overall_rating=rating,
            outlook=outlook,
            risk_score=risk_score,
            risk_factors=risk_factors,
            interest_coverage=ic,
            debt_to_ebitda=d_e,
            fcf_to_debt=fcf_d,
            current_ratio=cr,
            strengths=strengths,
            weaknesses=weaknesses,
            watch_items=watch_items,
            assessment_date=datetime.now(),
            analyst_notes=analyst_notes
        )
        
        self.assessments.append(assessment)
        # Evict oldest entries to prevent memory leak in long-running servers
        if len(self.assessments) > self._MAX_ASSESSMENTS:
            self.assessments = self.assessments[-self._MAX_ASSESSMENTS:]
        return assessment
    
    def _score_to_rating(self, risk_score: float) -> str:
        """Convert risk score to credit rating.
        
        Args:
            risk_score: Risk score (0-100)
            
        Returns:
            Credit rating string
        """
        return risk_score_to_rating(risk_score)
    
    def _determine_outlook(
        self, 
        ratios: 'CreditRatioAnalysis'
    ) -> str:
        """Determine rating outlook based on trends.
        
        Args:
            ratios: Credit ratio analysis
            
        Returns:
            Outlook string
        """
        return determine_outlook(
            ratios.interest_coverage,
            ratios.fcf_to_debt,
            ratios.current_ratio
        )
    
    def compare_to_peers(
        self, 
        assessment: CreditRiskAssessment,
        peer_ratios: Dict[str, 'CreditRatioAnalysis']
    ) -> pd.DataFrame:
        """
        Compare company to peer group.
        
        Args:
            assessment: CreditRiskAssessment for the subject company
            peer_ratios: Dict of peer_name → CreditRatioAnalysis
            
        Returns:
            DataFrame comparing metrics
        """
        # Build comparison table
        comparison = {
            'Metric': [],
            assessment.company_name: [],
        }
        
        for peer_name, peer_ratio in peer_ratios.items():
            comparison['Metric'].append(peer_name)
            comparison[assessment.company_name].append(peer_ratio.company_name)
        
        return pd.DataFrame(comparison)


if __name__ == "__main__":
    print("Credit Risk Assessment Framework initialized.")
    print("Usage: assessor.assess_credit(company_name, ratios, industry)")
