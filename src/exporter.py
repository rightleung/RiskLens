"""Export utilities for credit risk assessment."""

from typing import Any, Dict, Optional
from .models import CreditRiskAssessment
from .exceptions import ExportError


class RiskExporter:
    """Exports credit risk assessments to various formats."""
    
    def to_dict(self, assessment: CreditRiskAssessment) -> Dict[str, Any]:
        """Convert assessment to dictionary."""
        return assessment.to_dict()
    
    def to_json(self, assessment: CreditRiskAssessment, 
                indent: int = 2) -> str:
        """Convert assessment to JSON string."""
        try:
            import json
            return json.dumps(self.to_dict(assessment), indent=indent)
        except (TypeError, ValueError) as e:
            raise ExportError(f"Failed to export to JSON: {e}")
    
    def summary(self, assessment: CreditRiskAssessment) -> str:
        """Generate a human-readable summary."""
        lines = [
            f"Credit Risk Assessment for {assessment.company_name}",
            f"Fiscal Year: {assessment.fiscal_year}",
            "-" * 50,
            f"Overall Rating: {assessment.overall_rating}",
            f"Outlook: {assessment.outlook}",
            f"Risk Score: {assessment.risk_score:.1f}/100",
            "",
            "Key Metrics:",
            f"  Interest Coverage: {self._format_metric(assessment.interest_coverage)}",
            f"  Debt/EBITDA: {self._format_metric(assessment.debt_to_ebitda)}",
            f"  FCF/Debt: {self._format_metric(assessment.fcf_to_debt)}",
            f"  Current Ratio: {self._format_metric(assessment.current_ratio)}",
        ]
        
        if assessment.strengths:
            lines.extend(["", "Strengths:"])
            for strength in assessment.strengths:
                lines.append(f"  ✓ {strength}")
        
        if assessment.weaknesses:
            lines.extend(["", "Weaknesses:"])
            for weakness in assessment.weaknesses:
                lines.append(f"  ✗ {weakness}")
        
        if assessment.watch_items:
            lines.extend(["", "Watch Items:"])
            for item in assessment.watch_items:
                lines.append(f"  ⚠ {item}")
        
        lines.extend([
            "",
            f"Assessment Date: {assessment.assessment_date.strftime('%Y-%m-%d')}",
        ])
        
        return "\n".join(lines)
    
    def _format_metric(self, value: Optional[float], 
                       format_str: str = "{:.2f}") -> str:
        """Format a metric value for display."""
        if value is None:
            return "N/A"
        return format_str.format(value)
