"""Credit Risk Assessment Toolkit.

A comprehensive framework for assessing credit risk and generating risk ratings.

Modules:
- models: Data classes for risk assessments
- validator: Input validation
- calculator: Risk calculation engine
- exporter: Output formatting

Example:
    >>> from credit_risk import CreditRiskValidator, CreditRiskCalculator
    >>> 
    >>> validator = CreditRiskValidator()
    >>> financials = validator.validate_financials({
    ...     'company_name': 'ABC Corp',
    ...     'interest_coverage': 6.5,
    ...     'debt_to_ebitda': 3.2,
    ... })
    >>> 
    >>> calculator = CreditRiskCalculator()
    >>> assessment = calculator.calculate(financials, industry='technology')
    >>> print(assessment.overall_rating)
"""

from .models import (
    CreditRating,
    RiskDirection,
    RiskFactors,
    CreditRiskAssessment,
)

from .validator import CreditRiskValidator
from .calculator import CreditRiskCalculator
from .exporter import RiskExporter

__all__ = [
    'CreditRating',
    'RiskDirection',
    'RiskFactors',
    'CreditRiskAssessment',
    'CreditRiskValidator',
    'CreditRiskCalculator',
    'RiskExporter',
]

__version__ = '2.0.0'
