"""Data models for credit risk assessment."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


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


@dataclass
class RiskFactors:
    """Container for risk factor assessments with validation."""
    # Financial Risk Factors (1-5, higher = riskier)
    leverage_risk: int = 0
    liquidity_risk: int = 0
    profitability_risk: int = 0
    cash_flow_risk: int = 0
    coverage_risk: int = 0
    
    # Business Risk Factors (1-5, higher = riskier)
    industry_risk: int = 0
    competitive_position: int = 0  # Inverted: 1 = strong
    customer_concentration: int = 0
    technology_risk: int = 0
    
    # Management & Governance (1-5, higher = riskier)
    management_quality: int = 0  # Inverted: 1 = good
    governance_risk: int = 0
    
    # ESG Factors (1-5, higher = riskier)
    environmental_risk: int = 0
    social_risk: int = 0
    governance_esg_risk: int = 0
    
    def average_financial_risk(self) -> float:
        """Calculate average financial risk score."""
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
        """Calculate average business risk score."""
        risks = [
            self.industry_risk,
            self.competitive_position,
            self.customer_concentration,
            self.technology_risk
        ]
        valid_risks = [r for r in risks if r > 0]
        return sum(valid_risks) / len(valid_risks) if valid_risks else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'leverage_risk': self.leverage_risk,
            'liquidity_risk': self.liquidity_risk,
            'profitability_risk': self.profitability_risk,
            'cash_flow_risk': self.cash_flow_risk,
            'coverage_risk': self.coverage_risk,
            'industry_risk': self.industry_risk,
            'competitive_position': self.competitive_position,
            'customer_concentration': self.customer_concentration,
            'technology_risk': self.technology_risk,
            'management_quality': self.management_quality,
            'governance_risk': self.governance_risk,
            'environmental_risk': self.environmental_risk,
            'social_risk': self.social_risk,
            'governance_esg_risk': self.governance_esg_risk,
            'average_financial_risk': self.average_financial_risk(),
            'average_business_risk': self.average_business_risk(),
        }


@dataclass
class CreditRiskAssessment:
    """Complete credit risk assessment result."""
    company_name: str
    fiscal_year: int
    overall_rating: str
    outlook: str
    risk_score: float  # 0-100, higher = riskier
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
    assessment_date: datetime = None
    analyst_notes: str = ""
    
    def __post_init__(self):
        if self.assessment_date is None:
            self.assessment_date = __import__('datetime').datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'company_name': self.company_name,
            'fiscal_year': self.fiscal_year,
            'overall_rating': self.overall_rating,
            'outlook': self.outlook,
            'risk_score': round(self.risk_score, 2),
            'risk_factors': self.risk_factors.to_dict(),
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
