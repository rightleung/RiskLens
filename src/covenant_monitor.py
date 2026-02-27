"""
Covenant Monitoring Module
==========================
Analyzes financial ratios against defined financial covenants.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from ratio_analyzer import CreditRatioAnalysis


class FinancialCovenants(BaseModel):
    """Configuration for financial covenants / red lines."""
    min_interest_coverage: Optional[float] = Field(None, description="Minimum Interest Coverage ratio")
    max_debt_to_ebitda: Optional[float] = Field(None, description="Maximum Debt / EBITDA ratio")
    max_debt_to_equity: Optional[float] = Field(None, description="Maximum Debt / Equity ratio")
    min_current_ratio: Optional[float] = Field(None, description="Minimum Current Ratio")
    min_quick_ratio: Optional[float] = Field(None, description="Minimum Quick Ratio")
    min_fcf_to_debt: Optional[float] = Field(None, description="Minimum FCF / Debt ratio")


class CovenantAlert(BaseModel):
    """Alert structure for a breached covenant."""
    metric: str
    threshold: float
    actual_value: Optional[float]  # None / NaN when data is unavailable
    breached: bool
    direction: str  # "min" or "max"
    message: str


class CovenantReport(BaseModel):
    """Full report on covenant compliance."""
    company_name: str
    fiscal_year: int
    covenants_passed: int
    covenants_breached: int
    alerts: List[CovenantAlert]


class CovenantMonitor:
    """Monitors financial covenants for credit assessments."""
    
    @staticmethod
    def _check_metric(metric_name: str, actual: Optional[float], threshold: Optional[float], 
                      direction: str, label: str) -> Optional[CovenantAlert]:
        # OR-002: No threshold configured — skip this covenant entirely.
        if threshold is None:
            return None
        
        # OR-002: Threshold is set but data is unavailable → default breach.
        # Silently passing a missing metric would create a false-positive pass
        # and constitute a financial due-diligence failure.
        if actual is None:
            return CovenantAlert(
                metric=metric_name,
                threshold=threshold,
                actual_value=None,
                breached=True,
                direction=direction,
                message=f"⚠️ DATA_UNAVAILABLE: {label} could not be calculated — "
                        f"defaulting to BREACH pending manual verification."
            )
            
        breached = False
        message = ""
        
        if direction == "min":
            breached = actual < threshold
            verb = "below minimum"
        else:
            breached = actual > threshold
            verb = "above maximum"
            
        if breached:
            message = f"🚨 BREACH: {label} is {actual:.2f} ({verb} of {threshold:.2f})"
        else:
            message = f"✅ PASS: {label} is {actual:.2f} (threshold {direction} {threshold:.2f})"
            
        return CovenantAlert(
            metric=metric_name,
            threshold=threshold,
            actual_value=actual,
            breached=breached,
            direction=direction,
            message=message
        )

    def check_covenants(self, company_name: str, fiscal_year: int, 
                        ratios: CreditRatioAnalysis, covenants: FinancialCovenants) -> CovenantReport:
        """
        Check actual financial ratios against covenant requirements.
        """
        alerts = []
        
        checks = [
            ("interest_coverage", ratios.interest_coverage, covenants.min_interest_coverage, "min", "Interest Coverage"),
            ("debt_to_ebitda", ratios.debt_to_ebitda, covenants.max_debt_to_ebitda, "max", "Debt to EBITDA"),
            ("debt_to_equity", ratios.debt_to_equity, covenants.max_debt_to_equity, "max", "Debt to Equity"),
            ("current_ratio", ratios.current_ratio, covenants.min_current_ratio, "min", "Current Ratio"),
            ("quick_ratio", ratios.quick_ratio, covenants.min_quick_ratio, "min", "Quick Ratio"),
            ("fcf_to_debt", ratios.fcf_to_debt, covenants.min_fcf_to_debt, "min", "FCF to Debt"),
        ]
        
        for metric_name, actual, threshold, direction, label in checks:
            alert = self._check_metric(metric_name, actual, threshold, direction, label)
            if alert:
                alerts.append(alert)
                
        breached_count = sum(1 for a in alerts if a.breached)
        passed_count = len(alerts) - breached_count
        
        return CovenantReport(
            company_name=company_name,
            fiscal_year=fiscal_year,
            covenants_passed=passed_count,
            covenants_breached=breached_count,
            alerts=alerts
        )
