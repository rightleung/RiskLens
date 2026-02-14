## Architecture Overview

A modular, production-ready credit risk assessment framework with comprehensive error handling, full type annotations, and testable components. The architecture separates concerns into distinct layers: data models, validation, business logic, and assessment engine.

## Components

| Component | Responsibility | Inputs | Outputs |
|-----------|---------------|--------|---------|
| **Custom Exceptions** | Centralized error handling with specific exception types | Validation failures, calculation errors, configuration errors | Rich error messages with context |
| **Configuration Manager** | Manage thresholds, weights, and industry mappings | config.yaml, environment variables | Validated configuration object |
| **Data Models (Pydantic)** | Validate input/output data structures | JSON/dict data, user inputs | Validated Pydantic models |
| **Financial Ratio Validator** | Validate financial ratio calculations | Raw financial data | Validated ratios, validation warnings |
| **Risk Scoring Engine** | Calculate risk scores from risk factors | RiskFactors object, weights | Risk scores (0-100) |
| **Rating Mapper** | Map risk scores to credit ratings | Risk scores, ratio context | CreditRating enum value |
| **Outlook Analyzer** | Determine rating outlook based on trends | Historical/current ratios, trends | RiskDirection enum value |
| **Peer Comparison Engine** | Compare companies against peer groups | Assessment, peer ratios | Comparison DataFrame |
| **Assessment Orchestrator** | Coordinate full credit assessment workflow | Company data, ratios, config | Complete CreditRiskAssessment |
| **Test Fixtures Factory** | Generate realistic test data | Test scenarios | Mock financial data, assessments |

## Data Flow

### Assessment Flow (Step-by-step)

1. **Input Validation**
   - User provides: `company_name`, `ratios`, `industry`, `fiscal_year`, `additional_factors`
   - Configuration Manager loads thresholds and weights
   - Data Models validate input types and constraints
   - Financial Ratio Validator checks ratio reasonableness

2. **Risk Factor Assessment**
   - For each financial ratio (interest_coverage, debt_to_ebitda, etc.):
     - Compare against threshold bands
     - Assign risk score (1-5 scale)
   - Apply industry risk adjustment
   - Incorporate additional qualitative factors

3. **Score Calculation**
   - Calculate weighted average: `financial_risk * 0.6 + business_risk * 0.4`
   - Scale to 0-100 range
   - Apply confidence adjustments based on data completeness

4. **Rating Determination**
   - Pass risk_score through threshold mapper
   - Generate rating with modifiers (e.g., "AAA-", "BB+")
   - Validate rating alignment with key metrics

5. **Outlook Generation**
   - Analyze trend indicators from multiple periods
   - Determine direction: IMPROVING, STABLE, DETERIORATING, VOLATILE
   - Generate supporting evidence list

6. **Strengths/Weaknesses Identification**
   - Compare each metric against threshold bands
   - Populate strengths (positive factors), weaknesses (negative factors)
   - Generate watch items for borderline metrics

7. **Assessment Completion**
   - Assemble all components into CreditRiskAssessment object
   - Store assessment in history
   - Return to user

### Error Handling Flow

1. Input validation → `ValidationError` with field details
2. Configuration missing → `ConfigurationError`
3. Calculation overflow → `CalculationError`
4. Missing required data → `InsufficientDataError`
5. Invalid state → `AssessmentStateError`

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| **Use Pydantic for data validation** | Provides automatic validation, serialization, and type coercion. Reduces boilerplate and catches errors early. |
| **Custom exception hierarchy** | Enables precise error handling at different levels. Users can catch specific exceptions or use base classes for broad handling. |
| **Configuration object pattern** | Centralizes thresholds/weights for easy tuning without code changes. Enables A/B testing and regulatory adjustments. |
| **Plugin architecture for thresholds** | Allows industry-specific or client-specific threshold sets. Supports customization without modifying core logic. |
| **Separation of scoring and rating** | Makes it easy to swap rating methodologies. Financial scoring is reusable across different rating schemes. |
| **Comprehensive validation layer** | Catches data quality issues before calculations. Provides actionable error messages for analysts. |
| **Factory pattern for test fixtures** | Ensures consistent, realistic test data generation. Makes test maintenance easier as data structures evolve. |
| **Immutable data models** | Prevents accidental state changes. Makes code easier to reason about and test. |
| **Historical assessment tracking** | Enables trend analysis over time. Supports audit requirements and regulatory compliance. |
| **Type-safe ratio calculations** | Full type hints enable static analysis. Catches type-related bugs early in development. |

## Proposed File Structure

```
credit_risk_assessment/
├── __init__.py
├── exceptions.py           # Custom exception hierarchy
├── config.py               # Configuration management
├── models.py              # Pydantic data models
├── validators.py           # Input/data validators
├── scoring.py             # Risk scoring engine
├── rating.py              # Rating mapping logic
├── outlook.py             # Outlook determination
├── peer_comparison.py     # Peer analysis
├── assessor.py            # Main orchestrator
└── tests/
    ├── __init__.py
    ├── conftest.py        # Pytest fixtures
    ├── test_models.py     # Data model tests
    ├── test_validators.py  # Validation tests
    ├── test_scoring.py    # Scoring tests
    ├── test_rating.py     # Rating tests
    ├── test_outlook.py    # Outlook tests
    ├── test_assessor.py   # Integration tests
    └── test_e2e.py        # End-to-end scenarios
```

## Test Coverage Strategy

1. **Unit Tests** - Each component tested in isolation with mocked dependencies
2. **Integration Tests** - Test component interactions
3. **Edge Cases** - Boundary conditions, missing data, extreme values
4. **Error Handling** - Verify proper exceptions for invalid inputs
5. **Regression Tests** - Ensure existing behavior is preserved
6. **Property-Based Tests** - Generate random valid inputs to find edge cases

## API Compatibility

- Maintain `CreditRiskAssessor.assess_credit()` signature
- Preserve `CreditRiskAssessment` and `RiskFactors` interfaces
- Add optional parameters with sensible defaults
- Deprecate internal methods with warnings if needed
