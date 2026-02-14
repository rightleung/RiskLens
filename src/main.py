"""
Credit Analyst Toolkit — Main Module
=====================================
End-to-end credit analysis workflow.

Usage:
    from credit_analyst_toolkit import CreditAnalystToolkit
    toolkit = CreditAnalystToolkit()
    toolkit.run_full_analysis(company_data)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
import argparse

# Import toolkit modules
from financial_statement_parser import FinancialStatementParser, FinancialStatement
from ratio_analyzer import RatioAnalyzer, CreditRatioAnalysis
from credit_risk_assessment import CreditRiskAssessor, CreditRiskAssessment
from credit_visualizer import CreditVisualizer


class CreditAnalystToolkit:
    """
    Complete credit analysis toolkit.
    
    Workflow:
    1. Parse financial statements
    2. Calculate financial ratios
    3. Assess credit risk
    4. Generate visualizations and reports
    
    Example:
        >>> toolkit = CreditAnalystToolkit()
        >>> assessment = toolkit.run_full_analysis(
        ...     company_name="ABC Corp",
        ...     industry="Technology",
        ...     statements={'income': income_df, 'balance': balance_df, 'cash': cash_df}
        ... )
    """
    
    def __init__(self, output_dir: str = "../credit_analysis_reports"):
        """
        Initialize toolkit.
        
        Args:
            output_dir: Directory for all outputs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.parser = FinancialStatementParser()
        self.analyzer = RatioAnalyzer(str(self.output_dir))
        self.assessor = CreditRiskAssessor()
        self.visualizer = CreditVisualizer(str(self.output_dir))
        
        # Store results
        self.current_assessment: Optional[CreditRiskAssessment] = None
        self.current_ratios: Optional[CreditRatioAnalysis] = None
    
    def run_full_analysis(self, 
                          company_name: str,
                          industry: str,
                          statements: Dict[str, pd.DataFrame],
                          fiscal_year: int = None,
                          generate_visuals: bool = True,
                          export_format: str = 'json') -> Tuple[CreditRiskAssessment, CreditRatioAnalysis]:
        """
        Run complete credit analysis workflow.
        
        Args:
            company_name: Name of the company
            industry: Industry sector
            statements: Dict with keys 'income', 'balance', 'cash' → DataFrames
            fiscal_year: Fiscal year of data
            generate_visuals: Whether to create charts
            export_format: 'json' or 'csv'
        
        Returns:
            Tuple of (CreditRiskAssessment, CreditRatioAnalysis)
        """
        print(f"\n{'='*60}")
        print(f"Credit Analysis Report — {company_name}")
        print(f"Industry: {industry}")
        print(f"Fiscal Year: {fiscal_year or 'N/A'}")
        print(f"{'='*60}\n")
        
        # Step 1: Parse financial statements
        print("Step 1: Parsing Financial Statements...")
        parsed_statements = self._parse_statements(company_name, statements, fiscal_year)
        
        # Step 2: Calculate ratios
        print("Step 2: Calculating Financial Ratios...")
        ratios = self._calculate_ratios(parsed_statements)
        self.current_ratios = ratios
        
        # Print ratio summary
        print("\n--- Key Financial Ratios ---")
        ratio_df = ratios.to_dataframe()
        print(ratio_df.to_string(index=False))
        
        # Step 3: Assess credit risk
        print("\nStep 3: Assessing Credit Risk...")
        assessment = self._assess_risk(company_name, industry, ratios, fiscal_year)
        self.current_assessment = assessment
        
        # Print assessment summary
        print(f"\n--- Credit Assessment Summary ---")
        print(f"Rating: {assessment.overall_rating}")
        print(f"Outlook: {assessment.outlook}")
        print(f"Risk Score: {assessment.risk_score:.1f}/100")
        print(f"\nStrengths:")
        for s in assessment.strengths[:3]:
            print(f"  • {s}")
        print(f"\nWeaknesses:")
        for w in assessment.weaknesses[:3]:
            print(f"  • {w}")
        
        # Step 4: Generate outputs
        print("\nStep 4: Generating Reports...")
        
        # Export ratios
        ratio_path = self.analyzer.export_ratios(ratios)
        print(f"  ✓ Ratios exported to: {ratio_path}")
        
        # Export assessment
        assessment_path = self._export_assessment(assessment, export_format)
        print(f"  ✓ Assessment exported to: {assessment_path}")
        
        # Generate visualizations
        if generate_visuals:
            print("\nStep 5: Generating Visualizations...")
            self._generate_visuals(company_name, ratios, assessment)
        
        print(f"\n{'='*60}")
        print(f"Analysis Complete!")
        print(f"All outputs saved to: {self.output_dir}")
        print(f"{'='*60}\n")
        
        return assessment, ratios
    
    def _parse_statements(self, company_name: str,
                           statements: Dict[str, pd.DataFrame],
                           fiscal_year: int) -> Dict[str, FinancialStatement]:
        """Parse financial statements from DataFrames."""
        parsed = {}
        
        if 'income' in statements and not statements['income'].empty:
            is_stmt = FinancialStatement(
                company_name=company_name,
                fiscal_year=fiscal_year,
                statement_type='income_statement',
                data=statements['income']
            )
            parsed['income'] = is_stmt
            print(f"  ✓ Income statement parsed ({len(is_stmt.data)} items)")
        
        if 'balance' in statements and not statements['balance'].empty:
            bs_stmt = FinancialStatement(
                company_name=company_name,
                fiscal_year=fiscal_year,
                statement_type='balance_sheet',
                data=statements['balance']
            )
            parsed['balance'] = bs_stmt
            print(f"  ✓ Balance sheet parsed ({len(bs_stmt.data)} items)")
        
        if 'cash' in statements and not statements['cash'].empty:
            cf_stmt = FinancialStatement(
                company_name=company_name,
                fiscal_year=fiscal_year,
                statement_type='cash_flow',
                data=statements['cash']
            )
            parsed['cash'] = cf_stmt
            print(f"  ✓ Cash flow statement parsed ({len(cf_stmt.data)} items)")
        
        return parsed
    
    def _calculate_ratios(self, parsed: Dict[str, FinancialStatement]) -> CreditRatioAnalysis:
        """Calculate all credit ratios."""
        is_data = parsed.get('income_statement').data if 'income_statement' in parsed else None
        bs_data = parsed.get('balance_sheet').data if 'balance_sheet' in parsed else None
        cf_data = parsed.get('cash_flow').data if 'cash_flow' in parsed else None
        
        # Create sample data if parsing failed (for demo)
        if bs_data is None:
            print("  ⚠ No balance sheet data, using sample data for demonstration")
            bs_data = self._create_sample_balance_sheet()
        if is_data is None:
            print("  ⚠ No income statement data, using sample data for demonstration")
            is_data = self._create_sample_income_statement()
        
        ratios = self.analyzer.calculate_all_ratios(
            bs_data=bs_data,
            is_data=is_data,
            cf_data=cf_data
        )
        return ratios
    
    def _assess_risk(self, company_name: str, industry: str,
                     ratios: CreditRatioAnalysis, 
                     fiscal_year: int) -> CreditRiskAssessment:
        """Perform credit risk assessment."""
        assessment = self.assessor.assess_credit(
            company_name=company_name,
            ratios=ratios,
            industry=industry,
            fiscal_year=fiscal_year
        )
        return assessment
    
    def _export_assessment(self, assessment: CreditRiskAssessment, 
                           format: str) -> str:
        """Export assessment report."""
        if format == 'json':
            filepath = self.output_dir / f"credit_assessment_{assessment.fiscal_year}.json"
            with open(filepath, 'w') as f:
                json.dump(assessment.to_dict(), f, indent=2, default=str)
        else:
            filepath = self.output_dir / f"credit_assessment_{assessment.fiscal_year}.csv"
            # Convert to dataframe-friendly format
            summary = {
                'Company': assessment.company_name,
                'Fiscal Year': assessment.fiscal_year,
                'Rating': assessment.overall_rating,
                'Outlook': assessment.outlook,
                'Risk Score': assessment.risk_score,
                'Interest Coverage': assessment.interest_coverage,
                'Debt/EBITDA': assessment.debt_to_ebitda,
                'FCF/Debt': assessment.fcf_to_debt,
                'Current Ratio': assessment.current_ratio,
            }
            pd.DataFrame([summary]).to_csv(filepath, index=False)
        return str(filepath)
    
    def _generate_visuals(self, company_name: str,
                          ratios: CreditRatioAnalysis,
                          assessment: CreditRiskAssessment):
        """Generate visualization charts."""
        # Coverage trend (if multiple periods)
        # In real usage, you'd have historical data
        
        # Leverage comparison
        leverage_metrics = {
            'Debt/Equity': ratios.debt_to_equity or 0,
            'Debt/Assets': ratios.debt_to_assets or 0,
            'Financial Lev': ratios.financial_leverage or 0,
        }
        self.visualizer.plot_leverage_comparison(
            company_metrics=leverage_metrics,
            company=company_name,
            peer_averages={'Debt/Equity': 1.5, 'Debt/Assets': 0.4, 'Financial Lev': 2.5},
            industry_averages={'Debt/Equity': 2.0, 'Debt/Assets': 0.5, 'Financial Lev': 3.0}
        )
        print(f"  ✓ Leverage comparison chart generated")
        
        # Risk radar
        risk_scores = {
            'Leverage': assessment.risk_factors.leverage_risk,
            'Liquidity': assessment.risk_factors.liquidity_risk,
            'Profitability': assessment.risk_factors.profitability_risk,
            'Cash Flow': assessment.risk_factors.cash_flow_risk,
            'Coverage': assessment.risk_factors.coverage_risk,
        }
        self.visualizer.plot_risk_radar(risk_scores, company_name)
        print(f"  ✓ Risk radar chart generated")
        
        # Scorecard
        self.visualizer.create_credit_scorecard(assessment)
        print(f"  ✓ Credit scorecard generated")
    
    def _create_sample_balance_sheet(self) -> pd.DataFrame:
        """Create sample balance sheet for demo."""
        data = {
            'Cash': 5000,
            'Accounts Receivable': 8000,
            'Inventory': 6000,
            'Total Current Assets': 19000,
            'Property Plant Equipment': 25000,
            'Total Assets': 44000,
            'Accounts Payable': 5000,
            'Short Term Debt': 3000,
            'Total Current Liabilities': 8000,
            'Long Term Debt': 15000,
            'Total Liabilities': 23000,
            'Total Equity': 21000,
        }
        return pd.DataFrame(list(data.items()), columns=['Item', 'Value']).set_index('Item')
    
    def _create_sample_income_statement(self) -> pd.DataFrame:
        """Create sample income statement for demo."""
        data = {
            'Revenue': 50000,
            'Cost of Revenue': 30000,
            'Gross Profit': 20000,
            'Operating Expenses': 8000,
            'Operating Income': 12000,
            'Interest Expense': 2000,
            'Pretax Income': 10000,
            'Income Tax': 2000,
            'Net Income': 8000,
        }
        return pd.DataFrame(list(data.items()), columns=['Item', 'Value']).set_index('Item')


def demo():
    """Run demonstration with sample data."""
    print("\n" + "="*60)
    print("Credit Analyst Toolkit — Demo")
    print("="*60 + "\n")
    
    toolkit = CreditAnalystToolkit()
    
    # Create sample financial data
    sample_income = pd.DataFrame({
        'Item': ['Revenue', 'Cost of Revenue', 'Gross Profit', 'Operating Expenses', 
                'Operating Income', 'Interest Expense', 'Pretax Income', 'Income Tax', 'Net Income'],
        '2024': [100000, 60000, 40000, 15000, 25000, 5000, 20000, 4000, 16000]
    }).set_index('Item')
    
    sample_balance = pd.DataFrame({
        'Item': ['Cash', 'Accounts Receivable', 'Inventory', 'Total Current Assets',
                'Total Assets', 'Accounts Payable', 'Total Current Liabilities',
                'Long Term Debt', 'Total Liabilities', 'Total Equity'],
        '2024': [15000, 12000, 10000, 37000, 80000, 8000, 20000, 30000, 50000, 30000]
    }).set_index('Item')
    
    sample_cash = pd.DataFrame({
        'Item': ['Operating CF', 'Free CF', 'Capex'],
        '2024': [25000, 18000, 7000]
    }).set_index('Item')
    
    # Run analysis
    assessment, ratios = toolkit.run_full_analysis(
        company_name="Demo Corp",
        industry="Technology",
        statements={
            'income': sample_income,
            'balance': sample_balance,
            'cash': sample_cash
        },
        fiscal_year=2024
    )
    
    print("\nDemo complete! Check the output directory for reports.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--demo':
        demo()
    else:
        print("Credit Analyst Toolkit initialized.")
        print("Run with --demo flag for sample analysis:")
        print("  python main.py --demo")
