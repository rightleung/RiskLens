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
from matplotlib.patches import FancyBboxPatch
from matplotlib.backends.backend_pdf import PdfPages

STATEMENT_TABS_ORDER = ("income", "balance", "cash")
STATEMENT_TAB_LABEL_KEYS = {
    "income": "income_statement",
    "balance": "balance_sheet",
    "cash": "cash_flow_statement",
}
PAGE_WIDTH_INCH = 8.27
PAGE_HEIGHT_INCH = 11.69

PDF_THEME = {
    "page_bg": "#ffffff",
    "header_text": "#111827",
    "subtle_text": "#6b7280",
    "muted_text": "#94a3b8",
    "border": "#dbe2ea",
    "header_fill": "#111827",
    "header_fill_alt": "#1f2937",
    "accent_purple": "#7c3aed",
    "accent_blue": "#2563eb",
    "accent_green": "#059669",
    "accent_amber": "#d97706",
    "accent_red": "#dc2626",
    "panel_fill": "#f8fafc",
    "panel_fill_alt": "#eef2ff",
    "positive_fill": "#ecfdf5",
    "warning_fill": "#fffbeb",
    "negative_fill": "#fef2f2",
}

PDF_LABELS = {
    "en": {
        "summary": "CREDIT RISK SUMMARY",
        "strengths": "STRENGTHS",
        "watch": "WATCH ITEMS",
        "profile": "COMPANY PROFILE",
        "covenant": "COVENANT PRE-CHECK",
        "data_quality": "Data Quality Check",
        "breach": "Breach Count",
        "missing": "Missing Inputs",
        "history": "HISTORY",
        "kpi_trends": "KPI Trends",
        "statements": "Financial Statements Detail",
        "figures_millions": "Figures in millions",
        "figures_reported": "Figures in reported currency",
        "metric": "Metric",
        "actual": "Actual",
        "threshold": "Threshold",
        "status": "Status",
        "signal": "Signal",
        "notes": "Notes",
        "item": "Item",
        "no_data": "No statement data available.",
        "income_statement": "Income Statement",
        "balance_sheet": "Balance Sheet",
        "cash_flow_statement": "Cash Flow Statement",
        "latest_period": "Latest Period",
        "currency": "Currency",
        "zone": "Z-Score Zone",
        "implied_rating": "Implied Rating",
        "generated": "Generated",
        "sector": "Sector",
        "industry": "Industry",
        "country": "Country",
        "employees": "Employees",
        "website": "Website",
        "periods": "Periods",
        "quarterly": "Quarterly",
        "annual": "Annual",
        "historical_periods": "Historical periods",
        "yoy_comparisons": "YoY comparisons",
    },
    "zh-CN": {
        "summary": "信用风险评估摘要",
        "strengths": "信用优势",
        "watch": "关注事项",
        "profile": "公司概况",
        "covenant": "财务限制条款预检",
        "data_quality": "数据质量检查",
        "breach": "违约项数",
        "missing": "缺失指标数",
        "history": "历史期间",
        "kpi_trends": "关键指标趋势",
        "statements": "财务报表明细",
        "figures_millions": "数值单位：百万",
        "figures_reported": "数值单位：原始货币",
        "metric": "指标名称",
        "actual": "实际值",
        "threshold": "限制阈值",
        "status": "状态",
        "signal": "信号",
        "notes": "备注",
        "item": "报表项目",
        "no_data": "无可用财务报表数据。",
        "income_statement": "利润表",
        "balance_sheet": "资产负债表",
        "cash_flow_statement": "现金流量表",
        "latest_period": "最新期间",
        "currency": "币种",
        "zone": "Z-Score 分区",
        "implied_rating": "隐含评级",
        "generated": "生成时间",
        "sector": "行业板块",
        "industry": "细分行业",
        "country": "国家/地区",
        "employees": "员工数",
        "website": "网站",
        "periods": "期间数",
        "quarterly": "季度",
        "annual": "年度",
        "historical_periods": "历史期间",
        "yoy_comparisons": "同比对比",
    },
    "zh-TW": {
        "summary": "信用風險評估摘要",
        "strengths": "信用優勢",
        "watch": "關注事項",
        "profile": "公司概況",
        "covenant": "財務限制條款預檢",
        "data_quality": "資料品質檢查",
        "breach": "違約項數",
        "missing": "缺失指標數",
        "history": "歷史期間",
        "kpi_trends": "關鍵指標趨勢",
        "statements": "財務報表明細",
        "figures_millions": "數值單位：百萬",
        "figures_reported": "數值單位：原始貨幣",
        "metric": "指標名稱",
        "actual": "實際值",
        "threshold": "限制門檻",
        "status": "狀態",
        "signal": "訊號",
        "notes": "備註",
        "item": "報表項目",
        "no_data": "無可用財務報表資料。",
        "income_statement": "損益表",
        "balance_sheet": "資產負債表",
        "cash_flow_statement": "現金流量表",
        "latest_period": "最新期間",
        "currency": "幣別",
        "zone": "Z-Score 區間",
        "implied_rating": "隱含評級",
        "generated": "產生時間",
        "sector": "產業板塊",
        "industry": "細分產業",
        "country": "國家/地區",
        "employees": "員工數",
        "website": "網站",
        "periods": "期間數",
        "quarterly": "季度",
        "annual": "年度",
        "historical_periods": "歷史期間",
        "yoy_comparisons": "同比比較",
    },
    "ja": {
        "summary": "信用リスク要約",
        "strengths": "強み",
        "watch": "注意事項",
        "profile": "会社概要",
        "covenant": "コベナンツ事前チェック",
        "data_quality": "データ品質チェック",
        "breach": "違反件数",
        "missing": "欠損項目数",
        "history": "履歴期間",
        "kpi_trends": "主要指標トレンド",
        "statements": "財務諸表明細",
        "figures_millions": "表示単位：百万",
        "figures_reported": "表示単位：報告通貨",
        "metric": "指標",
        "actual": "実績値",
        "threshold": "閾値",
        "status": "判定",
        "signal": "シグナル",
        "notes": "備考",
        "item": "勘定科目",
        "no_data": "利用可能な財務データがありません。",
        "income_statement": "損益計算書",
        "balance_sheet": "貸借対照表",
        "cash_flow_statement": "キャッシュフロー計算書",
        "latest_period": "最新期間",
        "currency": "通貨",
        "zone": "Z-Score 区分",
        "implied_rating": "予想格付け",
        "generated": "生成時刻",
        "sector": "セクター",
        "industry": "業種",
        "country": "国/地域",
        "employees": "従業員数",
        "website": "Webサイト",
        "periods": "期間数",
        "quarterly": "四半期",
        "annual": "通期",
        "historical_periods": "履歴期間",
        "yoy_comparisons": "前年比比較",
    },
}

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


def _localized_labels(lang: str) -> Dict[str, str]:
    return PDF_LABELS.get(lang, PDF_LABELS["en"])


def _company_profile_summary(company_profile: Dict[str, Any], labels: Dict[str, str]) -> str:
    if not isinstance(company_profile, dict):
        return ""

    fields = []
    for key, label_key in (
        ("sector", "sector"),
        ("industry", "industry"),
        ("country", "country"),
        ("employees", "employees"),
        ("website", "website"),
    ):
        value = company_profile.get(key)
        if value in (None, "", []):
            continue
        if key == "employees":
            try:
                value = f"{int(float(value)):,}"
            except (TypeError, ValueError):
                value = str(value)
        fields.append(f"{labels[label_key]}: {value}")
    return " · ".join(fields)


def _compact_profile_items(company_profile: Dict[str, Any], labels: Dict[str, str]) -> List[Tuple[str, str]]:
    if not isinstance(company_profile, dict):
        return []

    items: List[Tuple[str, str]] = []
    for key, label_key in (
        ("sector", "sector"),
        ("industry", "industry"),
        ("country", "country"),
        ("employees", "employees"),
        ("website", "website"),
    ):
        value = company_profile.get(key)
        if value in (None, "", []):
            continue
        if key == "employees":
            try:
                value = f"{int(float(value)):,}"
            except (TypeError, ValueError):
                value = str(value)
        else:
            value = textwrap.shorten(str(value), width=26, placeholder="…")
        items.append((labels[label_key], str(value)))
    return items


def _compose_subtitle(
    ticker: str,
    latest_period: str,
    unit_text: str,
    company_profile: Dict[str, Any],
    labels: Dict[str, str],
) -> str:
    parts = [ticker, latest_period, unit_text]
    profile_summary = _company_profile_summary(company_profile, labels)
    if profile_summary:
        parts.append(profile_summary)
    return " · ".join(part for part in parts if part)


def _draw_info_strip(fig: Any, rect: List[float], items: List[Tuple[str, str]]) -> None:
    if not items:
        return

    ax = fig.add_axes(rect)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    strip = FancyBboxPatch(
        (0.0, 0.0),
        1.0,
        1.0,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.0,
        facecolor="#f8fafc",
        edgecolor=PDF_THEME["border"],
    )
    ax.add_patch(strip)

    cols = max(len(items), 1)
    for idx, (label, value) in enumerate(items):
        left = idx / cols
        if idx > 0:
            ax.plot([left, left], [0.16, 0.84], color=PDF_THEME["border"], linewidth=0.7)
        ax.text(left + 0.015, 0.68, label.upper(), ha="left", va="center", fontsize=6.6, color=PDF_THEME["subtle_text"], fontweight="bold")
        ax.text(left + 0.015, 0.30, value, ha="left", va="center", fontsize=7.8, color=PDF_THEME["header_text"])


def _statement_keys_for_tab(history: List[Dict[str, Any]], tab: str) -> List[str]:
    keys: List[str] = []
    seen = set()
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


def _statement_value_for_tab(period: Dict[str, Any], tab: str, key: str) -> Any:
    statements = period.get("statements") or {}
    tab_data = statements.get(tab) or {}
    if isinstance(tab_data, dict):
        return tab_data.get(key)
    return None


def _build_statement_rows_for_tab(
    history: List[Dict[str, Any]],
    tab: str,
    use_millions: bool,
    yoy_map: List[Dict[str, Any]],
) -> List[List[str]]:
    rows: List[List[str]] = []
    for key in _statement_keys_for_tab(history, tab):
        row = [_prettify_key(key)]
        for period in history:
            raw_val = _statement_value_for_tab(period, tab, key)
            row.append(_format_million_value(raw_val) if use_millions else _format_statement_value(raw_val))
        if yoy_map:
            row.append("")
            for cmp in yoy_map:
                v1 = _safe_num(_statement_value_for_tab(cmp["p1"], tab, key))
                v2 = _safe_num(_statement_value_for_tab(cmp["p2"], tab, key))
                if v1 is None or v2 is None:
                    row.extend(["--", "--"])
                else:
                    delta = v1 - v2
                    pct = None if v2 == 0 else delta / abs(v2)
                    row.append(_format_million_value(delta) if use_millions else f"{delta:,.2f}")
                    row.append("--" if pct is None else f"{pct * 100:.1f}%")
        rows.append(row)
    return rows


def _ordered_statement_entries(history: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    entries: List[Tuple[str, str]] = []
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
                    entries.append((tab, key))
    return entries


def _ordered_statement_keys(history: List[Dict[str, Any]]) -> List[str]:
    return [key for _tab, key in _ordered_statement_entries(history)]


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


def _style_table(
    table: Any,
    first_col_left: bool = True,
    font_size: int = 8,
    header_fill: str = "#111827",
    header_text: str = "#ffffff",
    body_fill: str = "#ffffff",
    alt_fill: str = "#f8fafc",
    row_kinds: List[str] | None = None,
    section_fill: str = "#e2e8f0",
) -> None:
    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    for (row, col), cell in table.get_celld().items():
        cell.set_linewidth(0.2)
        cell.set_edgecolor("#e2e8f0")
        if row == 0:
            cell.set_facecolor(header_fill)
            cell.get_text().set_color(header_text)
            cell.get_text().set_weight("bold")
            cell.set_height(0.048)
        else:
            kind = row_kinds[row - 1] if row_kinds and row - 1 < len(row_kinds) else "item"
            if kind == "section":
                cell.set_facecolor(section_fill)
                cell.get_text().set_color("#111827")
                cell.get_text().set_weight("bold")
                cell.set_height(0.040)
            else:
                cell.set_facecolor(alt_fill if row % 2 == 0 else body_fill)
                cell.set_height(0.034)

        if first_col_left and col == 0:
            cell.get_text().set_ha("left")
            cell.get_text().set_multialignment("left")
            if row != 0:
                cell.get_text().set_weight("medium")
                cell.get_text().set_color("#1f2937")
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
    # For statements/KPIs, first column (item names) needs significantly more space
    first = max(0.28, min(0.48, first_col_width))
    rest = 1.0 - first
    each = rest / (total_cols - 1)
    return [first] + [each] * (total_cols - 1)


def _draw_card(
    fig: Any,
    rect: List[float],
    title: str,
    value: str,
    subtitle: str | None = None,
    accent: str = "#7c3aed",
    fill: str = "#f8fafc",
    value_size: float = 16,
) -> None:
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    card = FancyBboxPatch(
        (0.0, 0.0),
        1.0,
        1.0,
        boxstyle="round,pad=0.015,rounding_size=0.04",
        linewidth=1.0,
        facecolor=fill,
        edgecolor=PDF_THEME["border"],
    )
    ax.add_patch(card)
    ax.add_patch(plt.Rectangle((0.0, 0.0), 0.03, 1.0, color=accent, transform=ax.transAxes, clip_on=False))
    ax.text(0.08, 0.72, title, ha="left", va="center", fontsize=8.5, color=PDF_THEME["subtle_text"], fontweight="bold")
    ax.text(0.08, 0.40, value, ha="left", va="center", fontsize=value_size, color=PDF_THEME["header_text"], fontweight="bold")
    if subtitle:
        ax.text(0.08, 0.14, subtitle, ha="left", va="center", fontsize=7.8, color=PDF_THEME["subtle_text"])


def _draw_panel(
    fig: Any,
    rect: List[float],
    title: str,
    body: str,
    accent: str,
    fill: str = "#ffffff",
    title_color: str = "#111827",
    body_color: str = "#374151",
    body_size: float = 8.7,
) -> None:
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    panel = FancyBboxPatch(
        (0.0, 0.0),
        1.0,
        1.0,
        boxstyle="round,pad=0.015,rounding_size=0.03",
        linewidth=1.0,
        facecolor=fill,
        edgecolor=PDF_THEME["border"],
    )
    ax.add_patch(panel)
    ax.add_patch(plt.Rectangle((0.0, 0.96), 1.0, 0.04, color=accent, transform=ax.transAxes, clip_on=False))
    ax.text(0.04, 0.90, title, ha="left", va="center", fontsize=10.0, color=title_color, fontweight="bold")
    ax.text(0.04, 0.83, body, ha="left", va="top", fontsize=body_size, color=body_color, linespacing=1.35)


def _draw_brand_header(fig: Any, title: str, subtitle: str | None, page_label: str) -> None:
    header_ax = fig.add_axes([0.0, 0.90, 1.0, 0.10])
    header_ax.set_xlim(0, 1)
    header_ax.set_ylim(0, 1)
    header_ax.axis("off")

    header_ax.add_patch(plt.Rectangle((0.0, 0.0), 1.0, 1.0, color="#ffffff", transform=header_ax.transAxes, zorder=0))
    header_ax.add_patch(plt.Rectangle((0.04, 0.20), 0.012, 0.60, color=PDF_THEME["accent_purple"], transform=header_ax.transAxes, zorder=1))
    header_ax.text(0.07, 0.60, "RiskLens", ha="left", va="center", color=PDF_THEME["header_text"], fontsize=14.5, fontweight="bold")
    header_ax.text(0.18, 0.68, title, ha="left", va="center", color=PDF_THEME["header_text"], fontsize=15.5, fontweight="bold")
    if subtitle:
        header_ax.text(0.18, 0.34, subtitle, ha="left", va="center", color=PDF_THEME["subtle_text"], fontsize=8.8)
    header_ax.text(0.96, 0.60, page_label, ha="right", va="center", color=PDF_THEME["subtle_text"], fontsize=8.5)
    header_ax.plot([0.04, 0.96], [0.10, 0.10], color=PDF_THEME["border"], linewidth=0.8)


def _add_footer(fig: Any, generated_at: str) -> None:
    fig.text(0.04, 0.02, f"RiskLens Terminal · Generated {generated_at} · Confidential", fontsize=7.2, color=PDF_THEME["muted_text"])


def _new_figure(title: str, subtitle: str | None = None, page_label: str = "") -> Tuple[Any, Any]:
    fig = plt.figure(figsize=(PAGE_WIDTH_INCH, PAGE_HEIGHT_INCH))
    fig.patch.set_facecolor(PDF_THEME["page_bg"])
    _draw_brand_header(fig, title=title, subtitle=subtitle, page_label=page_label)
    ax = fig.add_axes([0.05, 0.08, 0.90, 0.80])
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


def _build_statement_rows(
    history: List[Dict[str, Any]],
    labels: Dict[str, str],
    total_cols: int,
    use_millions: bool,
    yoy_map: List[Dict[str, Any]],
) -> Tuple[List[List[str]], List[str]]:
    rows: List[List[str]] = []
    row_kinds: List[str] = []
    current_tab: str | None = None

    for tab, key in _ordered_statement_entries(history):
        if tab != current_tab:
            current_tab = tab
            rows.append([labels[STATEMENT_TAB_LABEL_KEYS[tab]]] + [""] * (total_cols - 1))
            row_kinds.append("section")

        row = [_prettify_key(key)]
        for period in history:
            raw_val = _statement_value_for_key(period, key)
            row.append(_format_million_value(raw_val) if use_millions else _format_statement_value(raw_val))
        if yoy_map:
            row.append("")
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
        rows.append(row)
        row_kinds.append("item")

    return rows, row_kinds


def _is_negative_display_value(text: str) -> bool:
    return text not in {"", "--"} and text.startswith("-")


def generate_full_pdf(report: Dict[str, Any], lang: str = "zh-CN") -> bytes:
    t = _localized_labels(lang)

    ticker = str(report.get("ticker") or "N/A")
    company_name = str(report.get("company_name") or ticker)
    currency = str(report.get("currency") or "USD")
    company_profile = report.get("company_profile") if isinstance(report.get("company_profile"), dict) else {}
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
    covenant_meta: List[Dict[str, Any]] = []
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
        covenant_meta.append({"status": status})

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

    def _format_currency_by_unit(value: float | None) -> str:
        if value is None:
            return "--"
        if use_millions:
            return f"{value / 1_000_000:,.1f}"
        return f"{value:,.2f}"

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
        if yoy_headers:
            row.append("")
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
                        row.append(_format_currency_by_unit(delta))
                    else:
                        row.append(_format_metric_value(delta, value_type, is_delta=True))
                    row.append(_format_metric_value(pct, "%"))
        kpi_rows.append(row)

    statement_rows_by_tab = {
        tab: _build_statement_rows_for_tab(history, tab, use_millions, yoy_map)
        for tab in STATEMENT_TABS_ORDER
    }
    statement_headers_by_tab = {
        tab: [t[STATEMENT_TAB_LABEL_KEYS[tab]]] + periods + ([""] if yoy_headers else []) + yoy_headers
        for tab in STATEMENT_TABS_ORDER
    }

    buffer = BytesIO()
    with PdfPages(buffer) as pdf:
        latest_period = _format_period_label(str(latest.get("fiscal_year", "N/A")))
        score = _safe_num((latest.get("assessment") or {}).get("risk_score"))
        z_zone = str((latest.get("assessment") or {}).get("overall_rating") or "N/A")
        rating = str((latest.get("assessment") or {}).get("implied_rating") or "N/A")
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows_per_page = 30
        statement_pages = sum(
            max(1, math.ceil(len(rows) / rows_per_page)) if rows else 1
            for rows in statement_rows_by_tab.values()
        )
        total_pages = 2 + statement_pages
        page_no = 1

        profile_items = _compact_profile_items(company_profile, t)
        unit_text = f"{t['figures_millions']} ({currency})" if use_millions else f"{t['figures_reported']} ({currency})"
        subtitle = " · ".join(part for part in [ticker, latest_period, unit_text] if part)
        fig, ax = _new_figure(title=company_name, subtitle=subtitle, page_label=f"Page {page_no}/{total_pages}")

        annual_count = sum(1 for period in history if not period.get("is_quarterly"))
        quarterly_count = len(history) - annual_count
        _draw_card(
            fig,
            [0.05, 0.80, 0.21, 0.09],
            "Altman Z-Score",
            "--" if score is None else f"{score:.2f}",
            subtitle=t["summary"],
            accent=PDF_THEME["accent_purple"],
            fill=PDF_THEME["panel_fill_alt"],
            value_size=18,
        )
        _draw_card(
            fig,
            [0.28, 0.80, 0.21, 0.09],
            t["zone"],
            z_zone,
            subtitle=t["summary"],
            accent=PDF_THEME["accent_blue"],
            fill="#eff6ff",
            value_size=16,
        )
        _draw_card(
            fig,
            [0.51, 0.80, 0.21, 0.09],
            t["implied_rating"],
            rating,
            subtitle=t["summary"],
            accent=PDF_THEME["accent_green"],
            fill="#ecfdf5",
            value_size=16,
        )
        _draw_card(
            fig,
            [0.74, 0.80, 0.21, 0.09],
            t["periods"],
            f"{len(history)}",
            subtitle=f"{quarterly_count} {t['quarterly']} · {annual_count} {t['annual']}",
            accent=PDF_THEME["accent_amber"],
            fill="#fff7ed",
            value_size=18,
        )

        _draw_info_strip(fig, [0.05, 0.71, 0.90, 0.06], profile_items)

        strengths_body = _format_bulleted_lines([str(item) for item in strength_items[:8]], wrap_width=40, max_lines=10)
        watch_body = _format_bulleted_lines([str(item) for item in watch_items[:8]], wrap_width=40, max_lines=10)
        _draw_panel(
            fig,
            [0.05, 0.48, 0.44, 0.18],
            t["strengths"],
            strengths_body,
            accent=PDF_THEME["accent_green"],
            fill="#ffffff",
        )
        _draw_panel(
            fig,
            [0.51, 0.48, 0.44, 0.18],
            t["watch"],
            watch_body,
            accent=PDF_THEME["accent_amber"],
            fill="#ffffff",
        )

        covenant_ax = fig.add_axes([0.05, 0.16, 0.90, 0.14 if profile_items else 0.18])
        covenant_ax.axis("off")
        covenant_table = covenant_ax.table(
            cellText=covenant_rows,
            colLabels=[t["metric"], t["actual"], t["threshold"], t["status"], t["signal"], t["notes"]],
            loc="upper left",
            cellLoc="left",
            bbox=[0.0, 0.0, 1.0, 1.0],
            colWidths=[0.24, 0.12, 0.12, 0.18, 0.10, 0.24],
        )
        _style_table(covenant_table, first_col_left=True, font_size=7.9, section_fill="#f3f4f6")
        for idx, meta in enumerate(covenant_meta, start=1):
            status = meta["status"]
            row_fill = PDF_THEME["positive_fill"]
            if "MISSING" in status:
                row_fill = PDF_THEME["warning_fill"]
            elif "BREACH" in status:
                row_fill = PDF_THEME["negative_fill"]
            for col in range(0, 6):
                cell = covenant_table[idx, col]
                cell.set_facecolor(row_fill if col != 3 else row_fill)
                if col == 3:
                    if "BREACH" in status:
                        cell.get_text().set_color(PDF_THEME["accent_red"])
                    elif "PASS" in status:
                        cell.get_text().set_color(PDF_THEME["accent_green"])
                    else:
                        cell.get_text().set_color(PDF_THEME["accent_amber"])

        ax.text(
            0.00,
            0.11,
            f"{t['data_quality']} · {t['breach']}: {breach_count} · {t['missing']}: {len(missing_items)}",
            transform=ax.transAxes,
            fontsize=8.2,
            color=PDF_THEME["subtle_text"],
        )
        if missing_items:
            ax.text(
                0.00,
                0.075,
                f"{t['missing']}: {', '.join(missing_items)}",
                transform=ax.transAxes,
                fontsize=7.9,
                color=PDF_THEME["accent_red"],
            )

        _add_footer(fig, generated_at)
        pdf.savefig(fig)
        plt.close(fig)
        page_no += 1

        fig, _ = _new_figure(
            title=f"{company_name} · {t['kpi_trends']}",
            subtitle=f"{t['historical_periods']} · {len(periods)} / {t['yoy_comparisons']} · {len(yoy_map)}",
            page_label=f"Page {page_no}/{total_pages}",
        )
        fig.text(0.05, 0.855, f"{t['historical_periods']} · {', '.join(periods[:6])}" if periods else t["no_data"], fontsize=8.0, color=PDF_THEME["subtle_text"])
        if yoy_map:
            yoy_desc = " · ".join(f"{cmp['yearCode']} vs {cmp['prevYearCode']}" for cmp in yoy_map)
            fig.text(0.05, 0.832, f"{t['yoy_comparisons']} · {yoy_desc}", fontsize=8.0, color=PDF_THEME["subtle_text"])
        kpi_ax = fig.add_axes([0.05, 0.10, 0.90, 0.72])
        kpi_ax.axis("off")
        kpi_table = kpi_ax.table(
            cellText=kpi_rows,
            colLabels=[t["metric"]] + periods + ([""] if yoy_headers else []) + yoy_headers,
            loc="upper left",
            cellLoc="right",
            bbox=[0.0, 0.0, 1.0, 1.0],
            colWidths=_build_col_widths(len([t["metric"]] + periods + ([""] if yoy_headers else []) + yoy_headers), 0.26),
        )
        _style_table(kpi_table, first_col_left=True, font_size=6.5 if len(periods) + len(yoy_headers) > 8 else 7.2, section_fill="#eef2ff")
        for col in range(1, 1 + len(periods)):
            for row in range(1, len(kpi_rows) + 1):
                kpi_table[row, col].set_facecolor("#f8fafc" if col % 2 else "#f1f5f9")
        if yoy_headers:
            spacer_col = 1 + len(periods)
            for row in range(0, len(kpi_rows) + 1):
                if (row, spacer_col) in kpi_table.get_celld():
                    kpi_table[row, spacer_col].set_facecolor("#ffffff")
                    kpi_table[row, spacer_col].get_text().set_text("")
            for col in range(spacer_col + 1, spacer_col + 1 + len(yoy_headers)):
                for row in range(1, len(kpi_rows) + 1):
                    kpi_table[row, col].set_facecolor("#eef2ff" if col % 2 else "#ecfdf5")
        for row_index, row in enumerate(kpi_rows, start=1):
            for col_index, cell_text in enumerate(row, start=0):
                cell = kpi_table[row_index, col_index]
                text = str(cell_text)
                if col_index == 0:
                    cell.get_text().set_color(PDF_THEME["header_text"])
                elif _is_negative_display_value(text):
                    cell.get_text().set_color(PDF_THEME["accent_red"])
                elif text not in {"--", ""}:
                    cell.get_text().set_color(PDF_THEME["header_text"])
        _add_footer(fig, generated_at)
        pdf.savefig(fig)
        plt.close(fig)
        page_no += 1

        for tab in STATEMENT_TABS_ORDER:
            statement_rows = statement_rows_by_tab[tab]
            statement_headers = statement_headers_by_tab[tab]
            statement_title = t[STATEMENT_TAB_LABEL_KEYS[tab]]
            title_prefix = f"{company_name} · {statement_title}"
            statement_page_rows = max(1, math.ceil(len(statement_rows) / rows_per_page)) if statement_rows else 1

            if not statement_rows:
                fig, ax = _new_figure(
                    title=title_prefix,
                    subtitle=unit_text,
                    page_label=f"Page {page_no}/{total_pages}",
                )
                ax.text(0.00, 0.90, t["no_data"], transform=ax.transAxes, fontsize=10, color=PDF_THEME["subtle_text"])
                _add_footer(fig, generated_at)
                pdf.savefig(fig)
                plt.close(fig)
                page_no += 1
                continue

            for start in range(0, len(statement_rows), rows_per_page):
                chunk_rows = statement_rows[start:start + rows_per_page]
                chunk_index = (start // rows_per_page) + 1
                subtitle = f"{unit_text} · {t['historical_periods']}: {len(periods)} · {t['yoy_comparisons']}: {len(yoy_map)}"
                fig, _ = _new_figure(
                    title=title_prefix,
                    subtitle=subtitle,
                    page_label=f"Page {page_no}/{total_pages}",
                )
                fig.text(0.05, 0.855, f"{t['historical_periods']} · {', '.join(periods)}" if periods else t["no_data"], fontsize=8.0, color=PDF_THEME["subtle_text"])
                if yoy_map:
                    yoy_desc = " · ".join(f"{cmp['yearCode']} vs {cmp['prevYearCode']}" for cmp in yoy_map)
                    fig.text(0.05, 0.832, f"{t['yoy_comparisons']} · {yoy_desc}", fontsize=8.0, color=PDF_THEME["subtle_text"])
                if statement_page_rows > 1:
                    fig.text(0.90, 0.832, f"{chunk_index}/{statement_page_rows}", ha="right", fontsize=7.5, color=PDF_THEME["muted_text"])

                stmt_ax = fig.add_axes([0.04, 0.10, 0.92, 0.72])
                stmt_ax.axis("off")
                stmt_table = stmt_ax.table(
                    cellText=chunk_rows,
                    colLabels=statement_headers,
                    loc="upper left",
                    cellLoc="right",
                    bbox=[0.0, 0.0, 1.0, 1.0],
                    colWidths=_build_col_widths(len(statement_headers), 0.34),
                )
                font_size = 6.0 if len(statement_headers) >= 10 else 6.8
                _style_table(stmt_table, first_col_left=True, font_size=font_size, section_fill="#dbeafe")
                for col in range(1, 1 + len(periods)):
                    for row in range(1, len(chunk_rows) + 1):
                        stmt_table[row, col].set_facecolor("#f8fafc" if col % 2 else "#eef2ff")
                if yoy_headers:
                    spacer_col = 1 + len(periods)
                    for row in range(0, len(chunk_rows) + 1):
                        if (row, spacer_col) in stmt_table.get_celld():
                            stmt_table[row, spacer_col].set_facecolor("#ffffff")
                            stmt_table[row, spacer_col].get_text().set_text("")
                    for col in range(spacer_col + 1, spacer_col + 1 + len(yoy_headers)):
                        for row in range(1, len(chunk_rows) + 1):
                            stmt_table[row, col].set_facecolor("#eef2ff" if col % 2 else "#f1f5f9")
                for row_index, row in enumerate(chunk_rows, start=1):
                    for col_index, cell_text in enumerate(row, start=0):
                        cell = stmt_table[row_index, col_index]
                        text = str(cell_text)
                        if col_index == 0:
                            cell.get_text().set_color(PDF_THEME["header_text"])
                        elif _is_negative_display_value(text):
                            cell.get_text().set_color(PDF_THEME["accent_red"])
                        elif text not in {"--", ""}:
                            cell.get_text().set_color(PDF_THEME["header_text"])
                _add_footer(fig, generated_at)
                pdf.savefig(fig)
                plt.close(fig)
                page_no += 1

    return buffer.getvalue()
