"""Shared PDF report data shaping, sanitization, and localization helpers."""

from __future__ import annotations

import re
from typing import Any

from src.html_pdf_exporter import (
    _build_yoy_map as _html_build_yoy_map,
    _clean_display_text as _html_clean_display_text,
    _estimate_table_row_height as _html_estimate_table_row_height,
    _format_period_label as _html_format_period_label,
    _format_statement_display_value as _html_format_statement_display_value,
    _is_negative_display_value as _html_is_negative_display_value,
    _paginate_table_rows as _html_paginate_table_rows,
    _t as _html_t,
    _wrap_cell_lines as _html_wrap_cell_lines,
    build_pdf_context as _html_build_pdf_context,
    build_pdf_document_model as _html_build_pdf_document_model,
)

_INLINE_BREAK_RE = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
_MERGED_METRIC_RE = re.compile(
    r'(?i)(?:\d[\d,]*\.?\d*(?:x|%|pp)?)(?:\s*(?:vs|/|\||\+|-)\s*|\s+)(?:\d[\d,]*\.?\d*(?:x|%|pp)?|[a-z][a-z0-9_/-]*)'
)
_SPACED_MAGNITUDE_RE = re.compile(r'(?i)^[+-]?(?:\d[\d,]*)(?:\.\d+)?\s+[bmk]$')
_TRAILING_LABEL_PUNCT_RE = re.compile(r"[.\u3002\uFF0E:：\s]+$")
_ACRONYM_LABELS = {
    'ebit',
    'ebitda',
    'fcf',
    'cf',
    'ni',
    'ppe',
    'eps',
    'roi',
    'roa',
    'roe',
    'usd',
    'hkd',
    'cny',
    'jpy',
    'fx',
    'n/a',
}
_STATEMENT_PATH_MARKERS = ('.statements', '.financial_statements', '.statement_data')


def _clean_display_text(value: Any) -> str:
    return _html_clean_display_text(value)


def _raise_critical_multiline_error(value: Any) -> None:
    raise ValueError(
        f"FATAL: 渲染层拒绝接收硬合并的多行数据 '{value}'。"
    )


def _t(lang: str, key: str) -> str:
    return _html_t(lang, key)


def _build_yoy_map(periods: Any) -> Any:
    return _html_build_yoy_map(periods)


def _estimate_table_row_height(
    row: list[str],
    widths: list[float],
    chars_per_full_width: int,
    font_size: float,
    max_lines: int = 4,
    min_height: float = 18.0,
    height_scale: float = 1.0,
) -> float:
    return _html_estimate_table_row_height(
        row,
        widths,
        chars_per_full_width,
        font_size,
        max_lines=max_lines,
        min_height=min_height,
        height_scale=height_scale,
    )


def _format_period_label(label: str | None) -> str:
    return _html_format_period_label(label)


def _is_negative_display_value(value: Any) -> bool:
    return _html_is_negative_display_value(value)


def _paginate_table_rows(
    rows: list[list[str]],
    widths: list[float],
    available_height: float,
    chars_per_full_width: int,
    font_size: float,
    header_height: float,
    max_lines: int = 4,
    min_row_height: float = 18.0,
    height_scale: float = 1.0,
) -> list[list[list[str]]]:
    return _html_paginate_table_rows(
        rows,
        widths,
        available_height,
        chars_per_full_width,
        font_size,
        header_height,
        max_lines=max_lines,
        min_row_height=min_row_height,
        height_scale=height_scale,
    )


def _wrap_cell_lines(value: Any, width_fraction: float, chars_per_full_width: int, max_lines: int = 4) -> list[str]:
    return _html_wrap_cell_lines(value, width_fraction, chars_per_full_width, max_lines=max_lines)


def _normalize_label_text(value: Any) -> str:
    text = _clean_display_text(value)
    text = _TRAILING_LABEL_PUNCT_RE.sub('', text)
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
        if part.lower() in {'and', 'of', 'to', 'for', 'in', 'on', 'at', 'by', 'per'} and parts:
            parts.append(part.lower())
            continue
        if part.lower() in _ACRONYM_LABELS:
            parts.append(part.upper())
        elif part.isdigit():
            parts.append(part)
        elif '/' in part:
            segments = []
            for segment in part.split('/'):
                if not segment:
                    segments.append(segment)
                elif segment.lower() in _ACRONYM_LABELS:
                    segments.append(segment.upper())
                else:
                    segments.append(segment[:1].upper() + segment[1:])
            parts.append('/'.join(segments))
        else:
            parts.append(part[:1].upper() + part[1:])
    return ' '.join(parts)


def _normalize_statement_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cleaned = dict(row)
        label = _normalize_label_text(cleaned.get('label'))
        values = cleaned.get('values', [])
        if isinstance(values, (list, tuple)):
            cleaned['values'] = [
                '--' if not (text := _clean_display_text(value)) or re.fullmatch(r'[,;\s]+', text) else text
                for value in values
            ]
        else:
            text = _clean_display_text(values)
            cleaned['values'] = ['--' if not text or re.fullmatch(r'[,;\s]+', text) else text]
        if not label and not any(_clean_display_text(value) not in {'', '--', 'N/A', 'n/a'} for value in cleaned['values']):
            continue
        cleaned['label'] = label
        cleaned['yoy_q'] = _clean_display_text(cleaned.get('yoy_q'))
        cleaned['yoy_fy'] = _clean_display_text(cleaned.get('yoy_fy'))
        normalized.append(cleaned)
    return normalized


def _path_allows_statement_text(path: str) -> bool:
    return any(marker in path for marker in _STATEMENT_PATH_MARKERS)


def _scan_for_inline_breaks(value: Any, path: str, allow_statement_text: bool = False) -> None:
    if isinstance(value, str):
        if allow_statement_text and _path_allows_statement_text(path):
            return
        if '\n' in value or '\r' in value or _INLINE_BREAK_RE.search(value):
            _raise_critical_multiline_error(value)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and ('\n' in key or '\r' in key or _INLINE_BREAK_RE.search(key)):
                _raise_critical_multiline_error(key)
            _scan_for_inline_breaks(item, f'{path}.{key}', allow_statement_text=allow_statement_text)
    elif isinstance(value, (list, tuple)):
        for idx, item in enumerate(value):
            _scan_for_inline_breaks(item, f'{path}[{idx}]', allow_statement_text=allow_statement_text)


def _scan_for_merged_metric_text(value: Any, path: str) -> None:
    if not isinstance(value, str):
        return
    text = _clean_display_text(value)
    if not text or text in {'--', 'N/A', 'n/a', 'No data available'}:
        return
    if _INLINE_BREAK_RE.search(text) or '\n' in text or '\r' in text:
        _raise_critical_multiline_error(value)
    if _SPACED_MAGNITUDE_RE.fullmatch(text):
        return
    if any(token in path for token in ('.label', '.metric', '.actual', '.threshold', '.value', '.notes', '.description')):
        if _MERGED_METRIC_RE.search(text):
            raise ValueError(f'Merged metric text is not allowed in PDF content at {path}: {text!r}.')


def _sanitize_text_row(row: dict[str, Any], label_key: str = 'label') -> dict[str, Any]:
    cleaned = dict(row)
    if label_key in cleaned:
        _scan_for_inline_breaks(cleaned[label_key], f'{label_key}')
        cleaned[label_key] = _normalize_label_text(cleaned[label_key])
        _scan_for_merged_metric_text(cleaned[label_key], f'{label_key}')
    for key, value in cleaned.items():
        if key == label_key:
            continue
        _scan_for_inline_breaks(value, f'{key}')
    return cleaned


def _sanitize_pdf_document_model(model: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(model)
    cover = dict(sanitized.get('cover') or {})
    summary = dict(sanitized.get('summary') or {})
    covenant = dict(sanitized.get('covenant') or {})
    kpi = dict(sanitized.get('kpi') or {})
    appendix = dict(sanitized.get('appendix') or {})

    hero_summary = dict(cover.get('hero_summary') or {})
    hero_summary['items'] = [
        {
            **dict(item),
            'label': _normalize_label_text(item.get('label')),
            'value': _clean_display_text(item.get('value')),
            'tone': str(item.get('tone') or 'neutral'),
        }
        for item in hero_summary.get('items', [])
        if isinstance(item, dict)
    ]
    for idx, item in enumerate(hero_summary['items']):
        _scan_for_merged_metric_text(item.get('label'), f'cover.hero_summary.items[{idx}].label')
        _scan_for_merged_metric_text(item.get('value'), f'cover.hero_summary.items[{idx}].value')
    hero_summary['status_label'] = _clean_display_text(hero_summary.get('status_label'))
    hero_summary['description'] = _clean_display_text(hero_summary.get('description'))
    hero_summary['breakdown'] = [
        {
            **dict(item),
            'label': _normalize_label_text(item.get('label')),
            'value': _clean_display_text(item.get('value')),
            'contribution': _clean_display_text(item.get('contribution')),
            'tone': str(item.get('tone') or 'neutral'),
        }
        for item in hero_summary.get('breakdown', [])
        if isinstance(item, dict)
    ]
    for idx, item in enumerate(hero_summary['breakdown']):
        _scan_for_merged_metric_text(item.get('label'), f'cover.hero_summary.breakdown[{idx}].label')
        _scan_for_merged_metric_text(item.get('value'), f'cover.hero_summary.breakdown[{idx}].value')
        _scan_for_merged_metric_text(item.get('contribution'), f'cover.hero_summary.breakdown[{idx}].contribution')
    cover['hero_summary'] = hero_summary
    cover['company_name'] = _clean_display_text(cover.get('company_name'))
    cover['company_name_localized'] = _clean_display_text(cover.get('company_name_localized'))
    if isinstance(cover.get('company_name_localized'), str) and any(ord(ch) > 127 for ch in cover['company_name_localized']) and model.get('lang') == 'en':
        cover['company_name_localized'] = ''
    cover['ticker'] = _clean_display_text(cover.get('ticker'))
    cover['currency'] = _clean_display_text(cover.get('currency'))
    cover['latest_period'] = _clean_display_text(cover.get('latest_period'))
    cover['generated_at'] = _clean_display_text(cover.get('generated_at'))
    cover['report_title'] = _clean_display_text(cover.get('report_title'))

    summary['company_profile_rows'] = [_sanitize_text_row(row) for row in summary.get('company_profile_rows', []) if isinstance(row, dict)]
    for idx, row in enumerate(summary['company_profile_rows']):
        if row.get('label') != 'Description':
            _scan_for_merged_metric_text(row.get('label'), f'summary.company_profile_rows[{idx}].label')
            _scan_for_merged_metric_text(row.get('value'), f'summary.company_profile_rows[{idx}].value')
    summary['data_quality_rows'] = [
        {
            **_sanitize_text_row(row),
            'value': _clean_display_text(row.get('value')),
            'notes': _clean_display_text(row.get('notes')),
        }
        for row in summary.get('data_quality_rows', [])
        if isinstance(row, dict)
    ]
    for idx, row in enumerate(summary['data_quality_rows']):
        _scan_for_merged_metric_text(row.get('label'), f'summary.data_quality_rows[{idx}].label')
        _scan_for_merged_metric_text(row.get('value'), f'summary.data_quality_rows[{idx}].value')
        _scan_for_merged_metric_text(row.get('notes'), f'summary.data_quality_rows[{idx}].notes')
    summary['strengths'] = [_clean_display_text(row) for row in summary.get('strengths', []) if _clean_display_text(row)]
    summary['watch_items'] = [_clean_display_text(row) for row in summary.get('watch_items', []) if _clean_display_text(row)]
    summary['methodology_notes'] = [_clean_display_text(row) for row in summary.get('methodology_notes', []) if _clean_display_text(row)]

    covenant['rows'] = [
        {
            **_sanitize_text_row(row, 'metric'),
            'actual': _clean_display_text(row.get('actual')),
            'threshold': _clean_display_text(row.get('threshold')),
            'status_signal': _clean_display_text(row.get('status_signal')),
            'notes': _clean_display_text(row.get('notes')),
        }
        for row in covenant.get('rows', [])
        if isinstance(row, dict)
    ]
    for idx, row in enumerate(covenant['rows']):
        _scan_for_merged_metric_text(row.get('metric'), f'covenant.rows[{idx}].metric')
        _scan_for_merged_metric_text(row.get('actual'), f'covenant.rows[{idx}].actual')
        _scan_for_merged_metric_text(row.get('threshold'), f'covenant.rows[{idx}].threshold')
        _scan_for_merged_metric_text(row.get('status_signal'), f'covenant.rows[{idx}].status_signal')
        _scan_for_merged_metric_text(row.get('notes'), f'covenant.rows[{idx}].notes')
    covenant['notes'] = [
        {
            **_sanitize_text_row(row, 'metric'),
            'description': _clean_display_text(row.get('description')),
        }
        for row in covenant.get('notes', [])
        if isinstance(row, dict)
    ]
    for idx, row in enumerate(covenant['notes']):
        _scan_for_merged_metric_text(row.get('metric'), f'covenant.notes[{idx}].metric')
        _scan_for_merged_metric_text(row.get('description'), f'covenant.notes[{idx}].description')
    covenant['note_title'] = _clean_display_text(covenant.get('note_title'))
    covenant['title'] = _clean_display_text(covenant.get('title'))

    kpi['title'] = _clean_display_text(kpi.get('title'))
    kpi['benchmark_note'] = _clean_display_text(kpi.get('benchmark_note'))
    kpi['yoy_note'] = _clean_display_text(kpi.get('yoy_note'))
    kpi['headers'] = [_clean_display_text(header) for header in kpi.get('headers', [])]
    kpi['rows'] = [[_clean_display_text(cell) for cell in row] for row in kpi.get('rows', [])]
    for row_idx, row in enumerate(kpi['rows']):
        for col_idx, cell in enumerate(row):
            _scan_for_merged_metric_text(cell, f'kpi.rows[{row_idx}][{col_idx}]')

    sanitized['cover'] = cover
    sanitized['summary'] = summary
    sanitized['covenant'] = covenant
    sanitized['kpi'] = kpi
    statement_sections: list[dict[str, Any]] = []
    for section in sanitized.get('statements', []):
        if not isinstance(section, dict):
            continue
        section_key = _clean_display_text(section.get('key')).lower()
        repaired_rows: list[dict[str, Any]] = []
        for row in section.get('rows', []):
            if not isinstance(row, dict):
                continue
            cleaned_row = _sanitize_text_row(row)
            values = row.get('values', [])
            if isinstance(values, (list, tuple)):
                cleaned_values = [
                    _html_format_statement_display_value(value, cleaned_row.get('label'))
                    if section_key in {'income_statement', 'balance_sheet', 'cash_flow_statement'}
                    else ('--' if not (text := _clean_display_text(value)) or re.fullmatch(r'[,;\s]+', text) else text)
                    for value in values
                ]
            else:
                text = _clean_display_text(values)
                cleaned_values = [
                    _html_format_statement_display_value(text, cleaned_row.get('label'))
                    if section_key in {'income_statement', 'balance_sheet', 'cash_flow_statement'}
                    else ('--' if not text or re.fullmatch(r'[,;\s]+', text) else text)
                ]
            repaired_rows.append({
                **cleaned_row,
                'values': cleaned_values,
                'yoy_q': _clean_display_text(row.get('yoy_q')),
                'yoy_fy': _clean_display_text(row.get('yoy_fy')),
            })
        statement_sections.append({
            **section,
            'display_title': _clean_display_text(section.get('display_title')),
            'headers': [_clean_display_text(header) for header in section.get('headers', [])],
            'rows': _normalize_statement_rows(repaired_rows),
            'yoy_note': _clean_display_text(section.get('yoy_note')),
        })
    sanitized['statements'] = statement_sections
    for section_idx, section in enumerate(sanitized['statements']):
        for row_idx, row in enumerate(section.get('rows', [])):
            _scan_for_merged_metric_text(row.get('label'), f'statements[{section_idx}].rows[{row_idx}].label')
            for col_idx, value in enumerate(row.get('values', [])):
                _scan_for_merged_metric_text(value, f'statements[{section_idx}].rows[{row_idx}].values[{col_idx}]')
            _scan_for_merged_metric_text(row.get('yoy_q'), f'statements[{section_idx}].rows[{row_idx}].yoy_q')
            _scan_for_merged_metric_text(row.get('yoy_fy'), f'statements[{section_idx}].rows[{row_idx}].yoy_fy')
    appendix['title'] = _clean_display_text(appendix.get('title'))
    appendix['benchmark_note'] = _clean_display_text(appendix.get('benchmark_note'))
    appendix['notes'] = [_clean_display_text(note) for note in appendix.get('notes', []) if _clean_display_text(note)]
    appendix['covenant_note_title'] = _clean_display_text(appendix.get('covenant_note_title'))
    sanitized['appendix'] = appendix

    return sanitized


def _validate_pdf_document_model(model: dict[str, Any]) -> None:
    if not isinstance(model, dict):
        raise ValueError('PDF document model must be a mapping.')
    _scan_for_inline_breaks(model, 'document')


def build_pdf_context(report: dict[str, Any], lang: str = 'en', theme: str = 'dark') -> dict[str, Any]:
    return _html_build_pdf_context(report, lang, theme)


def build_pdf_document_model(report: dict[str, Any], lang: str = 'en', theme: str = 'dark') -> dict[str, Any]:
    _scan_for_inline_breaks(report, 'report', allow_statement_text=True)
    model = _html_build_pdf_document_model(report, lang, theme)
    sanitized = _sanitize_pdf_document_model(model)
    _validate_pdf_document_model(sanitized)
    return sanitized


__all__ = [
    'build_pdf_context',
    'build_pdf_document_model',
    '_build_yoy_map',
    '_clean_display_text',
    '_estimate_table_row_height',
    '_format_period_label',
    '_is_negative_display_value',
    '_normalize_label_text',
    '_paginate_table_rows',
    '_scan_for_inline_breaks',
    '_t',
    '_wrap_cell_lines',
]
