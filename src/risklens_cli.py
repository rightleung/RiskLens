"""RiskLens basic command-line interface."""

from __future__ import annotations

import argparse
from dataclasses import fields
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from collections.abc import Sequence

from src.covenant_monitor import CovenantMonitor, FinancialCovenants
from src.ratio_analyzer import CreditRatioAnalysis
from src.services import AssessmentService, AssessmentServiceError

ALLOWED_DATA_SOURCES = ("auto", "yfinance", "akshare", "demo")
_RATIO_FIELDS = {entry.name for entry in fields(CreditRatioAnalysis)}


def _json_text(payload: Any, compact: bool) -> str:
    if compact:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _emit(text: str, output: str | None) -> None:
    if not output:
        print(text)
        return

    out_path = Path(output).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text + "\n", encoding="utf-8")
    print(f"Wrote output to {out_path}", file=sys.stderr)


def _add_output_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output",
        default=None,
        help="Write JSON result to file instead of stdout",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit compact JSON",
    )


def _build_payload(command: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "command": command,
        "timestamp": datetime.now().isoformat(),
    }
    payload.update(extra)
    return payload


def _handle_assess(args: argparse.Namespace) -> int:
    service = AssessmentService(report_dir=args.report_dir)
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for raw_ticker in args.tickers:
        ticker = (raw_ticker or "").strip().upper()
        try:
            result = service.assess(
                ticker=ticker,
                data_source=args.data_source,
                fiscal_year=args.fiscal_year,
            )
            results.append(result)
        except AssessmentServiceError as exc:
            errors.append(
                {
                    "ticker": ticker,
                    "message": exc.message,
                    "status_code": exc.status_code,
                    "details": exc.details,
                }
            )

    payload = _build_payload(
        "assess",
        requested=len(args.tickers),
        count=len(results),
        results=results,
    )
    if errors:
        payload["errors"] = errors

    _emit(_json_text(payload, args.compact), args.output)
    return 0 if results else 1


def _handle_sources(args: argparse.Namespace) -> int:
    payload = _build_payload(
        "sources",
        data_sources=list(ALLOWED_DATA_SOURCES),
    )
    _emit(_json_text(payload, args.compact), args.output)
    return 0


def _search_tickers(query: str, limit: int) -> list[dict[str, str]]:
    import yfinance as yf

    search = yf.Search(query)
    quotes = search.quotes if hasattr(search, "quotes") else []
    query_symbol = query.strip().upper()
    allowed_quote_types = {"EQUITY"}

    results: list[dict[str, str]] = []
    seen_symbols: set[str] = set()
    for quote in quotes:
        symbol = str(quote.get("symbol", "")).strip().upper()
        if not symbol or symbol in seen_symbols or symbol == query_symbol:
            continue

        quote_type = str(quote.get("quoteType", "")).strip().upper()
        if quote_type not in allowed_quote_types:
            continue

        seen_symbols.add(symbol)
        results.append(
            {
                "symbol": symbol,
                "name": str(quote.get("shortname", quote.get("longname", ""))),
            }
        )
        if len(results) >= limit:
            break

    return results


def _handle_search(args: argparse.Namespace) -> int:
    try:
        results = _search_tickers(args.query, args.limit)
        payload = _build_payload(
            "search",
            query=args.query,
            count=len(results),
            results=results,
        )
        _emit(_json_text(payload, args.compact), args.output)
        return 0
    except Exception as exc:
        payload = _build_payload(
            "search",
            query=args.query,
            count=0,
            results=[],
            error=str(exc),
        )
        _emit(_json_text(payload, args.compact), args.output)
        return 1


def _build_ratio_analysis(assessment: dict[str, Any]) -> CreditRatioAnalysis:
    ratio_payload = assessment.get("ratios")
    if not isinstance(ratio_payload, dict):
        raise ValueError("Assessment payload missing ratios.")

    ratio_data: dict[str, Any] = {}
    for key in _RATIO_FIELDS:
        if key in ratio_payload:
            ratio_data[key] = ratio_payload[key]

    if ratio_data.get("company_name") is None:
        ratio_data["company_name"] = assessment.get("company_name")

    return CreditRatioAnalysis(**ratio_data)


def _handle_covenants(args: argparse.Namespace) -> int:
    threshold_payload = {
        "min_interest_coverage": args.min_interest_coverage,
        "max_debt_to_ebitda": args.max_debt_to_ebitda,
        "max_debt_to_equity": args.max_debt_to_equity,
        "min_current_ratio": args.min_current_ratio,
        "min_quick_ratio": args.min_quick_ratio,
        "min_fcf_to_debt": args.min_fcf_to_debt,
    }
    if all(value is None for value in threshold_payload.values()):
        payload = _build_payload(
            "covenants",
            ticker=args.ticker.strip().upper(),
            error="At least one covenant threshold must be provided.",
        )
        _emit(_json_text(payload, args.compact), args.output)
        return 2

    service = AssessmentService(report_dir=args.report_dir)
    ticker = args.ticker.strip().upper()
    try:
        assessment = service.assess(
            ticker=ticker,
            data_source=args.data_source,
            fiscal_year=args.fiscal_year,
        )
    except AssessmentServiceError as exc:
        payload = _build_payload(
            "covenants",
            ticker=ticker,
            error=exc.message,
            status_code=exc.status_code,
            details=exc.details,
        )
        _emit(_json_text(payload, args.compact), args.output)
        return 2

    ratios = _build_ratio_analysis(assessment)
    covenants = FinancialCovenants(**threshold_payload)
    report = CovenantMonitor().check_covenants(
        company_name=assessment.get("company_name", ticker),
        fiscal_year=args.fiscal_year or ratios.fiscal_year or datetime.now().year,
        ratios=ratios,
        covenants=covenants,
    )
    report_payload = report.model_dump()
    payload = _build_payload(
        "covenants",
        ticker=ticker,
        data_source=args.data_source,
        period=assessment.get("period"),
        covenants_passed=report_payload["covenants_passed"],
        covenants_breached=report_payload["covenants_breached"],
        alerts=report_payload["alerts"],
    )
    _emit(_json_text(payload, args.compact), args.output)
    return 0 if report_payload["covenants_breached"] == 0 else 1


def _handle_version(args: argparse.Namespace) -> int:
    del args
    print("RiskLens CLI v0.1.0")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="risklens",
        description="RiskLens basic CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    assess_parser = subparsers.add_parser(
        "assess",
        help="Run credit risk assessment for one or more tickers",
    )
    assess_parser.add_argument(
        "tickers",
        nargs="+",
        help="Ticker symbols, e.g. NVDA 0700.HK",
    )
    assess_parser.add_argument(
        "--data-source",
        choices=ALLOWED_DATA_SOURCES,
        default="yfinance",
        help="Financial data source",
    )
    assess_parser.add_argument(
        "--fiscal-year",
        type=int,
        default=None,
        help="Optional fiscal year override",
    )
    assess_parser.add_argument(
        "--report-dir",
        default=str(Path("data") / "reports"),
        help="Directory used for generated ratio report artifacts",
    )
    _add_output_args(assess_parser)
    assess_parser.set_defaults(handler=_handle_assess)

    sources_parser = subparsers.add_parser(
        "sources",
        help="List supported data sources",
    )
    _add_output_args(sources_parser)
    sources_parser.set_defaults(handler=_handle_sources)

    search_parser = subparsers.add_parser(
        "search",
        help="Search similar equity tickers",
    )
    search_parser.add_argument(
        "query",
        help="Company/ticker keyword",
    )
    search_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum results (default: 20)",
    )
    _add_output_args(search_parser)
    search_parser.set_defaults(handler=_handle_search)

    covenants_parser = subparsers.add_parser(
        "covenants",
        help="Check covenant thresholds against latest assessment ratios",
    )
    covenants_parser.add_argument(
        "ticker",
        help="Ticker symbol, e.g. NVDA",
    )
    covenants_parser.add_argument(
        "--data-source",
        choices=ALLOWED_DATA_SOURCES,
        default="yfinance",
        help="Financial data source",
    )
    covenants_parser.add_argument(
        "--fiscal-year",
        type=int,
        default=None,
        help="Optional fiscal year override",
    )
    covenants_parser.add_argument(
        "--report-dir",
        default=str(Path("data") / "reports"),
        help="Directory used for generated ratio report artifacts",
    )
    covenants_parser.add_argument("--min-interest-coverage", type=float, default=None)
    covenants_parser.add_argument("--max-debt-to-ebitda", type=float, default=None)
    covenants_parser.add_argument("--max-debt-to-equity", type=float, default=None)
    covenants_parser.add_argument("--min-current-ratio", type=float, default=None)
    covenants_parser.add_argument("--min-quick-ratio", type=float, default=None)
    covenants_parser.add_argument("--min-fcf-to-debt", type=float, default=None)
    _add_output_args(covenants_parser)
    covenants_parser.set_defaults(handler=_handle_covenants)

    version_parser = subparsers.add_parser(
        "version",
        help="Show CLI version",
    )
    version_parser.set_defaults(handler=_handle_version)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return args.handler(args)
    except BrokenPipeError:
        return 0
    except Exception as exc:  # pragma: no cover - defensive fallback
        print(_json_text({"error": str(exc)}, compact=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
