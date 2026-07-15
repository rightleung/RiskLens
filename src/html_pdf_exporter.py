from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from src.services._utils import safe_number as _safe_number
from src.statement_i18n import STATEMENT_I18N
from src.config import settings

LANG = {
    'en': {
        'report_title': 'RiskLens Financial Report',
        'credit_health_summary': 'Credit Health Summary',
        'executive_summary': 'Executive Summary',
        'company_profile': 'Company Profile',
        'sector': 'Sector',
        'industry': 'Industry',
        'country': 'Country',
        'employees': 'Employees',
        'website': 'Website',
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
        'methodology_altman_note': 'Altman Z: weighted model based on working capital, retained earnings, EBIT, market value, and sales; market value can dominate for mega-cap public companies.',
        'methodology_zone_note': 'Zone: >2.99 Safe, 1.81-2.99 Grey, <1.81 Distress.',
        'methodology_rating_note': 'Rating: implied rating mapped from Z-Score and historical default rates.',
        'methodology_reference_note': 'Methodology definitions are provided in the appendix.',
        'insufficient_data': 'Insufficient Data',
        'breach': 'Breach',
        'pass': 'Pass',
        'not_evaluated': 'Not Evaluated',
        'missing_data_breach_note': 'Data unavailable; defaulting to breach pending manual verification.',
        'data_source': 'Data Source',
        'disclaimer': 'Disclaimer',
        'disclaimer_text': 'This report is generated from available public data and is for due-diligence support only. It is not investment, legal, tax, or accounting advice.',
        'failed_periods': 'Failed Periods',
        'latest_period_valid': 'Latest Period Valid',
        'quality_status': 'Quality Status',
        'yes': 'Yes',
        'no': 'No',
        'statement_summary_note': 'Summary view. Detailed line items are moved to the appendix.',
        'statement_appendix_title': 'Statement Detail Appendix',
        'values_in_currency_millions': 'Values in {currency} millions',
        'values_in_currency_billions': 'Values in {currency} billions; ratios in x',
    },
    'zh-CN': {
        'report_title': 'RiskLens 风险分析报告',
        'credit_health_summary': '信用健康摘要',
        'executive_summary': '执行摘要',
        'company_profile': '公司概况',
        'sector': '行业板块',
        'industry': '细分行业',
        'country': '国家/地区',
        'employees': '员工人数',
        'website': '公司网站',
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
        'methodology_altman_note': 'Altman Z：基于营运资本、留存收益、EBIT、市值、营收的加权模型；对超大市值上市公司，市值项可能主导分数。',
        'methodology_zone_note': 'Zone：>2.99 Safe，1.81-2.99 Grey，<1.81 Distress。',
        'methodology_rating_note': 'Rating：基于 Z 分数与历史违约率映射的隐含评级。',
        'methodology_reference_note': '指标定义见附录。',
        'insufficient_data': '数据不足',
        'breach': '违约',
        'pass': '通过',
        'not_evaluated': '未评估',
        'missing_data_breach_note': '数据不可用；在人工核实前按违约处理。',
        'data_source': '数据来源',
        'disclaimer': '免责声明',
        'disclaimer_text': '本报告基于可获得的公开数据生成，仅用于尽职调查辅助，不构成投资、法律、税务或会计建议。',
        'failed_periods': '失败期间',
        'latest_period_valid': '最新期间有效',
        'quality_status': '质量状态',
        'yes': '是',
        'no': '否',
        'statement_summary_note': '正文仅展示摘要，完整明细已移至附录。',
        'statement_appendix_title': '报表明细附录',
        'values_in_currency_millions': '单位：{currency} 百万',
        'values_in_currency_billions': '单位：{currency} 十亿；比率以 x 表示',
    },
    'zh-TW': {
        'report_title': 'RiskLens 風險分析報告',
        'credit_health_summary': '信用健康摘要',
        'executive_summary': '執行摘要',
        'company_profile': '公司概況',
        'sector': '行業板塊',
        'industry': '細分行業',
        'country': '國家/地區',
        'employees': '員工人數',
        'website': '公司網站',
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
        'methodology_altman_note': 'Altman Z：基於營運資本、保留盈餘、EBIT、市值、營收的加權模型；對超大市值上市公司，市值項可能主導分數。',
        'methodology_zone_note': 'Zone：>2.99 Safe，1.81-2.99 Grey，<1.81 Distress。',
        'methodology_rating_note': 'Rating：基於 Z 分數與歷史違約率映射的隱含評等。',
        'methodology_reference_note': '指標定義見附錄。',
        'insufficient_data': '資料不足',
        'breach': '違約',
        'pass': '通過',
        'not_evaluated': '未評估',
        'missing_data_breach_note': '資料不可用；人工核實前按違約處理。',
        'data_source': '資料來源',
        'disclaimer': '免責聲明',
        'disclaimer_text': '本報告依據可取得的公開資料產生，僅供盡職調查參考，不構成投資、法律、稅務或會計建議。',
        'failed_periods': '失敗期間',
        'latest_period_valid': '最新期間有效',
        'quality_status': '品質狀態',
        'yes': '是',
        'no': '否',
        'statement_summary_note': '正文僅展示摘要，完整明細已移至附錄。',
        'statement_appendix_title': '報表明細附錄',
        'values_in_currency_millions': '單位：{currency} 百萬',
        'values_in_currency_billions': '單位：{currency} 十億；比率以 x 表示',
    },
    'ja': {
        'report_title': 'RiskLens 財務レポート',
        'credit_health_summary': 'クレジット健全性サマリー',
        'executive_summary': 'エグゼクティブサマリー',
        'company_profile': '会社概要',
        'sector': 'セクター',
        'industry': '業界',
        'country': '国/地域',
        'employees': '従業員数',
        'website': 'ウェブサイト',
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
        'methodology_altman_note': 'Altman Z: 運転資本、利益剰余金、EBIT、市場価値、売上高の加重モデル。超大型時価総額の上場企業では時価総額項目が支配的になりやすいです。',
        'methodology_zone_note': 'Zone: >2.99 Safe、1.81-2.99 Grey、<1.81 Distress。',
        'methodology_rating_note': 'Rating: Zスコアと歴史的デフォルト率を対応付けた推定格付け。',
        'methodology_reference_note': '指標定義は付録に記載しています。',
        'insufficient_data': 'データ不足',
        'breach': '違反',
        'pass': '合格',
        'not_evaluated': '未評価',
        'missing_data_breach_note': 'データが利用できないため、手動確認まで違反として扱います。',
        'data_source': 'データソース',
        'disclaimer': '免責事項',
        'disclaimer_text': '本レポートは利用可能な公開データに基づくデューデリジェンス支援資料であり、投資・法務・税務・会計上の助言ではありません。',
        'failed_periods': '失敗期間',
        'latest_period_valid': '最新期間の有効性',
        'quality_status': '品質ステータス',
        'yes': 'はい',
        'no': 'いいえ',
        'statement_summary_note': '本文は要約表示です。詳細項目は付録に移動しています。',
        'statement_appendix_title': '財務諸表詳細付録',
        'values_in_currency_millions': '単位: {currency} 百万',
        'values_in_currency_billions': '単位: {currency} 十億、倍率は x',
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
SUMMARY_STATEMENT_LABELS = {
    'income_statement': (
        'Revenue',
        'Total Revenue',
        'Gross Profit',
        'Operating Income',
        'EBIT',
        'EBITDA',
        'Net Income',
        'Normalized Income',
    ),
    'balance_sheet': (
        'Cash',
        'Cash and Cash Equivalents',
        'Working Capital',
        'Total Assets',
        'Current Assets',
        'Total Debt',
        'Net Debt',
        'Total Liabilities',
        'Current Liabilities',
        'Stockholders Equity',
        'Total Equity',
    ),
    'cash_flow_statement': (
        'Operating CF',
        'Operating Cash Flow',
        'Investing Cash Flow',
        'Financing Cash Flow',
        'Capital Expenditure',
        'Capex',
        'Free CF',
        'Free Cash Flow',
        'Repurchase of Capital Stock',
        'Cash Dividends Paid',
    ),
}
TOTAL_LABEL_HINTS = (
    'total',
    'gross profit',
    'operating income',
    'net income',
    'ebit',
    'ebitda',
    'free cash flow',
    'working capital',
    'stockholders equity',
)

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


def _t_statement(lang: str, raw_label: str) -> str:
    """Translate a financial statement line-item label.

    Normalizes *raw_label* to the STATEMENT_I18N key format and returns
    the localized label, or the original if no translation exists.
    """
    if lang == 'en':
        return raw_label
    key = raw_label.strip().lower().replace(' ', '_').replace('-', '_')
    for ch in "()[]{}.,;:'\"!/?":
        key = key.replace(ch, '')
    key = key.strip('_')
    entry = STATEMENT_I18N.get(key)
    if entry is None:
        key = key.replace('__', '_')
        entry = STATEMENT_I18N.get(key)
    return entry.get(lang, raw_label) if entry else raw_label


# -- Strength / weakness text translations (ported from web/src/translations.ts) --

_ASSESSMENT_I18N: dict[str, dict[str, str]] = {
    "Low leverage": {
        "en": "Low leverage", "zh-CN": "低杠杆", "zh-TW": "低槓桿", "ja": "低レバレッジ",
    },
    "Strong interest coverage": {
        "en": "Strong interest coverage", "zh-CN": "强劲的利息保障倍数", "zh-TW": "強勁的利息保障倍數", "ja": "強固なインタレストカバレッジ",
    },
    "Healthy liquidity position": {
        "en": "Healthy liquidity position", "zh-CN": "健康的流动性状况", "zh-TW": "健康的流動性狀況", "ja": "健全な流動性ポジション",
    },
    "Healthy liquidity": {
        "en": "Healthy liquidity", "zh-CN": "健康的流动性", "zh-TW": "健康的流動性", "ja": "健全な流動性",
    },
    "Good liquidity": {
        "en": "Good liquidity", "zh-CN": "良好的流动性", "zh-TW": "良好的流動性", "ja": "良好な流動性",
    },
    "Strong profitability margins": {
        "en": "Strong profitability margins", "zh-CN": "强劲的利润率", "zh-TW": "強勁的利潤率", "ja": "強固な利益率",
    },
    "Strong profitability": {
        "en": "Strong profitability", "zh-CN": "强劲的盈利能力", "zh-TW": "強勁的盈利能力", "ja": "強い収益性",
    },
    "Strong free cash flow generation": {
        "en": "Strong free cash flow generation", "zh-CN": "强劲的自由现金流生成", "zh-TW": "強勁的自由現金流生成", "ja": "強力なフリーキャッシュフロー創出",
    },
    "Strong free cash flow": {
        "en": "Strong free cash flow", "zh-CN": "强劲的自由现金流", "zh-TW": "強勁的自由現金流", "ja": "強力なフリーキャッシュフロー",
    },
    "Conservative debt level": {
        "en": "Conservative debt level", "zh-CN": "保守的债务水平", "zh-TW": "保守的債務水平", "ja": "保守的な負債水準",
    },
    "High financial leverage": {
        "en": "High financial leverage", "zh-CN": "高财务杠杆", "zh-TW": "高財務槓桿", "ja": "高い財務レバレッジ",
    },
    "High leverage": {
        "en": "High leverage", "zh-CN": "高杠杆", "zh-TW": "高槓桿", "ja": "高レバレッジ",
    },
    "Weak interest coverage": {
        "en": "Weak interest coverage", "zh-CN": "利息保障倍数较弱", "zh-TW": "利息保障倍數較弱", "ja": "弱いインタレストカバレッジ",
    },
    "Tight liquidity": {
        "en": "Tight liquidity", "zh-CN": "流动性紧张", "zh-TW": "流動性緊張", "ja": "ひっ迫した流動性",
    },
    "Weak liquidity": {
        "en": "Weak liquidity", "zh-CN": "流动性较弱", "zh-TW": "流動性較弱", "ja": "流動性が弱い",
    },
    "Negative or weak profitability": {
        "en": "Negative or weak profitability", "zh-CN": "盈利能力弱或为负", "zh-TW": "盈利能力弱或為負", "ja": "収益性がマイナスまたは弱い",
    },
    "Weak profitability": {
        "en": "Weak profitability", "zh-CN": "盈利能力较弱", "zh-TW": "盈利能力較弱", "ja": "弱い収益性",
    },
    "Negative free cash flow": {
        "en": "Negative free cash flow", "zh-CN": "负自由现金流", "zh-TW": "負自由現金流", "ja": "マイナスのフリーキャッシュフロー",
    },
    "Excessive debt burden": {
        "en": "Excessive debt burden", "zh-CN": "过度的债务负担", "zh-TW": "過度的債務負擔", "ja": "過剰な負債負担",
    },
    "Moderate leverage": {
        "en": "Moderate leverage", "zh-CN": "适度杠杆", "zh-TW": "適度槓桿", "ja": "適度なレバレッジ",
    },
}

_METRIC_LABEL_I18N: dict[str, dict[str, str]] = {
    "Debt/EBITDA": {"zh-CN": "债务/EBITDA", "zh-TW": "債務/EBITDA", "ja": "有利子負債/EBITDA"},
    "Current Ratio": {"zh-CN": "流动比率", "zh-TW": "流動比率", "ja": "流動比率"},
    "of debt": {"zh-CN": "占总债务", "zh-TW": "占總債務", "ja": "対負債"},
}


def _translate_assessment_text(text: str, lang: str) -> str:
    """Translate a strength/weakness assessment phrase.

    Handles exact matches, prefix matches (with parenthetical data kept),
    and substring fallback — mirroring the frontend's translateAssessmentText.
    """
    if lang == "en":
        return text

    # Exact match
    entry = _ASSESSMENT_I18N.get(text)
    if entry:
        return entry.get(lang, text)

    # Prefix match — e.g. "Low leverage (Debt/EBITDA: 2.1)" matches "Low leverage"
    lower_text = text.lower()
    for key, entry in _ASSESSMENT_I18N.items():
        if lower_text.startswith(key.lower()):
            remainder = text[len(key):]
            # Translate embedded metric labels in parenthetical
            for en_label, label_i18n in _METRIC_LABEL_I18N.items():
                trans = label_i18n.get(lang)
                if trans:
                    remainder = remainder.replace(en_label, trans)
            return entry.get(lang, key) + remainder

    # Substring fallback
    for key, entry in _ASSESSMENT_I18N.items():
        if key.lower() in lower_text:
            translated = entry.get(lang, key)
            pattern = re.compile(re.escape(key), re.IGNORECASE)
            return pattern.sub(translated, text)

    return text


def _lang(lang: str | None) -> str:
    if lang in LANG:
        return lang or 'en'
    return 'en'


def _t(lang: str, key: str) -> str:
    return LANG.get(lang, LANG['en']).get(key, key)


def _resolve_localized_name(raw: Any, lang: str, fallback: str = '') -> str:
    """Extract a localized company name from a dict like {'en': 'Apple', 'zh-CN': '苹果'}.

    Non-English exports intentionally require an exact language entry.  Using
    the English name as a second "localized" line makes the cover look broken
    and hides missing translation data.
    """
    if isinstance(raw, dict) and raw:
        val = raw.get(lang)
        if val and str(val).strip():
            return str(val).strip()
        if lang == 'en':
            english = raw.get('en')
            return str(english).strip() if english and str(english).strip() else fallback
        return ''
    if isinstance(raw, str) and raw.strip():
        return raw
    return fallback if lang == 'en' else ''


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


def _format_plain_number(value: float, decimals: int = 1) -> str:
    if float(value).is_integer():
        return f'{value:,.0f}'
    if abs(value) < 1:
        return f'{value:,.2f}'
    return f'{value:,.{decimals}f}'


def _format_statement_millions_value(value: Any, label: Any = None) -> str:
    text = _clean_display_text(value)
    if not text:
        return '--'
    lowered = text.lower()
    if lowered in {'--', 'n/a', 'na', 'no data available'}:
        return 'N/A' if lowered in {'n/a', 'na'} else '--'

    number = _statement_value_to_millions(value, label)
    if number is None:
        return text
    return _format_plain_number(number)


def _format_statement_billions_value(value: Any, label: Any = None) -> str:
    text = _clean_display_text(value)
    if not text:
        return '--'
    lowered = text.lower()
    if lowered in {'--', 'n/a', 'na', 'no data available'}:
        return 'N/A' if lowered in {'n/a', 'na'} else '--'

    number = _statement_value_to_millions(value, label)
    if number is None:
        return text
    if _statement_label_supports_magnitude(label):
        return _format_plain_number(number / 1000, decimals=1)
    return _format_plain_number(number)


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
    'profit',
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
_DECIMAL_COMMA_RE = re.compile(r'^(?P<num>[+-]?\d+),(?P<decimal>\d{1,2})$')


def _statement_label_supports_magnitude(label: Any) -> bool:
    text = _clean_display_text(label).lower()
    if not text or text in {'--', 'n/a', 'na', 'no data available'}:
        return False
    if any(re.search(rf'(?<![a-z]){re.escape(blocker)}(?![a-z])', text) for blocker in _STATEMENT_MAGNITUDE_LABEL_BLOCKERS):
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


def _statement_value_to_millions(value: Any, label: Any = None) -> float | None:
    text = _clean_display_text(value)
    if not text or text.lower() in {'--', 'n/a', 'na', 'no data available'}:
        return None
    if isinstance(value, str):
        compact = text.replace(' ', '')
        decimal_comma = _DECIMAL_COMMA_RE.fullmatch(compact)
        if decimal_comma:
            compact = f"{decimal_comma.group('num')}.{decimal_comma.group('decimal')}"
        unit_match = _MAGNITUDE_SUFFIX_RE.fullmatch(compact) or _OCR_STRAY_UNIT_PUNCT_RE.fullmatch(compact)
        if unit_match:
            number = _safe_number(unit_match.group('num'))
            if number is None:
                return None
            unit = unit_match.group('unit').lower()
            if unit == 'b':
                return number * 1000
            if unit == 'm':
                return number
            if unit == 'k':
                return number / 1000
        ocr_match = _OCR_MAGNITUDE_SUFFIX_RE.fullmatch(compact)
        if ocr_match:
            number = _safe_number(ocr_match.group('num'))
            if number is not None and abs(number) >= 10:
                return number * 1000
        number = _safe_number(compact)
        if number is not None and _statement_label_supports_magnitude(label):
            if abs(number) >= 1_000_000:
                return number / 1_000_000
            return number
    number = _safe_number(value)
    if number is None:
        return None
    if abs(number) >= 1_000_000:
        return number / 1_000_000
    return number


def _format_statement_display_value(value: Any, label: Any = None) -> str:
    return _format_statement_millions_value(value, label)


def _format_ratio_value(label: str, value: Any) -> str:
    if value is None:
        return 'N/A'
    text = _format_value(value)
    if text == '--':
        return 'N/A'
    return f'{text}x' if label in RATIO_METRICS else text


def _format_kpi_metric_value(value: Any, label: Any = None) -> str:
    if value is None:
        return 'N/A'
    number = _safe_number(value)
    if number is None:
        return _format_value(value)
    return _format_magnitude_display(number)


def _format_kpi_table_value(value: Any, label: Any = None) -> str:
    if value is None:
        return 'N/A'
    number = _safe_number(value)
    if number is None:
        return _format_value(value)
    if label in RATIO_METRICS:
        return _format_plain_number(number, decimals=2)
    return _format_plain_number(number / 1_000_000_000, decimals=1)


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
    """Return a sortable ``(year, quarter, kind)`` key for report periods."""
    if not label:
        return (0, 0, 0)
    text = str(label).strip().upper().replace("’", "'")
    # Upstream payloads use both ``25Q3`` and presentation-friendly forms such
    # as ``Q3 FY25``/``Q3 '25``.  Normalize all of them before sorting.
    quarter = re.match(r'^(?:FY)?(?P<year>\d{2,4})\s*Q(?P<quarter>[1-4])$', text)
    if not quarter:
        quarter = re.match(r'^Q(?P<quarter>[1-4])\s*(?:FY\s*)?[\']?(?P<year>\d{2,4})$', text)
    if quarter:
        year = int(quarter.group('year'))
        if year < 100:
            year += 2000
        return (year, int(quarter.group('quarter')), 1)
    annual = re.match(r'^(?:FY\s*)?(?P<year>\d{2,4})$', text)
    if annual:
        year = int(annual.group('year'))
        if year < 100:
            year += 2000
        return (year, 0, 0)
    return (0, 0, 0)


def _period_kind(label: str | None) -> str:
    year, quarter, kind = _period_key(label)
    if not year:
        return 'unknown'
    if kind == 1 and quarter:
        return 'quarter'
    if kind == 0:
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


def _select_pdf_history(history: list[dict[str, Any]], max_periods: int) -> list[dict[str, Any]]:
    """Select one consistent, bounded set of periods for the complete PDF.

    Quarterly reports keep the latest quarter, the prior-year matching quarter
    when available, and the latest annual periods.  Other quarters are ignored
    so the report never presents an orphaned sequential-quarter comparison.
    Annual-only reports retain the latest four annual periods.  The caller's
    limit is applied after these semantic choices and never changes the
    quarter/annual filtering rules.
    """
    entries = [item for item in history if isinstance(item, dict)]
    entries.sort(
        key=lambda item: _period_key(str(item.get('fiscal_year') or item.get('period') or item.get('label') or '')),
        reverse=True,
    )
    limit = max(1, int(max_periods or 1))
    if not entries:
        return []

    def period_value(item: dict[str, Any]) -> str:
        return str(item.get('fiscal_year') or item.get('period') or item.get('label') or '')
    latest_kind = _period_kind(period_value(entries[0]))
    annuals = [item for item in entries if _period_kind(period_value(item)) == 'annual']
    if latest_kind == 'annual':
        return annuals[: min(4, limit)]
    if latest_kind != 'quarter':
        return entries[:limit]

    selected: list[dict[str, Any]] = [entries[0]]
    latest_year, latest_quarter, _ = _period_key(period_value(entries[0]))
    matching_prior = next(
        (
            item for item in entries[1:]
            if _period_kind(period_value(item)) == 'quarter'
            and _period_key(period_value(item))[0] == latest_year - 1
            and _period_key(period_value(item))[1] == latest_quarter
        ),
        None,
    )
    if matching_prior is not None:
        selected.append(matching_prior)
    selected.extend(annuals[:3])

    # De-duplicate periods defensively, then apply the configured bound.
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in selected:
        key = period_value(item).strip().upper()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:limit]


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


def _normalize_covenant_state(
    status: Any,
    signal: Any,
    actual_missing: bool,
    lang: str,
) -> tuple[str, str, str]:
    """Normalize covenant state without weakening conservative missing-data semantics."""
    status_text = _clean_display_text(status)
    signal_text = _clean_display_text(signal)
    status_lower = status_text.lower()
    signal_lower = signal_text.lower()
    unknown_status = {
        '', '--', 'n/a', 'na', 'insufficient data',
        _t(lang, 'insufficient_data').lower(),
    }
    unknown_signal = {'', '--', 'n/a', 'na', 'neutral'}

    if actual_missing:
        if status_lower in unknown_status:
            status_text = _t(lang, 'breach')
        if signal_lower in unknown_signal:
            signal_text = 'Red'
    else:
        if status_lower in unknown_status:
            if signal_lower in {'green', 'pass', 'safe', 'ok'}:
                status_text = _t(lang, 'pass')
            elif signal_lower in {'red', 'fail', 'breach', 'risk'}:
                status_text = _t(lang, 'breach')
            else:
                status_text = _t(lang, 'not_evaluated')
        if signal_lower in unknown_signal:
            normalized_status = status_text.lower()
            if normalized_status in {'pass', 'safe', 'ok', _t(lang, 'pass').lower()}:
                signal_text = 'Green'
            elif normalized_status in {'fail', 'breach', 'risk', _t(lang, 'breach').lower()}:
                signal_text = 'Red'
            else:
                signal_text = 'Neutral'

    return status_text or _t(lang, 'not_evaluated'), signal_text or 'Neutral', _signal_tone(signal_text, status_text)


def _normalize_data_quality_rows(raw_quality: Any, lang: str) -> list[dict[str, str]]:
    """Normalize both current report-level and legacy entry-level quality payloads."""
    if not raw_quality:
        return []

    if isinstance(raw_quality, dict) and any(
        key in raw_quality for key in ('status', 'failed_periods', 'latest_period_valid')
    ):
        rows: list[dict[str, str]] = []
        if raw_quality.get('status') not in (None, ''):
            rows.append({
                'label': _t(lang, 'quality_status'),
                'value': _clean_display_text(raw_quality.get('status')),
                'notes': '--',
            })
        failed_periods = raw_quality.get('failed_periods')
        if isinstance(failed_periods, (list, tuple, set)):
            failed_value = ', '.join(
                _clean_display_text(item) for item in failed_periods if _clean_display_text(item)
            ) or '--'
        else:
            failed_value = _clean_display_text(failed_periods) or '--'
        rows.append({
            'label': _t(lang, 'failed_periods'),
            'value': failed_value,
            'notes': '--',
        })
        latest_valid = raw_quality.get('latest_period_valid')
        if isinstance(latest_valid, bool):
            valid_value = _t(lang, 'yes') if latest_valid else _t(lang, 'no')
        else:
            valid_value = _clean_display_text(latest_valid) or '--'
        rows.append({
            'label': _t(lang, 'latest_period_valid'),
            'value': valid_value,
            'notes': '--',
        })
        return rows

    rows = []
    if isinstance(raw_quality, dict):
        for key, value in raw_quality.items():
            if isinstance(value, dict):
                label = _normalize_label_text(value.get('label') or key)
                rows.append({
                    'label': label,
                    'value': _format_data_quality_value(label, value.get('value') or value.get('score') or value.get('status')),
                    'notes': str(value.get('notes') or value.get('note') or '--'),
                })
            else:
                label = _normalize_label_text(key)
                rows.append({
                    'label': label,
                    'value': _format_data_quality_value(label, value),
                    'notes': '--',
                })
    elif isinstance(raw_quality, list):
        for item in raw_quality:
            if isinstance(item, dict):
                label = _normalize_label_text(item.get('label') or item.get('name') or '--')
                rows.append({
                    'label': label,
                    'value': _format_data_quality_value(label, item.get('value') or item.get('score') or item.get('status')),
                    'notes': str(item.get('notes') or item.get('note') or '--'),
                })
    return rows


def _extract_summary(
    entry: dict[str, Any],
    lang: str = 'en',
    report_quality: Any = None,
) -> dict[str, Any]:
    assessment = _mapping(entry.get('assessment'))
    strengths = [
        _translate_assessment_text(s, lang)
        for s in _extract_texts(assessment.get('strengths') or entry.get('strengths'))
    ]
    watch_items = [
        _translate_assessment_text(s, lang)
        for s in _extract_texts(
            assessment.get('watch_items')
            or assessment.get('concerns')
            or assessment.get('weaknesses')
            or entry.get('watch_items')
            or entry.get('concerns')
            or entry.get('weaknesses')
            or entry.get('risks')
        )
    ]
    covenant_rows: list[dict[str, str]] = []
    for item in _sequence(assessment.get('covenant_pre_check') or assessment.get('covenants') or entry.get('covenant_pre_check') or entry.get('covenants')):
        if isinstance(item, dict):
            actual_value = item.get('actual') if 'actual' in item else item.get('value')
            threshold_value = item.get('threshold') if 'threshold' in item else item.get('limit') if 'limit' in item else item.get('target')
            actual_missing = _safe_number(actual_value) is None
            status, signal, status_tone = _normalize_covenant_state(
                item.get('status') or item.get('result'),
                item.get('signal') or item.get('direction'),
                actual_missing,
                lang,
            )
            status_signal = status
            metric_name = _normalize_label_text(item.get('metric') or item.get('label') or item.get('name') or '--')
            description = _covenant_description(lang, metric_name)
            covenant_rows.append({
                'metric': metric_name,
                'actual': 'N/A' if actual_missing else _format_value(actual_value),
                'threshold': _format_value(threshold_value),
                'status': status,
                'signal': signal,
                'status_signal': status_signal,
                'status_signal_tone': status_tone,
                'notes': (
                    _clean_display_text(item.get('notes') or item.get('note'))
                    or _t(lang, 'missing_data_breach_note')
                ) if actual_missing else _clean_display_text(item.get('notes') or item.get('note') or '--'),
                'description': description,
            })
    if not covenant_rows:
        covenant_rows = _build_covenant_fallback_rows(entry, lang)
    raw_quality = report_quality or assessment.get('data_quality') or entry.get('data_quality') or entry.get('quality') or {}
    data_quality = _normalize_data_quality_rows(raw_quality, lang)
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
            'threshold': 1.2,
            'passed_note': 'Healthy liquidity',
            'failed_note': 'Weak liquidity',
            'passes': lambda actual, threshold: actual is not None and actual >= threshold,
            'signal': ('Green', 'Red'),
        },
    ]

    rows: list[dict[str, str]] = []
    for spec in specs:
        actual = pick_number(spec['candidates'])
        threshold = float(spec['threshold'])
        metric_name = _normalize_label_text(spec['metric'])
        if actual is None:
            rows.append({
                'metric': metric_name,
                'actual': 'N/A',
                'threshold': _format_value(threshold),
                'status': _t(lang, 'breach'),
                'signal': 'Red',
                'status_signal': _t(lang, 'breach'),
                'status_signal_tone': 'danger',
                'notes': _t(lang, 'missing_data_breach_note'),
                'description': _covenant_description(lang, metric_name),
            })
            continue
        is_pass = bool(spec['passes'](actual, threshold))
        signal = spec['signal'][0] if is_pass else spec['signal'][1]
        status = 'Pass' if is_pass else 'Fail'
        rows.append({
            'metric': metric_name,
            'actual': _format_value(actual),
            'threshold': _format_value(threshold),
            'status': status,
            'signal': signal,
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


def _extract_profile(report: dict[str, Any], latest: dict[str, Any], lang: str = 'en') -> list[dict[str, str]]:
    profile = report.get('company_profile') or latest.get('company_profile') or {}
    rows: list[dict[str, str]] = []
    if isinstance(profile, dict):
        # Prefer an exact localized description when the upstream profile
        # provides one; otherwise retain the English text with an explicit
        # label so the reader knows it was not translated.
        description_value = profile.get('description')
        description_is_english = False
        if isinstance(description_value, dict):
            localized = description_value.get(lang)
            if localized not in (None, ''):
                description_value = localized
            else:
                description_value = description_value.get('en')
                description_is_english = lang != 'en'
        if lang != 'en':
            for key in (f'description_{lang}', f'description-{lang}', f'description{lang}'):
                if profile.get(key) not in (None, ''):
                    description_value = profile[key]
                    description_is_english = False
                    break
            else:
                description_is_english = bool(description_value not in (None, ''))
        for key, value in profile.items():
            if str(key).lower() != 'description':
                if str(key).lower().startswith('description_') or str(key).lower().startswith('description-'):
                    continue
            if str(key).lower() == 'description':
                value = description_value
            if value in (None, '', [], {}):
                continue
            if isinstance(value, dict):
                value = value.get('value') or value.get('text') or value.get('name') or '--'
            if isinstance(value, (list, tuple, set)):
                value = ', '.join(_clean_display_text(item) for item in value if _clean_display_text(item))
            translated = _t(lang, key)
            label = translated if translated != key else _normalize_label_text(key)
            if str(key).lower() == 'description' and description_is_english and lang != 'en':
                label = f'{label} (English)'
            display_value = _format_value(value)
            if str(key).lower() == 'description' and len(display_value) > 900:
                display_value = display_value[:897].rstrip() + '...'
            if not label or display_value in {'', '--', 'N/A', 'n/a', '[]', '{}'}:
                continue
            rows.append({'label': label, 'value': display_value})
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
            _format_kpi_table_value(v, label)
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


def _statement_label_depth(label: Any) -> int:
    text = _clean_display_text(label)
    lowered = text.lower()
    if not text or any(hint in lowered for hint in TOTAL_LABEL_HINTS):
        return 0
    if any(token in lowered for token in ('current ', 'non current', 'operating ', 'investing ', 'financing ')):
        return 1
    return 2


def _is_statement_total(label: Any) -> bool:
    lowered = _clean_display_text(label).lower()
    return any(hint in lowered for hint in TOTAL_LABEL_HINTS)


def _statement_yoy_tone(value: Any) -> str:
    text = _clean_display_text(value)
    if not text or text in {'--', 'N/A', 'n/a', 'N/M'}:
        return 'neutral'
    number = _safe_number(text)
    if number is None:
        return 'neutral'
    if abs(number) >= 100:
        return 'alert'
    if abs(number) >= 50:
        return 'warning'
    return 'neutral'


def _summary_label_set(statement_key: str) -> set[str]:
    return {_normalize_key(label) for label in SUMMARY_STATEMENT_LABELS.get(statement_key, ())}


def _dedupe_statement_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for row in rows:
        key = (
            _normalize_key(str(row.get('label') or '')),
            tuple(str(value) for value in row.get('detail_display_values') or row.get('values', [])),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


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
        # Pre-build per-period label→value maps to avoid O(N) next(...) scans
        rows_by_period_maps: list[dict[str, Any]] = [
            {str(r.get('label') or '--'): r.get('value') for r in rows}
            for rows in rows_by_period
        ]

        detail_rows: list[dict[str, Any]] = []
        for label in labels:
            values: list[Any] = []
            for rows_map in rows_by_period_maps:
                matched = rows_map.get(label)
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
            row = {
                'label': label,
                'raw_values': values,
                'values': [_format_statement_millions_value(v, label) for v in values],
                'summary_display_values': [_format_statement_billions_value(v, label) for v in values],
                'detail_display_values': [_format_statement_millions_value(v, label) for v in values],
                'yoy_q': yoy_q,
                'yoy_fy': yoy_fy,
                'level': _statement_label_depth(label),
                'depth': _statement_label_depth(label),
                'is_total': _is_statement_total(label),
                'yoy_q_tone': _statement_yoy_tone(yoy_q),
                'yoy_fy_tone': _statement_yoy_tone(yoy_fy),
            }
            detail_rows.append(row)
        detail_rows = _dedupe_statement_rows(detail_rows)
        summary_labels = _summary_label_set(statement_key)
        summary_rows = [
            row for row in detail_rows
            if _normalize_key(str(row.get('label') or '')) in summary_labels or row.get('is_total')
        ]
        if not summary_rows:
            summary_rows = detail_rows[:12]
        max_detail_rows = max(1, settings.max_pdf_detail_rows)
        if len(detail_rows) > max_detail_rows:
            detail_rows = detail_rows[:max_detail_rows]
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
            'rows': summary_rows,
            'detail_rows': detail_rows,
            'level_field': 'level',
            'unit_note': '',
            'detail_unit_note': '',
        })
    return sections


def build_pdf_context(report: dict[str, object], lang: str = 'en', theme: str = 'dark') -> dict[str, object]:
    lang = _lang(lang)
    theme = 'light' if str(theme).lower() == 'light' else 'dark'
    history = _select_pdf_history(_extract_history(report), settings.max_pdf_periods)
    if not history:
        raise ValueError('No history available')
    latest = history[0]
    periods = [str(entry.get('fiscal_year') or entry.get('period') or entry.get('label') or '--') for entry in history]
    period_labels = [_format_period_label(p) for p in periods]
    summary = _extract_summary(latest, lang, report.get('data_quality'))
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
    if lang != 'en':
        for section in statement_sections:
            for row in section.get('detail_rows', []):
                row['label'] = _t_statement(lang, str(row.get('label', '')))
            for row in section.get('rows', []):
                row['label'] = _t_statement(lang, str(row.get('label', '')))
    currency = str(report.get('currency') or latest.get('currency') or latest.get('reporting_currency') or '--')
    for section in statement_sections:
        section['yoy_label_q'] = _format_yoy_label(lang, section.get('current_quarter_period'), section.get('compare_quarter_period'))
        section['yoy_label_fy'] = _format_yoy_label(lang, section.get('current_annual_period'), section.get('compare_annual_period'))
        section['yoy_note'] = yoy_note
        section['unit_note'] = _t(lang, 'values_in_currency_billions').format(currency=currency)
        section['detail_unit_note'] = _t(lang, 'values_in_currency_millions').format(currency=currency)
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
    localized_name = '' if lang == 'en' else _resolve_localized_name(
        report.get('company_name_localized') or latest.get('company_name_localized'),
        lang,
        fallback=str(report.get('company_name') or latest.get('company_name') or ''),
    )
    company_name = str(report.get('company_name') or latest.get('company_name') or latest.get('name') or 'Unknown Company')
    if localized_name and re.sub(r'\s+', ' ', localized_name).strip().casefold() == re.sub(r'\s+', ' ', company_name).strip().casefold():
        localized_name = ''
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
        'company_name': company_name,
        'company_name_localized': localized_name,
        'ticker': str(report.get('ticker') or latest.get('ticker') or '--'),
        'currency': currency,
        'data_source': _clean_display_text(report.get('data_source') or report.get('source') or 'Unknown'),
        'disclaimer': _t(lang, 'disclaimer_text'),
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
        'company_profile_rows': _extract_profile(report, latest, lang),
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


def build_pdf_document_model(report: dict[str, object], lang: str = 'en', theme: str = 'dark') -> dict[str, object]:
    ctx = build_pdf_context(report, lang, theme)
    sections: list[dict[str, Any]] = []
    for section in ctx['statement_sections']:
        widths = [0.20] + [0.085] * len(section['periods']) + [0.16, 0.16]
        headers = [_t(lang, 'metric')] + [p['label'] for p in section['periods']] + [section['yoy_label_q'], section['yoy_label_fy']]
        table_rows = [
            [row['label'], *(row.get('summary_display_values') or row.get('values', [])), row['yoy_q'], row['yoy_fy']]
            for row in section['rows']
        ]
        detail_table_rows = [
            [row['label'], *(row.get('detail_display_values') or row.get('values', [])), row['yoy_q'], row['yoy_fy']]
            for row in section.get('detail_rows', [])
        ]
        sections.append({
            'key': section['key'],
            'title': section['title'],
            'display_title': ctx['labels'][section['title']],
            'periods': section['periods'],
            'headers': headers,
            'rows': section['rows'],
            'detail_rows': section.get('detail_rows', []),
            'table_rows': table_rows,
            'detail_table_rows': detail_table_rows,
            'widths': widths,
            'benchmark_cols': set(),
            'group_break_cols': {1 + idx for idx, period in enumerate(section['periods']) if period.get('group_start')},
            'yoy_label_q': section['yoy_label_q'],
            'yoy_label_fy': section['yoy_label_fy'],
            'yoy_note': section['yoy_note'],
            'unit_note': section.get('unit_note', ''),
            'detail_unit_note': section.get('detail_unit_note', ''),
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
            'data_source': ctx['data_source'],
            'disclaimer': ctx['disclaimer'],
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
            'unit_note': _t(lang, 'values_in_currency_billions').format(currency=ctx['currency']),
            'headers': [_t(lang, 'metric')] + [p['label'] for p in ctx['periods']] + [ctx['kpi_yoy_label_q'], ctx['kpi_yoy_label_fy']],
            'rows': [[row['label'], *row['values'], row['yoy_q'], row['yoy_fy']] for row in ctx['kpi_rows']],
            'widths': [0.18] + [0.085] * len(ctx['periods']) + [0.16, 0.16],
            'benchmark_cols': set(),
            'group_break_cols': {1 + idx for idx, period in enumerate(ctx['periods']) if period.get('group_start')},
        },
        'statements': sections,
        'appendix': {
            'title': _t(lang, 'methodology_note_title'),
            'statement_detail_title': _t(lang, 'statement_appendix_title'),
            'benchmark_note': ctx['benchmark_note'],
            'notes': ctx['methodology_notes'],
            'covenant_note_title': ctx['covenant_note_title'],
            'data_source': ctx['data_source'],
            'disclaimer': ctx['disclaimer'],
        },
    }


def generate_full_pdf_async(report: dict[str, object], lang: str = 'en', theme: str = 'dark') -> bytes:
    from src.reportlab_pdf_exporter import generate_full_pdf_async as _generate_full_pdf_async

    return _generate_full_pdf_async(report, lang, theme)


def generate_full_pdf(report: dict[str, object], lang: str = 'en', theme: str = 'dark') -> bytes:
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
    '_select_pdf_history',
]
