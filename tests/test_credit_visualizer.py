"""
Test suite for credit_visualizer module - Basic smoke tests.

Run with: pytest tests/test_credit_visualizer.py -v
"""

import pytest
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from credit_visualizer import CreditVisualizer


class TestCreditVisualizer:
    """Basic tests for CreditVisualizer class."""
    
    def test_initialization(self, tmp_path):
        """Test visualizer initialization."""
        visualizer = CreditVisualizer(str(tmp_path))
        assert visualizer is not None
    
    def test_default_output_dir(self):
        """Test default output directory."""
        visualizer = CreditVisualizer()
        assert visualizer.output_dir is not None
    
    def test_save_figure(self, tmp_path):
        """Test saving a figure."""
        visualizer = CreditVisualizer(str(tmp_path))
        
        output_path = tmp_path / "test_chart.png"
        result = visualizer._save_figure(str(output_path))
        
        assert result == str(output_path)
        assert output_path.exists()


class TestChartCreation:
    """Basic chart creation tests."""
    
    def test_plot_coverage_trend(self):
        """Test creating coverage trend chart."""
        visualizer = CreditVisualizer()
        fig = visualizer.plot_coverage_trend([2020, 2021, 2022], [2.1, 2.3, 2.5])
        assert fig is not None
    
    def test_plot_risk_radar(self):
        """Test risk radar chart."""
        visualizer = CreditVisualizer()
        fig = visualizer.plot_risk_radar({
            'liquidity': 85,
            'leverage': 75
        })
        assert fig is not None
    
    def test_plot_waterfall(self):
        """Test waterfall chart."""
        visualizer = CreditVisualizer()
        fig = visualizer.plot_cash_flow_waterfall({
            'Starting Cash': 100,
            'Operations': 50
        })
        assert fig is not None
    
    def test_leverage_comparison(self):
        """Test leverage comparison chart."""
        visualizer = CreditVisualizer()
        metrics = {'debt_to_equity': 0.65, 'debt_to_assets': 0.42}
        fig = visualizer.plot_leverage_comparison(metrics)
        assert fig is not None


class TestExport:
    """Export functionality tests."""
    
    def test_export_png(self, tmp_path):
        """Test export to PNG."""
        visualizer = CreditVisualizer(str(tmp_path))
        fig = visualizer.plot_coverage_trend([2020, 2021], [2.1, 2.3])
        output_path = tmp_path / "chart.png"
        result = visualizer._save_figure(str(output_path))
        assert result == str(output_path)
        assert output_path.exists()
    
    def test_export_pdf(self, tmp_path):
        """Test export to PDF."""
        visualizer = CreditVisualizer(str(tmp_path))
        fig = visualizer.plot_coverage_trend([2020, 2021], [2.1, 2.3])
        output_path = tmp_path / "chart.pdf"
        result = visualizer._save_figure(str(output_path))
        assert result == str(output_path)
        assert output_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
