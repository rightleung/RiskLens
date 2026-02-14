"""
Credit Analyst Toolkit — Visualization Module
==============================================
Create charts and visualizations for credit analysis presentations.

Usage:
    from credit_visualizer import CreditVisualizer
    viz = CreditVisualizer(output_dir="../reports")
    viz.plot_coverage_trend(years, interest_coverage)
    viz.plot_leverage_comparison(company, peer_avg, industry_avg)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json


class CreditVisualizer:
    """
    Create professional charts for credit analysis reports.
    
    Chart types:
    - Coverage ratio trends
    - Leverage comparison (company vs peers)
    - Cash flow waterfall
    - Radar charts for risk profiles
    - Scorecards
    
    Example:
        >>> viz = CreditVisualizer()
        >>> viz.plot_coverage_trend(
        ...     [2021, 2022, 2023, 2024],
        ...     [4.2, 3.8, 5.1, 6.2],
        ...     company="ABC Corp"
        ... )
    """
    
    # Color schemes
    COLORS = {
        'primary': '#1f77b4',      # Blue
        'secondary': '#ff7f0e',    # Orange
        'positive': '#2ca02c',     # Green
        'negative': '#d62728',     # Red
        'warning': '#ff7f0e',      # Orange
        'neutral': '#7f7f7f',      # Gray
        'industry_avg': '#9467bd', # Purple
        'peer_avg': '#8c564b',     # Brown
    }
    
    def __init__(self, output_dir: str = "../reports", style: str = "seaborn-v0_8"):
        """
        Initialize visualizer.
        
        Args:
            output_dir: Directory for saving charts
            style: Matplotlib style to use
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        plt.style.use(style)
    
    def _save_figure(self, filename: str) -> str:
        """Save figure and return path."""
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=150, bbox_inches='tight', 
                    facecolor='white', edgecolor='none')
        plt.close()
        return str(filepath)
    
    def plot_coverage_trend(self, years: List[int], 
                            coverage_ratios: List[float],
                            company: str = "Company",
                            benchmark: List[float] = None,
                            threshold: float = 3.0,
                            title: str = None) -> str:
        """
        Plot interest coverage ratio trend.
        
        Args:
            years: List of years
            coverage_ratios: List of coverage ratios
            company: Company name for legend
            benchmark: Optional benchmark line (e.g., industry average)
            threshold: Coverage threshold for "healthy" (default 3x)
        
        Returns:
            Path to saved chart
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot company trend
        ax.plot(years, coverage_ratios, marker='o', linewidth=2.5, 
                color=self.COLORS['primary'], label=company, markersize=8)
        
        # Fill areas based on coverage health
        ax.fill_between(years, coverage_ratios, threshold, 
                        where=[c >= threshold for c in coverage_ratios],
                        alpha=0.3, color=self.COLORS['positive'], interpolate=True)
        ax.fill_between(years, coverage_ratios, threshold,
                        where=[c < threshold for c in coverage_ratios],
                        alpha=0.3, color=self.COLORS['negative'], interpolate=True)
        
        # Threshold line
        ax.axhline(y=threshold, color=self.COLORS['warning'], 
                   linestyle='--', linewidth=2, label=f'Healthy Threshold ({threshold}x)')
        
        # Benchmark if provided
        if benchmark:
            ax.plot(years, benchmark, marker='s', linewidth=2, 
                    color=self.COLORS['industry_avg'], linestyle='--',
                    label='Industry Average', markersize=6)
        
        # Styling
        ax.set_xlabel('Fiscal Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Interest Coverage (x)', fontsize=12, fontweight='bold')
        ax.set_title(title or f'{company} — Interest Coverage Trend', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.set_xticks(years)
        
        # Add value labels
        for i, (year, ratio) in enumerate(zip(years, coverage_ratios)):
            offset = 0.3 if ratio >= threshold else -0.5
            ax.annotate(f'{ratio:.1f}x', (year, ratio), 
                       textcoords="offset points", xytext=(0, 15),
                       ha='center', fontsize=10, fontweight='bold')
        
        return self._save_figure(f'{company.replace(" ", "_")}_coverage_trend.png')
    
    def plot_leverage_comparison(self, company_metrics: Dict,
                                  peer_averages: Dict = None,
                                  industry_averages: Dict = None,
                                  company: str = "Company",
                                  title: str = None) -> str:
        """
        Create bar chart comparing leverage metrics.
        
        Args:
            company_metrics: Dict of metric_name → value
            peer_averages: Optional dict of peer averages
            industry_averages: Optional dict of industry averages
            company: Company name
            title: Chart title
        
        Returns:
            Path to saved chart
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        metrics = list(company_metrics.keys())
        x = np.arange(len(metrics))
        width = 0.25
        
        # Company bars
        company_values = list(company_metrics.values())
        bars1 = ax.bar(x - width, company_values, width, label=company,
                       color=self.COLORS['primary'], edgecolor='white')
        
        # Peer averages
        if peer_averages:
            peer_values = [peer_averages.get(m, 0) for m in metrics]
            bars2 = ax.bar(x, peer_values, width, label='Peer Average',
                          color=self.COLORS['peer_avg'], edgecolor='white')
        
        # Industry averages
        if industry_averages:
            industry_values = [industry_averages.get(m, 0) for m in metrics]
            bars3 = ax.bar(x + width, industry_values, width, label='Industry Average',
                          color=self.COLORS['industry_avg'], edgecolor='white')
        
        # Styling
        ax.set_xlabel('Leverage Metric', fontsize=12, fontweight='bold')
        ax.set_ylabel('Ratio', fontsize=12, fontweight='bold')
        ax.set_title(title or f'{company} — Leverage Comparison', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels([m.replace('_', '\n').title() for m in metrics], fontsize=10)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels
        for bars in [bars1] + ([bars2] if peer_averages else []) + ([bars3] if industry_averages else []):
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'{height:.2f}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3), textcoords="offset points",
                           ha='center', va='bottom', fontsize=8)
        
        return self._save_figure(f'{company.replace(" ", "_")}_leverage_comparison.png')
    
    def plot_risk_radar(self, risk_scores: Dict[str, float],
                        company: str = "Company",
                        title: str = None) -> str:
        """
        Create radar chart showing risk profile.
        
        Args:
            risk_scores: Dict of category → score (1-5, higher = riskier)
            company: Company name
            title: Chart title
        
        Returns:
            Path to saved chart
        """
        categories = list(risk_scores.keys())
        values = list(risk_scores.values())
        values += values[:1]  # Close the polygon
        
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]
        
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
        
        # Plot company risk profile
        ax.plot(angles, values, 'o-', linewidth=2, 
                color=self.COLORS['primary'], label=company, markersize=8)
        ax.fill(angles, values, alpha=0.25, color=self.COLORS['primary'])
        
        # Reference: average risk (3)
        ref_values = [3] * len(categories) + [3]
        ax.plot(angles, ref_values, '--', linewidth=1.5, 
                color=self.COLORS['neutral'], label='Average Risk', alpha=0.7)
        
        # Styling
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([c.replace('_', '\n').title() for c in categories], fontsize=10)
        ax.set_ylim(0, 5)
        ax.set_yticks([1, 2, 3, 4, 5])
        ax.set_yticklabels(['1', '2', '3', '4', '5'], fontsize=8)
        ax.set_title(title or f'{company} — Risk Profile', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
        
        return self._save_figure(f'{company.replace(" ", "_")}_risk_radar.png')
    
    def plot_cash_flow_waterfall(self, cf_items: Dict[str, float],
                                  company: str = "Company",
                                  title: str = None) -> str:
        """
        Create waterfall chart for cash flow analysis.
        
        Args:
            cf_items: Dict of category → value (in millions)
            company: Company name
            title: Chart title
        
        Returns:
            Path to saved chart
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        categories = list(cf_items.keys())
        values = list(cf_items.values())
        
        # Calculate cumulative values for waterfall
        cumulative = [0]
        for v in values:
            cumulative.append(cumulative[-1] + v)
        
        # Color based on positive/negative
        colors = [self.COLORS['positive'] if v >= 0 else self.COLORS['negative'] 
                  for v in values]
        
        # Add "Start" and "End" bars
        all_categories = ['Start'] + categories + ['End']
        cumulative.insert(0, 0)
        cumulative.append(cumulative[-1])
        
        # Calculate bar positions
        start_pos = cumulative[:-1]
        end_pos = cumulative[1:]
        
        # Create bars
        for i, (cat, start, end, val) in enumerate(zip(all_categories, start_pos, end_pos, [0] + values + [0])):
            if cat in ['Start', 'End']:
                color = self.COLORS['neutral']
                bottom = 0
            else:
                color = self.COLORS['positive'] if val >= 0 else self.COLORS['negative']
                bottom = min(start, end)
            
            ax.bar(cat, abs(end - start), bottom=bottom, 
                  color=color, edgecolor='white', width=0.6)
            
            # Add value labels
            if cat not in ['Start', 'End']:
                label_pos = end if val >= 0 else start
                ax.annotate(f'{val:+.1f}', (cat, label_pos),
                           textcoords="offset points", xytext=(0, 5),
                           ha='center', fontsize=9, fontweight='bold')
        
        # Styling
        ax.set_xlabel('Cash Flow Component', fontsize=12, fontweight='bold')
        ax.set_ylabel('Amount ($M)', fontsize=12, fontweight='bold')
        ax.set_title(title or f'{company} — Cash Flow Waterfall', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, axis='y')
        ax.axhline(y=0, color='black', linewidth=0.5)
        
        return self._save_figure(f'{company.replace(" ", "_")}_cf_waterfall.png')
    
    def create_credit_scorecard(self, assessment: 'CreditRiskAssessment',
                                 output_filename: str = None) -> str:
        """
        Create a credit scorecard summary page.
        
        Args:
            assessment: CreditRiskAssessment object
            output_filename: Custom filename (optional)
        
        Returns:
            Path to saved chart
        """
        fig = plt.figure(figsize=(11, 8.5))  # Letter size
        
        # Title
        fig.suptitle(f'Credit Scorecard — {assessment.company_name}', 
                    fontsize=18, fontweight='bold', y=0.98)
        
        # Create grid
        gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.3, 
                              left=0.05, right=0.95, top=0.90, bottom=0.05)
        
        # Overall Rating Box (top left)
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.text(0.5, 0.6, assessment.overall_rating, 
                fontsize=36, fontweight='bold', ha='center', va='center',
                color=self.COLORS['primary'])
        ax1.text(0.5, 0.2, f'Outlook: {assessment.outlook}', 
                fontsize=11, ha='center', va='center')
        ax1.axis('off')
        ax1.set_title('Credit Rating', fontsize=12, fontweight='bold')
        
        # Risk Score (top middle)
        ax2 = fig.add_subplot(gs[0, 1])
        score_color = self.COLORS['positive'] if assessment.risk_score < 40 else \
                     self.COLORS['warning'] if assessment.risk_score < 60 else self.COLORS['negative']
        ax2.text(0.5, 0.6, f'{assessment.risk_score:.0f}', 
                fontsize=36, fontweight='bold', ha='center', va='center',
                color=score_color)
        ax2.text(0.5, 0.2, 'Risk Score (0-100)', 
                fontsize=11, ha='center', va='center')
        ax2.axis('off')
        ax2.set_title('Overall Risk', fontsize=12, fontweight='bold')
        
        # Key Metrics Summary (top right)
        ax3 = fig.add_subplot(gs[0, 2])
        metrics_text = f"""Key Metrics:
• Interest Coverage: {assessment.interest_coverage or 'N/A':.1f}x
• Debt/EBITDA: {assessment.debt_to_ebitda or 'N/A':.1f}x
• FCF/Debt: {assessment.fcf_to_debt or 'N/A':.1%}
• Current Ratio: {assessment.current_ratio or 'N/A':.2f}"""
        ax3.text(0.1, 0.9, metrics_text, fontsize=10, va='top', family='monospace')
        ax3.axis('off')
        ax3.set_title('Key Metrics', fontsize=12, fontweight='bold')
        
        # Strengths (middle left)
        ax4 = fig.add_subplot(gs[1, 0])
        strengths_text = 'Strengths:\n' + '\n'.join([f'• {s}' for s in assessment.strengths]) if assessment.strengths else '• None identified'
        ax4.text(0.1, 0.9, strengths_text, fontsize=9, va='top', 
                color=self.COLORS['positive'])
        ax4.axis('off')
        ax4.set_title('Strengths', fontsize=12, fontweight='bold')
        
        # Weaknesses (middle center)
        ax5 = fig.add_subplot(gs[1, 1])
        weaknesses_text = 'Weaknesses:\n' + '\n'.join([f'• {w}' for w in assessment.weaknesses]) if assessment.weaknesses else '• None identified'
        ax5.text(0.1, 0.9, weaknesses_text, fontsize=9, va='top',
                color=self.COLORS['negative'])
        ax5.axis('off')
        ax5.set_title('Weaknesses', fontsize=12, fontweight='bold')
        
        # Watch Items (middle right)
        ax6 = fig.add_subplot(gs[1, 2])
        watch_text = 'Watch Items:\n' + '\n'.join([f'• {w}' for w in assessment.watch_items]) if assessment.watch_items else '• None identified'
        ax6.text(0.1,  watch_text, fontsize=9, va='top',
                color=self.COLORS['warning'])
        ax6.axis('off')
        ax6.set_title('Watch Items', fontsize=12, fontweight='bold')
        
        # Financial Risk Breakdown (bottom)
        ax7 = fig.add_subplot(gs[2, :])
        
        risk_categories = ['Leverage', 'Liquidity', 'Profitability', 'Cash Flow', 'Coverage']
        risk_values = [
            assessment.risk_factors.leverage_risk,
            assessment.risk_factors.liquidity_risk,
            assessment.risk_factors.profitability_risk,
            assessment.risk_factors.cash_flow_risk,
            assessment.risk_factors.coverage_risk,
        ]
        
        colors = [self.COLORS['positive'] if v <= 2 else 
                 self.COLORS['warning'] if v <= 3 else self.COLORS['negative'] 
                 for v in risk_values]
        
        bars = ax7.barh(risk_categories, risk_values, color=colors, edgecolor='white')
        ax7.set_xlim(0, 5)
        ax7.set_xlabel('Risk Score (1=Low, 5=High)', fontsize=10)
        ax7.set_title('Risk Factor Breakdown', fontsize=12, fontweight='bold')
        
        # Add value labels
        for bar, val in zip(bars, risk_values):
            ax7.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                    f'{val}', va='center', fontsize=10, fontweight='bold')
        
        # Footer
        fig.text(0.5, 0.02, 
                f'Assessment Date: {assessment.analysis_date.strftime("%Y-%m-%d") if assessment.analysis_date else "N/A"} | Generated by Credit Analyst Toolkit',
                ha='center', fontsize=8, color='gray')
        
        filename = output_filename or f'{assessment.company_name.replace(" ", "_")}_scorecard.png'
        return self._save_figure(filename)
    
    def create_ratio_comparison_table(self, company_ratios: Dict,
                                       peer_ratios: Dict = None,
                                       industry_benchmarks: Dict = None,
                                       company: str = "Company") -> str:
        """
        Create a formatted ratio comparison table.
        
        Returns:
            Path to saved CSV (tables are exported as CSV, not chart)
        """
        # Build comparison data
        comparison = {'Metric': [], company: []}
        
        if peer_ratios:
            comparison['Peer Average'] = []
        if industry_benchmarks:
            comparison['Industry Benchmark'] = []
        
        metric_names = {
            'interest_coverage': 'Interest Coverage (x)',
            'debt_to_ebitda': 'Debt/EBITDA',
            'fcf_to_debt': 'FCF/Debt',
            'current_ratio': 'Current Ratio',
            'debt_to_equity': 'Debt/Equity',
            'net_margin': 'Net Margin (%)',
            'roa': 'ROA (%)',
            'roe': 'ROE (%)',
        }
        
        for key, display_name in metric_names.items():
            comparison['Metric'].append(display_name)
            comparison[company].append(company_ratios.get(key, 'N/A'))
            
            if peer_ratios:
                comparison['Peer Average'].append(peer_ratios.get(key, 'N/A'))
            if industry_benchmarks:
                comparison['Industry Benchmark'].append(industry_benchmarks.get(key, 'N/A'))
        
        df = pd.DataFrame(comparison)
        filepath = self.output_dir / f'{company.replace(" ", "_")}_ratio_comparison.csv'
        df.to_csv(filepath, index=False)
        return str(filepath)


if __name__ == "__main__":
    print("Credit Analyst Visualization Module initialized.")
    print("Usage: viz = CreditVisualizer(); viz.plot_coverage_trend(years, ratios)")
