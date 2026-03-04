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
PAGE_WIDTH_INCH = 8.27
PAGE_HEIGHT_INCH = 11.69

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


def _format_million_value(value: Any) -> str:
    num = _safe_num(value)
    if num is None:
        return "--"
    return f"{num / 1_000_000:,.1f}"


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
        cell.set_linewidth(0.35)
        cell.set_edgecolor("#d9dce1")
        if row == 0:
            cell.set_facecolor("#1f2937")
            cell.get_text().set_color("#ffffff")
            cell.get_text().set_weight("bold")
        else:
            cell.set_facecolor("#f8fafc" if row % 2 == 0 else "#ffffff")
        if first_col_left and col == 0:
            cell.get_text().set_ha("left")
            if row != 0:
                cell.get_text().set_weight("semibold")
        else:
            cell.get_text().set_ha("right")


def _set_table_column_widths(table: Any, col_widths: List[float]) -> None:
    if not col_widths:
        return
    for (row, col), cell in table.get_celld().items():
        if col < len(col_widths):
            cell.set_width(col_widths[col])


def _build_col_widths(total_cols: int, first_col_width: float) -> List[float]:
    if total_cols <= 1:
        return [1.0]
    first = max(0.18, min(0.45, first_col_width))
    rest = max(0.55, 1.0 - first)
    each = rest / (total_cols - 1)
    return [first] + [each] * (total_cols - 1)


def _draw_brand_header(fig: Any, title: str, subtitle: str | None, page_label: str) -> None:
    header_ax = fig.add_axes([0.0, 0.92, 1.0, 0.08])
    header_ax.set_xlim(0, 1)
    header_ax.set_ylim(0, 1)
    header_ax.axis("off")

    header_ax.text(0.04, 0.50, "RiskLens", ha="left", va="center", color="#111111", fontsize=13, fontweight="bold")
    header_ax.text(0.20, 0.62, title, ha="left", va="center", color="#111827", fontsize=15, fontweight="bold")
    if subtitle:
        header_ax.text(0.20, 0.30, subtitle, ha="left", va="center", color="#4b5563", fontsize=8.6)
    header_ax.text(0.96, 0.50, page_label, ha="right", va="center", color="#6b7280", fontsize=8.5)
    header_ax.plot([0.04, 0.96], [0.08, 0.08], color="#d1d5db", linewidth=0.8)


def _add_footer(fig: Any, generated_at: str) -> None:
    fig.text(0.04, 0.02, f"RiskLens Confidential · Generated {generated_at}", fontsize=7.5, color="#6b7280")


def _new_figure(title: str, subtitle: str | None = None, page_label: str = "") -> Tuple[Any, Any]:
    fig = plt.figure(figsize=(PAGE_WIDTH_INCH, PAGE_HEIGHT_INCH))
    fig.patch.set_facecolor("white")
    _draw_brand_header(fig, title=title, subtitle=subtitle, page_label=page_label)
    ax = fig.add_axes([0.05, 0.08, 0.90, 0.82])
    ax.axis("off")
    return fig, ax


def _format_bulleted_lines(items: List[str], wrap_width: int, max_lines: int) -> str:
    lines: List[str] = []
    for item in items:
        wrapped = textwrap.wrap(str(item), width=wrap_width) or [str(item)]
        for idx, part in enumerate(wrapped):
            prefix = "• " if idx == 0 else "  "
            lines.append(f"{prefix}{part}")
            if len(lines) >= max_lines:
                break
        if len(lines) >= max_lines:
            break
    if len(lines) >= max_lines and items:
        lines[-1] = lines[-1].rstrip(". ") + " …"
    return "\n".join(lines)


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
    currency_metric_keys = {key for key, _label, _src, value_type in metrics if value_type == "currency"}

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

    statement_numeric_values: List[float] = []
    for period in history:
        statements = period.get("statements") or {}
        if not isinstance(statements, dict):
            continue
        for tab in STATEMENT_TABS_ORDER:
            tab_data = statements.get(tab) or {}
            if isinstance(tab_data, dict):
                for value in tab_data.values():
                    numeric = _safe_num(value)
                    if numeric is not None:
                        statement_numeric_values.append(abs(numeric))
    use_millions = max(statement_numeric_values) >= 1_000_000 if statement_numeric_values else False

    def _format_currency_by_unit(value: float | None, is_delta: bool = False) -> str:
        if value is None:
            return "--"
        if use_millions:
            scaled = value / 1_000_000
            return f"{scaled:,.1f}"
        return f"{value:,.2f}"

    kpi_headers = ["Metric"] + periods + yoy_headers
    kpi_rows: List[List[str]] = []
    for key, label, src, value_type in metrics:
        row = [label]
        for period in history:
            source_obj = period.get(src) or {}
            metric_value = _safe_num(source_obj.get(key))
            if key in currency_metric_keys:
                row.append(_format_currency_by_unit(metric_value))
            else:
                row.append(_format_metric_value(metric_value, value_type))
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
                if key in currency_metric_keys:
                    row.append(_format_currency_by_unit(delta, is_delta=True))
                else:
                    row.append(_format_metric_value(delta, value_type, is_delta=True))
                row.append(_format_metric_value(pct, "%"))
        kpi_rows.append(row)

    statement_keys = _ordered_statement_keys(history)
    statement_headers = ["Item"] + periods + yoy_headers
    statement_rows: List[List[str]] = []
    for key in statement_keys:
        row = [textwrap.shorten(_prettify_key(key), width=36, placeholder="…")]
        for period in history:
            raw_val = _statement_value_for_key(period, key)
            row.append(_format_million_value(raw_val) if use_millions else _format_statement_value(raw_val))
        for cmp in yoy_map:
            v1 = _safe_num(_statement_value_for_key(cmp["p1"], key))
            v2 = _safe_num(_statement_value_for_key(cmp["p2"], key))
            if v1 is None or v2 is None:
                row.extend(["--", "--"])
            else:
                delta = v1 - v2
                pct = None if v2 == 0 else delta / abs(v2)
                row.append(_format_million_value(delta) if use_millions else f"{delta:,.2f}")
                row.append("--" if pct is None else f"{pct * 100:.1f}%")
        statement_rows.append(row)

    buffer = BytesIO()
    with PdfPages(buffer) as pdf:
        latest_period = _format_period_label(str(latest.get("fiscal_year", "N/A")))
        score = _safe_num((latest.get("assessment") or {}).get("risk_score"))
        z_zone = str((latest.get("assessment") or {}).get("overall_rating") or "N/A")
        rating = str((latest.get("assessment") or {}).get("implied_rating") or "N/A")
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows_per_page = 34
        statement_pages = max(1, math.ceil(len(statement_rows) / rows_per_page)) if statement_rows else 1
        total_pages = 2 + statement_pages
        page_no = 1

        # Page 1: Summary + covenant/data-quality
        fig, ax = _new_figure(
            title=company_name,
            subtitle=f"{ticker} · Latest Period {latest_period} · Currency {currency}",
            page_label=f"Page {page_no}/{total_pages}",
        )
        ax.text(
            0.00,
            0.96,
            f"Altman Z-Score  {'--' if score is None else f'{score:.2f}'}",
            transform=ax.transAxes,
            fontsize=11.5,
            fontweight="bold",
            color="#111827",
            bbox=dict(boxstyle="round,pad=0.30", facecolor="#f3f4f6", edgecolor="#d1d5db", linewidth=0.6),
        )
        ax.text(
            0.45,
            0.96,
            f"Zone  {z_zone}",
            transform=ax.transAxes,
            fontsize=10.2,
            color="#111827",
            bbox=dict(boxstyle="round,pad=0.30", facecolor="#f3f4f6", edgecolor="#d1d5db", linewidth=0.6),
        )
        ax.text(
            0.71,
            0.96,
            f"Implied Rating  {rating}",
            transform=ax.transAxes,
            fontsize=10.2,
            color="#111827",
            bbox=dict(boxstyle="round,pad=0.30", facecolor="#f3f4f6", edgecolor="#d1d5db", linewidth=0.6),
        )

        strengths_ax = fig.add_axes([0.05, 0.56, 0.42, 0.26])
        strengths_ax.axis("off")
        strengths_ax.set_facecolor("#ffffff")
        strengths_ax.text(0.0, 1.0, "Strengths", transform=strengths_ax.transAxes, fontsize=11, fontweight="bold", color="#111827", va="top")
        strengths_ax.text(
            0.0,
            0.90,
            _format_bulleted_lines([str(item) for item in strength_items[:8]], wrap_width=40, max_lines=10),
            transform=strengths_ax.transAxes,
            fontsize=8.6,
            va="top",
            color="#1f2937",
        )

        watch_ax = fig.add_axes([0.53, 0.56, 0.42, 0.26])
        watch_ax.axis("off")
        watch_ax.set_facecolor("#ffffff")
        watch_ax.text(0.0, 1.0, "Watch Items", transform=watch_ax.transAxes, fontsize=11, fontweight="bold", color="#111827", va="top")
        watch_ax.text(
            0.0,
            0.90,
            _format_bulleted_lines([str(item) for item in watch_items[:8]], wrap_width=36, max_lines=10),
            transform=watch_ax.transAxes,
            fontsize=8.6,
            va="top",
            color="#1f2937",
        )

        ax.text(0.00, 0.52, "Covenant Pre-Check", transform=ax.transAxes, fontsize=11.2, fontweight="bold", color="#111827")
        covenant_ax = fig.add_axes([0.05, 0.18, 0.90, 0.30])
        covenant_ax.axis("off")
        covenant_table = covenant_ax.table(
            cellText=covenant_rows,
            colLabels=["Metric", "Actual", "Threshold", "Status", "Signal", "Notes"],
            loc="upper left",
            cellLoc="left",
            bbox=[0.0, 0.0, 1.0, 1.0],
            colWidths=[0.24, 0.12, 0.12, 0.18, 0.10, 0.24],
        )
        _style_table(covenant_table, first_col_left=True, font_size=8)

        missing_text = ", ".join(missing_items) if missing_items else "None"
        ax.text(0.00, 0.10, f"Data Quality · Breach Count: {breach_count}", transform=ax.transAxes, fontsize=8.4, color="#374151")
        ax.text(0.00, 0.065, f"Data Quality · Missing Key Inputs: {len(missing_items)}", transform=ax.transAxes, fontsize=8.4, color="#374151")
        ax.text(0.00, 0.03, f"Data Quality · Missing Items: {missing_text}", transform=ax.transAxes, fontsize=8.4, color="#374151")
        _add_footer(fig, generated_at)

        pdf.savefig(fig)
        plt.close(fig)
        page_no += 1

        # Page 2: KPI trends
        unit_text = f"Figures in millions ({currency})" if use_millions else f"Figures in reported currency ({currency})"
        fig, _ = _new_figure(
            title=f"{company_name} · KPI Trends",
            subtitle=unit_text,
            page_label=f"Page {page_no}/{total_pages}",
        )
        kpi_ax = fig.add_axes([0.05, 0.08, 0.90, 0.80])
        kpi_ax.axis("off")
        kpi_table = kpi_ax.table(
            cellText=kpi_rows,
            colLabels=kpi_headers,
            loc="upper left",
            cellLoc="right",
            bbox=[0.0, 0.0, 1.0, 1.0],
            colWidths=_build_col_widths(len(kpi_headers), 0.24),
        )
        _style_table(kpi_table, first_col_left=True, font_size=6.0 if len(kpi_headers) > 9 else 7.1)
        _add_footer(fig, generated_at)
        pdf.savefig(fig)
        plt.close(fig)
        page_no += 1

        # Page 3+: statements detail (chunked)
        if not statement_rows:
            fig, ax = _new_figure(
                title=f"{company_name} · Financial Statements Detail",
                subtitle=None,
                page_label=f"Page {page_no}/{total_pages}",
            )
            ax.text(0.00, 0.90, "No statement rows available.", transform=ax.transAxes, fontsize=10, color="#374151")
            _add_footer(fig, generated_at)
            pdf.savefig(fig)
            plt.close(fig)
        else:
            for start in range(0, len(statement_rows), rows_per_page):
                chunk = statement_rows[start:start + rows_per_page]
                fig, _ = _new_figure(
                    title=f"{company_name} · Financial Statements Detail",
                    subtitle=unit_text,
                    page_label=f"Page {page_no}/{total_pages}",
                )
                stmt_ax = fig.add_axes([0.05, 0.08, 0.90, 0.80])
                stmt_ax.axis("off")
                stmt_table = stmt_ax.table(
                    cellText=chunk,
                    colLabels=statement_headers,
                    loc="upper left",
                    cellLoc="right",
                    bbox=[0.0, 0.0, 1.0, 1.0],
                    colWidths=_build_col_widths(len(statement_headers), 0.30),
                )
                _style_table(stmt_table, first_col_left=True, font_size=5.6 if len(statement_headers) > 9 else 6.6)
                _add_footer(fig, generated_at)
                pdf.savefig(fig)
                plt.close(fig)
                page_no += 1

    return buffer.getvalue()
