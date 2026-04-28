"""Service layer for MVP credit assessment."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from src.services._utils import infer_fiscal_year, json_safe, safe_number
from src.config import settings

import pandas as pd

from src.data_fetcher import DataFetchError, FinancialDataFetcher
from src.ratio_analyzer import CreditRatioAnalysis, RatioAnalyzer
from src.zscore import ZScoreResult, calculate_z_score


class AssessmentServiceError(Exception):
    """Business-level exception with HTTP-safe metadata."""

    def __init__(self, message: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class AssessmentService:
    """Orchestrates fetch -> ratio analysis -> z-score assessment."""

    _ALLOWED_SOURCES = {"auto", "yfinance", "akshare", "demo"}

    def __init__(self, report_dir: str | None = None) -> None:
        self.fetcher = FinancialDataFetcher()
        self.analyzer = RatioAnalyzer(report_dir=report_dir or settings.mvp_report_dir)

    def assess(
        self,
        ticker: str,
        data_source: str = "yfinance",
        fiscal_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        normalized_ticker = (ticker or "").strip().upper()
        if not normalized_ticker:
            raise AssessmentServiceError(
                "Ticker 不能为空。",
                status_code=422,
                details={"field": "ticker"},
            )

        source = (data_source or "yfinance").strip().lower()
        if source not in self._ALLOWED_SOURCES:
            raise AssessmentServiceError(
                f"不支持的数据源: {data_source}",
                status_code=422,
                details={"allowed": sorted(self._ALLOWED_SOURCES)},
            )

        financial_data = self._fetch_financial_data(normalized_ticker, source)
        history = financial_data.get("history") or []
        if not history:
            raise AssessmentServiceError(
                f"Ticker '{normalized_ticker}' 没有可用财务历史数据。",
                status_code=404,
            )

        latest_period = self._select_latest_period(history)
        balance_df = self._as_dataframe(latest_period.get("balance"))
        income_df = self._as_dataframe(latest_period.get("income"))
        cash_df = self._as_dataframe(latest_period.get("cash"))

        if balance_df.empty:
            raise AssessmentServiceError(
                "资产负债表为空，无法计算比率。",
                status_code=422,
                details={"period": latest_period.get("year_label")},
            )

        company_name = financial_data.get("company_name") or normalized_ticker
        analysis_year = fiscal_year or infer_fiscal_year(latest_period.get("year_label"))

        ratios = self._calculate_ratios(
            balance_df=balance_df,
            income_df=income_df,
            cash_df=cash_df,
            company_name=company_name,
            fiscal_year=analysis_year,
        )

        z_result = self._calculate_zscore(
            balance_df=balance_df,
            income_df=income_df,
            ratios=ratios,
            market_cap=financial_data.get("market_cap") or 0,
        )

        warnings = []
        if z_result.z_score is None:
            warnings.append("关键字段不足，Z-Score 未计算。")

        payload = {
            "ticker": normalized_ticker,
            "company_name": company_name,
            "period": latest_period.get("year_label") or str(analysis_year),
            "data_source": source,
            "assessment": {
                "z_score": safe_number(z_result.z_score),
                "risk_zone": z_result.zone,
                "implied_rating": z_result.implied_rating,
            },
            "key_metrics": self._build_key_metrics(balance_df, income_df, cash_df, ratios),
            "ratios": ratios.to_dict(),
            "warnings": warnings,
            "timestamp": datetime.now().isoformat(),
        }
        return json_safe(payload)

    def _fetch_financial_data(self, ticker: str, source: str) -> Dict[str, Any]:
        if source == "demo" or ticker == "DEMO":
            return self._build_demo_data(ticker)

        try:
            result = self.fetcher.get_financial_data(ticker, source)
        except DataFetchError as exc:
            raise AssessmentServiceError(
                exc.message,
                status_code=404,
                details=exc.to_dict(),
            ) from exc

        if not result:
            raise AssessmentServiceError(
                f"Ticker '{ticker}' 未返回可用数据。",
                status_code=404,
            )

        return result

    @staticmethod
    def _select_latest_period(history: list[Dict[str, Any]]) -> Dict[str, Any]:
        fallback: Optional[Dict[str, Any]] = None
        for period in history:
            if not isinstance(period, dict):
                continue
            if fallback is None:
                fallback = period
            balance = period.get("balance")
            if isinstance(balance, pd.DataFrame) and not balance.empty:
                return period
        if fallback is not None:
            return fallback
        raise AssessmentServiceError("财务历史数据格式不合法。", status_code=500)

    @staticmethod
    def _as_dataframe(data: Any) -> pd.DataFrame:
        if isinstance(data, pd.DataFrame):
            return data
        return pd.DataFrame()

    def _calculate_ratios(
        self,
        balance_df: pd.DataFrame,
        income_df: pd.DataFrame,
        cash_df: pd.DataFrame,
        company_name: str,
        fiscal_year: int,
    ) -> CreditRatioAnalysis:
        try:
            return self.analyzer.calculate_all_ratios(
                bs_data=balance_df,
                is_data=income_df,
                cf_data=cash_df,
                company_name=company_name,
                fiscal_year=fiscal_year,
            )
        except Exception as exc:
            raise AssessmentServiceError(
                "财务比率计算失败，请检查 ticker 或数据源。",
                status_code=422,
                details={"error": str(exc)},
            ) from exc

    def _calculate_zscore(
        self,
        balance_df: pd.DataFrame,
        income_df: pd.DataFrame,
        ratios: CreditRatioAnalysis,
        market_cap: float,
    ) -> ZScoreResult:
        total_assets = self.analyzer._get_value(balance_df, "total_assets")
        total_liabilities = self.analyzer._get_value(balance_df, "total_liabilities")
        total_current_assets = self.analyzer._get_value(balance_df, "total_current_assets")
        total_current_liabilities = self.analyzer._get_value(balance_df, "total_current_liabilities")
        retained_earnings = self.analyzer._get_value(balance_df, "retained_earnings")
        ebit = self.analyzer._get_value(income_df, "operating_income")
        sales = ratios.revenue

        return calculate_z_score(
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            working_capital=(total_current_assets or 0) - (total_current_liabilities or 0),
            retained_earnings=retained_earnings,
            ebit=ebit,
            sales=sales,
            market_cap=market_cap,
        )

    def _build_key_metrics(
        self,
        balance_df: pd.DataFrame,
        income_df: pd.DataFrame,
        cash_df: pd.DataFrame,
        ratios: CreditRatioAnalysis,
    ) -> Dict[str, Optional[float]]:
        return {
            "total_assets": safe_number(self.analyzer._get_value(balance_df, "total_assets")),
            "total_liabilities": safe_number(self.analyzer._get_value(balance_df, "total_liabilities")),
            "revenue": safe_number(self.analyzer._get_value(income_df, "revenue")),
            "operating_income": safe_number(self.analyzer._get_value(income_df, "operating_income")),
            "free_cf": safe_number(self.analyzer._get_value(cash_df, "free_cf")),
            "current_ratio": safe_number(ratios.current_ratio),
            "debt_to_equity": safe_number(ratios.debt_to_equity),
            "interest_coverage": safe_number(ratios.interest_coverage),
            "fcf_to_debt": safe_number(ratios.fcf_to_debt),
        }

    @staticmethod
    def _build_demo_data(ticker: str) -> Dict[str, Any]:
        year = datetime.now().year
        balance = pd.DataFrame.from_dict(
            {
                "total_assets": 1500.0,
                "total_liabilities": 700.0,
                "total_equity": 800.0,
                "total_debt": 320.0,
                "total_current_assets": 520.0,
                "total_current_liabilities": 260.0,
                "retained_earnings": 210.0,
                "cash": 140.0,
            },
            orient="index",
            columns=["Value"],
        )
        income = pd.DataFrame.from_dict(
            {
                "revenue": 1680.0,
                "operating_income": 230.0,
                "net_income": 180.0,
                "interest_expense": 36.0,
                "gross_profit": 640.0,
            },
            orient="index",
            columns=["Value"],
        )
        cash = pd.DataFrame.from_dict(
            {
                "operating_cf": 250.0,
                "capital_expenditures": -70.0,
                "free_cf": 180.0,
            },
            orient="index",
            columns=["Value"],
        )

        return {
            "ticker": ticker,
            "company_name": "Demo Industrial Co.",
            "market_cap": 1400.0,
            "history": [
                {
                    "year_label": f"FY{str(year)[2:]}",
                    "is_quarterly": False,
                    "income": income,
                    "balance": balance,
                    "cash": cash,
                }
            ],
        }
