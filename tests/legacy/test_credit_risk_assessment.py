"""
Test suite for credit_risk_assessment module.

Tests cover:
- Custom exceptions
- RiskFactorsValidator
- RiskFactors dataclass
- CreditRiskAssessment dataclass
- Scoring utilities
- CreditRiskAssessor class
- Integration tests

Run with: pytest tests/test_credit_risk_assessment.py -v --cov
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from credit_risk_assessment import (
    # Exceptions
    CreditRiskError,
    ValidationError,
    RatioAnalysisError,
    ConfigurationError,
    # Enums
    CreditRating,
    RiskDirection,
    # Data Classes
    RiskFactors,
    CreditRiskAssessment,
    # Validator
    RiskFactorsValidator,
    # Scoring Utilities
    score_interest_coverage,
    score_debt_to_ebitda,
    score_fcf_to_debt,
    score_current_ratio,
    score_net_margin,
    risk_score_to_rating,
    determine_outlook,
    # Main Class
    CreditRiskAssessor,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_ratios() -> Mock:
    """Create a mock CreditRatioAnalysis object."""
    ratios = Mock()
    ratios.interest_coverage = 5.5
    ratios.debt_to_ebitda = 3.2
    ratios.fcf_to_debt = 0.15
    ratios.current_ratio = 1.8
    ratios.net_margin = 12.0
    return ratios


@pytest.fixture
def strong_ratios() -> Mock:
    """Create a mock with strong credit metrics."""
    ratios = Mock()
    ratios.interest_coverage = 12.0
    ratios.debt_to_ebitda = 1.5
    ratios.fcf_to_debt = 0.45
    ratios.current_ratio = 2.5
    ratios.net_margin = 20.0
    return ratios


@pytest.fixture
def weak_ratios() -> Mock:
    """Create a mock with weak credit metrics."""
    ratios = Mock()
    ratios.interest_coverage = 1.2
    ratios.debt_to_ebitda = 8.5
    ratios.fcf_to_debt = -0.15
    ratios.current_ratio = 0.75
    ratios.net_margin = -5.0
    return ratios


@pytest.fixture
def sample_risk_factors() -> RiskFactors:
    """Create sample RiskFactors with moderate risk."""
    return RiskFactors(
        leverage_risk=3,
        liquidity_risk=2,
        profitability_risk=3,
        cash_flow_risk=2,
        coverage_risk=3,
        industry_risk=3,
        competitive_position=2,
        customer_concentration=1,
        technology_risk=3,
        management_quality=2,
        governance_risk=2,
        environmental_risk=2,
        social_risk=2,
        governance_esg_risk=2,
    )


# =============================================================================
# Exception Tests
# =============================================================================

class TestCreditRiskError:
    """Tests for CreditRiskError exception class."""
    
    def test_base_exception_with_message(self):
        """Test CreditRiskError with just a message."""
        error = CreditRiskError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.details == {}
    
    def test_base_exception_with_details(self):
        """Test CreditRiskError with message and details."""
        error = CreditRiskError("Validation failed", details={"field": "name", "value": ""})
        assert "field=name" in str(error)
        assert "field" in error.details
        assert error.details["field"] == "name"
    
    def test_exception_inheritance(self):
        """Test that other exceptions inherit from CreditRiskError."""
        error = ValidationError("test", "value", "type")
        assert isinstance(error, CreditRiskError)
        assert isinstance(error, Exception)


class TestValidationError:
    """Tests for ValidationError exception class."""
    
    def test_validation_error_attributes(self):
        """Test ValidationError has correct attributes."""
        error = ValidationError("field_name", "invalid_value", "string", "reason")
        assert error.field_name == "field_name"
        assert error.value == "invalid_value"
        assert error.expected_type == "string"
    
    def test_validation_error_message(self):
        """Test ValidationError formats message correctly."""
        error = ValidationError("company_name", "", "non-empty string")
        assert "company_name" in str(error)
        assert "Validation failed" in str(error)


class TestRatioAnalysisError:
    """Tests for RatioAnalysisError exception class."""
    
    def test_ratio_analysis_error(self):
        """Test RatioAnalysisError contains ratio info."""
        error = RatioAnalysisError("interest_coverage", -5.0, "non-negative")
        assert error.ratio_name == "interest_coverage"
        assert error.value == -5.0
        assert error.expected_range == "non-negative"


# =============================================================================
# RiskFactors Tests
# =============================================================================

class TestRiskFactors:
    """Tests for RiskFactors dataclass."""
    
    def test_default_risk_factors(self):
        """Test RiskFactors with default values."""
        rf = RiskFactors()
        assert rf.leverage_risk == 0
        assert rf.liquidity_risk == 0
        assert rf.average_financial_risk() == 0.0
        assert rf.average_business_risk() == 0.0
    
    def test_risk_factors_with_values(self, sample_risk_factors):
        """Test RiskFactors with custom values."""
        rf = sample_risk_factors
        assert rf.leverage_risk == 3
        assert rf.industry_risk == 3
    
    def test_average_financial_risk(self):
        """Test average_financial_risk calculation."""
        rf = RiskFactors(
            leverage_risk=2,
            liquidity_risk=4,
            profitability_risk=3,
            cash_flow_risk=1,
            coverage_risk=5,  # 5 values, avg = 3.0
        )
        assert rf.average_financial_risk() == 3.0
    
    def test_average_business_risk(self):
        """Test average_business_risk calculation."""
        rf = RiskFactors(
            industry_risk=2,
            competitive_position=4,
            customer_concentration=3,
            technology_risk=1,  # 4 values, avg = 2.5
        )
        assert rf.average_business_risk() == 2.5
    
    def test_total_risk_score(self, sample_risk_factors):
        """Test total_risk_score calculation with weights."""
        rf = sample_risk_factors
        # Financial avg = (3+2+3+2+3)/5 = 2.6
        # Business avg = (3+2+1+3)/4 = 2.25
        # Management avg = (2+2)/2 = 2.0
        # ESG avg = (2+2+2)/3 = 2.0
        # Weighted = 2.6*0.40 + 2.25*0.25 + 2.0*0.20 + 2.0*0.15 = 1.04 + 0.5625 + 0.4 + 0.3 = 2.3025
        # Scaled = 2.3025 * 20 = 46.05
        score = rf.total_risk_score()
        assert 40 < score < 50
    
    def test_risk_factor_validation_positive(self):
        """Test valid risk factor values."""
        rf = RiskFactors(leverage_risk=5, liquidity_risk=1)
        assert rf.leverage_risk == 5
        assert rf.liquidity_risk == 1
    
    def test_risk_factor_validation_negative(self):
        """Test invalid risk factor values raise error."""
        with pytest.raises(ValidationError):
            RiskFactors(leverage_risk=10)  # > 5
    
    def test_risk_factor_validation_non_integer(self):
        """Test non-integer risk factor values raise error."""
        with pytest.raises(ValidationError):
            RiskFactors(leverage_risk=3.5)
    
    def test_risk_factor_validation_negative_value(self):
        """Test negative risk factor values raise error."""
        with pytest.raises(ValidationError):
            RiskFactors(leverage_risk=-1)


# =============================================================================
# CreditRiskAssessment Tests
# =============================================================================

class TestCreditRiskAssessment:
    """Tests for CreditRiskAssessment dataclass."""
    
    def test_assessment_creation(self, sample_risk_factors):
        """Test creating a valid CreditRiskAssessment."""
        assessment = CreditRiskAssessment(
            company_name="Test Corp",
            fiscal_year=2024,
            overall_rating="BBB",
            outlook="Stable",
            risk_score=45.0,
            risk_factors=sample_risk_factors,
        )
        assert assessment.company_name == "Test Corp"
        assert assessment.fiscal_year == 2024
        assert assessment.risk_score == 45.0
    
    def test_assessment_validation_empty_company(self, sample_risk_factors):
        """Test empty company name raises error."""
        with pytest.raises(ValidationError):
            CreditRiskAssessment(
                company_name="",
                fiscal_year=2024,
                overall_rating="BBB",
                outlook="Stable",
                risk_score=45.0,
                risk_factors=sample_risk_factors,
            )
    
    def test_assessment_validation_invalid_year(self, sample_risk_factors):
        """Test invalid fiscal year raises error."""
        with pytest.raises(ValidationError):
            CreditRiskAssessment(
                company_name="Test Corp",
                fiscal_year=1800,  # Too old
                overall_rating="BBB",
                outlook="Stable",
                risk_score=45.0,
                risk_factors=sample_risk_factors,
            )
    
    def test_assessment_to_dict(self, sample_risk_factors):
        """Test to_dict method returns valid dictionary."""
        assessment = CreditRiskAssessment(
            company_name="Test Corp",
            fiscal_year=2024,
            overall_rating="BBB",
            outlook="Stable",
            risk_score=45.0,
            risk_factors=sample_risk_factors,
        )
        data = assessment.to_dict()
        assert isinstance(data, dict)
        assert data['company_name'] == "Test Corp"
        assert data['overall_rating'] == "BBB"
    
    def test_assessment_summary(self, sample_risk_factors):
        """Test summary method returns string."""
        assessment = CreditRiskAssessment(
            company_name="Test Corp",
            fiscal_year=2024,
            overall_rating="BBB",
            outlook="Stable",
            risk_score=45.0,
            risk_factors=sample_risk_factors,
            strengths=["Strong cash flow"],
            weaknesses=["High leverage"],
        )
        summary = assessment.summary()
        assert "Test Corp" in summary
        assert "BBB" in summary
        assert "Strengths" in summary
    
    def test_assessment_json_serialization(self, sample_risk_factors):
        """Test to_json method returns valid JSON."""
        assessment = CreditRiskAssessment(
            company_name="Test Corp",
            fiscal_year=2024,
            overall_rating="BBB",
            outlook="Stable",
            risk_score=45.0,
            risk_factors=sample_risk_factors,
        )
        import json
        json_str = assessment.to_json()
        data = json.loads(json_str)
        assert data['company_name'] == "Test Corp"


# =============================================================================
# Validator Tests
# =============================================================================

class TestRiskFactorsValidator:
    """Tests for RiskFactorsValidator class."""
    
    def test_validate_company_name_valid(self):
        """Test valid company name."""
        result = RiskFactorsValidator.validate_company_name("  Test Corp  ")
        assert result == "Test Corp"
    
    def test_validate_company_name_empty(self):
        """Test empty company name raises error."""
        with pytest.raises(ValidationError):
            RiskFactorsValidator.validate_company_name("")
    
    def test_validate_company_name_non_string(self):
        """Test non-string company name raises error."""
        with pytest.raises(ValidationError):
            RiskFactorsValidator.validate_company_name(123)
    
    def test_validate_company_name_too_long(self):
        """Test overly long company name raises error."""
        long_name = "x" * 501
        with pytest.raises(ValidationError):
            RiskFactorsValidator.validate_company_name(long_name)
    
    def test_validate_industry_valid(self):
        """Test valid industry name."""
        result = RiskFactorsValidator.validate_industry("  Technology  ")
        assert result == "technology"
    
    def test_validate_industry_empty(self):
        """Test empty industry raises error."""
        with pytest.raises(ValidationError):
            RiskFactorsValidator.validate_industry("")
    
    def test_validate_fiscal_year_valid(self):
        """Test valid fiscal year."""
        result = RiskFactorsValidator.validate_fiscal_year(2024)
        assert result == 2024
    
    def test_validate_fiscal_year_future(self):
        """Test future fiscal year raises error."""
        with pytest.raises(ValidationError):
            RiskFactorsValidator.validate_fiscal_year(2100)
    
    def test_validate_interest_coverage_valid(self):
        """Test valid interest coverage."""
        result = RiskFactorsValidator.validate_interest_coverage(5.5)
        assert result == 5.5
    
    def test_validate_interest_coverage_none_allowed(self):
        """Test None is allowed when allow_none=True."""
        result = RiskFactorsValidator.validate_interest_coverage(None, allow_none=True)
        assert result is None
    
    def test_validate_interest_coverage_none_not_allowed(self):
        """Test None raises error when allow_none=False."""
        with pytest.raises(ValidationError):
            RiskFactorsValidator.validate_interest_coverage(None, allow_none=False)
    
    def test_validate_debt_to_ebitda_valid(self):
        """Test valid Debt/EBITDA."""
        result = RiskFactorsValidator.validate_debt_to_ebitda(3.5)
        assert result == 3.5
    
    def test_validate_current_ratio_valid(self):
        """Test valid current ratio."""
        result = RiskFactorsValidator.validate_current_ratio(1.8)
        assert result == 1.8
    
    def test_validate_current_ratio_negative(self):
        """Test negative current ratio raises error."""
        with pytest.raises(ValidationError):
            RiskFactorsValidator.validate_current_ratio(-1.0)
    
    def test_validate_fcf_to_debt_valid(self):
        """Test valid FCF/Debt."""
        result = RiskFactorsValidator.validate_fcf_to_debt(0.25)
        assert result == 0.25


# =============================================================================
# Scoring Utility Tests
# =============================================================================

class TestScoringUtilities:
    """Tests for scoring utility functions."""
    
    @pytest.mark.parametrize("ic,expected", [
        (10, 1),   # Excellent
        (8, 1),
        (6, 2),    # Good
        (5, 2),
        (4, 3),    # Fair
        (3, 3),
        (2, 4),    # Weak
        (1.5, 4),
        (1, 5),    # Poor
        (0.5, 5),
    ])
    def test_score_interest_coverage(self, ic, expected):
        """Test interest coverage scoring."""
        assert score_interest_coverage(ic) == expected
    
    def test_score_interest_coverage_negative_raises(self):
        """Test negative interest coverage raises ValueError."""
        with pytest.raises(ValueError):
            score_interest_coverage(-1)
    
    @pytest.mark.parametrize("d_e,expected", [
        (1, 1),    # Excellent
        (2, 1),
        (3, 2),    # Good
        (3.5, 2),
        (4, 3),    # Fair
        (5, 3),
        (6, 4),    # Weak
        (7, 4),
        (8, 5),    # Poor
    ])
    def test_score_debt_to_ebitda(self, d_e, expected):
        """Test Debt/EBITDA scoring."""
        assert score_debt_to_ebitda(d_e) == expected
    
    @pytest.mark.parametrize("fcf_d,expected", [
        (0.6, 1),   # Excellent
        (0.5, 1),
        (0.3, 2),   # Good
        (0.25, 2),
        (0.15, 3),  # Fair
        (0.1, 3),
        (0.05, 4),  # Weak
        (0, 4),
        (-0.1, 5),  # Poor
    ])
    def test_score_fcf_to_debt(self, fcf_d, expected):
        """Test FCF/Debt scoring."""
        assert score_fcf_to_debt(fcf_d) == expected
    
    @pytest.mark.parametrize("cr,expected", [
        (3.0, 1),   # Excellent
        (2.0, 1),
        (1.7, 2),   # Good
        (1.5, 2),
        (1.3, 3),   # Fair
        (1.2, 3),
        (1.05, 4),  # Weak
        (1.0, 4),
        (0.5, 5),   # Poor
    ])
    def test_score_current_ratio(self, cr, expected):
        """Test current ratio scoring."""
        assert score_current_ratio(cr) == expected
    
    def test_score_current_ratio_negative_raises(self):
        """Test negative current ratio raises ValueError."""
        with pytest.raises(ValueError):
            score_current_ratio(-1.0)
    
    @pytest.mark.parametrize("margin,expected", [
        (20, 1),   # Excellent
        (15, 1),
        (12, 2),   # Good
        (10, 2),
        (7, 3),    # Fair
        (5, 3),
        (2, 4),    # Weak
        (0.5, 4),
        (-5, 5),   # Poor
    ])
    def test_score_net_margin(self, margin, expected):
        """Test net margin scoring."""
        assert score_net_margin(margin) == expected
    
    def test_score_net_margin_none(self):
        """Test None net margin returns 0."""
        assert score_net_margin(None) == 0
    
    @pytest.mark.parametrize("score,expected_rating", [
        (0, "AAA"),
        (10, "AAA"),
        (19.9, "AAA"),
        (20, "AA"),
        (29.9, "AA"),
        (30, "A"),
        (39.9, "A"),
        (40, "BBB"),
        (49.9, "BBB"),
        (50, "BB"),
        (59.9, "BB"),
        (60, "B"),
        (69.9, "B"),
        (70, "CCC"),
        (79.9, "CCC"),
        (80, "CC"),
        (89.9, "CC"),
        (90, "C"),
        (100, "C"),
    ])
    def test_risk_score_to_rating(self, score, expected_rating):
        """Test risk score to rating conversion."""
        assert risk_score_to_rating(score) == expected_rating
    
    def test_risk_score_to_rating_invalid(self):
        """Test invalid risk score raises ValueError."""
        with pytest.raises(ValueError):
            risk_score_to_rating(-1)
        with pytest.raises(ValueError):
            risk_score_to_rating(101)
    
    def test_determine_outlook_positive(self):
        """Test positive outlook determination."""
        result = determine_outlook(6.0, 0.2, 1.8)
        assert "Positive" in result
    
    def test_determine_outlook_negative(self):
        """Test negative outlook determination."""
        result = determine_outlook(1.0, -0.2, 0.8)
        assert "Negative" in result
    
    def test_determine_outlook_stable(self):
        """Test stable outlook determination."""
        result = determine_outlook(3.0, 0.05, 1.1)
        assert result == "Stable"
    
    def test_determine_outlook_mixed(self):
        """Test mixed outlook determination."""
        result = determine_outlook(6.0, -0.2, 1.8)
        assert "Mixed" in result


# =============================================================================
# CreditRiskAssessor Tests
# =============================================================================

class TestCreditRiskAssessor:
    """Tests for CreditRiskAssessor class."""
    
    def test_assessor_initialization(self):
        """Test assessor initializes with empty assessments."""
        assessor = CreditRiskAssessor()
        assert assessor.assessments == []
    
    def test_assess_credit_success(self, mock_ratios):
        """Test successful credit assessment."""
        assessor = CreditRiskAssessor()
        assessment = assessor.assess_credit(
            company_name="Test Corp",
            ratios=mock_ratios,
            industry="Technology",
        )
        assert assessment.company_name == "Test Corp"
        assert assessment.industry_risk == 3  # Technology = 3
        assert assessment.risk_score > 0
        assert len(assessor.assessments) == 1
    
    def test_assess_credit_strong_profile(self, strong_ratios):
        """Test assessment with strong credit profile."""
        assessor = CreditRiskAssessor()
        assessment = assessor.assess_credit(
            company_name="Strong Corp",
            ratios=strong_ratios,
            industry="Technology",
        )
        assert assessment.risk_score < 30  # Low risk
        assert assessment.overall_rating in ["AAA", "AA", "A"]
        assert "Positive" in assessment.outlook
        assert len(assessment.strengths) > 0
    
    def test_assess_credit_weak_profile(self, weak_ratios):
        """Test assessment with weak credit profile."""
        assessor = CreditRiskAssessor()
        assessment = assessor.assess_credit(
            company_name="Weak Corp",
            ratios=weak_ratios,
            industry="Retail",
        )
        assert assessment.risk_score > 60  # High risk
        assert assessment.overall_rating in ["B", "CCC", "CC", "C"]
        assert len(assessment.weaknesses) > 0
    
    def test_assess_credit_invalid_company_name(self, mock_ratios):
        """Test assessment with invalid company name."""
        assessor = CreditRiskAssessor()
        with pytest.raises(ValidationError):
            assessor.assess_credit(
                company_name="",
                ratios=mock_ratios,
            )
    
    def test_assess_credit_invalid_industry(self, mock_ratios):
        """Test assessment with invalid additional_factors."""
        assessor = CreditRiskAssessor()
        with pytest.raises(ValidationError):
            assessor.assess_credit(
                company_name="Test Corp",
                ratios=mock_ratios,
                industry="Technology",
                additional_factors={"customer_concentration": 6}  # Invalid - must be 1-5
            )
    
    def test_assess_credit_invalid_ratios_type(self):
        """Test assessment with invalid ratios type."""
        assessor = CreditRiskAssessor()
        with pytest.raises(TypeError):
            assessor.assess_credit(
                company_name="Test Corp",
                ratios="not a ratios object",  # type: ignore
            )
    
    def test_assess_credit_with_additional_factors(self, mock_ratios):
        """Test assessment with additional risk factors."""
        assessor = CreditRiskAssessor()
        assessment = assessor.assess_credit(
            company_name="Test Corp",
            ratios=mock_ratios,
            additional_factors={
                "customer_concentration": 4,
                "management_quality": 3,
            },
        )
        assert assessment.risk_factors.customer_concentration == 4
        assert assessment.risk_factors.management_quality == 3
    
    def test_assess_credit_with_analyst_notes(self, mock_ratios):
        """Test assessment includes analyst notes."""
        assessor = CreditRiskAssessor()
        assessment = assessor.assess_credit(
            company_name="Test Corp",
            ratios=mock_ratios,
            analyst_notes="Special note about restructuring",
        )
        assert "restructuring" in assessment.analyst_notes
    
    def test_assess_credit_with_fiscal_year(self, mock_ratios):
        """Test assessment with custom fiscal year."""
        assessor = CreditRiskAssessor()
        assessment = assessor.assess_credit(
            company_name="Test Corp",
            ratios=mock_ratios,
            fiscal_year=2022,
        )
        assert assessment.fiscal_year == 2022
    
    def test_compare_to_peers(self, mock_ratios):
        """Test peer comparison."""
        assessor = CreditRiskAssessor()
        assessment = assessor.assess_credit(
            company_name="Test Corp",
            ratios=mock_ratios,
        )
        
        peer_ratios = {
            "Peer A": Mock(company_name="Peer A"),
            "Peer B": Mock(company_name="Peer B"),
        }
        
        comparison = assessor.compare_to_peers(assessment, peer_ratios)
        assert "Test Corp" in comparison.columns
        assert "Peer A" in comparison['Metric'].values


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the complete workflow."""
    
    def test_full_assessment_workflow(self):
        """Test complete assessment workflow."""
        # Create mock ratios with realistic data
        ratios = Mock()
        ratios.interest_coverage = 7.5
        ratios.debt_to_ebitda = 2.8
        ratios.fcf_to_debt = 0.35
        ratios.current_ratio = 1.9
        ratios.net_margin = 15.0
        
        # Create assessor and run assessment
        assessor = CreditRiskAssessor()
        assessment = assessor.assess_credit(
            company_name="Integration Test Corp",
            ratios=ratios,
            industry="Healthcare",
            fiscal_year=2024,
            additional_factors={
                "customer_concentration": 2,
                "management_quality": 2,
            },
            analyst_notes="Integration test assessment",
        )
        
        # Verify all components work together
        assert assessment.company_name == "Integration Test Corp"
        assert assessment.risk_factors.industry_risk == 2  # Healthcare = 2
        assert assessment.risk_factors.customer_concentration == 2
        assert 20 < assessment.risk_score < 50  # Medium risk
        assert assessment.overall_rating in ["A", "BBB", "BB"]
        
        # Verify serialization works
        data = assessment.to_dict()
        json_str = assessment.to_json()
        summary = assessment.summary()
        
        assert "Integration Test Corp" in summary
        assert len(assessor.assessments) == 1
    
    def test_exception_propagation(self):
        """Test that exceptions propagate correctly through the workflow."""
        assessor = CreditRiskAssessor()
        
        # Invalid ratios should raise TypeError
        with pytest.raises(TypeError) as exc_info:
            assessor.assess_credit(
                company_name="Test",
                ratios="invalid",  # type: ignore
            )
        assert "CreditRatioAnalysis" in str(exc_info.value)
    
    def test_validation_error_details(self):
        """Test that validation errors contain useful details."""
        assessor = CreditRiskAssessor()
        
        ratios = Mock()
        ratios.interest_coverage = None
        ratios.debt_to_ebitda = None
        ratios.fcf_to_debt = None
        ratios.current_ratio = -5  # Invalid!
        ratios.net_margin = None
        
        # Negative current ratio should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            assessor.assess_credit(
                company_name="Test",
                ratios=ratios,
            )
        assert exc_info.value.field_name == "current_ratio"
        assert "negative" in str(exc_info.value).lower()


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
