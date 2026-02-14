"""Risk calculation engine for credit risk assessment."""

from typing import Dict, Optional, Any
from .models import RiskFactors, CreditRiskAssessment
from .exceptions import CalculationError, InvalidRatioError


class CreditRiskCalculator:
    """Calculates credit risk scores and ratings based on financial data."""
    
    # Scoring thresholds
    THRESHOLDS: Dict[str, Dict[str, float]] = {
        'interest_coverage': {
            'excellent': 8,
            'good': 5,
            'fair': 3,
            'weak': 1.5,
            'poor': 0,
        },
        'debt_to_ebitda': {
            'excellent': 2,
            'good': 3.5,
            'fair': 5,
            'weak': 7,
            'poor': 10,
        },
        'fcf_to_debt': {
            'excellent': 0.5,
            'good': 0.25,
            'fair': 0.1,
            'weak': 0,
            'poor': -0.1,
        },
        'current_ratio': {
            'excellent': 2,
            'good': 1.5,
            'fair': 1.2,
            'weak': 1,
            'poor': 0.8,
        },
    }
    
    # Industry risk scores (1-5, higher = riskier)
    INDUSTRY_RISK: Dict[str, int] = {
        'technology': 3,
        'software': 3,
        'hardware': 4,
        'financial': 4,
        'banking': 4,
        'insurance': 3,
        'healthcare': 2,
        'pharmaceuticals': 2,
        'retail': 4,
        'consumer': 4,
        'industrial': 3,
        'energy': 5,
        'utilities': 2,
        'real_estate': 4,
        'telecom': 4,
        'media': 4,
    }
    
    # Financial weight (60%) vs Business weight (40%)
    FINANCIAL_WEIGHT = 0.6
    BUSINESS_WEIGHT = 0.4
    
    def __init__(self):
        """Initialize calculator with default thresholds."""
        pass
    
    def _score_to_risk(self, name: str, value: float) -> int:
        """Convert a financial ratio to a risk score (1-5)."""
        thresholds = self.THRESHOLDS.get(name, {})
        
        if not thresholds:
            raise CalculationError(f'Unknown ratio: {name}')
        
        # Interest coverage: higher is better
        if name == 'interest_coverage':
            if value >= thresholds['excellent']:
                return 1
            elif value >= thresholds['good']:
                return 2
            elif value >= thresholds['fair']:
                return 3
            elif value >= thresholds['weak']:
                return 4
            else:
                return 5
        
        # Debt/EBITDA: lower is better
        elif name == 'debt_to_ebitda':
            if value <= thresholds['excellent']:
                return 1
            elif value <= thresholds['good']:
                return 2
            elif value <= thresholds['fair']:
                return 3
            elif value <= thresholds['weak']:
                return 4
            else:
                return 5
        
        # FCF/Debt: higher is better
        elif name == 'fcf_to_debt':
            if value >= thresholds['excellent']:
                return 1
            elif value >= thresholds['good']:
                return 2
            elif value >= thresholds['fair']:
                return 3
            elif value >= thresholds['weak']:
                return 4
            else:
                return 5
        
        # Current ratio: higher is better
        elif name == 'current_ratio':
            if value >= thresholds['excellent']:
                return 1
            elif value >= thresholds['good']:
                return 2
            elif value >= thresholds['fair']:
                return 3
            elif value >= thresholds['weak']:
                return 4
            else:
                return 5
        
        else:
            raise CalculationError(f'No scoring logic for ratio: {name}')
    
    def _calculate_net_margin_risk(self, net_margin: Optional[float]) -> int:
        """Calculate risk based on net profit margin."""
        if net_margin is None:
            return 0
        
        if net_margin >= 15:
            return 1
        elif net_margin >= 10:
            return 2
        elif net_margin >= 5:
            return 3
        elif net_margin > 0:
            return 4
        else:
            return 5
    
    def _score_to_rating(self, risk_score: float, 
                         financials: Dict[str, Any]) -> str:
        """Convert risk score to credit rating."""
        # Adjust for very strong coverage ratios
        ic = financials.get('interest_coverage')
        if ic and ic > 10:
            # Strong coverage can boost rating by one notch
            if risk_score < 25:
                return "AAA"
            elif risk_score < 35:
                return "AA"
            elif risk_score < 45:
                return "A"
            elif risk_score < 55:
                return "BBB"
        
        # Standard rating conversion
        if risk_score < 20:
            return "AAA"
        elif risk_score < 30:
            return "AA"
        elif risk_score < 40:
            return "A"
        elif risk_score < 50:
            return "BBB"
        elif risk_score < 60:
            return "BB"
        elif risk_score < 70:
            return "B"
        elif risk_score < 80:
            return "CCC"
        elif risk_score < 90:
            return "CC"
        else:
            return "C"
    
    def _determine_outlook(self, financials: Dict[str, Any]) -> str:
        """Determine rating outlook based on metrics."""
        improving_factors = []
        
        ic = financials.get('interest_coverage')
        if ic and ic > 5:
            improving_factors.append("interest coverage")
        
        fcf = financials.get('fcf_to_debt')
        if fcf and fcf > 0.1:
            improving_factors.append("free cash flow")
        
        cr = financials.get('current_ratio')
        if cr and cr > 1.5:
            improving_factors.append("liquidity")
        
        if improving_factors:
            return f"Positive ({', '.join(improving_factors)})"
        
        return "Stable"
    
    def _identify_strengths_weaknesses(self, 
                                        financials: Dict[str, Any],
                                        risk_factors: RiskFactors) -> tuple:
        """Identify key strengths and weaknesses."""
        strengths = []
        weaknesses = []
        watch_items = []
        
        ic = financials.get('interest_coverage')
        if ic:
            if ic > 5:
                strengths.append(f"Strong interest coverage ({ic:.1f}x)")
            elif ic < 2:
                weaknesses.append(f"Weak interest coverage ({ic:.1f}x)")
                watch_items.append("Interest coverage deterioration")
        
        d_e = financials.get('debt_to_ebitda')
        if d_e:
            if d_e < 3:
                strengths.append(f"Low leverage (Debt/EBITDA: {d_e:.1f})")
            elif d_e > 5:
                weaknesses.append(f"High leverage (Debt/EBITDA: {d_e:.1f})")
        
        fcf = financials.get('fcf_to_debt')
        if fcf:
            if fcf > 0.2:
                strengths.append(f"Strong free cash flow ({fcf*100:.1f}% of debt)")
            elif fcf < 0:
                weaknesses.append("Negative free cash flow")
        
        cr = financials.get('current_ratio')
        if cr:
            if cr > 1.5:
                strengths.append(f"Good liquidity (Current Ratio: {cr:.2f})")
            elif cr < 1:
                weaknesses.append(f"Weak liquidity (Current Ratio: {cr:.2f})")
        
        return strengths, weaknesses, watch_items
    
    def calculate(self, 
                  financials: Dict[str, Any],
                  industry: str = "general",
                  fiscal_year: Optional[int] = None,
                  additional_factors: Optional[Dict[str, Any]] = None) -> CreditRiskAssessment:
        """Perform comprehensive credit risk assessment.
        
        Args:
            financials: Dictionary of financial ratios and company info
            industry: Industry sector for peer comparison
            fiscal_year: Fiscal year of analysis
            additional_factors: Additional risk factors
        
        Returns:
            CreditRiskAssessment with rating and analysis
        """
        # Build risk factors
        risk_factors = RiskFactors()
        
        # Financial Risk Scoring
        ic = financials.get('interest_coverage')
        if ic is not None:
            risk_factors.coverage_risk = self._score_to_risk('interest_coverage', ic)
        
        d_e = financials.get('debt_to_ebitda')
        if d_e is not None:
            risk_factors.leverage_risk = self._score_to_risk('debt_to_ebitda', d_e)
        
        fcf = financials.get('fcf_to_debt')
        if fcf is not None:
            risk_factors.cash_flow_risk = self._score_to_risk('fcf_to_debt', fcf)
        
        cr = financials.get('current_ratio')
        if cr is not None:
            risk_factors.liquidity_risk = self._score_to_risk('current_ratio', cr)
        
        net_margin = financials.get('net_margin')
        risk_factors.profitability_risk = self._calculate_net_margin_risk(net_margin)
        
        # Business Risk Scoring
        industry_lower = industry.lower()
        risk_factors.industry_risk = self.INDUSTRY_RISK.get(industry_lower, 3)
        
        # Additional factors
        if additional_factors:
            if 'customer_concentration' in additional_factors:
                risk_factors.customer_concentration = additional_factors['customer_concentration']
            if 'management_quality' in additional_factors:
                risk_factors.management_quality = additional_factors['management_quality']
        
        # Calculate Overall Risk Score
        financial_risk = risk_factors.average_financial_risk()
        business_risk = risk_factors.average_business_risk()
        
        risk_score = (
            financial_risk * self.FINANCIAL_WEIGHT + 
            business_risk * self.BUSINESS_WEIGHT
        ) * 20  # Scale to 0-100
        
        # Generate Rating and Outlook
        rating = self._score_to_rating(risk_score, financials)
        outlook = self._determine_outlook(financials)
        
        # Identify Strengths and Weaknesses
        strengths, weaknesses, watch_items = self._identify_strengths_weaknesses(
            financials, risk_factors
        )
        
        # Create Assessment
        assessment = CreditRiskAssessment(
            company_name=financials.get('company_name', 'Unknown'),
            fiscal_year=fiscal_year or __import__('datetime').datetime.now().year,
            overall_rating=rating,
            outlook=outlook,
            risk_score=risk_score,
            risk_factors=risk_factors,
            interest_coverage=ic,
            debt_to_ebitda=d_e,
            fcf_to_debt=fcf,
            current_ratio=cr,
            strengths=strengths,
            weaknesses=weaknesses,
            watch_items=watch_items,
        )
        
        return assessment
