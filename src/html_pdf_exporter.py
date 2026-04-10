from __future__ import annotations

import asyncio
import html as html_lib
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / 'templates' / 'pdf_report.html'

LANG = {
    'en': {
        'report_title': 'RiskLens Financial Report',
        'executive_summary': 'Executive Summary',
        'company_profile': 'Company Profile',
        'latest_period': 'Latest Period',
        'currency': 'Currency',
        'generated_at': 'Generated At',
        'strengths': 'Strengths',
        'watch_items': 'Watch Items',
        'covenant_pre_check': 'Covenant Pre-Check',
        'data_quality': 'Data Quality',
        'kpi_trends': 'KPI Trends',
        'financial_statements': 'Financial Statements',
        'income_statement': 'Income Statement',
        'balance_sheet': 'Balance Sheet',
        'cash_flow_statement': 'Cash Flow Statement',
        'metric': 'Metric',
        'actual': 'Actual',
        'threshold': 'Threshold',
        'status': 'Status',
        'signal': 'Signal',
        'notes': 'Notes',
        'yoy': 'YoY',
        'no_data': 'No data available',
        'altman_z_score': 'Altman Z-Score',
        'zone': 'Zone',
        'implied_rating': 'Implied Rating',
    },
    'zh-CN': {
        'report_title': 'RiskLens 风险分析报告',
        'executive_summary': '执行摘要',
        'company_profile': '公司概况',
        'latest_period': '最新期间',
        'currency': '币种',
        'generated_at': '生成时间',
        'strengths': '优势',
        'watch_items': '关注项',
        'covenant_pre_check': '契约预检',
        'data_quality': '数据质量',
        'kpi_trends': '核心指标趋势',
        'financial_statements': '财务报表',
        'income_statement': '利润表',
        'balance_sheet': '资产负债表',
        'cash_flow_statement': '现金流量表',
        'metric': '指标',
        'actual': '实际值',
        'threshold': '阈值',
        'status': '状态',
        'signal': '信号',
        'notes': '备注',
        'yoy': '同比',
        'no_data': '暂无数据',
        'altman_z_score': 'Altman Z 分数',
        'zone': '区间',
        'implied_rating': '隐含评级',
    },
    'zh-TW': {
        'report_title': 'RiskLens 風險分析報告',
        'executive_summary': '執行摘要',
        'company_profile': '公司概況',
        'latest_period': '最新期間',
        'currency': '幣別',
        'generated_at': '產生時間',
        'strengths': '優勢',
        'watch_items': '關注項',
        'covenant_pre_check': '契約預檢',
        'data_quality': '資料品質',
        'kpi_trends': '核心指標趨勢',
        'financial_statements': '財務報表',
        'income_statement': '損益表',
        'balance_sheet': '資產負債表',
        'cash_flow_statement': '現金流量表',
        'metric': '指標',
        'actual': '實際值',
        'threshold': '門檻',
        'status': '狀態',
        'signal': '訊號',
        'notes': '備註',
        'yoy': '年增率',
        'no_data': '暫無資料',
        'altman_z_score': 'Altman Z 分數',
        'zone': '區間',
        'implied_rating': '隱含評等',
    },
    'ja': {
        'report_title': 'RiskLens 財務レポート',
        'executive_summary': 'エグゼクティブサマリー',
        'company_profile': '会社概要',
        'latest_period': '最新期間',
        'currency': '通貨',
        'generated_at': '生成日時',
        'strengths': '強み',
        'watch_items': '注意項目',
        'covenant_pre_check': 'コベナント事前確認',
        'data_quality': 'データ品質',
        'kpi_trends': 'KPIトレンド',
        'financial_statements': '財務諸表',
        'income_statement': '損益計算書',
        'balance_sheet': '貸借対照表',
        'cash_flow_statement': 'キャッシュフロー計算書',
        'metric': '指標',
        'actual': '実績',
        'threshold': '基準',
        'status': '状態',
        'signal': 'シグナル',
        'notes': '注記',
        'yoy': '前年差',
        'no_data': 'データなし',
        'altman_z_score': 'Altman Zスコア',
        'zone': 'ゾーン',
        'implied_rating': '推定格付け',
    },
}

KPI_SPECS = [
    ('EBIT', ('ebit',)),
    ('EBITDA', ('ebitda',)),
    ('Total Debt', ('total_debt', 'gross_debt', 'debt_total')),
    ('Debt / EBITDA', ('debt_ebitda', 'debt_to_ebitda')),
    ('Interest Coverage', ('interest_coverage', 'ebit_interest_coverage')),
    ('Free CF', ('free_cash_flow', 'fcf')),
    ('FCF / Debt', ('fcf_debt',)),
    ('Current Ratio', ('current_ratio',)),
]

STATEMENT_KEYS = [
    ('income_statement', 'Income Statement', ('income', 'pnl', 'profit_and_loss')),
    ('balance_sheet', 'Balance Sheet', ('bs', 'statement_of_financial_position')),
    ('cash_flow_statement', 'Cash Flow Statement', ('cash_flow', 'cashflow', 'cf')),
]


def _lang(lang: str | None) -> str:
    if lang in LANG:
        return lang or 'en'
    return 'en'


def _t(lang: str, key: str) -> str:
    return LANG.get(lang, LANG['en']).get(key, key)


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _normalize_key(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', value.lower())


def _safe_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text or text in {'--', '-', 'n/a', 'N/A'}:
            return None
        negative = text.startswith('(') and text.endswith(')')
        text = text.strip('()').replace(',', '').replace('%', '')
        try:
            number = float(text)
        except ValueError:
            return None
        return -number if negative else number
    return None


def _is_negative_display_value(value: Any) -> bool:
    number = _safe_number(value)
    return bool(number is not None and number < 0)


def _format_number(value: Any, decimals: int = 1, signed: bool = False, suffix: str = '') -> str:
    number = _safe_number(value)
    if number is None:
        return '--' if value is None else str(value)
    if float(number).is_integer():
        text = f'{number:,.0f}'
    else:
        text = f'{number:,.{decimals}f}'
    if signed and number >= 0:
        text = '+' + text
    return text + suffix


def _format_value(value: Any) -> str:
    if value is None:
        return '--'
    if isinstance(value, str):
        return value.strip() or '--'
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    number = _safe_number(value)
    if number is None:
        return str(value)
    if abs(number) >= 1000 or float(number).is_integer():
        return f'{number:,.0f}'
    return f'{number:,.2f}'


def _period_key(label: str | None) -> tuple[int, int, int]:
    if not label:
        return (0, 0, 0)
    text = str(label).upper()
    quarter = re.match(r'^(?:FY)?(?P<year>\d{2,4})Q(?P<quarter>[1-4])$', text)
    if quarter:
        year = int(quarter.group('year'))
        if year < 100:
            year += 2000
        return (year, int(quarter.group('quarter')), 1)
    annual = re.match(r'^FY(?P<year>\d{2,4})$', text)
    if annual:
        year = int(annual.group('year'))
        if year < 100:
            year += 2000
        return (year, 4, 0)
    return (0, 0, 0)


def _format_period_label(label: str | None) -> str:
    if not label:
        return '--'
    text = str(label).strip().upper()
    quarter = re.match(r'^(?P<year>\d{2,4})Q(?P<quarter>[1-4])$', text)
    if quarter:
        return f"Q{quarter.group('quarter')} FY{quarter.group('year')}"
    annual = re.match(r'^FY(?P<year>\d{2,4})$', text)
    if annual:
        return f"FY{annual.group('year')}"
    return str(label)


def _build_yoy_map(periods: list[str]) -> dict[str, str]:
    available = {str(p).upper() for p in periods if p}
    mapping: dict[str, str] = {}
    for period in periods:
        if not period:
            continue
        key = str(period).upper()
        if m := re.match(r'^(?:FY)?(?P<year>\d{2,4})Q(?P<quarter>[1-4])$', key):
            year = int(m.group('year'))
            if year < 100:
                year += 2000
            prev = f'{(year - 1) % 100:02d}Q{m.group("quarter")}'
            alt = f'{year - 1}Q{m.group("quarter")}'
            if prev in available:
                mapping[key] = prev
            elif alt in available:
                mapping[key] = alt
        elif m := re.match(r'^FY(?P<year>\d{2,4})$', key):
            year = int(m.group('year'))
            if year < 100:
                year += 2000
            prev = f'FY{(year - 1) % 100:02d}'
            alt = f'FY{year - 1}'
            if prev in available:
                mapping[key] = prev
            elif alt in available:
                mapping[key] = alt
    return mapping


def _pick(source: dict[str, Any], candidates: tuple[str, ...]) -> Any:
    if not isinstance(source, dict):
        return None
    flat = {_normalize_key(str(k)): v for k, v in source.items()}
    for candidate in candidates:
        key = _normalize_key(candidate)
        if key in flat:
            return flat[key]
    for candidate in candidates:
        key = _normalize_key(candidate)
        for source_key, value in source.items():
            norm = _normalize_key(str(source_key))
            if key in norm or norm in key:
                return value
    return None


def _extract_history(report: dict[str, Any]) -> list[dict[str, Any]]:
    history = report.get('history') or report.get('histories') or []
    entries = [item for item in history if isinstance(item, dict)]
    entries.sort(key=lambda item: _period_key(str(item.get('fiscal_year') or item.get('period') or item.get('label') or '')), reverse=True)
    return entries


def _extract_texts(value: Any) -> list[str]:
    items: list[str] = []
    for item in _sequence(value):
        if isinstance(item, str):
            text = item.strip()
            if text:
                items.append(text)
        elif isinstance(item, dict):
            text = item.get('text') or item.get('label') or item.get('name') or item.get('value')
            if text is not None:
                text = str(text).strip()
                if text:
                    items.append(text)
        elif item is not None:
            text = str(item).strip()
            if text:
                items.append(text)
    return items


def _extract_summary(entry: dict[str, Any]) -> dict[str, Any]:
    assessment = _mapping(entry.get('assessment'))
    strengths = _extract_texts(assessment.get('strengths') or entry.get('strengths'))
    watch_items = _extract_texts(assessment.get('watch_items') or assessment.get('concerns') or entry.get('watch_items') or entry.get('concerns') or entry.get('risks'))
    covenant_rows: list[dict[str, str]] = []
    for item in _sequence(assessment.get('covenant_pre_check') or assessment.get('covenants') or entry.get('covenant_pre_check') or entry.get('covenants')):
        if isinstance(item, dict):
            covenant_rows.append({
                'metric': str(item.get('metric') or item.get('label') or item.get('name') or '--'),
                'actual': _format_value(item.get('actual') or item.get('value')),
                'threshold': _format_value(item.get('threshold') or item.get('limit') or item.get('target')),
                'status': str(item.get('status') or item.get('result') or '--'),
                'signal': str(item.get('signal') or item.get('direction') or '--'),
                'notes': str(item.get('notes') or item.get('note') or '--'),
            })
    data_quality: list[dict[str, str]] = []
    raw_quality = assessment.get('data_quality') or entry.get('data_quality') or entry.get('quality') or {}
    if isinstance(raw_quality, dict):
        for key, value in raw_quality.items():
            if isinstance(value, dict):
                data_quality.append({'label': str(value.get('label') or key), 'value': _format_value(value.get('value') or value.get('score') or value.get('status')), 'notes': str(value.get('notes') or value.get('note') or '--')})
            else:
                data_quality.append({'label': str(key), 'value': _format_value(value), 'notes': '--'})
    elif isinstance(raw_quality, list):
        for item in raw_quality:
            if isinstance(item, dict):
                data_quality.append({'label': str(item.get('label') or item.get('name') or '--'), 'value': _format_value(item.get('value') or item.get('score') or item.get('status')), 'notes': str(item.get('notes') or item.get('note') or '--')})
    if not data_quality:
        data_quality.append({'label': 'Coverage', 'value': '--', 'notes': '--'})

    return {
        'altman_z_score': _pick(assessment, ('altman_z_score', 'altman_score', 'z_score')),
        'zone': _pick(assessment, ('altman_zone', 'zone', 'risk_zone')),
        'implied_rating': _pick(assessment, ('implied_rating', 'rating', 'credit_rating')),
        'strengths': strengths,
        'watch_items': watch_items,
        'covenant_rows': covenant_rows,
        'data_quality': data_quality,
    }


def _extract_profile(report: dict[str, Any], latest: dict[str, Any]) -> list[dict[str, str]]:
    profile = report.get('company_profile') or latest.get('company_profile') or {}
    rows: list[dict[str, str]] = []
    if isinstance(profile, dict):
        for key, value in profile.items():
            if isinstance(value, dict):
                value = value.get('value') or value.get('text') or value.get('name') or '--'
            rows.append({'label': str(key), 'value': _format_value(value)})
    if not rows:
        rows.append({'label': 'Overview', 'value': '--'})
    return rows


def _extract_metric_value(entry: dict[str, Any], candidates: tuple[str, ...]) -> Any:
    for key in ('raw_metrics', 'ratios', 'metrics', 'assessment'):
        value = entry.get(key)
        if isinstance(value, dict):
            picked = _pick(value, candidates)
            if picked is not None:
                return picked
    return _pick(entry, candidates)


def _build_kpi_rows(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, candidates in KPI_SPECS:
        values = [_extract_metric_value(entry, candidates) for entry in history]
        yoy = '--'
        if len(values) > 1:
            current, previous = _safe_number(values[0]), _safe_number(values[1])
            if current is not None and previous is not None:
                if previous == 0:
                    yoy = _format_number(current - previous, signed=True)
                else:
                    yoy = _format_number((current - previous) / abs(previous) * 100, signed=True, suffix='%')
        rows.append({'label': label, 'values': [_format_value(v) for v in values], 'yoy': yoy})
    return rows


def _normalize_statement_rows(raw: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if raw is None:
        return rows
    if isinstance(raw, dict):
        if any(isinstance(v, (dict, list, tuple)) for v in raw.values()):
            for key in ('items', 'rows', 'line_items', 'data'):
                if key in raw:
                    return _normalize_statement_rows(raw[key])
        for key, value in raw.items():
            rows.append({'label': str(key), 'value': value})
        return rows
    for item in _sequence(raw):
        if isinstance(item, dict):
            label = item.get('label') or item.get('name') or item.get('metric') or item.get('line_item') or item.get('account')
            if label is None and len(item) == 1:
                k, v = next(iter(item.items()))
                rows.append({'label': str(k), 'value': v})
            else:
                rows.append({'label': str(label or '--'), 'value': item.get('value', item.get('amount', item.get('balance', item.get('text'))))})
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            rows.append({'label': str(item[0]), 'value': item[1]})
        elif item is not None:
            rows.append({'label': str(item), 'value': '--'})
    return rows


def _extract_statement_block(entry: dict[str, Any], statement_key: str, aliases: tuple[str, ...]) -> list[dict[str, Any]]:
    candidates = [entry.get('statements'), entry.get('financial_statements'), entry.get('statement_data')]
    alias_norms = {_normalize_key(alias) for alias in (statement_key, *aliases)}
    for candidate in candidates:
        if isinstance(candidate, dict):
            for alias in (statement_key, *aliases):
                if alias in candidate:
                    return _normalize_statement_rows(candidate[alias])
            for key, value in candidate.items():
                if _normalize_key(str(key)) in alias_norms:
                    return _normalize_statement_rows(value)
        elif isinstance(candidate, list):
            for item in candidate:
                if isinstance(item, dict):
                    name = item.get('statement') or item.get('type') or item.get('name')
                    if name and _normalize_key(str(name)) in alias_norms:
                        return _normalize_statement_rows(item.get('items') or item.get('rows') or item.get('data') or item)
    return []


def _build_statement_sections(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    periods = [str(entry.get('fiscal_year') or entry.get('period') or entry.get('label') or '--') for entry in history]
    sections: list[dict[str, Any]] = []
    for statement_key, title_key, aliases in STATEMENT_KEYS:
        labels: list[str] = []
        rows_by_period: list[list[dict[str, Any]]] = []
        for entry in history:
            rows = _extract_statement_block(entry, statement_key, aliases)
            rows_by_period.append(rows)
            for row in rows:
                label = str(row.get('label') or '--')
                if label not in labels:
                    labels.append(label)
        normalized_rows: list[dict[str, Any]] = []
        for label in labels:
            values: list[Any] = []
            for rows in rows_by_period:
                matched = next((row.get('value') for row in rows if str(row.get('label') or '--') == label), None)
                values.append(matched)
            yoy = '--'
            if len(values) > 1:
                current, previous = _safe_number(values[0]), _safe_number(values[1])
                if current is not None and previous is not None:
                    if previous == 0:
                        yoy = _format_number(current - previous, signed=True)
                    else:
                        yoy = _format_number((current - previous) / abs(previous) * 100, signed=True, suffix='%')
            normalized_rows.append({'label': label, 'values': [_format_value(v) for v in values], 'yoy': yoy})
        sections.append({'key': statement_key, 'title': title_key, 'periods': [_format_period_label(p) for p in periods], 'rows': normalized_rows})
    return sections


def build_pdf_context(report: dict[str, Any], lang: str = 'en') -> dict[str, Any]:
    lang = _lang(lang)
    history = _extract_history(report)
    if not history:
        history = [{}]
    latest = history[0]
    periods = [str(entry.get('fiscal_year') or entry.get('period') or entry.get('label') or '--') for entry in history]
    summary = _extract_summary(latest)
    return {
        'lang': lang,
        'labels': LANG[lang],
        'report_title': _t(lang, 'report_title'),
        'company_name': str(report.get('company_name') or latest.get('company_name') or latest.get('name') or 'Unknown Company'),
        'company_name_localized': str(report.get('company_name_localized') or latest.get('company_name_localized') or report.get('company_name') or latest.get('company_name') or 'Unknown Company'),
        'ticker': str(report.get('ticker') or latest.get('ticker') or '--'),
        'currency': str(report.get('currency') or latest.get('currency') or latest.get('reporting_currency') or '--'),
        'latest_period': _format_period_label(periods[0]),
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'periods': [{'raw': p, 'label': _format_period_label(p)} for p in periods],
        'summary_cards': [
            {'label': _t(lang, 'altman_z_score'), 'value': _format_value(summary['altman_z_score'])},
            {'label': _t(lang, 'zone'), 'value': _format_value(summary['zone'])},
            {'label': _t(lang, 'implied_rating'), 'value': _format_value(summary['implied_rating'])},
        ],
        'company_profile_rows': _extract_profile(report, latest),
        'strengths': summary['strengths'],
        'watch_items': summary['watch_items'],
        'covenant_rows': summary['covenant_rows'],
        'data_quality_rows': summary['data_quality'],
        'kpi_rows': _build_kpi_rows(history),
        'statement_sections': _build_statement_sections(history),
    }


def _render_html_fallback(ctx: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html_lib.escape(str(value))

    summary_cards = ''.join(f'<div class="summary-card"><div class="summary-label">{esc(card["label"])}</div><div class="summary-value">{esc(card["value"])}</div></div>' for card in ctx['summary_cards'])
    profile = ''.join(f'<tr><td>{esc(row["label"])}</td><td>{esc(row["value"])}</td></tr>' for row in ctx['company_profile_rows'])
    strengths = ''.join(f'<li>{esc(item)}</li>' for item in ctx['strengths']) or '<li>--</li>'
    watches = ''.join(f'<li>{esc(item)}</li>' for item in ctx['watch_items']) or '<li>--</li>'
    covenant = ''.join(f'<tr><td>{esc(row["metric"])}</td><td>{esc(row["actual"])}</td><td>{esc(row["threshold"])}</td><td>{esc(row["status"])}</td><td>{esc(row["signal"])}</td><td>{esc(row["notes"])}</td></tr>' for row in ctx['covenant_rows']) or '<tr><td colspan="6">--</td></tr>'
    quality = ''.join(f'<tr><td>{esc(row["label"])}</td><td>{esc(row["value"])}</td><td>{esc(row["notes"])}</td></tr>' for row in ctx['data_quality_rows']) or '<tr><td colspan="3">--</td></tr>'
    kpi_rows = ''.join('<tr><td class="item">%s</td>%s<td>%s</td></tr>' % (esc(row['label']), ''.join(f'<td>{esc(v)}</td>' for v in row['values']), esc(row['yoy'])) for row in ctx['kpi_rows']) or '<tr><td colspan="10">--</td></tr>'
    statement_pages = []
    for section in ctx['statement_sections']:
        rows = ''.join('<tr><td class="item">%s</td>%s<td>%s</td></tr>' % (esc(row['label']), ''.join(f'<td>{esc(v)}</td>' for v in row['values']), esc(row['yoy'])) for row in section['rows']) or '<tr><td colspan="10">--</td></tr>'
        statement_pages.append(f'''
        <section class="page statement-section">
          <div class="section-head"><h2 class="section-title">{esc(_t(ctx['lang'], section['title']))}</h2><span class="section-badge">{esc(section['periods'][0] if section['periods'] else ctx['latest_period'])}</span></div>
          <table class="statement-table">
            <thead><tr><th>{_t(ctx['lang'], 'metric')}</th>{''.join(f'<th>{esc(p)}</th>' for p in section['periods'])}<th>{_t(ctx['lang'], 'yoy')}</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </section>''')
    return f'''
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        @page {{ size: A4 landscape; margin: 12mm; }}
        body {{ font-family: Arial, "Noto Sans SC", sans-serif; background: #f8f6ff; color: #1f2430; }}
        .page {{ page-break-after: always; }}
        .hero {{ background: linear-gradient(135deg, #2e1065, #5b21b6); color: #fff; border-radius: 18px; padding: 18px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 12px; }}
        .summary-card, .panel {{ background: #fff; border: 1px solid #d9d7ea; border-radius: 14px; padding: 12px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 10px; }}
        th, td {{ border-bottom: 1px solid #d9d7ea; padding: 6px 8px; }}
        th {{ background: #f4f0ff; text-align: left; }}
      </style>
    </head>
    <body>
      <section class="page">
        <div class="hero"><h1>{esc(ctx['company_name'])}</h1><div>{esc(ctx['ticker'])} · {esc(ctx['latest_period'])} · {esc(ctx['currency'])}</div></div>
        <div class="summary-grid">{summary_cards}</div>
        <div class="panel"><h2>{_t(ctx['lang'], 'company_profile')}</h2><table><tbody>{profile}</tbody></table></div>
        <div class="panel"><h2>{_t(ctx['lang'], 'strengths')}</h2><ul>{strengths}</ul><h2>{_t(ctx['lang'], 'watch_items')}</h2><ul>{watches}</ul></div>
        <div class="panel"><h2>{_t(ctx['lang'], 'covenant_pre_check')}</h2><table><thead><tr><th>{_t(ctx['lang'], 'metric')}</th><th>{_t(ctx['lang'], 'actual')}</th><th>{_t(ctx['lang'], 'threshold')}</th><th>{_t(ctx['lang'], 'status')}</th><th>{_t(ctx['lang'], 'signal')}</th><th>{_t(ctx['lang'], 'notes')}</th></tr></thead><tbody>{covenant}</tbody></table></div>
        <div class="panel"><h2>{_t(ctx['lang'], 'data_quality')}</h2><table><thead><tr><th>{_t(ctx['lang'], 'metric')}</th><th>{_t(ctx['lang'], 'actual')}</th><th>{_t(ctx['lang'], 'notes')}</th></tr></thead><tbody>{quality}</tbody></table></div>
      </section>
      <section class="page"><div class="panel"><h2>{_t(ctx['lang'], 'kpi_trends')}</h2><table><thead><tr><th>{_t(ctx['lang'], 'metric')}</th>{''.join(f'<th>{esc(p["label"])}</th>' for p in ctx['periods'])}<th>{_t(ctx['lang'], 'yoy')}</th></tr></thead><tbody>{kpi_rows}</tbody></table></div></section>
      {''.join(statement_pages)}
    </body></html>
    '''


def render_pdf_html(report: dict[str, Any], lang: str = 'en') -> str:
    ctx = build_pdf_context(report, lang)
    if TEMPLATE_PATH.exists():
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape  # type: ignore

            env = Environment(
                loader=FileSystemLoader(str(TEMPLATE_PATH.parent)),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True,
            )
            return env.get_template(TEMPLATE_PATH.name).render(**ctx)
        except Exception:
            pass
    return _render_html_fallback(ctx)


def _pdf_escape(text: str) -> str:
    return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _context_pages(ctx: dict[str, Any]) -> list[list[str]]:
    pages: list[list[str]] = []
    summary = [f"{card['label']}: {card['value']}" for card in ctx['summary_cards']]
    profile = [f"{row['label']}: {row['value']}" for row in ctx['company_profile_rows']]
    strengths = [f"+ {item}" for item in ctx['strengths']] or ['+ --']
    watches = [f"! {item}" for item in ctx['watch_items']] or ['! --']
    covenant = [f"{r['metric']} | {r['actual']} | {r['threshold']} | {r['status']} | {r['signal']} | {r['notes']}" for r in ctx['covenant_rows']] or ['--']
    quality = [f"{r['label']} | {r['value']} | {r['notes']}" for r in ctx['data_quality_rows']] or ['--']
    pages.append([
        ctx['report_title'],
        f"{ctx['company_name']} ({ctx['ticker']})",
        f"{ctx['latest_period']} | {ctx['currency']} | {ctx['generated_at']}",
        '',
        *summary,
        '',
        *profile,
        '',
        *strengths,
        '',
        *watches,
        '',
        *covenant,
        '',
        *quality,
    ])
    pages.append([
        ctx['labels']['kpi_trends'],
        *[p['label'] for p in ctx['periods']],
        '',
        *[f"{row['label']} | {' | '.join(row['values'])} | YoY {row['yoy']}" for row in ctx['kpi_rows']],
    ])
    for section in ctx['statement_sections']:
        pages.append([
            section['title'],
            *section['periods'],
            '',
            *[f"{row['label']} | {' | '.join(row['values'])} | YoY {row['yoy']}" for row in section['rows']],
        ])
    appendix = [
        'Data Appendix',
        f"Periods: {', '.join(ctx['periods'][i]['label'] for i in range(len(ctx['periods'])))}",
        f"YoY map: {ctx['labels']['yoy']} => {', '.join(f'{k}:{v}' for k, v in _build_yoy_map([p['raw'] for p in ctx['periods']]).items()) or '--'}",
        '',
        'KPI Detail',
        *[f"{row['label']} | {' | '.join(row['values'])} | YoY {row['yoy']}" for row in ctx['kpi_rows']],
        '',
        'Statement Detail',
        *[
            line
            for section in ctx['statement_sections']
            for line in ([section['title'], *section['periods']] + [f"{row['label']} | {' | '.join(row['values'])} | YoY {row['yoy']}" for row in section['rows']])
        ],
    ]
    pages.append(appendix)
    detail = [
        'Fallback Detail Snapshot',
        *[f"{row['label']} | {' | '.join(row['values'])} | YoY {row['yoy']}" for row in ctx['kpi_rows']],
        '',
        *[
            f"{section['title']} :: {row['label']} | {' | '.join(row['values'])} | YoY {row['yoy']}"
            for section in ctx['statement_sections']
            for row in section['rows']
        ],
        '',
        *[f"PROFILE {row['label']} = {row['value']}" for row in ctx['company_profile_rows']],
        *[f"COVENANT {row['metric']} => {row['actual']} / {row['threshold']} / {row['status']} / {row['signal']} / {row['notes']}" for row in ctx['covenant_rows']],
        *[f"QUALITY {row['label']} => {row['value']} / {row['notes']}" for row in ctx['data_quality_rows']],
    ]
    pages.append(detail)
    verbose = [
        'Verbose Detail',
        *[f"VERBOSE KPI {row['label']} :: {' | '.join(row['values'])} :: YoY {row['yoy']}" for row in ctx['kpi_rows']],
        *[
            f"VERBOSE STATEMENT {section['title']} :: {row['label']} :: {' | '.join(row['values'])} :: YoY {row['yoy']}"
            for section in ctx['statement_sections']
            for row in section['rows']
        ],
        *[f"VERBOSE PROFILE {row['label']} = {row['value']}" for row in ctx['company_profile_rows']],
        *[f"VERBOSE COVENANT {row['metric']} = {row['actual']} | {row['threshold']} | {row['status']} | {row['signal']} | {row['notes']}" for row in ctx['covenant_rows']],
        *[f"VERBOSE QUALITY {row['label']} = {row['value']} | {row['notes']}" for row in ctx['data_quality_rows']],
    ]
    pages.append(verbose)
    return pages


def _simple_pdf(pages: list[list[str]], width: int = 842, height: int = 595) -> bytes:
    objects: list[bytes] = []
    page_entries: list[tuple[int, int, bytes]] = []
    next_obj = 4
    for page in pages:
        lines: list[str] = ['BT', '/F1 10 Tf']
        y = height - 36
        for line in page:
            if not str(line).strip():
                y -= 12
                continue
            lines.append(f'1 0 0 1 36 {y:.2f} Tm ({_pdf_escape(str(line))}) Tj')
            y -= 12
            if y < 36:
                break
        lines.append('ET')
        content = '\n'.join(lines).encode('latin-1', 'replace')
        page_entries.append((next_obj, next_obj + 1, content))
        next_obj += 2
    out = bytearray(b'%PDF-1.4\n')
    offsets = [0]

    def emit(obj_num: int, payload: bytes) -> None:
        offsets.append(len(out))
        out.extend(f'{obj_num} 0 obj\n'.encode('ascii'))
        out.extend(payload)
        out.extend(b'\nendobj\n')

    kids = ' '.join(f'{page_obj} 0 R' for page_obj, _, _ in page_entries)
    emit(1, b'<< /Type /Catalog /Pages 2 0 R >>')
    emit(2, f'<< /Type /Pages /Kids [{kids}] /Count {len(page_entries)} >>'.encode('ascii'))
    emit(3, b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    for page_obj, content_obj, content in page_entries:
        emit(content_obj, b'<< /Length ' + str(len(content)).encode('ascii') + b' >>\nstream\n' + content + b'\nendstream')
        emit(page_obj, f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj} 0 R >>'.encode('ascii'))
    xref = len(out)
    out.extend(f'xref\n0 {len(offsets)}\n'.encode('ascii'))
    out.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        out.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))
    out.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode('ascii'))
    return bytes(out)


async def _render_html_to_pdf_bytes(html_text: str, context: dict[str, Any] | None = None) -> bytes:
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except Exception:
        return _simple_pdf(_context_pages(context or {}))
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                page = await browser.new_page(viewport={'width': 1600, 'height': 1200})
                await page.set_content(html_text, wait_until='networkidle')
                await page.emulate_media(media='print')
                return await page.pdf(format='A4', landscape=True, print_background=True, prefer_css_page_size=True, margin={'top': '12mm', 'right': '12mm', 'bottom': '12mm', 'left': '12mm'})
            finally:
                await browser.close()
    except Exception:
        return _simple_pdf(_context_pages(context or {}))


async def generate_full_pdf_async(report: dict[str, Any], lang: str = 'en') -> bytes:
    ctx = build_pdf_context(report, lang)
    return await _render_html_to_pdf_bytes(render_pdf_html(report, lang), ctx)


def _run_sync(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}
    error: list[BaseException] = []

    def runner() -> None:
        try:
            result['value'] = asyncio.run(coro)
        except BaseException as exc:  # pragma: no cover - defensive
            error.append(exc)

    thread = Thread(target=runner, daemon=True)
    thread.start()
    thread.join()
    if error:
        raise error[0]
    return result['value']


def generate_full_pdf(report: dict[str, Any], lang: str = 'en') -> bytes:
    return _run_sync(generate_full_pdf_async(report, lang))


__all__ = [
    'build_pdf_context',
    'generate_full_pdf',
    'generate_full_pdf_async',
    'render_pdf_html',
    '_build_yoy_map',
    '_format_period_label',
    '_is_negative_display_value',
]
