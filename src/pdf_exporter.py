"""
PDF Exporter (desktop-first)
============================
Generate a downloadable Full PDF directly on backend.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
import math
import re
import textwrap
from typing import Any, Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

STATEMENT_TABS_ORDER = ("income", "balance", "cash")

matplotlib.rcParams["font.sans-serif"] = [
    "PingFang SC",
    "Noto Sans CJK SC",
    "Microsoft YaHei",
    "SimHei",
    "Arial Unicode MS",
    "DejaVu Sans",
]
matplotlib.rcParams["axes.unicode_minus"] = False


def _format_period_label(label: str) -> str:
    q_match = re.search(r"Q([1-4])\s+'?(\d{2})", label or "", flags=re.I)
    if q_match:
        return f"{q_match.group(2)}Q{q_match.group(1)}"
    return str(label or "")


def _parse_quarter_label(label: str) -> Tuple[int, int] | None:
    raw = str(label or "")
    normalized = _format_period_label(raw)
    m1 = re.match(r"^(\d{2,4})Q([1-4])$", normalized, flags=re.I)
    if m1:
        raw_year = int(m1.group(1))
        year = raw_year if len(m1.group(1)) > 2 else 2000 + raw_year
        return year, int(m1.group(2))
    m2 = re.search(r"Q([1-4])\s*'?\s*(\d{2,4})", raw, flags=re.I)
    if m2:
        raw_year = int(m2.group(2))
        year = raw_year if len(m2.group(2)) > 2 else 2000 + raw_year
        return year, int(m2.group(1))
    return None


def _build_yoy_map(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if len(history) < 2:
        return []

    comparisons: List[Dict[str, Any]] = []
    latest = history[0]
    if latest.get("is_quarterly"):
        latest_q = _parse_quarter_label(latest.get("fiscal_year", ""))
        if latest_q is not None:
            for idx, period in enumerate(history):
                if idx == 0 or not period.get("is_quarterly"):
                    continue
                candidate = _parse_quarter_label(period.get("fiscal_year", ""))
                if candidate and candidate[1] == latest_q[1] and candidate[0] == latest_q[0] - 1:
                    comparisons.append({
                        "yearCode": _format_period_label(latest.get("fiscal_year", "")),
                        "prevYearCode": _format_period_label(period.get("fiscal_year", "")),
                        "p1": latest,
                        "p2": period,
                    })
                    break

    annuals = [period for period in history if not period.get("is_quarterly")]
    if len(annuals) >= 2:
        comparisons.append({
            "yearCode": _format_period_label(annuals[0].get("fiscal_year", "")),
            "prevYearCode": _format_period_label(annuals[1].get("fiscal_year", "")),
            "p1": annuals[0],
            "p2": annuals[1],
        })
    if not latest.get("is_quarterly") and len(annuals) >= 3:
        comparisons.append({
            "yearCode": _format_period_label(annuals[1].get("fiscal_year", "")),
            "prevYearCode": _format_period_label(annuals[2].get("fiscal_year", "")),
            "p1": annuals[1],
            "p2": annuals[2],
        })
    return comparisons


def _safe_num(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        f_val = float(value)
        if not math.isnan(f_val) and not math.isinf(f_val):
            return f_val
    return None


def _format_metric_value(value: float | None, value_type: str, is_delta: bool = False) -> str:
    if value is None:
        return "--"
    if value_type == "currency":
        return f"{value:,.2f}"
    if value_type == "x":
        return f"{value:.2f}x"
    if value_type == "%":
        scaled = value * 100
        return f"{scaled:.1f}pp" if is_delta else f"{scaled:.1f}%"
    return f"{value:.2f}"


def _format_statement_value(value: Any) -> str:
    num = _safe_num(value)
    if num is None:
        return "--"
    return f"{num:,.2f}"


def _prettify_key(key: str) -> str:
    parts = re.split(r"[_\s]+", str(key or "").strip())
    return " ".join(part.capitalize() for part in parts if part)


def _ordered_statement_keys(history: List[Dict[str, Any]]) -> List[str]:
    keys: List[str] = []
    seen = set()
    for tab in STATEMENT_TABS_ORDER:
        for period in history:
            statements = period.get("statements") or {}
            tab_data = statements.get(tab) or {}
            if not isinstance(tab_data, dict):
                continue
            for key in tab_data.keys():
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
    return keys


def _statement_value_for_key(period: Dict[str, Any], key: str) -> Any:
    statements = period.get("statements") or {}
    for tab in STATEMENT_TABS_ORDER:
        tab_data = statements.get(tab) or {}
        if isinstance(tab_data, dict) and key in tab_data:
            return tab_data.get(key)
    return None


def _evaluate_covenant(value: float | None, threshold: float, comparator: str) -> Tuple[str, str, str]:
    if value is None:
        return "BREACH (DATA MISSING)", "Watch", "Missing input"
    if comparator == "min":
        if value < threshold:
            return "BREACH", "Watch", f"Below minimum {threshold}"
        if value >= threshold * 1.25:
            return "PASS", "Strong", "Comfortable buffer above threshold"
        return "PASS", "Neutral", "Within threshold"
    if value > threshold:
        return "BREACH", "Watch", f"Above maximum {threshold}"
    if value <= threshold * 0.75:
        return "PASS", "Strong", "Comfortable buffer below threshold"
    return "PASS", "Neutral", "Within threshold"


def _style_table(table: Any, first_col_left: bool = True, font_size: int = 8) -> None:
    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    for (row, col), cell in table.get_celld().items():
        cell.set_linewidth(0.4)
        cell.set_edgecolor("#d0d0d0")
        if row == 0:
            cell.set_facecolor("#efefef")
            cell.get_text().set_weight("bold")
        else:
            cell.set_facecolor("#ffffff")
        if first_col_left and col == 0:
            cell.get_text().set_ha("left")
        else:
            cell.get_text().set_ha("right")


def _new_figure(title: str, subtitle: str | None = None) -> Tuple[Any, Any]:
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor("white")
    fig.text(0.04, 0.96, title, fontsize=17, fontweight="bold", va="top")
    if subtitle:
        fig.text(0.04, 0.925, subtitle, fontsize=9, color="#555555", va="top")
    ax = fig.add_axes([0.04, 0.08, 0.92, 0.80])
    ax.axis("off")
    return fig, ax


def generate_full_pdf(report: Dict[str, Any], lang: str = "zh-CN") -> bytes:
    ticker = str(report.get("ticker") or "N/A")
    company_name = str(report.get("company_name") or ticker)
    currency = str(report.get("currency") or "USD")
    history = report.get("history") if isinstance(report.get("history"), list) else []
    latest = next((p for p in history if p.get("assessment") is not None), history[0] if history else None)
    if not latest:
        raise ValueError("No history available for PDF export.")

    yoy_map = _build_yoy_map(history)
    periods = [_format_period_label(str(period.get("fiscal_year", ""))) for period in history]
    yoy_headers: List[str] = []
    for cmp in yoy_map:
        yoy_headers.extend([f"{cmp['yearCode']} vs {cmp['prevYearCode']}", "%"])

    metrics = [
        ("operating_income", "EBIT", "raw_metrics", "currency"),
        ("ebitda", "EBITDA", "ratios", "currency"),
        ("total_debt", "Total Debt", "raw_metrics", "currency"),
        ("debt_to_ebitda", "Debt / EBITDA", "ratios", "x"),
        ("interest_coverage", "Interest Coverage", "ratios", "x"),
        ("free_cf", "Free Cash Flow", "raw_metrics", "currency"),
        ("fcf_to_debt", "FCF / Debt", "ratios", "%"),
        ("current_ratio", "Current Ratio", "ratios", "x"),
    ]

    strength_items = latest.get("assessment", {}).get("strengths") or ["No major strengths detected."]
    watch_items = latest.get("assessment", {}).get("weaknesses") or ["No critical watch items."]

    covenant_source = [
        ("Interest Coverage", _safe_num((latest.get("ratios") or {}).get("interest_coverage")), 3.0, "min"),
        ("Debt / EBITDA", _safe_num((latest.get("ratios") or {}).get("debt_to_ebitda")), 4.0, "max"),
        ("Current Ratio", _safe_num((latest.get("ratios") or {}).get("current_ratio")), 1.2, "min"),
        ("FCF / Debt", _safe_num((latest.get("ratios") or {}).get("fcf_to_debt")), 0.05, "min"),
    ]
    covenant_rows: List[List[str]] = []
    breach_count = 0
    missing_items: List[str] = []
    for metric, actual, threshold, comparator in covenant_source:
        status, signal, note = _evaluate_covenant(actual, threshold, comparator)
        if "BREACH" in status:
            breach_count += 1
        if "MISSING" in status:
            missing_items.append(metric)
        if metric == "FCF / Debt":
            actual_text = "--" if actual is None else f"{actual * 100:.1f}%"
        elif metric in {"Interest Coverage", "Debt / EBITDA", "Current Ratio"}:
            actual_text = "--" if actual is None else f"{actual:.2f}x"
        else:
            actual_text = "--" if actual is None else f"{actual:.2f}"
        threshold_label = f">= {threshold}" if comparator == "min" else f"<= {threshold}"
        covenant_rows.append([metric, actual_text, threshold_label, status, signal, note])

    kpi_headers = ["Metric"] + periods + yoy_headers
    kpi_rows: List[List[str]] = []
    for key, label, src, value_type in metrics:
        row = [label]
        for period in history:
            source_obj = period.get(src) or {}
            row.append(_format_metric_value(_safe_num(source_obj.get(key)), value_type))
        for cmp in yoy_map:
            s1 = (cmp.get("p1") or {}).get(src) or {}
            s2 = (cmp.get("p2") or {}).get(src) or {}
            v1 = _safe_num(s1.get(key))
            v2 = _safe_num(s2.get(key))
            if v1 is None or v2 is None:
                row.extend(["--", "--"])
            else:
                delta = v1 - v2
                pct = None if v2 == 0 else delta / abs(v2)
                row.append(_format_metric_value(delta, value_type, is_delta=True))
                row.append(_format_metric_value(pct, "%"))
        kpi_rows.append(row)

    statement_keys = _ordered_statement_keys(history)
    statement_headers = ["Item"] + periods + yoy_headers
    statement_rows: List[List[str]] = []
    for key in statement_keys:
        row = [_prettify_key(key)]
        for period in history:
            row.append(_format_statement_value(_statement_value_for_key(period, key)))
        for cmp in yoy_map:
            v1 = _safe_num(_statement_value_for_key(cmp["p1"], key))
            v2 = _safe_num(_statement_value_for_key(cmp["p2"], key))
            if v1 is None or v2 is None:
                row.extend(["--", "--"])
            else:
                delta = v1 - v2
                pct = None if v2 == 0 else delta / abs(v2)
                row.append(f"{delta:,.2f}")
                row.append("--" if pct is None else f"{pct * 100:.1f}%")
        statement_rows.append(row)

    buffer = BytesIO()
    with PdfPages(buffer) as pdf:
        latest_period = _format_period_label(str(latest.get("fiscal_year", "N/A")))
        score = _safe_num((latest.get("assessment") or {}).get("risk_score"))
        z_zone = str((latest.get("assessment") or {}).get("overall_rating") or "N/A")
        rating = str((latest.get("assessment") or {}).get("implied_rating") or "N/A")
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Page 1: Summary + covenant/data-quality
        fig, ax = _new_figure(
            title=f"{company_name} ({ticker})",
            subtitle=f"Latest Period: {latest_period}   Currency: {currency}   Generated: {generated_at}",
        )
        ax.text(0.00, 0.95, f"Altman Z-Score: {'--' if score is None else f'{score:.2f}'}", transform=ax.transAxes, fontsize=11, fontweight="bold")
        ax.text(0.36, 0.95, f"Zone: {z_zone}", transform=ax.transAxes, fontsize=11)
        ax.text(0.62, 0.95, f"Implied Rating: {rating}", transform=ax.transAxes, fontsize=11)

        ax.text(0.00, 0.89, "Strengths", transform=ax.transAxes, fontsize=11, fontweight="bold")
        strength_text = "\n".join([f"• {textwrap.fill(str(item), width=78)}" for item in strength_items[:6]])
        ax.text(0.00, 0.85, strength_text, transform=ax.transAxes, fontsize=9, va="top")

        ax.text(0.52, 0.89, "Watch Items", transform=ax.transAxes, fontsize=11, fontweight="bold")
        watch_text = "\n".join([f"• {textwrap.fill(str(item), width=58)}" for item in watch_items[:6]])
        ax.text(0.52, 0.85, watch_text, transform=ax.transAxes, fontsize=9, va="top")

        ax.text(0.00, 0.60, "Covenant Pre-Check", transform=ax.transAxes, fontsize=11, fontweight="bold")
        covenant_ax = fig.add_axes([0.04, 0.23, 0.92, 0.34])
        covenant_ax.axis("off")
        covenant_table = covenant_ax.table(
            cellText=covenant_rows,
            colLabels=["Metric", "Actual", "Threshold", "Status", "Signal", "Notes"],
            loc="upper left",
            cellLoc="left",
            bbox=[0.0, 0.0, 1.0, 1.0],
        )
        _style_table(covenant_table, first_col_left=True, font_size=8)

        missing_text = ", ".join(missing_items) if missing_items else "None"
        ax.text(0.00, 0.14, f"Data Quality · Breach Count: {breach_count}", transform=ax.transAxes, fontsize=9)
        ax.text(0.00, 0.10, f"Data Quality · Missing Key Inputs: {len(missing_items)}", transform=ax.transAxes, fontsize=9)
        ax.text(0.00, 0.06, f"Data Quality · Missing Items: {missing_text}", transform=ax.transAxes, fontsize=9)

        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # Page 2: KPI trends
        fig, _ = _new_figure(title="KPI Trends", subtitle="Columns follow Excel export periods and YoY rules.")
        kpi_ax = fig.add_axes([0.04, 0.12, 0.92, 0.78])
        kpi_ax.axis("off")
        kpi_table = kpi_ax.table(
            cellText=kpi_rows,
            colLabels=kpi_headers,
            loc="upper left",
            cellLoc="right",
            bbox=[0.0, 0.0, 1.0, 1.0],
        )
        _style_table(kpi_table, first_col_left=True, font_size=7 if len(kpi_headers) > 9 else 8)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # Page 3+: statements detail (chunked)
        rows_per_page = 28
        if not statement_rows:
            fig, ax = _new_figure(title="Financial Statements Detail")
            ax.text(0.00, 0.90, "No statement rows available.", transform=ax.transAxes, fontsize=10)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
        else:
            for start in range(0, len(statement_rows), rows_per_page):
                chunk = statement_rows[start:start + rows_per_page]
                page_no = start // rows_per_page + 1
                fig, _ = _new_figure(
                    title="Financial Statements Detail",
                    subtitle=f"Page {page_no} · Rows {start + 1}-{start + len(chunk)}",
                )
                stmt_ax = fig.add_axes([0.04, 0.10, 0.92, 0.80])
                stmt_ax.axis("off")
                stmt_table = stmt_ax.table(
                    cellText=chunk,
                    colLabels=statement_headers,
                    loc="upper left",
                    cellLoc="right",
                    bbox=[0.0, 0.0, 1.0, 1.0],
                )
                _style_table(stmt_table, first_col_left=True, font_size=6 if len(statement_headers) > 9 else 7)
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

    return buffer.getvalue()
