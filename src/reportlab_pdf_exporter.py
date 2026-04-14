"""ReportLab-based production PDF exporter.

This module owns the public PDF generation entry point.
"""

from __future__ import annotations

import asyncio
import re
from threading import Thread
from typing import Any

from src.pdf_report_core import build_pdf_document_model
from src.reportlab_pdf_renderer import _render_reportlab_pdf

_NUMERIC_TEXT_RE = re.compile(r'^[+-]?(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?(?:\s?(?:x|%|pp))?$', re.IGNORECASE)


def _validate_numeric_value(value: Any, path: str) -> None:
    if value is None or isinstance(value, (int, float, bool)):
        return
    if isinstance(value, str):
        text = value.strip()
        if not text or text in {'--', 'N/A', 'n/a'}:
            return
        if any(ch.isdigit() for ch in text) and not _NUMERIC_TEXT_RE.fullmatch(text):
            raise ValueError(f'Invalid numeric value at {path}: {value!r}')
        return
    raise ValueError(f'Unsupported numeric value at {path}: {type(value).__name__}')


def _validate_statement_payload(payload: Any, path: str, allow_textual_values: bool = False) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            next_path = f'{path}.{key}'
            if key in {'value', 'amount', 'balance', 'actual', 'threshold', 'target', 'limit', 'score'} and not isinstance(value, (dict, list, tuple)):
                if not allow_textual_values:
                    _validate_numeric_value(value, next_path)
            elif isinstance(value, (dict, list, tuple)):
                _validate_statement_payload(value, next_path, allow_textual_values=allow_textual_values)
    elif isinstance(payload, (list, tuple)):
        for idx, item in enumerate(payload):
            next_path = f'{path}[{idx}]'
            if isinstance(item, dict):
                _validate_statement_payload(item, next_path, allow_textual_values=allow_textual_values)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                if not allow_textual_values:
                    _validate_numeric_value(item[1], f'{next_path}[1]')


def _validate_report_payload(report: dict[str, Any]) -> None:
    if not isinstance(report, dict):
        raise ValueError('Report payload must be a mapping.')
    history = report.get('history') or report.get('histories')
    if not isinstance(history, list) or not history:
        raise ValueError('No history available')
    for idx, entry in enumerate(history):
        if not isinstance(entry, dict):
            raise ValueError(f'History entry {idx + 1} must be an object.')
        assessment = entry.get('assessment')
        if isinstance(assessment, dict):
            for key in ('altman_z_score', 'risk_score', 'z_score'):
                if key in assessment:
                    _validate_numeric_value(assessment.get(key), f'history[{idx}].assessment.{key}')
            covenants = assessment.get('covenant_pre_check') or assessment.get('covenants')
            _validate_statement_payload(covenants, f'history[{idx}].assessment.covenant_pre_check')
        for key in ('raw_metrics', 'ratios', 'metrics'):
            payload = entry.get(key)
            if isinstance(payload, dict):
                for metric_key, metric_value in payload.items():
                    if metric_key not in ('analysis_date', 'timestamp'):
                        _validate_numeric_value(metric_value, f'history[{idx}].{key}.{metric_key}')
        for key in ('statements', 'financial_statements', 'statement_data'):
            payload = entry.get(key)
            if payload is not None:
                _validate_statement_payload(payload, f'history[{idx}].{key}', allow_textual_values=True)


async def generate_full_pdf_async(report: dict[str, Any], lang: str = 'en', theme: str = 'dark') -> bytes:
    _validate_report_payload(report)
    model = build_pdf_document_model(report, lang, theme)
    return _render_reportlab_pdf(model)


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


def generate_full_pdf(report: dict[str, Any], lang: str = 'en', theme: str = 'dark') -> bytes:
    return _run_sync(generate_full_pdf_async(report, lang, theme))


__all__ = ['generate_full_pdf', 'generate_full_pdf_async']
