"""Rich single-ticker assessment pipeline shared by API and CLI."""

from __future__ import annotations

from datetime import datetime
import logging
import re
from typing import Any, Dict, Optional

import pandas as pd

from src.data_fetcher import DataFetchError, FinancialDataFetcher
from src.ratio_analyzer import CreditRatioAnalysis, RatioAnalyzer
from src.zscore import build_z_score_breakdown, calculate_z_score
from src.config import settings

from src.services.assessment_service import AssessmentServiceError
from src.services._utils import (
    CJK_PATTERN,
    JAPANESE_PATTERN,
    convert_simplified_to_traditional,
    get_dataframe_value,
    infer_fiscal_year,
    json_safe,
    safe_number,
)

logger = logging.getLogger(__name__)



class RichAssessmentService:
    """Build the full multi-period analysis payload used by the dashboard."""

    _ALLOWED_SOURCES = {"auto", "yfinance", "akshare", "demo"}

    def __init__(self, report_dir: str | None = None) -> None:
        self.fetcher = FinancialDataFetcher()
        self.analyzer = RatioAnalyzer(report_dir=report_dir or settings.rich_report_dir)

    def analyze(
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

        company_name = str(financial_data.get("company_name") or normalized_ticker)
        company_profile = financial_data.get("company_profile") or {}
        currency = self._infer_currency(normalized_ticker)
        company_name_localized = self._build_company_name_localized(company_name, normalized_ticker)

        historical_results: list[Dict[str, Any]] = []
        latest_fy_assessment: Optional[Dict[str, Any]] = None

        for period in history:
            if not isinstance(period, dict):
                continue

            try:
                fy_label = str(period.get("year_label") or fiscal_year or datetime.now().year)
                is_quarterly = bool(period.get("is_quarterly", False))
                fy_int = infer_fiscal_year(fy_label, fallback=fiscal_year)

                income_df = self._copy_dataframe(period.get("income"))
                cash_df = self._copy_dataframe(period.get("cash"))
                balance_df = self._copy_dataframe(period.get("balance"))

                if is_quarterly:
                    annualize_factor = self._annualize_factor(currency, fy_label)
                    self._annualize_flow_statement(income_df, annualize_factor)
                    self._annualize_flow_statement(cash_df, annualize_factor)

                period_data = {
                    "balance": balance_df,
                    "income": income_df,
                    "cash": cash_df,
                    "company_name": company_name,
                    "fiscal_year": fy_int,
                }
                ratios = self._calculate_ratios(period_data)
                raw_metrics = self._build_raw_metrics(balance_df, income_df, cash_df, ratios)
                assessment = self._build_assessment(balance_df, income_df, ratios, safe_number(financial_data.get("market_cap")))

                if not is_quarterly and assessment.get("overall_rating") != "N/A":
                    latest_fy_assessment = assessment

                historical_results.append(
                    {
                        "fiscal_year": fy_label,
                        "is_quarterly": is_quarterly,
                        "assessment": assessment,
                        "ratios": json_safe(ratios.to_dict()),
                        "raw_metrics": raw_metrics,
                        "statements": {
                            "income": self._statement_values(income_df),
                            "balance": self._statement_values(balance_df),
                            "cash": self._statement_values(cash_df),
                        },
                    }
                )
            except Exception as exc:
                reason = "insufficient_data" if isinstance(exc, (KeyError, IndexError, TypeError)) else "calculation_error"
                logger.warning(
                    "Skipping period %s for %s (reason=%s): %s",
                    period.get("year_label", "?"),
                    normalized_ticker,
                    reason,
                    exc,
                    exc_info=True,
                )
                historical_results.append(
                    {
                        "fiscal_year": period.get("year_label", "?"),
                        "is_quarterly": bool(period.get("is_quarterly", False)),
                        "error": reason,
                        "assessment": None,
                        "ratios": {},
                        "raw_metrics": {},
                        "statements": {},
                    }
                )

        # After processing all periods, verify at least one produced a valid assessment.
        if historical_results and not any(
            isinstance(entry.get("assessment"), dict) and "error" not in entry
            for entry in historical_results
        ):
            period_errors = [
                {"fiscal_year": entry.get("fiscal_year"), "error": entry.get("error")}
                for entry in historical_results
                if entry.get("error")
            ]
            raise AssessmentServiceError(
                "No valid financial periods could be analyzed.",
                status_code=422,
                details={"error_type": "calculation_failed", "period_errors": period_errors},
            )

        if latest_fy_assessment is not None:
            for entry in historical_results:
                assessment = entry.get("assessment")
                if not isinstance(assessment, dict):
                    continue
                if assessment.get("overall_rating") == "N/A" and entry.get("is_quarterly"):
                    entry["assessment"] = dict(latest_fy_assessment)

        # Build data_quality metadata
        failed_periods = [
            entry.get("fiscal_year") for entry in historical_results if entry.get("error")
        ]
        latest_period = historical_results[0] if historical_results else None
        latest_period_valid = (
            isinstance(latest_period, dict)
            and latest_period.get("assessment") is not None
            and not latest_period.get("error")
        ) if latest_period else False
        data_quality = {
            "status": "partial" if failed_periods else "complete",
            "failed_periods": failed_periods,
            "latest_period_valid": latest_period_valid,
        }

        return json_safe(
            {
                "ticker": normalized_ticker,
                "company_name": company_name,
                "company_name_localized": company_name_localized,
                "currency": currency,
                "company_profile": company_profile,
                "history": historical_results,
                "data_quality": data_quality,
            }
        )

    def _fetch_financial_data(self, ticker: str, source: str) -> Dict[str, Any]:
        if source == "demo" or ticker == "DEMO":
            return self._build_demo_data(ticker)

        try:
            result = self.fetcher.get_financial_data(ticker, source)
        except DataFetchError:
            raise
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.error("Financial data fetch unexpected error for %s: %s", ticker, exc, exc_info=True)
            raise AssessmentServiceError(
                "财务数据获取失败。",
                status_code=500,
            ) from exc

        if not result:
            raise AssessmentServiceError(
                f"Ticker '{ticker}' 未返回可用数据。",
                status_code=404,
            )

        return result

    def _calculate_ratios(self, period_data: Dict[str, Any]) -> CreditRatioAnalysis:
        try:
            return self.analyzer.calculate_all_ratios(
                bs_data=period_data["balance"],
                is_data=period_data["income"],
                cf_data=period_data["cash"],
                company_name=period_data["company_name"],
                fiscal_year=period_data["fiscal_year"],
            )
        except Exception as exc:
            logger.error("Ratio calculation failed for %s: %s", period_data.get("company_name", "?"), exc, exc_info=True)
            raise AssessmentServiceError(
                "财务比率计算失败，请检查 ticker 或数据源。",
                status_code=422,
                details={"error_type": "calculation_failed"},
            ) from exc

    def _build_assessment(
        self,
        balance_df: pd.DataFrame,
        income_df: pd.DataFrame,
        ratios: CreditRatioAnalysis,
        market_cap: float | None,
    ) -> Dict[str, Any]:
        total_assets = get_dataframe_value(balance_df, "total_assets")
        total_liabilities = get_dataframe_value(balance_df, "total_liabilities")
        total_current_assets = get_dataframe_value(balance_df, "total_current_assets")
        total_current_liabilities = get_dataframe_value(balance_df, "total_current_liabilities")
        retained_earnings = get_dataframe_value(balance_df, "retained_earnings")
        ebit = get_dataframe_value(income_df, "operating_income")
        sales = ratios.revenue

        working_capital = (
            (total_current_assets - total_current_liabilities)
            if total_current_assets is not None and total_current_liabilities is not None
            else None
        )

        z_result = calculate_z_score(
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            working_capital=working_capital,
            retained_earnings=retained_earnings,
            ebit=ebit,
            sales=sales,
            market_cap=market_cap,
        )
        z_breakdown = build_z_score_breakdown(
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            working_capital=working_capital,
            retained_earnings=retained_earnings,
            ebit=ebit,
            sales=sales,
            market_cap=market_cap,
        )

        strengths: list[str] = []
        weaknesses: list[str] = []

        if z_result.z_score is not None:
            interest_coverage = ratios.interest_coverage
            debt_to_ebitda = ratios.debt_to_ebitda
            fcf_to_debt = ratios.fcf_to_debt
            current_ratio = ratios.current_ratio

            if interest_coverage is not None and interest_coverage > 5:
                strengths.append(f"Strong interest coverage ({interest_coverage:.1f}x)")
            elif interest_coverage is not None and interest_coverage < 2:
                weaknesses.append(f"Weak interest coverage ({interest_coverage:.1f}x)")

            if debt_to_ebitda is not None and debt_to_ebitda < 3:
                strengths.append(f"Low leverage (Debt/EBITDA: {debt_to_ebitda:.1f})")
            elif debt_to_ebitda is not None and debt_to_ebitda > 5:
                weaknesses.append(f"High leverage (Debt/EBITDA: {debt_to_ebitda:.1f})")

            if fcf_to_debt is not None and fcf_to_debt > 0.2:
                strengths.append(f"Strong free cash flow ({fcf_to_debt * 100:.1f}% of debt)")
            elif fcf_to_debt is not None and fcf_to_debt < 0:
                weaknesses.append("Negative free cash flow")

            if current_ratio is not None and current_ratio > 1.5:
                strengths.append(f"Good liquidity (Current Ratio: {current_ratio:.2f})")
            elif current_ratio is not None and current_ratio < 1:
                weaknesses.append(f"Weak liquidity (Current Ratio: {current_ratio:.2f})")

        def covenant_row(
            metric: str,
            actual: float | None,
            threshold: float,
            passes_when: str,
            pass_note: str,
            fail_note: str,
        ) -> Dict[str, object]:
            if actual is None:
                return {
                    "metric": metric,
                    "actual": None,
                    "threshold": threshold,
                    "status": "Breach",
                    "signal": "Red",
                    "notes": "Data unavailable; defaulting to breach pending manual verification",
                }
            passed = actual <= threshold if passes_when == "lte" else actual >= threshold
            return {
                "metric": metric,
                "actual": float(round(actual, 2)),
                "threshold": threshold,
                "status": "Pass" if passed else "Fail",
                "signal": "Green" if passed else "Red",
                "notes": pass_note if passed else fail_note,
            }

        assessment = {
            "risk_score": float(round(z_result.z_score, 2)) if z_result.z_score is not None else 0.0,
            "overall_rating": z_result.zone,
            "implied_rating": z_result.implied_rating,
            "zscore_breakdown": z_breakdown,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "covenant_pre_check": [
                covenant_row("Debt/EBITDA", ratios.debt_to_ebitda, 3.5, "lte", "Comfortable leverage", "High leverage"),
                covenant_row("Interest Coverage", ratios.interest_coverage, 3.0, "gte", "Strong coverage", "Weak coverage"),
                covenant_row("Current Ratio", ratios.current_ratio, 1.2, "gte", "Adequate liquidity", "Poor liquidity"),
            ]
        }
        return json_safe(assessment)

    def _build_raw_metrics(
        self,
        balance_df: pd.DataFrame,
        income_df: pd.DataFrame,
        cash_df: pd.DataFrame,
        ratios: CreditRatioAnalysis,
    ) -> Dict[str, Optional[float]]:
        return {
            "total_debt": self._sanitize_metric(get_dataframe_value(balance_df, "total_debt")),
            "ebitda": self._sanitize_metric(ratios.ebitda),
            "operating_income": self._sanitize_metric(get_dataframe_value(income_df, "operating_income")),
            "interest_expense": self._sanitize_metric(get_dataframe_value(income_df, "interest_expense")),
            "total_current_assets": self._sanitize_metric(get_dataframe_value(balance_df, "total_current_assets")),
            "total_current_liabilities": self._sanitize_metric(get_dataframe_value(balance_df, "total_current_liabilities")),
            "free_cf": self._sanitize_metric(get_dataframe_value(cash_df, "free_cf")),
        }

    @staticmethod
    def _annualize_flow_statement(df: pd.DataFrame, factor: float) -> None:
        if df is None or df.empty or "Value" not in df.columns:
            return
        try:
            df["Value"] = df["Value"] * factor
        except (KeyError, TypeError, ValueError):
            return

    @staticmethod
    def _statement_values(df: pd.DataFrame) -> Dict[str, Any]:
        if df is None or df.empty or "Value" not in df.columns:
            return {}
        try:
            return df["Value"].dropna().to_dict()
        except (KeyError, AttributeError):
            return {}

    @staticmethod
    def _copy_dataframe(data: Any) -> pd.DataFrame:
        if isinstance(data, pd.DataFrame):
            try:
                if data.empty:
                    return pd.DataFrame()
                return data.copy()
            except (AttributeError, ValueError):
                return pd.DataFrame()
        return pd.DataFrame()

    @staticmethod
    def _infer_currency(ticker: str) -> str:
        normalized = ticker.upper()
        if normalized.endswith(".HK"):
            return "HKD"
        raw = normalized.replace(".SS", "").replace(".SZ", "").replace(".SH", "")
        if raw.isdigit() and len(raw) == 6:
            return "CNY"
        return "USD"

    @staticmethod
    def _annualize_factor(currency: str, year_label: str) -> float:
        factor = 4.0
        if currency != "CNY":
            return factor

        quarter_match = re.search(r"Q([1-4])", year_label or "", flags=re.I)
        if not quarter_match:
            return factor

        quarter = int(quarter_match.group(1))
        months_covered = quarter * 3
        return 12.0 / months_covered if months_covered > 0 else factor

    @classmethod
    def _build_company_name_localized(cls, company_name: str, ticker: str) -> Dict[str, str]:
        fallback_name = str(company_name or ticker or "N/A").strip() or ticker or "N/A"
        localized: Dict[str, str] = {"en": fallback_name}

        if JAPANESE_PATTERN.search(fallback_name):
            localized["ja"] = fallback_name
        elif CJK_PATTERN.search(fallback_name):
            localized["zh-CN"] = fallback_name
            localized["zh-TW"] = convert_simplified_to_traditional(fallback_name)

        return localized

    @staticmethod
    def _sanitize_metric(value: Any) -> Optional[float]:
        result = safe_number(value)
        return round(result, 4) if result is not None else None

    @staticmethod
    def _build_demo_data(ticker: str) -> Dict[str, Any]:
        def _frame(values: Dict[str, float], scale: float = 1.0) -> pd.DataFrame:
            return pd.DataFrame.from_dict(
                {key: value * scale for key, value in values.items()},
                orient="index",
                columns=["Value"],
            )

        income_template = {
            "revenue": 1_680_000_000.0,
            "cost_of_revenue": 1_040_000_000.0,
            "gross_profit": 640_000_000.0,
            "research_and_development": 130_000_000.0,
            "selling_general_admin": 125_000_000.0,
            "operating_expenses": 255_000_000.0,
            "operating_income": 230_000_000.0,
            "non_operating_income": 15_000_000.0,
            "interest_expense": 36_000_000.0,
            "pretax_income": 209_000_000.0,
            "income_tax_expense": 29_000_000.0,
            "net_income": 180_000_000.0,
            "depreciation_and_amortization": 90_000_000.0,
            "ebitda": 320_000_000.0,
        }
        balance_template = {
            "cash": 140_000_000.0,
            "short_term_investments": 60_000_000.0,
            "accounts_receivable": 210_000_000.0,
            "inventory": 85_000_000.0,
            "total_current_assets": 520_000_000.0,
            "property_plant_equipment": 640_000_000.0,
            "goodwill": 180_000_000.0,
            "other_assets": 160_000_000.0,
            "total_assets": 1_500_000_000.0,
            "accounts_payable": 130_000_000.0,
            "short_term_debt": 90_000_000.0,
            "total_current_liabilities": 260_000_000.0,
            "long_term_debt": 230_000_000.0,
            "total_liabilities": 700_000_000.0,
            "total_equity": 800_000_000.0,
        }
        cash_template = {
            "operating_cf": 250_000_000.0,
            "net_income": 180_000_000.0,
            "depreciation_and_amortization": 90_000_000.0,
            "stock_based_compensation": 35_000_000.0,
            "change_in_working_capital": -18_000_000.0,
            "investing_cf": -120_000_000.0,
            "capital_expenditures": -70_000_000.0,
            "free_cf": 180_000_000.0,
            "financing_cf": -60_000_000.0,
            "dividends_paid": -45_000_000.0,
            "share_repurchase": -25_000_000.0,
            "ending_cash": 140_000_000.0,
        }

        period_specs = [
            ("25Q3", True, 0.28),
            ("24Q3", True, 0.25),
            ("FY24", False, 1.00),
            ("FY23", False, 0.93),
            ("FY22", False, 0.86),
        ]

        history = []
        for year_label, is_quarterly, scale in period_specs:
            history.append(
                {
                    "year_label": year_label,
                    "is_quarterly": is_quarterly,
                    "income": _frame(income_template, scale),
                    "balance": _frame(balance_template, scale),
                    "cash": _frame(cash_template, scale),
                }
            )

        return {
            "ticker": ticker,
            "company_name": "Demo Industrial Co.",
            "market_cap": 18_000_000_000.0,
            "company_profile": {
                "description": "Synthetic multi-period demo data",
                "sector": "Industrials",
                "industry": "Diversified Industrials",
                "country": "US",
                "employees": 48_000,
                "website": "https://example.com",
            },
            "history": history,
        }
