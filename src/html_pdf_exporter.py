from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

LANG = {
    'en': {
        'report_title': 'RiskLens Financial Report',
        'credit_health_summary': 'Credit Health Summary',
        'executive_summary': 'Executive Summary',
        'company_profile': 'Company Profile',
        'key_risk_profile': 'Key Risk Profile',
        'latest_period': 'Latest Period',
        'currency': 'Currency',
        'generated_at': 'Generated At',
        'strengths': 'Strengths',
        'watch_items': 'Watch Items',
        'watch_items_none': 'No significant watch items',
        'covenant_pre_check': 'Covenant Pre-Check',
        'data_quality': 'Data Quality',
        'kpi_trends': 'KPI Trends',
        'financial_statements': 'Financial Statements',
        'contents': 'Contents',
        'income_statement': 'Income Statement',
        'balance_sheet': 'Balance Sheet',
        'cash_flow_statement': 'Cash Flow Statement',
        'metric': 'Metric',
        'actual': 'Actual',
        'threshold': 'Threshold',
        'status': 'Status',
        'status_signal': 'Status / Signal',
        'signal': 'Signal',
        'indicator_description': 'Indicator / Usage',
        'notes': 'Notes',
        'yoy': 'YoY',
        'no_data': 'No data available',
        'altman_z_score': 'Altman Z-Score',
        'zone': 'Zone',
        'implied_rating': 'Implied Rating',
        'methodology_note_title': 'Methodology Note',
        'covenant_note_title': 'Indicator Notes',
        'altman_component_wc': 'Working Capital / Total Assets',
        'altman_component_re': 'Retained Earnings / Total Assets',
        'altman_component_ebit': 'EBIT / Total Assets',
        'altman_status_safe': 'Safe',
        'altman_status_watch': 'Watch',
        'altman_status_distress': 'Distress',
        'altman_summary_safe': 'Resilient balance-sheet profile with comfortable operating coverage.',
        'altman_summary_watch': 'Moderate credit profile with key watch points in liquidity and leverage.',
        'altman_summary_distress': 'Elevated balance-sheet stress and a weaker operating cushion require close monitoring.',
        'altman_summary_neutral': 'Altman Z-Score is available for the latest period.',
        'benchmark_note': '* Shaded columns mark the latest completed audited fiscal year (Historical Benchmark).',
        'model_note': 'Derived from the Altman model',
        'methodology_altman_note': 'Altman Z: weighted model based on working capital, retained earnings, EBIT, market value, and sales.',
        'methodology_zone_note': 'Zone: >2.99 Safe, 1.81-2.99 Grey, <1.81 Distress.',
        'methodology_rating_note': 'Rating: implied rating mapped from Z-Score and historical default rates.',
    },
    'zh-CN': {
        'report_title': 'RiskLens 风险分析报告',
        'credit_health_summary': '信用健康摘要',
        'executive_summary': '执行摘要',
        'company_profile': '公司概况',
        'key_risk_profile': '核心风险特征',
        'latest_period': '最新期间',
        'currency': '币种',
        'generated_at': '生成时间',
        'strengths': '优势',
        'watch_items': '关注项',
        'watch_items_none': '无显著风险项',
        'covenant_pre_check': '契约预检',
        'data_quality': '数据质量',
        'kpi_trends': '核心指标趋势',
        'financial_statements': '财务报表',
        'contents': '目录',
        'income_statement': '利润表',
        'balance_sheet': '资产负债表',
        'cash_flow_statement': '现金流量表',
        'metric': '指标',
        'actual': '实际值',
        'threshold': '阈值',
        'status': '状态',
        'status_signal': '状态/信号',
        'signal': '信号',
        'indicator_description': '指标说明/用途',
        'notes': '备注',
        'yoy': '同比',
        'no_data': '暂无数据',
        'altman_z_score': 'Altman Z 分数',
        'zone': '区间',
        'implied_rating': '隐含评级',
        'methodology_note_title': '方法论注解',
        'covenant_note_title': '指标说明',
        'altman_component_wc': '营运资本 / 总资产',
        'altman_component_re': '留存收益 / 总资产',
        'altman_component_ebit': 'EBIT / 总资产',
        'altman_status_safe': '安全',
        'altman_status_watch': '观察',
        'altman_status_distress': '困境',
        'altman_summary_safe': '资产负债结构稳健，营运覆盖能力充足。',
        'altman_summary_watch': '信用状况中性偏弱，需关注流动性与杠杆。',
        'altman_summary_distress': '资产负债压力偏高，需持续密切监控。',
        'altman_summary_neutral': '已取得最新期间的 Altman Z 分数。',
        'benchmark_note': '* 加深列代表最近一个完整会计年度的已审计基准数据 (Historical Benchmark)。',
        'model_note': '基于 Altman 模型推导',
        'methodology_altman_note': 'Altman Z：基于营运资本、留存收益、EBIT、市值、营收的加权模型。',
        'methodology_zone_note': 'Zone：>2.99 Safe，1.81-2.99 Grey，<1.81 Distress。',
        'methodology_rating_note': 'Rating：基于 Z 分数与历史违约率映射的隐含评级。',
    },
    'zh-TW': {
        'report_title': 'RiskLens 風險分析報告',
        'credit_health_summary': '信用健康摘要',
        'executive_summary': '執行摘要',
        'company_profile': '公司概況',
        'key_risk_profile': '核心風險特徵',
        'latest_period': '最新期間',
        'currency': '幣別',
        'generated_at': '產生時間',
        'strengths': '優勢',
        'watch_items': '關注項',
        'watch_items_none': '無顯著風險項',
        'covenant_pre_check': '契約預檢',
        'data_quality': '資料品質',
        'kpi_trends': '核心指標趨勢',
        'financial_statements': '財務報表',
        'contents': '目錄',
        'income_statement': '損益表',
        'balance_sheet': '資產負債表',
        'cash_flow_statement': '現金流量表',
        'metric': '指標',
        'actual': '實際值',
        'threshold': '門檻',
        'status': '狀態',
        'status_signal': '狀態/訊號',
        'signal': '訊號',
        'indicator_description': '指標說明/用途',
        'notes': '備註',
        'yoy': '同比',
        'no_data': '暫無資料',
        'altman_z_score': 'Altman Z 分數',
        'zone': '區間',
        'implied_rating': '隱含評等',
        'methodology_note_title': '方法論註解',
        'covenant_note_title': '指標說明',
        'altman_component_wc': '營運資本 / 總資產',
        'altman_component_re': '保留盈餘 / 總資產',
        'altman_component_ebit': 'EBIT / 總資產',
        'altman_status_safe': '安全',
        'altman_status_watch': '觀察',
        'altman_status_distress': '困境',
        'altman_summary_safe': '資產負債結構穩健，營運覆蓋能力充足。',
        'altman_summary_watch': '信用狀況中性偏弱，需關注流動性與槓桿。',
        'altman_summary_distress': '資產負債壓力偏高，需持續密切監控。',
        'altman_summary_neutral': '已取得最新期間的 Altman Z 分數。',
        'benchmark_note': '* 加深列代表最近一個完整會計年度的已審計基準資料 (Historical Benchmark)。',
        'model_note': '基於 Altman 模型推導',
        'methodology_altman_note': 'Altman Z：基於營運資本、保留盈餘、EBIT、市值、營收的加權模型。',
        'methodology_zone_note': 'Zone：>2.99 Safe，1.81-2.99 Grey，<1.81 Distress。',
        'methodology_rating_note': 'Rating：基於 Z 分數與歷史違約率映射的隱含評等。',
    },
    'ja': {
        'report_title': 'RiskLens 財務レポート',
        'credit_health_summary': 'クレジット健全性サマリー',
        'executive_summary': 'エグゼクティブサマリー',
        'company_profile': '会社概要',
        'key_risk_profile': '主要リスク特性',
        'latest_period': '最新期間',
        'currency': '通貨',
        'generated_at': '生成日時',
        'strengths': '強み',
        'watch_items': '注意項目',
        'watch_items_none': '特記事項なし',
        'covenant_pre_check': 'コベナント事前確認',
        'data_quality': 'データ品質',
        'kpi_trends': 'KPIトレンド',
        'financial_statements': '財務諸表',
        'contents': '目次',
        'income_statement': '損益計算書',
        'balance_sheet': '貸借対照表',
        'cash_flow_statement': 'キャッシュフロー計算書',
        'metric': '指標',
        'actual': '実績',
        'threshold': '基準',
        'status': '状態',
        'status_signal': '状態/シグナル',
        'signal': 'シグナル',
        'indicator_description': '指標の説明/用途',
        'notes': '注記',
        'yoy': '前年同期比',
        'no_data': 'データなし',
        'altman_z_score': 'Altman Zスコア',
        'zone': 'ゾーン',
        'implied_rating': '推定格付け',
        'methodology_note_title': '方法論注記',
        'covenant_note_title': '指標の説明',
        'altman_component_wc': '運転資本 / 総資産',
        'altman_component_re': '利益剰余金 / 総資産',
        'altman_component_ebit': 'EBIT / 総資産',
        'altman_status_safe': '安全',
        'altman_status_watch': 'ウォッチ',
        'altman_status_distress': 'ディストレス',
        'altman_summary_safe': '財務基盤は堅調で、営業カバー力も十分です。',
        'altman_summary_watch': '信用プロファイルは中立からやや弱含みで、流動性とレバレッジの監視が必要です。',
        'altman_summary_distress': '財務負担が高く、継続的な注視が必要です。',
        'altman_summary_neutral': '最新期間の Altman Z スコアが取得されています。',
        'benchmark_note': '* 強調列は直近の完了した監査済み年度 (Historical Benchmark) を示します。',
        'model_note': 'Altmanモデルに基づく推定',
        'methodology_altman_note': 'Altman Z: 運転資本、利益剰余金、EBIT、市場価値、売上高の加重モデル。',
        'methodology_zone_note': 'Zone: >2.99 Safe、1.81-2.99 Grey、<1.81 Distress。',
        'methodology_rating_note': 'Rating: Zスコアと歴史的デフォルト率を対応付けた推定格付け。',
    },
}

KPI_SPECS = [
    ('EBIT', ('ebit', 'operating_income', 'operatingincome')),
    ('EBITDA', ('ebitda',)),
    ('Total Debt', ('total_debt', 'gross_debt', 'debt_total')),
    ('Debt / EBITDA', ('debt_ebitda', 'debt_to_ebitda')),
    ('Interest Coverage', ('interest_coverage', 'ebit_interest_coverage')),
    ('Free CF', ('free_cash_flow', 'fcf', 'free_cf')),
    ('FCF / Debt', ('fcf_debt', 'fcf_to_debt')),
    ('Current Ratio', ('current_ratio',)),
]
STATEMENT_KEYS = [
    ('income_statement', 'income_statement', ('income', 'pnl', 'profit_and_loss')),
    ('balance_sheet', 'balance_sheet', ('bs', 'statement_of_financial_position', 'balance')),
    ('cash_flow_statement', 'cash_flow_statement', ('cash_flow', 'cashflow', 'cf', 'cash')),
]
RATIO_METRICS = {'Debt / EBITDA', 'Interest Coverage', 'FCF / Debt', 'Current Ratio'}

PDF_STYLE_TOKENS = {
    'bg': '#020617',
    'panel': '#0f172a',
    'panel_strong': '#111827',
    'ink': '#e2e8f0',
    'muted': '#94a3b8',
    'line': '#273244',
    'positive': '#4ade80',
    'warning': '#f59e0b',
    'danger': '#f87171',
    'info': '#e2c98e',
    'accent': '#d4b46a',
    'shadow': '0 26px 70px rgba(2, 6, 23, 0.28)',
    'shadow_soft': '0 18px 34px rgba(2, 6, 23, 0.24)',
    'body_font': "'IBM Plex Sans', 'Noto Sans SC', 'Microsoft YaHei', sans-serif",
    'heading_font': "'IBM Plex Sans', 'Noto Sans SC', 'Microsoft YaHei', sans-serif",
}


def _style_tokens() -> dict[str, str]:
    return dict(PDF_STYLE_TOKENS)


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

    abs_num = abs(number)
    if abs_num >= 1_000_000_000:
        return f'{number / 1_000_000_000:.1f}B'
    if abs_num >= 1_000_000:
        return f'{number / 1_000_000:.1f}M'
    if abs_num >= 1_000:
        return f'{number / 1_000:.1f}K'

    if float(number).is_integer():
        return f'{number:,.0f}'
    return f'{number:,.2f}'


_STATEMENT_MAGNITUDE_LABEL_HINTS = (
    'revenue',
    'income',
    'expense',
    'ebit',
    'ebitda',
    'cash flow',
    'cash',
    'debt',
    'asset',
    'liabilit',
    'equity',
    'earnings',
    'sale',
    'purchase',
    'inventory',
    'receivable',
    'payable',
    'ppe',
    'capital',
    'interest',
    'investment',
    'working capital',
    'retained earnings',
    'total assets',
    'total liabilities',
    'tax effect',
    'unusual items',
    'operating cf',
    'free cf',
    'gross ppe',
    'net ppe',
    'normalized',
)
_STATEMENT_MAGNITUDE_LABEL_BLOCKERS = (
    'rate',
    'ratio',
    'margin',
    'coverage',
    'yield',
    'share',
    'shares',
    'eps',
    'percent',
    'pct',
    'yoy',
    'per share',
)
_MAGNITUDE_SUFFIX_RE = re.compile(r'^(?P<num>[+-]?(?:\d[\d,]*)(?:\.\d+)?)(?P<unit>[bmk])$', re.IGNORECASE)
_OCR_MAGNITUDE_SUFFIX_RE = re.compile(r'^(?P<num>[+-]?(?:\d[\d,]*)(?:\.\d))8$', re.IGNORECASE)
_OCR_STRAY_UNIT_PUNCT_RE = re.compile(
    r'^(?P<num>[+-]?(?:\d[\d,]*)(?:\.\d+)?)(?:[.\u00B7]+)(?P<unit>[bmk])$',
    re.IGNORECASE,
)


def _statement_label_supports_magnitude(label: Any) -> bool:
    text = _clean_display_text(label).lower()
    if not text or text in {'--', 'n/a', 'na', 'no data available'}:
        return False
    if any(blocker in text for blocker in _STATEMENT_MAGNITUDE_LABEL_BLOCKERS):
        return False
    return any(hint in text for hint in _STATEMENT_MAGNITUDE_LABEL_HINTS)


def _format_magnitude_display(number: float) -> str:
    abs_num = abs(number)
    if abs_num >= 1_000_000_000:
        return f'{number / 1_000_000_000:.1f} B'
    if abs_num >= 1_000_000:
        return f'{number / 1_000_000:.1f} M'
    if abs_num >= 1_000:
        return f'{number / 1_000:.1f} K'
    if float(number).is_integer():
        return f'{number:,.0f}'
    return f'{number:,.2f}'


def _format_statement_display_value(value: Any, label: Any = None) -> str:
    text = _clean_display_text(value)
    if not text:
        return '--'
    lowered = text.lower()
    if lowered in {'--', 'n/a', 'na', 'no data available'}:
        return text

    if isinstance(value, str) and _statement_label_supports_magnitude(label):
        compact = text.replace(' ', '')
        unit_match = _MAGNITUDE_SUFFIX_RE.fullmatch(compact)
        if unit_match:
            number_text = unit_match.group('num').replace(',', '')
            unit = unit_match.group('unit').upper()
            return f'{number_text} {unit}'
        ocr_match = _OCR_MAGNITUDE_SUFFIX_RE.fullmatch(compact)
        if ocr_match:
            number_text = ocr_match.group('num').replace(',', '')
            try:
                float(number_text)
            except ValueError:
                pass
            else:
                if abs(float(number_text)) >= 10:
                    return f'{number_text} B'
        stray_unit_match = _OCR_STRAY_UNIT_PUNCT_RE.fullmatch(compact)
        if stray_unit_match:
            number_text = stray_unit_match.group('num').replace(',', '')
            unit = stray_unit_match.group('unit').upper()
            return f'{number_text} {unit}'

    number = _safe_number(value)
    if number is None:
        return text
    return _format_magnitude_display(number)


def _format_ratio_value(label: str, value: Any) -> str:
    text = _format_value(value)
    if text == '--':
        return text
    return f'{text}x' if label in RATIO_METRICS else text


def _format_yoy_change(current: Any, previous: Any) -> str:
    current_num = _safe_number(current)
    previous_num = _safe_number(previous)
    if current_num is None or previous_num is None:
        return 'N/A'
    if previous_num == 0:
        return 'N/M'
    if current_num < 0 < previous_num or previous_num < 0 < current_num:
        return 'N/M'
    if current_num < 0 and previous_num < 0:
        pct = (abs(current_num) - abs(previous_num)) / abs(previous_num) * 100
        return _format_number(pct, signed=True, suffix='%')
    pct = (current_num - previous_num) / abs(previous_num) * 100
    return _format_number(pct, signed=True, suffix='%')


def _split_history_by_kind(history: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {'quarter': [], 'annual': [], 'unknown': []}
    for entry in history:
        kind = _period_kind(str(entry.get('fiscal_year') or entry.get('period') or entry.get('label') or ''))
        buckets.setdefault(kind, []).append(entry)
    return buckets


def _covenant_description(lang: str, metric: str) -> str:
    key = _normalize_key(metric)
    descriptions = {
        'en': {
            'debtebitda': 'Leverage and debt burden',
            'interestcoverage': 'EBIT coverage of interest',
            'fcfdebt': 'Cash flow support for debt',
            'currentratio': 'Short-term liquidity',
        },
        'zh-CN': {
            'debtebitda': '衡量杠杆与偿债能力',
            'interestcoverage': '衡量利息覆盖倍数',
            'fcfdebt': '衡量现金流偿债能力',
            'currentratio': '衡量短期流动性',
        },
        'zh-TW': {
            'debtebitda': '衡量槓桿與償債能力',
            'interestcoverage': '衡量利息覆蓋倍數',
            'fcfdebt': '衡量現金流償債能力',
            'currentratio': '衡量短期流動性',
        },
        'ja': {
            'debtebitda': 'レバレッジと返済負担',
            'interestcoverage': '利息支払余力を測定',
            'fcfdebt': '負債に対するCF余力',
            'currentratio': '短期流動性を測定',
        },
    }
    return descriptions.get(lang, descriptions['en']).get(key, '--')


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
        return (year, 0, 0)
    return (0, 0, 0)


def _period_kind(label: str | None) -> str:
    if not label:
        return 'unknown'
    text = str(label).upper()
    if re.match(r'^(?:FY)?(?P<year>\d{2,4})Q(?P<quarter>[1-4])$', text):
        return 'quarter'
    if re.match(r'^FY(?P<year>\d{2,4})$', text):
        return 'annual'
    return 'unknown'


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


def _build_yoy_map(periods: Any) -> Any:
    sequence = list(_sequence(periods))
    if any(isinstance(item, dict) for item in sequence):
        entries: list[dict[str, str]] = []
        seen: set[str] = set()
        seen_kind: set[str] = set()
        raw_periods: list[str] = []
        for item in sequence:
            if not isinstance(item, dict):
                continue
            raw = str(item.get('fiscal_year') or item.get('period') or item.get('label') or '').strip()
            if not raw or raw in seen:
                continue
            seen.add(raw)
            raw_periods.append(raw)
        available = {period.upper(): period for period in raw_periods}
        for period in raw_periods:
            key = str(period).upper()
            if m := re.match(r'^(?:FY)?(?P<year>\d{2,4})Q(?P<quarter>[1-4])$', key):
                if 'quarter' in seen_kind:
                    continue
                year = int(m.group('year'))
                if year < 100:
                    year += 2000
                prev_candidates = (f'{(year - 1) % 100:02d}Q{m.group("quarter")}', f'{year - 1}Q{m.group("quarter")}')
                compare = next((available[candidate] for candidate in prev_candidates if candidate in available), None)
                if compare:
                    entries.append({'yearCode': period, 'prevYearCode': compare})
                    seen_kind.add('quarter')
            elif m := re.match(r'^FY(?P<year>\d{2,4})$', key):
                if 'annual' in seen_kind:
                    continue
                year = int(m.group('year'))
                if year < 100:
                    year += 2000
                prev_candidates = (f'FY{(year - 1) % 100:02d}', f'FY{year - 1}')
                compare = next((available[candidate] for candidate in prev_candidates if candidate in available), None)
                if compare:
                    entries.append({'yearCode': period, 'prevYearCode': compare})
                    seen_kind.add('annual')
        return entries

    available = {str(p).upper() for p in sequence if p}
    mapping: dict[str, str] = {}
    for period in sequence:
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


def _format_yoy_label(lang: str, current_period: str | None, compare_period: str | None) -> str:
    if not current_period or not compare_period:
        return _t(lang, 'yoy')
    def _compact(label: str) -> str:
        text = str(label or '').strip()
        quarter = re.match(r'^Q([1-4]) FY(\d{2,4})$', text, re.IGNORECASE)
        if quarter:
            year = quarter.group(2)
            if len(year) == 4:
                year = year[-2:]
            return f"Q{quarter.group(1)}'{year}"
        annual = re.match(r'^FY(\d{2,4})$', text, re.IGNORECASE)
        if annual:
            year = annual.group(1)
            if len(year) == 4:
                year = year[-2:]
            return f'FY{year}'
        return text
    return f"{_compact(current_period)} vs {_compact(compare_period)}"


def _format_yoy_short_label(lang: str, kind: str) -> str:
    return _t(lang, 'yoy')


def _format_yoy_note(lang: str, quarter_current: str | None, quarter_compare: str | None, annual_current: str | None, annual_compare: str | None) -> str:
    quarter_text = _format_yoy_label(lang, quarter_current, quarter_compare) if quarter_current and quarter_compare else ""
    annual_text = _format_yoy_label(lang, annual_current, annual_compare) if annual_current and annual_compare else ""
    
    parts = [text for text in (quarter_text, annual_text) if text]
    if not parts:
        return ""
        
    combined = " | ".join(parts)
    templates = {
        'en': '({combined})',
        'zh-CN': '（{combined}）',
        'zh-TW': '（{combined}）',
        'ja': '（{combined}）',
    }
    return templates.get(lang, templates['en']).format(combined=combined)


def _format_period_span_note(lang: str, quarter_periods: list[str], annual_periods: list[str]) -> str:
    parts: list[str] = []
    if len(quarter_periods) > 1:
        quarter_labels = [_format_period_label(period) for period in quarter_periods]
        if lang == 'zh-CN':
            quarter_list = '、'.join(quarter_labels[:-1]) + f"及{quarter_labels[-1]}"
        elif lang == 'zh-TW':
            quarter_list = '、'.join(quarter_labels[:-1]) + f"及{quarter_labels[-1]}"
        elif lang == 'ja':
            quarter_list = '、'.join(quarter_labels[:-1]) + f"および{quarter_labels[-1]}"
        else:
            quarter_list = ', '.join(quarter_labels[:-1]) + f" and {quarter_labels[-1]}"
        quarter_templates = {
            'en': 'For the quarters ended {periods}',
            'zh-CN': '截至{periods}季度',
            'zh-TW': '截至{periods}季度',
            'ja': '{periods}四半期',
        }
        parts.append(quarter_templates.get(lang, quarter_templates['en']).format(periods=quarter_list))
    if len(annual_periods) > 1:
        annual_labels = [_format_period_label(period) for period in annual_periods]
        if lang == 'zh-CN':
            annual_list = '、'.join(annual_labels[:-1]) + f"及{annual_labels[-1]}"
        elif lang == 'zh-TW':
            annual_list = '、'.join(annual_labels[:-1]) + f"及{annual_labels[-1]}"
        elif lang == 'ja':
            annual_list = '、'.join(annual_labels[:-1]) + f"および{annual_labels[-1]}"
        else:
            annual_list = ', '.join(annual_labels[:-1]) + f" and {annual_labels[-1]}"
        annual_templates = {
            'en': 'For the fiscal years ended {periods}',
            'zh-CN': '截至{periods}财政年度',
            'zh-TW': '截至{periods}財政年度',
            'ja': '{periods}会計年度',
        }
        parts.append(annual_templates.get(lang, annual_templates['en']).format(periods=annual_list))
    if not parts:
        return ''
    combined = ' | '.join(parts)
    templates = {
        'en': '({combined})',
        'zh-CN': '（{combined}）',
        'zh-TW': '（{combined}）',
        'ja': '（{combined}）',
    }
    return templates.get(lang, templates['en']).format(combined=combined)


def _normalize_signal_text(signal: Any, status: Any = None) -> str:
    signal_text = str(signal or '').strip()
    status_text = str(status or '').strip()
    if signal_text.lower() in {'green', 'ok', 'pass', 'safe'} and status_text:
        return status_text
    return signal_text or status_text or '--'


def _signal_tone(signal: Any, status: Any = None) -> str:
    text = f"{signal or ''} {status or ''}".lower()
    if any(token in text for token in ('green', 'pass', 'safe', 'ok', 'good')):
        return 'success'
    if any(token in text for token in ('yellow', 'amber', 'watch', 'warning', 'caution')):
        return 'warning'
    if any(token in text for token in ('red', 'fail', 'breach', 'bad', 'risk')):
        return 'danger'
    return 'neutral'


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


def _pick_exact(source: dict[str, Any], candidates: tuple[str, ...]) -> Any:
    if not isinstance(source, dict):
        return None
    flat = {_normalize_key(str(k)): v for k, v in source.items()}
    for candidate in candidates:
        key = _normalize_key(candidate)
        if key in flat:
            return flat[key]
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


def _extract_summary(entry: dict[str, Any], lang: str = 'en') -> dict[str, Any]:
    assessment = _mapping(entry.get('assessment'))
    strengths = _extract_texts(assessment.get('strengths') or entry.get('strengths'))
    watch_items = _extract_texts(
        assessment.get('watch_items')
        or assessment.get('concerns')
        or assessment.get('weaknesses')
        or entry.get('watch_items')
        or entry.get('concerns')
        or entry.get('weaknesses')
        or entry.get('risks')
    )
    covenant_rows: list[dict[str, str]] = []
    for item in _sequence(assessment.get('covenant_pre_check') or assessment.get('covenants') or entry.get('covenant_pre_check') or entry.get('covenants')):
        if isinstance(item, dict):
            status = str(item.get('status') or item.get('result') or '').strip()
            signal = str(item.get('signal') or item.get('direction') or '--')
            status_signal = status if status and status != '--' else _normalize_signal_text(signal, status)
            metric_name = _normalize_label_text(item.get('metric') or item.get('label') or item.get('name') or '--')
            description = _covenant_description(lang, metric_name)
            covenant_rows.append({
                'metric': metric_name,
                'actual': _format_value(item.get('actual') or item.get('value')),
                'threshold': _format_value(item.get('threshold') or item.get('limit') or item.get('target')),
                'status_signal': status_signal,
                'status_signal_tone': _signal_tone(signal, status),
                'notes': _clean_display_text(item.get('notes') or item.get('note') or '--'),
                'description': description,
            })
    if not covenant_rows:
        covenant_rows = _build_covenant_fallback_rows(entry, lang)
    data_quality: list[dict[str, str]] = []
    raw_quality = assessment.get('data_quality') or entry.get('data_quality') or entry.get('quality') or {}
    if isinstance(raw_quality, dict):
        for key, value in raw_quality.items():
            if isinstance(value, dict):
                label = _normalize_label_text(value.get('label') or key)
                data_quality.append({'label': label, 'value': _format_data_quality_value(label, value.get('value') or value.get('score') or value.get('status')), 'notes': str(value.get('notes') or value.get('note') or '--')})
            else:
                label = _normalize_label_text(key)
                data_quality.append({'label': label, 'value': _format_data_quality_value(label, value), 'notes': '--'})
    elif isinstance(raw_quality, list):
        for item in raw_quality:
            if isinstance(item, dict):
                label = _normalize_label_text(item.get('label') or item.get('name') or '--')
                data_quality.append({'label': label, 'value': _format_data_quality_value(label, item.get('value') or item.get('score') or item.get('status')), 'notes': str(item.get('notes') or item.get('note') or '--')})
    if not data_quality:
        data_quality.append({'label': 'Coverage', 'value': '--', 'notes': '--'})
    covenant_notes = [
        {'metric': row['metric'], 'description': row['description']}
        for row in covenant_rows
        if row.get('description') and row.get('description') != '--'
    ]
    if not watch_items:
        watch_items = [_t(lang, 'watch_items_none')]
    return {
        'altman_z_score': _pick(assessment, ('altman_z_score', 'altman_score', 'z_score', 'risk_score')),
        'zone': _pick(assessment, ('altman_zone', 'zone', 'risk_zone', 'overall_rating')),
        'implied_rating': _pick(assessment, ('implied_rating', 'rating', 'credit_rating')),
        'strengths': strengths,
        'watch_items': watch_items,
        'covenant_rows': covenant_rows,
        'covenant_notes': covenant_notes,
        'data_quality': data_quality,
    }


def _build_covenant_fallback_rows(entry: dict[str, Any], lang: str) -> list[dict[str, str]]:
    assessment = _mapping(entry.get('assessment'))
    ratios = _mapping(entry.get('ratios'))
    raw_metrics = _mapping(entry.get('raw_metrics'))
    sources = [ratios, raw_metrics, assessment, entry]

    def pick_number(candidates: tuple[str, ...]) -> float | None:
        for source in sources:
            if not isinstance(source, dict):
                continue
            picked = _pick_exact(source, candidates)
            number = _safe_number(picked)
            if number is not None:
                return number
        return None

    specs = [
        {
            'metric': 'Debt/EBITDA',
            'candidates': ('debt_to_ebitda', 'debt_ebitda'),
            'threshold': 3.5,
            'passed_note': 'Comfortable leverage',
            'failed_note': 'High leverage',
            'passes': lambda actual, threshold: actual is not None and actual <= threshold,
            'signal': ('Green', 'Red'),
        },
        {
            'metric': 'Interest Coverage',
            'candidates': ('interest_coverage', 'ebit_interest_coverage'),
            'threshold': 3.0,
            'passed_note': 'Strong coverage',
            'failed_note': 'Weak coverage',
            'passes': lambda actual, threshold: actual is not None and actual >= threshold,
            'signal': ('Green', 'Red'),
        },
        {
            'metric': 'FCF / Debt',
            'candidates': ('fcf_to_debt', 'fcf_debt'),
            'threshold': 0.2,
            'passed_note': 'Strong cash flow support',
            'failed_note': 'Weak cash flow support',
            'passes': lambda actual, threshold: actual is not None and actual >= threshold,
            'signal': ('Green', 'Red'),
        },
        {
            'metric': 'Current Ratio',
            'candidates': ('current_ratio',),
            'threshold': 1.5,
            'passed_note': 'Healthy liquidity',
            'failed_note': 'Weak liquidity',
            'passes': lambda actual, threshold: actual is not None and actual >= threshold,
            'signal': ('Green', 'Red'),
        },
    ]

    rows: list[dict[str, str]] = []
    for spec in specs:
        actual = pick_number(spec['candidates'])
        if actual is None:
            continue
        threshold = float(spec['threshold'])
        is_pass = bool(spec['passes'](actual, threshold))
        signal = spec['signal'][0] if is_pass else spec['signal'][1]
        status = 'Pass' if is_pass else 'Fail'
        metric_name = _normalize_label_text(spec['metric'])
        rows.append({
            'metric': metric_name,
            'actual': _format_value(actual),
            'threshold': _format_value(threshold),
            'status_signal': status,
            'status_signal_tone': _signal_tone(signal, status),
            'notes': spec['passed_note'] if is_pass else spec['failed_note'],
            'description': _covenant_description(lang, metric_name),
        })
    return rows


def _altman_status_label(lang: str, z_score: Any, zone: Any) -> str:
    number = _safe_number(z_score)
    if number is not None:
        if number >= 2.99:
            return _t(lang, 'altman_status_safe')
        if number >= 1.81:
            return _t(lang, 'altman_status_watch')
        return _t(lang, 'altman_status_distress')
    zone_text = str(zone or '').lower()
    if not zone_text:
        return _t(lang, 'altman_status_watch')
    if 'safe' in zone_text:
        return _t(lang, 'altman_status_safe')
    if 'grey' in zone_text or 'watch' in zone_text:
        return _t(lang, 'altman_status_watch')
    return _t(lang, 'altman_status_distress')


def _altman_summary_text(lang: str, z_score: Any, zone: Any) -> str:
    number = _safe_number(z_score)
    if number is not None:
        if number >= 2.99:
            return _t(lang, 'altman_summary_safe')
        if number >= 1.81:
            return _t(lang, 'altman_summary_watch')
        return _t(lang, 'altman_summary_distress')
    zone_text = str(zone or '').lower()
    if not zone_text:
        return _t(lang, 'altman_summary_neutral')
    if 'safe' in zone_text:
        return _t(lang, 'altman_summary_safe')
    if 'grey' in zone_text or 'watch' in zone_text:
        return _t(lang, 'altman_summary_watch')
    return _t(lang, 'altman_summary_distress')


def _build_altman_breakdown(entry: dict[str, Any], lang: str) -> list[dict[str, Any]]:
    statements = _mapping(entry.get('statements', {}))
    raw_metrics = _mapping(entry.get('raw_metrics'))
    balance = _mapping(entry.get('balance') or entry.get('balance_sheet') or entry.get('bs') or statements.get('balance'))
    income = _mapping(entry.get('income') or entry.get('income_statement') or entry.get('pnl') or statements.get('income'))

    total_assets = _safe_number(_pick(raw_metrics, ('total_assets',))) or _safe_number(_pick(balance, ('total_assets',)))
    current_assets = _safe_number(_pick(raw_metrics, ('total_current_assets',))) or _safe_number(_pick(balance, ('total_current_assets',)))
    current_liabilities = _safe_number(_pick(raw_metrics, ('total_current_liabilities',))) or _safe_number(_pick(balance, ('total_current_liabilities',)))
    retained_earnings = _safe_number(_pick(raw_metrics, ('retained_earnings',))) or _safe_number(_pick(balance, ('retained_earnings',)))
    ebit = _safe_number(_pick(raw_metrics, ('operating_income', 'ebit'))) or _safe_number(_pick(income, ('operating_income', 'ebit')))

    working_capital = None
    if current_assets is not None and current_liabilities is not None:
        working_capital = current_assets - current_liabilities

    components = [
        (_t(lang, 'altman_component_wc'), working_capital, 1.2),
        (_t(lang, 'altman_component_re'), retained_earnings, 1.4),
        (_t(lang, 'altman_component_ebit'), ebit, 3.3),
    ]
    breakdown: list[dict[str, Any]] = []
    for label, numerator, weight in components:
        ratio = None
        if numerator is not None and total_assets is not None and total_assets > 0:
            ratio = numerator / total_assets
        contribution = None if ratio is None else ratio * weight
        progress = None if ratio is None else max(0.0, min(abs(ratio) * 100.0, 100.0))
        tone = 'neutral'
        if ratio is not None:
            tone = 'danger' if ratio < 0 else 'positive'
        breakdown.append({
            'label': label,
            'value': '--' if ratio is None else f'{ratio * 100:.2f}%',
            'contribution': '--' if contribution is None else f'{contribution:+.2f}',
            'tone': tone,
            'progress': progress,
        })
    return breakdown


def _format_data_quality_value(label: Any, value: Any) -> str:
    text_label = str(label or '').strip().lower()
    if text_label == 'coverage':
        number = _safe_number(value)
        if number is not None:
            if 0 <= number <= 1:
                return f'{number * 100:.0f}%'
            if 1 < number <= 100:
                return f'{number:.0f}%'
    return _format_value(value)


def _clean_display_text(value: Any) -> str:
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def _normalize_label_text(value: Any) -> str:
    text = re.sub(r'[.\u3002\uFF0E:：\s]+$', '', _clean_display_text(value))
    if not text:
        return text
    lowered = text.lower()
    if lowered in {'--', 'n/a', 'na', 'no data available'}:
        return text
    text = text.replace('_', ' ')
    text = re.sub(r'\btradeand\b', 'trade and', text, flags=re.IGNORECASE)
    text = re.sub(r'\bpensionand\b', 'pension and', text, flags=re.IGNORECASE)
    text = re.sub(r'\bavailto\b', 'avail to', text, flags=re.IGNORECASE)
    text = re.sub(r'\bgand\b', 'g and', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    parts: list[str] = []
    for part in text.split(' '):
        if not part:
            continue
        lower_part = part.lower()
        if lower_part in {'and', 'of', 'to', 'for', 'in', 'on', 'at', 'by', 'per'} and parts:
            parts.append(lower_part)
            continue
        if lower_part in {'ebit', 'ebitda', 'fcf', 'cf', 'ni', 'ppe', 'eps', 'roi', 'roa', 'roe', 'usd', 'hkd', 'cny', 'jpy', 'fx', 'n/a'}:
            parts.append(part.upper())
        elif part.isdigit():
            parts.append(part)
        elif '/' in part:
            segments: list[str] = []
            for segment in part.split('/'):
                if not segment:
                    segments.append(segment)
                elif segment.lower() in {'ebit', 'ebitda', 'fcf', 'cf', 'ni', 'ppe', 'eps', 'roi', 'roa', 'roe', 'usd', 'hkd', 'cny', 'jpy', 'fx', 'n/a'}:
                    segments.append(segment.upper())
                else:
                    segments.append(segment[:1].upper() + segment[1:])
            parts.append('/'.join(segments))
        else:
            parts.append(part[:1].upper() + part[1:])
    return ' '.join(parts)


def _wrap_cell_lines(value: Any, width_fraction: float, chars_per_full_width: int, max_lines: int = 4) -> list[str]:
    text = _clean_display_text(value)
    if not text:
        return ['']
    limit = max(8, int(round(width_fraction * chars_per_full_width)))
    words = text.split(' ')
    lines: list[str] = []
    current = ''
    for word in words:
        if not word:
            continue
        if not current:
            if len(word) <= limit:
                current = word
            else:
                while len(word) > limit:
                    lines.append(word[: max(1, limit - 3)] + '...')
                    word = word[max(1, limit - 3):]
                current = word
            continue
        trial = f'{current} {word}'
        if len(trial) <= limit:
            current = trial
        else:
            lines.append(current)
            if len(word) <= limit:
                current = word
            else:
                while len(word) > limit:
                    lines.append(word[: max(1, limit - 3)] + '...')
                    word = word[max(1, limit - 3):]
                current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        tail = lines[-1]
        if not tail.endswith('...'):
            lines[-1] = tail[: max(1, limit - 3)].rstrip() + '...'
    return lines or ['']


def _estimate_table_row_height(row: list[str], widths: list[float], chars_per_full_width: int, font_size: float, max_lines: int = 4, min_height: float = 18.0, height_scale: float = 1.0) -> float:
    max_wrapped_lines = 1
    for idx, cell in enumerate(row):
        width_fraction = widths[min(idx, len(widths) - 1)] if widths else 1.0
        max_wrapped_lines = max(max_wrapped_lines, len(_wrap_cell_lines(cell, width_fraction, chars_per_full_width, max_lines=max_lines)))
    line_height = max(9.5, font_size + 1.8)
    return (max(min_height, 6.0 + max_wrapped_lines * line_height)) * height_scale


def _paginate_table_rows(rows: list[list[str]], widths: list[float], available_height: float, chars_per_full_width: int, font_size: float, header_height: float, max_lines: int = 4, min_row_height: float = 18.0, height_scale: float = 1.0) -> list[list[list[str]]]:
    if not rows:
        return [[]]
    chunks: list[list[list[str]]] = []
    current: list[list[str]] = []
    used = header_height
    for row in rows:
        row_height = _estimate_table_row_height(row, widths, chars_per_full_width, font_size, max_lines=max_lines, min_height=min_row_height, height_scale=height_scale)
        if current and used + row_height > available_height:
            chunks.append(current)
            current = [row]
            used = header_height + row_height
        else:
            current.append(row)
            used += row_height
    if current:
        chunks.append(current)
    return chunks


def _extract_profile(report: dict[str, Any], latest: dict[str, Any]) -> list[dict[str, str]]:
    profile = report.get('company_profile') or latest.get('company_profile') or {}
    rows: list[dict[str, str]] = []
    if isinstance(profile, dict):
        for key, value in profile.items():
            if isinstance(value, dict):
                value = value.get('value') or value.get('text') or value.get('name') or '--'
            rows.append({'label': _normalize_label_text(key), 'value': _format_value(value)})
    return rows


def _extract_metric_value(entry: dict[str, Any], candidates: tuple[str, ...]) -> Any:
    for key in ('raw_metrics', 'ratios', 'metrics', 'assessment'):
        value = entry.get(key)
        if isinstance(value, dict):
            picked = _pick(value, candidates)
            if picked is not None:
                return picked
    return _pick(entry, candidates)


def _extract_metric_value_strict(entry: dict[str, Any], candidates: tuple[str, ...]) -> Any:
    ratios = entry.get('ratios')
    if isinstance(ratios, dict):
        picked = _pick_exact(ratios, candidates)
        if picked is not None:
            return picked
    raw_metrics = entry.get('raw_metrics')
    if isinstance(raw_metrics, dict):
        picked = _pick_exact(raw_metrics, candidates)
        if picked is not None:
            return picked
    metrics = entry.get('metrics')
    if isinstance(metrics, dict):
        picked = _pick_exact(metrics, candidates)
        if picked is not None:
            return picked
    return _pick_exact(entry, candidates)


def _statement_text_parts(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        parts: list[str] = []
        for item in value:
            parts.extend(_statement_text_parts(item))
        return parts
    text = re.sub(r'<\s*br\s*/?\s*>', '\n', str(value), flags=re.IGNORECASE)
    parts: list[str] = []
    for raw_part in re.split(r'[\r\n]+', text):
        cleaned = _clean_display_text(raw_part)
        if not cleaned or re.fullmatch(r'[,;\s]+', cleaned):
            continue
        parts.append(cleaned)
    return parts


def _build_kpi_rows(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    buckets = _split_history_by_kind(history)
    quarter_history = buckets.get('quarter', [])
    annual_history = buckets.get('annual', [])
    for label, candidates in KPI_SPECS:
        values = [_extract_metric_value_strict(entry, candidates) for entry in history]
        quarter_values = [_extract_metric_value_strict(entry, candidates) for entry in quarter_history]
        annual_values = [_extract_metric_value_strict(entry, candidates) for entry in annual_history]
        if not quarter_history and len(annual_values) > 1:
            yoy_q = _format_yoy_change(annual_values[0], annual_values[1])
            yoy_fy = _format_yoy_change(annual_values[1], annual_values[2]) if len(annual_values) > 2 else 'N/A'
        else:
            yoy_q = _format_yoy_change(quarter_values[0], quarter_values[1]) if len(quarter_values) > 1 else 'N/A'
            yoy_fy = _format_yoy_change(annual_values[0], annual_values[1]) if len(annual_values) > 1 else 'N/A'
        display_values = [
            _format_ratio_value(label, v) if label in RATIO_METRICS else _format_statement_display_value(v, label)
            for v in values
        ]
        rows.append({
            'label': label,
            'values': display_values,
            'yoy_q': yoy_q,
            'yoy_fy': yoy_fy,
        })
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
            rows.append({'label': _normalize_label_text(key), 'value': value})
        return rows
    for item in _sequence(raw):
        if isinstance(item, dict):
            label = item.get('label') or item.get('name') or item.get('metric') or item.get('line_item') or item.get('account')
            if label is None and len(item) == 1:
                k, v = next(iter(item.items()))
                label_parts = _statement_text_parts(k)
                value_parts = _statement_text_parts(v)
                label_text = _normalize_label_text(' '.join(label_parts) if label_parts else k)
                value_text = ' '.join(value_parts) if value_parts else '--'
                if len(label_parts) > 1 and len(value_parts) > 1:
                    if len(label_parts) == len(value_parts):
                        for label_part, value_part in zip(label_parts, value_parts):
                            rows.append({'label': _normalize_label_text(label_part), 'value': value_part})
                    else:
                        rows.append({'label': label_text, 'value': value_text})
                elif len(label_parts) > 1:
                    rows.append({'label': label_text, 'value': value_text})
                elif len(value_parts) > 1:
                    rows.append({'label': label_text, 'value': value_text})
                else:
                    rows.append({'label': label_text, 'value': value_text})
            else:
                value = item.get('value', item.get('amount', item.get('balance', item.get('text'))))
                label_parts = _statement_text_parts(label or '--')
                value_parts = _statement_text_parts(value)
                label_text = _normalize_label_text(' '.join(label_parts) if label_parts else label or '--')
                value_text = ' '.join(value_parts) if value_parts else '--'
                if len(label_parts) > 1 and len(value_parts) > 1:
                    if len(label_parts) == len(value_parts):
                        for label_part, value_part in zip(label_parts, value_parts):
                            rows.append({'label': _normalize_label_text(label_part), 'value': value_part})
                    else:
                        rows.append({'label': label_text, 'value': value_text})
                elif len(label_parts) > 1:
                    rows.append({'label': label_text, 'value': value_text})
                elif len(value_parts) > 1:
                    rows.append({'label': label_text, 'value': value_text})
                else:
                    rows.append({'label': label_text, 'value': value_text})
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            label_parts = _statement_text_parts(item[0])
            value_parts = _statement_text_parts(item[1])
            label_text = _normalize_label_text(' '.join(label_parts) if label_parts else item[0])
            value_text = ' '.join(value_parts) if value_parts else '--'
            if len(label_parts) > 1 and len(value_parts) > 1 and len(label_parts) == len(value_parts):
                for label_part, value_part in zip(label_parts, value_parts):
                    rows.append({'label': _normalize_label_text(label_part), 'value': value_part})
            elif len(label_parts) > 1:
                rows.append({'label': label_text, 'value': value_text})
            elif len(value_parts) > 1:
                rows.append({'label': label_text, 'value': value_text})
            else:
                rows.append({'label': label_text, 'value': value_text})
        elif item is not None:
            rows.append({'label': _normalize_label_text(item), 'value': '--'})
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
    period_entries: list[dict[str, Any]] = []
    prev_kind: str | None = None
    first_annual_found = False
    for raw_period in periods:
        label = _format_period_label(raw_period)
        kind = _period_kind(raw_period)
        benchmark = bool(kind == 'annual' and not first_annual_found)
        if benchmark:
            first_annual_found = True
        period_entries.append({
            'raw': raw_period,
            'label': label,
            'kind': kind,
            'group_start': bool(prev_kind and kind != prev_kind),
            'benchmark': False,
            'benchmark_style': '',
        })
        prev_kind = kind
    sections: list[dict[str, Any]] = []
    for statement_key, title_key, aliases in STATEMENT_KEYS:
        labels: list[str] = []
        rows_by_period: list[list[dict[str, Any]]] = []
        quarter_entries = [entry for entry in period_entries if entry.get('kind') == 'quarter']
        annual_entries = [entry for entry in period_entries if entry.get('kind') == 'annual']
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
            yoy_q = 'N/A'
            yoy_fy = 'N/A'
            quarter_values = []
            annual_values = []
            for period_entry, value in zip(period_entries, values):
                kind = period_entry.get('kind')
                if kind == 'quarter':
                    quarter_values.append(value)
                elif kind == 'annual':
                    annual_values.append(value)
            if not quarter_entries and len(annual_values) > 1:
                yoy_q = _format_yoy_change(annual_values[0], annual_values[1])
                yoy_fy = _format_yoy_change(annual_values[1], annual_values[2]) if len(annual_values) > 2 else 'N/A'
            else:
                if len(quarter_values) > 1:
                    yoy_q = _format_yoy_change(quarter_values[0], quarter_values[1])
                if len(annual_values) > 1:
                    yoy_fy = _format_yoy_change(annual_values[0], annual_values[1])
            normalized_rows.append({
                'label': label,
                'values': [_format_statement_display_value(v, label) for v in values],
                'yoy_q': yoy_q,
                'yoy_fy': yoy_fy,
            })
        if not quarter_entries and len(annual_entries) > 1:
            cq = annual_entries[0]['label']
            cmpq = annual_entries[1]['label']
            ca = annual_entries[1]['label'] if len(annual_entries) > 1 else None
            cmpa = annual_entries[2]['label'] if len(annual_entries) > 2 else None
        else:
            cq = quarter_entries[0]['label'] if quarter_entries else None
            cmpq = quarter_entries[1]['label'] if len(quarter_entries) > 1 else None
            ca = annual_entries[0]['label'] if annual_entries else None
            cmpa = annual_entries[1]['label'] if len(annual_entries) > 1 else None
        sections.append({
            'key': statement_key,
            'title': title_key,
            'periods': period_entries,
            'current_quarter_period': cq,
            'compare_quarter_period': cmpq,
            'current_annual_period': ca,
            'compare_annual_period': cmpa,
            'rows': normalized_rows,
        })
    return sections


def build_pdf_context(report: dict[str, Any], lang: str = 'en', theme: str = 'dark') -> dict[str, Any]:
    lang = _lang(lang)
    theme = 'light' if str(theme).lower() == 'light' else 'dark'
    history = _extract_history(report)
    if not history:
        raise ValueError('No history available')
    latest = history[0]
    periods = [str(entry.get('fiscal_year') or entry.get('period') or entry.get('label') or '--') for entry in history]
    period_labels = [_format_period_label(p) for p in periods]
    summary = _extract_summary(latest, lang)
    quarter_periods = [label for raw, label in zip(periods, period_labels) if _period_kind(raw) == 'quarter']
    annual_periods = [label for raw, label in zip(periods, period_labels) if _period_kind(raw) == 'annual']
    if annual_periods:
        yoy_note = _format_period_span_note(lang, [], annual_periods)
    elif quarter_periods:
        yoy_note = _format_period_span_note(lang, quarter_periods, [])
    else:
        yoy_note = _format_yoy_note(
            lang,
            quarter_periods[0] if quarter_periods else None,
            quarter_periods[1] if len(quarter_periods) > 1 else None,
            annual_periods[0] if annual_periods else None,
            annual_periods[1] if len(annual_periods) > 1 else None,
        )
    statement_sections = _build_statement_sections(history)
    for section in statement_sections:
        section['yoy_label_q'] = _format_yoy_label(lang, section.get('current_quarter_period'), section.get('compare_quarter_period'))
        section['yoy_label_fy'] = _format_yoy_label(lang, section.get('current_annual_period'), section.get('compare_annual_period'))
        section['yoy_note'] = yoy_note
    benchmark_period = next((label for raw, label in zip(periods, period_labels) if _period_kind(raw) == 'annual'), None)
    benchmark_note = ''
    altman_z_score = summary.get('altman_z_score')
    zone = summary.get('zone')
    implied_rating = summary.get('implied_rating')
    altman_status = _altman_status_label(lang, altman_z_score, zone)
    altman_breakdown = _build_altman_breakdown(latest, lang)
    hero_summary = {
        'note': f"{_t(lang, 'methodology_note_title')}: " + " | ".join([
            _t(lang, 'methodology_altman_note'),
            _t(lang, 'methodology_zone_note'),
            _t(lang, 'methodology_rating_note'),
        ]),
        'status_label': altman_status,
        'description': _altman_summary_text(lang, altman_z_score, zone),
        'items': [
            {'label': _t(lang, 'altman_z_score'), 'value': _format_value(altman_z_score), 'tone': 'neutral'},
            {'label': _t(lang, 'zone'), 'value': _format_value(zone), 'tone': 'success'},
            {'label': _t(lang, 'implied_rating'), 'value': _format_value(implied_rating), 'tone': 'info'},
        ],
        'breakdown': altman_breakdown,
    }
    return {
        'lang': lang,
        'theme': theme,
        'labels': LANG[lang],
        'report_title': _t(lang, 'report_title'),
        'credit_health_summary_title': _t(lang, 'credit_health_summary'),
        'company_profile_title': _t(lang, 'company_profile'),
        'key_risk_profile_title': _t(lang, 'key_risk_profile'),
        'strengths_title': _t(lang, 'strengths'),
        'watch_items_title': _t(lang, 'watch_items'),
        'covenant_title': _t(lang, 'covenant_pre_check'),
        'data_quality_title': _t(lang, 'data_quality'),
        'kpi_title': _t(lang, 'kpi_trends'),
        'latest_period_title': _t(lang, 'latest_period'),
        'currency_title': _t(lang, 'currency'),
        'generated_at_title': _t(lang, 'generated_at'),
        'style': _style_tokens(),
        'company_name': str(report.get('company_name') or latest.get('company_name') or latest.get('name') or 'Unknown Company'),
        'company_name_localized': '' if lang == 'en' else str(report.get('company_name_localized') or latest.get('company_name_localized') or report.get('company_name') or latest.get('company_name') or 'Unknown Company'),
        'ticker': str(report.get('ticker') or latest.get('ticker') or '--'),
        'currency': str(report.get('currency') or latest.get('currency') or latest.get('reporting_currency') or '--'),
        'latest_period': period_labels[0],
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'periods': [
            {
                'raw': raw,
                'label': label,
                'display_label': label,
                'kind': _period_kind(raw),
                'group_start': idx > 0 and _period_kind(raw) != _period_kind(periods[idx - 1]),
                'benchmark': False,
                'benchmark_style': '',
            }
            for idx, (raw, label) in enumerate(zip(periods, period_labels))
        ],
        'hero_summary': hero_summary,
        'zone_text': _format_value(summary['zone']) if summary['zone'] is not None else None,
        'company_profile_rows': _extract_profile(report, latest),
        'strengths': summary.get('strengths', []),
        'watch_items': summary.get('watch_items', []),
        'covenant_rows': summary.get('covenant_rows', []),
        'covenant_notes': summary.get('covenant_notes', []),
        'data_quality_rows': summary.get('data_quality', []),
        'kpi_rows': _build_kpi_rows(history),
        'kpi_yoy_label_q': _format_yoy_label(lang, annual_periods[0] if len(annual_periods) > 1 else None, annual_periods[1] if len(annual_periods) > 1 else None) if not quarter_periods else _format_yoy_label(lang, quarter_periods[0] if quarter_periods else None, quarter_periods[1] if len(quarter_periods) > 1 else None),
        'kpi_yoy_label_fy': _format_yoy_label(lang, annual_periods[1] if len(annual_periods) > 2 else None, annual_periods[2] if len(annual_periods) > 2 else None) if not quarter_periods else _format_yoy_label(lang, annual_periods[0] if annual_periods else None, annual_periods[1] if len(annual_periods) > 1 else None),
        'yoy_note': yoy_note,
        'benchmark_note': benchmark_note,
        'methodology_notes': [
            _t(lang, 'methodology_altman_note'),
            _t(lang, 'methodology_zone_note'),
            _t(lang, 'methodology_rating_note'),
        ],
        'covenant_note_title': _t(lang, 'covenant_note_title'),
        'statement_sections': statement_sections,
    }


def build_pdf_document_model(report: dict[str, Any], lang: str = 'en', theme: str = 'dark') -> dict[str, Any]:
    ctx = build_pdf_context(report, lang, theme)
    sections: list[dict[str, Any]] = []
    for section in ctx['statement_sections']:
        widths = [0.20] + [0.085] * len(section['periods']) + [0.16, 0.16]
        sections.append({
            'key': section['key'],
            'title': section['title'],
            'display_title': ctx['labels'][section['title']],
            'periods': section['periods'],
            'headers': [_t(lang, 'metric')] + [p['label'] for p in section['periods']] + [section['yoy_label_q'], section['yoy_label_fy']],
            'rows': section['rows'],
            'widths': widths,
            'benchmark_cols': set(),
            'group_break_cols': {1 + idx for idx, period in enumerate(section['periods']) if period.get('group_start')},
            'yoy_label_q': section['yoy_label_q'],
            'yoy_label_fy': section['yoy_label_fy'],
            'yoy_note': section['yoy_note'],
            'current_period': section['current_annual_period'] or section['current_quarter_period'] or ctx['latest_period'],
        })

    return {
        'lang': lang,
        'theme': ctx['theme'],
        'context': ctx,
        'cover': {
            'report_title': ctx['report_title'],
            'company_name': ctx['company_name'],
            'company_name_localized': ctx['company_name_localized'],
            'ticker': ctx['ticker'],
            'currency': ctx['currency'],
            'latest_period': ctx['latest_period'],
            'generated_at': ctx['generated_at'],
            'zone_text': ctx['zone_text'],
            'hero_summary': ctx['hero_summary'],
        },
        'summary': {
            'company_profile_rows': ctx['company_profile_rows'],
            'strengths': ctx['strengths'],
            'watch_items': ctx['watch_items'],
            'data_quality_rows': ctx['data_quality_rows'],
            'methodology_notes': ctx['methodology_notes'],
        },
        'covenant': {
            'title': ctx['covenant_title'],
            'rows': ctx['covenant_rows'],
            'notes': ctx['covenant_notes'],
            'note_title': ctx['covenant_note_title'],
        },
        'kpi': {
            'title': ctx['kpi_title'],
            'benchmark_note': ctx['benchmark_note'],
            'yoy_note': ctx['yoy_note'],
            'headers': [_t(lang, 'metric')] + [p['label'] for p in ctx['periods']] + [ctx['kpi_yoy_label_q'], ctx['kpi_yoy_label_fy']],
            'rows': [[row['label'], *row['values'], row['yoy_q'], row['yoy_fy']] for row in ctx['kpi_rows']],
            'widths': [0.18] + [0.085] * len(ctx['periods']) + [0.16, 0.16],
            'benchmark_cols': set(),
            'group_break_cols': {1 + idx for idx, period in enumerate(ctx['periods']) if period.get('group_start')},
        },
        'statements': sections,
        'appendix': {
            'title': _t(lang, 'methodology_note_title'),
            'benchmark_note': ctx['benchmark_note'],
            'notes': ctx['methodology_notes'],
            'covenant_note_title': ctx['covenant_note_title'],
        },
    }


def generate_full_pdf_async(report: dict[str, Any], lang: str = 'en', theme: str = 'dark') -> bytes:
    from src.reportlab_pdf_exporter import generate_full_pdf_async as _generate_full_pdf_async

    return _generate_full_pdf_async(report, lang, theme)


def generate_full_pdf(report: dict[str, Any], lang: str = 'en', theme: str = 'dark') -> bytes:
    from src.reportlab_pdf_exporter import generate_full_pdf as _generate_full_pdf

    return _generate_full_pdf(report, lang, theme)


__all__ = [
    'build_pdf_context',
    'build_pdf_document_model',
    'generate_full_pdf',
    'generate_full_pdf_async',
    '_build_yoy_map',
    '_format_period_label',
    '_is_negative_display_value',
]
