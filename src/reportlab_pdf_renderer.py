from __future__ import annotations

import html as html_lib
import io
import logging
import re
from typing import Any

from src.pdf_report_core import _clean_display_text, _is_negative_display_value, _t

_INLINE_BREAK_RE = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
logger = logging.getLogger(__name__)


def _ensure_no_inline_breaks(value: Any, path: str) -> None:
    if isinstance(value, str) and ('\n' in value or '\r' in value or _INLINE_BREAK_RE.search(value)):
        raise ValueError(
            f"FATAL: Renderer rejects hard-merged multiline data at '{value}'."
        )
    if isinstance(value, dict):
        for key, item in value.items():
            _ensure_no_inline_breaks(item, f'{path}.{key}')
    elif isinstance(value, (list, tuple)):
        for idx, item in enumerate(value):
            _ensure_no_inline_breaks(item, f'{path}[{idx}]')

def _render_reportlab_pdf(model: dict[str, object]) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from src.fonts import register_cjk_fonts
        from reportlab.platypus import (
            BaseDocTemplate,
            Frame,
            LongTable,
            NextPageTemplate,
            PageBreak,
            PageTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
    except Exception as exc:  # pragma: no cover - dependency guard
        raise RuntimeError(
            'ReportLab is required for PDF export. Add reportlab to requirements and install it before exporting.'
        ) from exc

    ctx = model['context']
    lang = model['lang']
    theme = str(model.get('theme') or ctx.get('theme') or 'dark').lower()
    theme_is_light = theme == 'light'
    cover = model['cover']
    summary = model['summary']
    covenant = model['covenant']
    kpi = model['kpi']
    statements = model['statements']
    appendix = model['appendix']

    page_width, page_height = landscape(A4)
    margin = 12 * mm
    body_width = page_width - margin * 2
    body_height = page_height - margin * 2

    if lang in ('ja', 'zh-TW', 'zh-CN'):
        body_font, heading_font = register_cjk_fonts(lang)
    else:
        body_font = 'Helvetica'
        heading_font = 'Helvetica-Bold'

    palette_dark = {
        'page': colors.HexColor('#020617'),
        'panel': colors.HexColor('#0f172a'),
        'panel_soft': colors.HexColor('#1a2640'),
        'ink': colors.HexColor('#e2e8f0'),
        'muted': colors.HexColor('#94a3b8'),
        'line': colors.HexColor('#273244'),
        'accent': colors.HexColor('#14b8a6'),
        'accent_soft': colors.HexColor('#0f172a'),
        'positive': colors.HexColor('#4ade80'),
        'warning': colors.HexColor('#f59e0b'),
        'danger': colors.HexColor('#f87171'),
        'warning_soft': colors.HexColor('#3b2a10'),
        'alert_soft': colors.HexColor('#3a1717'),
        'bench': colors.HexColor('#1e293b'),
        'header': colors.HexColor('#0b1220'),
        'header_text': colors.white,
        'panel_border': colors.HexColor('#334155'),
    }
    palette_light = {
        'page': colors.HexColor('#FFFFFF'),
        'panel': colors.HexColor('#FFFFFF'),
        'panel_soft': colors.HexColor('#F8FAFC'),
        'ink': colors.HexColor('#0F172A'),
        'muted': colors.HexColor('#64748B'),
        'line': colors.HexColor('#E2E8F0'),
        'accent': colors.HexColor('#0F172A'),
        'accent_soft': colors.HexColor('#F1F5F9'),
        'positive': colors.HexColor('#16A34A'),
        'warning': colors.HexColor('#D97706'),
        'danger': colors.HexColor('#DC2626'),
        'warning_soft': colors.HexColor('#FEF3C7'),
        'alert_soft': colors.HexColor('#FEE2E2'),
        'bench': colors.HexColor('#F8FAFC'),
        'header': colors.HexColor('#F1F5F9'),
        'header_text': colors.HexColor('#334155'),
        'panel_border': colors.HexColor('#CBD5E1'),
    }
    palette = palette_light if theme_is_light else palette_dark

    styles: dict[str, ParagraphStyle] = {
        'title': ParagraphStyle(
            'title',
            fontName=heading_font,
            fontSize=24,
            leading=27,
            textColor=palette['ink'],
            spaceAfter=4,
            keepWithNext=True,
        ),
        'subtitle': ParagraphStyle(
            'subtitle',
            fontName=body_font,
            fontSize=10.5,
            leading=14.5,
            textColor=palette['muted'],
            spaceAfter=8,
        ),
        'section': ParagraphStyle(
            'section',
            fontName=heading_font,
            fontSize=14.0 if theme_is_light else 13.8,
            leading=17.5,
            textColor=palette['ink'],
            spaceBefore=6,
            spaceAfter=8,
            keepWithNext=True,
        ),
        'note': ParagraphStyle(
            'note',
            fontName=body_font,
            fontSize=8.2,
            leading=11,
            textColor=palette['muted'],
            spaceAfter=6,
        ),
        'caption': ParagraphStyle(
            'caption',
            fontName=body_font,
            fontSize=7.2,
            leading=9,
            textColor=palette['muted'],
            spaceAfter=4,
        ),
        'footer_note': ParagraphStyle(
            'footer_note',
            fontName=body_font,
            fontSize=7.0,
            leading=8.5,
            textColor=palette['muted'],
            spaceAfter=2,
        ),
        'body': ParagraphStyle(
            'body',
            fontName=body_font,
            fontSize=8.8,
            leading=12.5,
            textColor=palette['ink'],
            splitLongWords=True,
            wordWrap='CJK',
        ),
        'body_bold': ParagraphStyle(
            'body_bold',
            fontName=heading_font,
            fontSize=8.8,
            leading=12.5,
            textColor=palette['ink'],
            splitLongWords=True,
            wordWrap='CJK',
        ),
        'body_right': ParagraphStyle(
            'body_right',
            parent=None,
            fontName=body_font,
            fontSize=8.8,
            leading=12.5,
            textColor=palette['ink'],
            splitLongWords=True,
            wordWrap='CJK',
            alignment=TA_RIGHT,
        ),
        'body_center': ParagraphStyle(
            'body_center',
            parent=None,
            fontName=body_font,
            fontSize=8.8,
            leading=12.5,
            textColor=palette['ink'],
            splitLongWords=True,
            wordWrap='CJK',
            alignment=TA_CENTER,
        ),
        'header': ParagraphStyle(
            'header',
            fontName=heading_font,
            fontSize=8.5,
            leading=10.5,
            textColor=palette['header_text'],
            alignment=TA_LEFT,
            splitLongWords=True,
            wordWrap='CJK',
        ),
        'header_right': ParagraphStyle(
            'header_right',
            fontName=heading_font,
            fontSize=8.5,
            leading=10.5,
            textColor=palette['header_text'],
            alignment=TA_RIGHT,
            splitLongWords=True,
            wordWrap='CJK',
        ),
        'statement_body': ParagraphStyle(
            'statement_body',
            fontName=body_font,
            fontSize=7.2,
            leading=9.4,
            textColor=palette['ink'],
            splitLongWords=False,
            wordWrap='LTR',
        ),
        'statement_body_bold': ParagraphStyle(
            'statement_body_bold',
            fontName=heading_font,
            fontSize=7.2,
            leading=9.4,
            textColor=palette['ink'],
            splitLongWords=False,
            wordWrap='LTR',
        ),
        'statement_body_right': ParagraphStyle(
            'statement_body_right',
            parent=None,
            fontName=body_font,
            fontSize=7.2,
            leading=9.4,
            textColor=palette['ink'],
            splitLongWords=False,
            wordWrap='LTR',
            alignment=TA_RIGHT,
        ),
        'statement_body_center': ParagraphStyle(
            'statement_body_center',
            parent=None,
            fontName=body_font,
            fontSize=7.2,
            leading=9.4,
            textColor=palette['ink'],
            splitLongWords=False,
            wordWrap='LTR',
            alignment=TA_CENTER,
        ),
        'statement_header': ParagraphStyle(
            'statement_header',
            fontName=heading_font,
            fontSize=7.4,
            leading=9.5,
            textColor=palette['header_text'],
            alignment=TA_LEFT,
            splitLongWords=False,
            wordWrap='LTR',
        ),
        'statement_header_right': ParagraphStyle(
            'statement_header_right',
            fontName=heading_font,
            fontSize=7.4,
            leading=9.5,
            textColor=palette['header_text'],
            alignment=TA_RIGHT,
            splitLongWords=False,
            wordWrap='LTR',
        ),
        'chip_label': ParagraphStyle(
            'chip_label',
            fontName=body_font,
            fontSize=7.2,
            leading=9.2,
            textColor=palette['muted'],
        ),
        'chip_value': ParagraphStyle(
            'chip_value',
            fontName=heading_font,
            fontSize=11.5,
            leading=13.5,
            textColor=palette['ink'],
        ),
        'hero_kicker': ParagraphStyle(
            'hero_kicker',
            fontName=body_font,
            fontSize=8.2,
            leading=10,
            textColor=palette['muted'],
            spaceAfter=2,
        ),
        'hero_score': ParagraphStyle(
            'hero_score',
            fontName=heading_font,
            fontSize=30 if theme_is_light else 27,
            leading=32 if theme_is_light else 29,
            textColor=palette['ink'],
            spaceAfter=2,
        ),
        'hero_summary': ParagraphStyle(
            'hero_summary',
            fontName=body_font,
            fontSize=8.7,
            leading=11.3,
            textColor=palette['muted'],
            spaceAfter=0,
        ),
        'hero_metric_label': ParagraphStyle(
            'hero_metric_label',
            fontName=heading_font,
            fontSize=7.2,
            leading=8.8,
            textColor=palette['ink'],
        ),
        'hero_metric_contrib': ParagraphStyle(
            'hero_metric_contrib',
            fontName=body_font,
            fontSize=6.5,
            leading=7.7,
            textColor=palette['muted'],
        ),
        'metric_label': ParagraphStyle(
            'metric_label',
            fontName=body_font,
            fontSize=7.4,
            leading=9.6,
            textColor=palette['muted'],
            alignment=TA_LEFT,
        ),
        'metric_value': ParagraphStyle(
            'metric_value',
            fontName=heading_font,
            fontSize=18,
            leading=21,
            textColor=palette['ink'],
            alignment=TA_LEFT,
        ),
        'metric_value_center': ParagraphStyle(
            'metric_value_center',
            fontName=heading_font,
            fontSize=18,
            leading=21,
            textColor=palette['ink'],
            alignment=TA_CENTER,
        ),
        'bullet': ParagraphStyle(
            'bullet',
            fontName=body_font,
            fontSize=8.6,
            leading=11.8,
            textColor=palette['ink'],
            leftIndent=8,
            firstLineIndent=0,
            splitLongWords=True,
            wordWrap='CJK',
        ),
        'contents': ParagraphStyle(
            'contents',
            fontName=body_font,
            fontSize=10.2,
            leading=14.5,
            textColor=palette['ink'],
            splitLongWords=True,
            wordWrap='CJK',
        ),
    }

    def esc(value: Any, path: str = 'text') -> str:
        _ensure_no_inline_breaks(value, path)
        text = _clean_display_text(value)
        return html_lib.escape(text) or '&nbsp;'

    def p(value: Any, style_name: str, color: Any | None = None, alignment: int | None = None) -> Paragraph:
        base = styles[style_name]
        if color is None and alignment is None:
            return Paragraph(esc(value), base)
        overrides: dict[str, Any] = {}
        if color is not None:
            overrides['textColor'] = color
        if alignment is not None:
            overrides['alignment'] = alignment
        return Paragraph(esc(value), ParagraphStyle(f'{style_name}_{id(overrides)}', parent=base, **overrides))

    def num_color(text: str) -> Any:
        if _is_negative_display_value(text):
            return palette['danger']
        return palette['ink']

    def delta_color(text: str) -> Any:
        cleaned = _clean_display_text(text)
        if not cleaned or cleaned in {'--', 'N/A', 'n/a'}:
            return palette['ink']
        if _is_negative_display_value(cleaned):
            return palette['danger']
        if cleaned.startswith('+'):
            return palette['positive']
        numeric = re.sub(r'[^0-9.\-+]', '', cleaned)
        try:
            return palette['positive'] if float(numeric) > 0 else palette['ink']
        except (ValueError, TypeError) as exc:
            logger.debug("delta_color fallback: %s", exc)
            return palette['ink']

    def kpi_widths(total_width: float, column_count: int) -> list[float]:
        if column_count < 4:
            return [total_width / max(column_count, 1)] * max(column_count, 1)
        period_count = max(0, column_count - 3)
        if theme_is_light:
            base = [164.0] + [66.0] * period_count + [78.0, 78.0]
        else:
            base = [162.0] + [64.0] * period_count + [76.0, 76.0]
        minimum = sum(base)
        if minimum > total_width:
            scale = total_width / minimum
            return [width * scale for width in base]
        extra = total_width - minimum
        period_bonus = extra / max(period_count, 1)
        if theme_is_light:
            return [164.0] + [66.0 + period_bonus] * period_count + [78.0, 78.0]
        return [162.0] + [64.0 + period_bonus] * period_count + [76.0, 76.0]

    def statement_widths(total_width: float, period_count: int) -> list[float]:
        if theme_is_light:
            base = [186.0] + [64.0] * period_count + [68.0, 68.0]
        else:
            base = [190.0] + [62.0] * period_count + [66.0, 66.0]
        minimum = sum(base)
        if minimum > total_width:
            scale = total_width / minimum
            return [width * scale for width in base]
        extra = total_width - minimum
        period_bonus = extra / max(period_count, 1)
        if theme_is_light:
            return [186.0] + [64.0 + period_bonus] * period_count + [68.0, 68.0]
        return [190.0] + [62.0 + period_bonus] * period_count + [66.0, 66.0]

    def cell(value: Any, style_name: str = 'body', align: str = 'left', color: Any | None = None, statement_mode: bool = False) -> Paragraph:
        alignment = TA_LEFT if align == 'left' else TA_RIGHT if align == 'right' else TA_CENTER
        if color is None and isinstance(value, str):
            color = num_color(value)
        if style_name == 'header':
            return p(value, 'statement_header' if statement_mode else 'header', color=palette['header_text'], alignment=alignment)
        if style_name == 'header_right':
            return p(value, 'statement_header_right' if statement_mode else 'header_right', color=palette['header_text'], alignment=alignment)
        if align == 'right':
            return p(value, 'statement_body_right' if statement_mode else 'body_right', color=color, alignment=alignment)
        if align == 'center':
            return p(value, 'statement_body_center' if statement_mode else 'body_center', color=color, alignment=alignment)
        if statement_mode and style_name == 'body_bold':
            style_name = 'statement_body_bold'
        if statement_mode and style_name == 'body':
            style_name = 'statement_body'
        return p(value, style_name if style_name in styles else ('statement_body' if statement_mode else 'body'), color=color, alignment=alignment)

    def badge_text(value: str, tone: str) -> Paragraph:
        tone_color = {
            'success': palette['positive'],
            'warning': palette['warning'],
            'danger': palette['danger'],
        }.get(tone, palette['accent'])
        return p(value, 'body_center', color=tone_color, alignment=TA_CENTER)

    def tone_from_text(text: str) -> str:
        lowered = text.lower()
        if any(token in lowered for token in ('green', 'pass', 'safe', 'ok', 'comfortable', 'within')):
            return 'success'
        if any(token in lowered for token in ('amber', 'warn', 'watch', 'caution', 'grey')):
            return 'warning'
        if any(token in lowered for token in ('red', 'fail', 'breach', 'risk', 'distress')):
            return 'danger'
        return 'neutral'

    def subtle_section_block(title: str | None, rows: list[Any], width: float, renderer: str = 'bullet') -> Table:
        body_rows: list[list[Any]] = []
        if title:
            body_rows.append([p(title, 'section' if theme_is_light else 'chip_value')])
        if renderer == 'bullet':
            source_rows = rows or [ctx['labels']['no_data']]
            for row in source_rows:
                body_rows.append([p(f'• {row}', 'bullet')])
        elif renderer == 'kv':
            source_rows = rows or [(ctx['labels']['no_data'], '--')]
            for label, value in source_rows:
                body_rows.append([Paragraph(f"<b>{html_lib.escape(str(label))}</b>: {html_lib.escape(str(value))}", styles['body'])])
        elif renderer == 'note':
            source_rows = rows or [ctx['labels']['no_data']]
            for row in source_rows:
                body_rows.append([p(row, 'body')])
        else:
            source_rows = rows or [ctx['labels']['no_data']]
            for row in source_rows:
                body_rows.append([row if isinstance(row, Paragraph) else p(row, 'body')])
        table = Table(body_rows, colWidths=[width], repeatRows=1)
        style_cmds: list[tuple[Any, ...]] = [
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]
        if title:
            style_cmds.append(('LINEBELOW', (0, 0), (-1, 0), 0.5, palette['line']))
        table.setStyle(TableStyle(style_cmds))
        return table

    def section_rule(width: float, thickness: float | None = None) -> Table:
        rule = Table([['']], colWidths=[width])
        rule.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), thickness or 0.5, palette['line']),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        return rule

    def split_body(left: Table, right: Table, width: float) -> Table:
        gutter = 6 * mm
        col_width = (width - gutter) / 2
        body = Table([[left, Spacer(1, 1), right]], colWidths=[col_width, gutter, col_width])
        body.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return body

    def stack_blocks(blocks: list[Any], width: float, gap: float = 4 * mm) -> Table:
        rows: list[list[Any]] = []
        for idx, block in enumerate(blocks):
            rows.append([block])
            if idx < len(blocks) - 1:
                rows.append([Spacer(1, gap)])
        table = Table(rows, colWidths=[width])
        table.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return table

    def label_value_line(label: str, value: Any) -> Paragraph:
        cleaned_label = html_lib.escape(_clean_display_text(label).rstrip('.:：'))
        cleaned_value = html_lib.escape(_clean_display_text(value))
        return Paragraph(f"<b>{cleaned_label}</b>: {cleaned_value}", styles['body'])

    def data_quality_line(row: dict[str, Any]) -> Paragraph:
        label = html_lib.escape(_clean_display_text(row.get('label')).rstrip('.:：'))
        value = html_lib.escape(_clean_display_text(row.get('value')))
        notes = _clean_display_text(row.get('notes'))
        if notes and notes != '--':
            notes_part = f" · {html_lib.escape(notes)}"
        else:
            notes_part = ''
        return Paragraph(f"<b>{label}</b>: {value}{notes_part}", styles['body'])

    def has_data_quality_rows(rows: list[dict[str, Any]]) -> bool:
        for row in rows:
            if not isinstance(row, dict):
                continue
            if any(_clean_display_text(row.get(field)) not in ('', '--', 'N/A', 'n/a') for field in ('value', 'notes')):
                return True
        return False

    def report_table(headers: list[str], rows: list[list[Any]], widths: list[float], benchmark_cols: set[int] | None = None, group_break_cols: set[int] | None = None, alignments: list[str] | None = None, status_col_idx: int | None = None, delta_cols: set[int] | None = None, statement_mode: bool = False, row_meta: list[dict[str, Any]] | None = None, status_tones: list[str] | None = None) -> LongTable:
        _ensure_no_inline_breaks(headers, 'report_table.headers')
        _ensure_no_inline_breaks(rows, 'report_table.rows')
        if len(widths) != len(headers):
            raise ValueError(f'PDF table width/header mismatch: expected {len(headers)}, got {len(widths)}.')
        for row_idx, row in enumerate(rows):
            if len(row) != len(headers):
                raise ValueError(
                    f'PDF table row length mismatch at row {row_idx}: expected {len(headers)}, got {len(row)}.'
                )
        is_empty_state = not rows
        header_rule_width = 0.8 if not theme_is_light else 1.0
        alignments = alignments or ['left'] + ['right'] * (len(headers) - 1)
        total_pattern = re.compile(r'(?i).*(total|subtotal|category|gross profit|operating income|net income|ebitda?|free cash flow).*')
        # Header row: left-align the label column, right-align numeric/data columns to
        # match the right-aligned data cells and avoid a "floating" centred header over
        # right-justified numbers — standard practice in financial statement layout.
        header_aligns = alignments if alignments else ['left'] + ['right'] * (len(headers) - 1)
        table_data: list[list[Paragraph]] = [[
            cell(header, 'header', header_aligns[idx] if idx < len(header_aligns) else 'right', statement_mode=statement_mode)
            for idx, header in enumerate(headers)
        ]]
        for row_idx, row in enumerate(rows):
            row_cells: list[Paragraph] = []
            row_label = str(_clean_display_text(row[0])) if row else ''
            meta = row_meta[row_idx] if row_meta and row_idx < len(row_meta) else {}
            level = int(meta.get('level') or meta.get('depth') or 0)
            is_total = bool(meta.get('is_total') or total_pattern.match(row_label))
            for idx, value in enumerate(row):
                align = alignments[idx] if idx < len(alignments) else ('left' if idx == 0 else 'right')
                text = _clean_display_text(value)
                color = delta_color(text) if delta_cols and idx in delta_cols else num_color(text) if align != 'left' else None
                if status_col_idx is not None and idx == status_col_idx:
                    tone = status_tones[row_idx] if status_tones and row_idx < len(status_tones) else tone_from_text(text)
                    row_cells.append(badge_text(text, tone))
                else:
                    if statement_mode:
                        style_name = 'statement_body_bold' if is_total and idx == 0 else 'statement_body'
                        if align == 'right':
                            style_name = 'statement_body_right'
                        elif align == 'center':
                            style_name = 'statement_body_center'
                        row_cells.append(cell(text, style_name, align, color=color, statement_mode=statement_mode))
                    else:
                        style_name = 'body_bold' if is_total and idx == 0 else 'body'
                        row_cells.append(cell(text, style_name, align, color=color))
            table_data.append(row_cells)
        if is_empty_state:
            empty_label = f"({ctx['labels']['no_data']})"
            table_data.append([cell(empty_label, 'body_center', 'center', statement_mode=statement_mode)] + [cell('', 'body_center', 'center', statement_mode=statement_mode) for _ in range(max(len(headers) - 1, 0))])
        table = LongTable(table_data, colWidths=widths, repeatRows=1, splitByRow=1, hAlign='LEFT')
        style_cmds: list[tuple[Any, ...]] = [
            ('BACKGROUND', (0, 0), (-1, 0), palette['header']),
            ('TEXTCOLOR', (0, 0), (-1, 0), palette['header_text']),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        if statement_mode:
            style_cmds[2] = ('LEFTPADDING', (0, 0), (-1, -1), 5.5)
            style_cmds[3] = ('RIGHTPADDING', (0, 0), (-1, -1), 5.5)
            style_cmds[4] = ('TOPPADDING', (0, 0), (-1, -1), 4.5)
            style_cmds[5] = ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5)
            style_cmds[6] = ('VALIGN', (0, 0), (-1, -1), 'TOP')
        if is_empty_state:
            style_cmds.extend([
                ('SPAN', (0, 1), (-1, 1)),
                ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
                ('VALIGN', (0, 1), (-1, 1), 'MIDDLE'),
                ('TEXTCOLOR', (0, 1), (-1, 1), palette['muted']),
                ('LINEBELOW', (0, 0), (-1, 0), header_rule_width, palette['line']),
            ])
        else:
            for table_row_idx in range(0, len(table_data)):
                if table_row_idx == 0:
                    style_cmds.append(('LINEBELOW', (0, table_row_idx), (-1, table_row_idx), header_rule_width, palette['line']))
                    continue
                source_idx = table_row_idx - 1
                row_label = str(_clean_display_text(rows[source_idx][0])) if source_idx < len(rows) and rows[source_idx] else ''
                meta = row_meta[source_idx] if row_meta and source_idx < len(row_meta) else {}
                depth = int(meta.get('depth') or 0)
                if statement_mode and depth > 0:
                    style_cmds.append(('LEFTPADDING', (0, table_row_idx), (0, table_row_idx), 5.5 + depth * 7))
                if total_pattern.match(row_label) or meta.get('is_total'):
                    style_cmds.append(('LINEBELOW', (0, table_row_idx), (-1, table_row_idx), 0.8, palette['ink']))
                if statement_mode and level > 0:
                    style_cmds.append(('LEFTPADDING', (0, table_row_idx), (0, table_row_idx), 5.5 + level * 7))
                if delta_cols and statement_mode:
                    tone_by_col = {
                        len(headers) - 2: meta.get('yoy_q_tone'),
                        len(headers) - 1: meta.get('yoy_fy_tone'),
                    }
                    for col_idx, tone in tone_by_col.items():
                        if tone == 'alert':
                            style_cmds.append(('BACKGROUND', (col_idx, table_row_idx), (col_idx, table_row_idx), palette['alert_soft']))
                        elif tone == 'warning':
                            style_cmds.append(('BACKGROUND', (col_idx, table_row_idx), (col_idx, table_row_idx), palette['warning_soft']))
        table.setStyle(TableStyle(style_cmds))
        return table

    def draw_cover(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(palette['page'])
        canvas.rect(0, 0, page_width, page_height, stroke=0, fill=1)
        canvas.setStrokeColor(palette['line'])
        canvas.setLineWidth(1 if theme_is_light else 0.6)
        canvas.line(margin, page_height - 13, page_width - margin, page_height - 13)
        canvas.restoreState()

    def draw_content(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(palette['page'])
        canvas.rect(0, 0, page_width, page_height, stroke=0, fill=1)
        canvas.setStrokeColor(palette['line'])
        canvas.setLineWidth(1 if theme_is_light else 0.6)
        canvas.line(margin, page_height - 13, page_width - margin, page_height - 13)
        canvas.line(margin, margin - 2, page_width - margin, margin - 2)
        canvas.setFont(body_font, 8)
        canvas.setFillColor(palette['muted'])
        canvas.drawRightString(page_width - margin, margin - 12, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    story: list[Any] = []

    # Cover page
    hero_summary = dict(cover.get('hero_summary') or {})

    def status_pill(label: str, tone: str) -> Table:
        # In dark theme: all states use outlined style (panel_soft bg + coloured border & text)
        # to avoid saturated filled chips that read as dashboard widgets.
        if not theme_is_light:
            tone_color = {
                'success': palette['positive'],
                'warning': palette['warning'],
                'danger': palette['danger'],
            }.get(tone, palette['accent'])
            pill = Table([[p(label, 'chip_label', color=tone_color, alignment=TA_CENTER)]], colWidths=[18 * mm])
            pill.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), palette['panel_soft']),
                ('BOX', (0, 0), (-1, -1), 0.8, tone_color),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            return pill
        tone_map = {
            'success': (palette['positive'], palette['page']),
            'warning': (palette['warning'], palette['page']),
            'danger': (palette['danger'], palette['page']),
        }
        bg, text_color = tone_map.get(tone, (palette['panel_soft'], palette['ink']))
        pill = Table([[p(label, 'chip_label', color=text_color, alignment=TA_CENTER)]], colWidths=[18 * mm])
        pill.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg),
            ('TEXTCOLOR', (0, 0), (-1, -1), text_color),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return pill

    def altman_progress_bar(percent: float | None, tone: str, width: float) -> Table:
        if percent is None:
            fill_width = 2.0
            track_width = max(2.0, width - fill_width)
            fill_color = palette['line']
        else:
            fill_width = max(2.5, min(width, width * max(0.0, min(percent, 100.0)) / 100.0))
            track_width = max(2.0, width - fill_width)
            fill_color = {
                'danger': palette['danger'],
                'warning': palette['warning'],
                'positive': palette['positive'],
            }.get(tone, palette['positive'])
        bar = Table([['', '']], colWidths=[fill_width, track_width], rowHeights=[5.6])
        bar.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), fill_color),
            ('BACKGROUND', (1, 0), (1, 0), palette['line']),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        return bar

    def altman_progress_row(item: dict[str, Any], width: float) -> Table:
        progress = item.get('progress')
        row_width = max(width - 8 * mm, width * 0.78)
        top_row = [
            p(item.get('label', '--'), 'hero_metric_label'),
            p(item.get('value', '--'), 'hero_metric_label', alignment=TA_RIGHT),
        ]
        row = Table(
            [
                top_row,
                [altman_progress_bar(progress, str(item.get('tone') or 'neutral'), row_width), ''],
                [Paragraph(f"Contribution: {html_lib.escape(str(item.get('contribution') or '--'))}", styles['hero_metric_contrib']), ''],
            ],
            colWidths=[row_width * 0.60, row_width * 0.40],
            rowHeights=[None, None, None],
        )
        row.setStyle(TableStyle([
            ('SPAN', (0, 1), (-1, 1)),
            ('SPAN', (0, 2), (-1, 2)),
            ('LEFTPADDING', (0, 0), (-1, -1), 0.5 * mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4.5 * mm),
            ('TOPPADDING', (0, 0), (-1, -1), 0.5 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5 * mm),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return row

    def _progress_is_valid(item: dict[str, Any]) -> bool:
        """Return True only when progress is a real numeric value worth visualising."""
        p_val = item.get('progress')
        if p_val is None:
            return False
        value_str = _clean_display_text(item.get('value', '--'))
        if value_str in ('--', 'N/A', 'n/a', ''):
            return False
        try:
            float(p_val)
            return True
        except (TypeError, ValueError):
            return False

    def altman_factor_row(item: dict[str, Any], width: float) -> Table:
        """Compact tabular factor row: label | value | contribution (no progress bar)."""
        row_width = max(width - 8 * mm, width * 0.78)
        label_w = row_width * 0.58
        value_w = row_width * 0.20
        contrib_w = row_width - label_w - value_w
        contrib_str = _clean_display_text(item.get('contribution', '--'))
        row = Table(
            [[
                p(item.get('label', '--'), 'hero_metric_label'),
                p(item.get('value', '--'), 'hero_metric_label', alignment=TA_RIGHT),
                Paragraph(f"<i>{html_lib.escape(contrib_str)}</i>", styles['hero_metric_contrib']),
            ]],
            colWidths=[label_w, value_w, contrib_w],
        )
        row.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0.5 * mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4.5 * mm),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (-1, 0), 0.25, palette['line']),
        ]))
        return row

    breakdown_items = [dict(item) for item in hero_summary.get('breakdown', []) if isinstance(item, dict)]
    if not breakdown_items:
        breakdown_items = [
            {'label': _t(lang, 'altman_component_wc'), 'value': '--', 'contribution': '--', 'tone': 'neutral', 'progress': None},
            {'label': _t(lang, 'altman_component_re'), 'value': '--', 'contribution': '--', 'tone': 'neutral', 'progress': None},
            {'label': _t(lang, 'altman_component_ebit'), 'value': '--', 'contribution': '--', 'tone': 'neutral', 'progress': None},
        ]

    # Change 6: editorial width split (54/46 minus an 8 mm gutter)
    gutter_width = 8 * mm
    left_width = (body_width - gutter_width) * 0.54
    right_width = body_width - gutter_width - left_width

    hero_score = _clean_display_text((hero_summary.get('items') or [{}])[0].get('value') if isinstance(hero_summary.get('items'), list) else '--') or '--'
    hero_status = _clean_display_text(hero_summary.get('status_label') or _t(lang, 'altman_status_watch')) or _t(lang, 'altman_status_watch')
    hero_status_tone = {
        'safe': 'success',
        'watch': 'warning',
        'distress': 'danger',
        '安全': 'success',
        '觀察': 'warning',
        '困境': 'danger',
        'ウォッチ': 'warning',
        'ディストレス': 'danger',
    }.get(hero_status.lower(), 'warning')
    hero_description = _clean_display_text(hero_summary.get('description') or '--')

    # Change 2: secondary items rendered as a single metadata line, not mini stat cards
    secondary_items = [dict(item) for item in (hero_summary.get('items') or [])[1:3] if isinstance(item, dict)]
    if not secondary_items:
        secondary_items = [
            {'label': _t(lang, 'zone'), 'value': '--', 'tone': 'neutral'},
            {'label': _t(lang, 'implied_rating'), 'value': '--', 'tone': 'neutral'},
        ]
    while len(secondary_items) < 2:
        secondary_items.append({'label': _t(lang, 'no_data'), 'value': '--', 'tone': 'neutral'})

    # Metadata line: "Zone: XXX  |  Implied Rating: YYY"
    meta_parts = []
    for si in secondary_items[:2]:
        si_label = _clean_display_text(si.get('label', '--'))
        si_value = _clean_display_text(si.get('value', '--'))
        if si_label and si_value:
            meta_parts.append(f"{html_lib.escape(si_label)}: <b>{html_lib.escape(si_value)}</b>")
    meta_line_text = '  \u2002  '.join(meta_parts) if meta_parts else '&nbsp;'
    meta_line = Paragraph(meta_line_text, styles['hero_metric_contrib'])

    score_and_pill = Table(
        [[Paragraph(esc(hero_score), styles['hero_score']), status_pill(hero_status, hero_status_tone)]],
        colWidths=[40 * mm, left_width - 40 * mm],
    )
    score_and_pill.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (0, 0), 'BOTTOM'),
        ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
    ]))

    left_panel = Table(
        [
            [Paragraph(esc(_t(lang, 'altman_z_score')), styles['hero_kicker'])],
            [score_and_pill],
            [Paragraph(esc(hero_description), styles['hero_summary'])],
            [Spacer(1, 2 * mm)],
            [meta_line],
        ],
        colWidths=[left_width],
    )
    left_panel.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    # Right panel: show breakdown factors, or a muted placeholder when all data is unavailable
    right_inner_width = right_width - 4 * mm
    all_breakdown_empty = all(
        _clean_display_text(item.get('value', '--')) in ('--', 'N/A', 'n/a', '')
        for item in breakdown_items[:3]
    )
    if all_breakdown_empty:
        right_content = p(_t(lang, 'no_data'), 'hero_metric_contrib', color=palette['muted'])
        right_panel = Table([[right_content]], colWidths=[right_width])
        right_panel.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 2 * mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2 * mm),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
    else:
        use_bars = all(_progress_is_valid(item) for item in breakdown_items[:3])
        if use_bars:
            factor_widgets = [altman_progress_row(item, right_inner_width) for item in breakdown_items[:3]]
        else:
            factor_widgets = [altman_factor_row(item, right_inner_width) for item in breakdown_items[:3]]
        progress_stack = stack_blocks(factor_widgets, right_inner_width, gap=2 * mm)
        right_panel = Table([[progress_stack]], colWidths=[right_width])
        right_panel.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 2 * mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2 * mm),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

    hero_panel = Table([[left_panel, Spacer(1, 1), right_panel]], colWidths=[left_width, gutter_width, right_width])
    hero_panel_style = [
        ('BACKGROUND', (0, 0), (-1, -1), palette['panel_soft'] if not theme_is_light else palette['page']),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]
    if theme_is_light:
        hero_panel_style.extend([
            ('BOX', (0, 0), (-1, -1), 0.5, palette['line']),
        ])
    else:
        hero_panel_style.extend([
            ('BOX', (0, 0), (-1, -1), 0.6, palette['line']),
        ])
    hero_panel.setStyle(TableStyle(hero_panel_style))

    localized_font = body_font
    if any(ord(ch) > 127 for ch in str(cover['company_name_localized'])) and body_font in {'Helvetica', 'Helvetica-Bold'}:
        cjk_lang = lang if lang in ('ja', 'zh-TW', 'zh-CN') else 'zh-CN'
        localized_font, _ = register_cjk_fonts(cjk_lang)
    localized_style = ParagraphStyle(
        'localized_style',
        parent=styles['subtitle'],
        fontName=localized_font,
        fontSize=13,
        leading=15,
        textColor=palette['ink'],
    )

    dateline_text = f"{_t(lang, 'latest_period')}: {cover['latest_period']} | {_t(lang, 'currency')}: {cover['currency']} | {_t(lang, 'data_source')}: {cover.get('data_source') or '--'} | {_t(lang, 'generated_at')}: {cover['generated_at']}"
    title_rows = [[p(cover['company_name'], 'title')]]
    if cover.get('company_name_localized'):
        title_rows.append([Paragraph(esc(f"{cover['company_name_localized']} | {cover['ticker']}"), localized_style)])
    else:
        title_rows.append([Paragraph(esc(cover['ticker']), localized_style)])
    title_rows.append([p(dateline_text, 'caption')])
    title_block = Table(title_rows, colWidths=[body_width])
    title_block.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    story.extend([
        Spacer(1, 16 * mm),
        title_block,
        Spacer(1, 8 * mm),
        hero_panel,
    ])

    # Summary section (Page 1: Key Risk Profile)
    story.extend([
        p(ctx['key_risk_profile_title'], 'section'),
        section_rule(body_width),
        Spacer(1, 1.5 * mm),
        split_body(
            subtle_section_block(_t(lang, 'strengths'), summary['strengths'], (body_width - 6 * mm) / 2, 'bullet'),
            subtle_section_block(_t(lang, 'watch_items'), summary['watch_items'], (body_width - 6 * mm) / 2, 'bullet'),
            body_width,
        ),
        NextPageTemplate('content'),
        PageBreak(),
    ])

    # Summary section (Page 2: Company Profile & Data Quality)
    company_profile_rows = summary['company_profile_rows']
    data_quality_rows = summary['data_quality_rows']
    if has_data_quality_rows(data_quality_rows):
        profile_block = subtle_section_block(
            None,
            [label_value_line(row['label'], row['value']) for row in company_profile_rows],
            (body_width - 6 * mm) / 2,
            'flowables',
        )
        data_quality_block = subtle_section_block(
            _t(lang, 'data_quality'),
            [data_quality_line(row) for row in data_quality_rows],
            (body_width - 6 * mm) / 2,
            'flowables',
        )
        profile_panel = split_body(
            profile_block,
            data_quality_block,
            body_width,
        )
    else:
        profile_block = subtle_section_block(
            None,
            [label_value_line(row['label'], row['value']) for row in company_profile_rows],
            body_width,
            'flowables',
        )
        profile_panel = profile_block
    story.extend([
        p(ctx['company_profile_title'], 'section'),
        section_rule(body_width),
        Spacer(1, 1.5 * mm),
        profile_panel,
        Spacer(1, 8 * mm),
    ])
    story.append(PageBreak())

    # Covenant page
    story.extend([
        p(covenant['title'], 'section'),
        p(covenant['note_title'], 'note'),
        report_table(
            [
                _t(lang, 'metric'),
                _t(lang, 'actual'),
                _t(lang, 'threshold'),
                _t(lang, 'status'),
                _t(lang, 'signal'),
                _t(lang, 'notes'),
            ],
            [[row.get('metric', '--'), row.get('actual', '--'), row.get('threshold', '--'), row.get('status', row.get('status_signal', '--')), row.get('signal', '--'), row.get('notes', '--')] for row in covenant['rows']],
            [body_width * 0.23, body_width * 0.12, body_width * 0.12, body_width * 0.12, body_width * 0.10, body_width * 0.31],
            alignments=['left', 'right', 'right', 'center', 'center', 'left'],
            status_col_idx=3,
            status_tones=[str(row.get('status_signal_tone') or 'neutral') for row in covenant['rows']],
        ),
    ])
    story.append(PageBreak())

    # KPI page
    story.extend([
        p(kpi['title'], 'section'),
        p(' | '.join(item for item in (kpi.get('unit_note'), kpi.get('yoy_note')) if _clean_display_text(item)), 'note'),
        report_table(
            kpi['headers'],
            kpi['rows'],
            kpi_widths(body_width, len(kpi['headers'])),
            benchmark_cols=kpi['benchmark_cols'],
            group_break_cols=kpi['group_break_cols'],
            alignments=['left'] + ['right'] * (len(kpi['headers']) - 1),
            delta_cols={len(kpi['headers']) - 2, len(kpi['headers']) - 1},
        ),
    ])

    # Statement sections — skip sections with no valid data rows
    for section in statements:
        rows_for_section = section.get('table_rows') or [[row['label'], *row['values'], row['yoy_q'], row['yoy_fy']] for row in section['rows']]
        row_meta = [dict(row) for row in section['rows']]
        has_data = any(
            any(_clean_display_text(cell) not in ('', '--', 'N/A', 'n/a') for cell in row[1:])
            for row in rows_for_section
        )
        if not has_data and not section.get('force_show'):
            continue
        statement_note = ' | '.join(
            item for item in (
                section.get('unit_note'),
                _t(lang, 'statement_summary_note'),
                section.get('yoy_note'),
            )
            if _clean_display_text(item)
        )
        story.append(PageBreak())
        story.extend([
            p(section['display_title'], 'section'),
            p(statement_note, 'note'),
            report_table(
                [_t(lang, 'metric')] + [period['label'] for period in section['periods']] + [section['yoy_label_q'], section['yoy_label_fy']],
                rows_for_section,
                statement_widths(body_width, len(section['periods'])),
                benchmark_cols=section['benchmark_cols'],
                group_break_cols=section['group_break_cols'],
                alignments=['left'] + ['right'] * (len(section['periods']) + 2),
                delta_cols={len(section['periods']) + 1, len(section['periods']) + 2},
                statement_mode=True,
                row_meta=row_meta,
            ),
        ])

    # Appendix: statement details, methodology notes, and covenant indicator descriptions.
    detail_sections = [section for section in statements if section.get('detail_rows')]
    if detail_sections:
        story.append(PageBreak())
        story.extend([
            p(appendix.get('statement_detail_title') or _t(lang, 'financial_statements'), 'section'),
            section_rule(body_width),
            Spacer(1, 2 * mm),
        ])
        first_detail = True
        for section in detail_sections:
            if not first_detail:
                story.append(PageBreak())
            first_detail = False
            rows_for_section = [[row['label'], *row['values'], row['yoy_q'], row['yoy_fy']] for row in section['detail_rows']]
            rows_for_section = section.get('detail_table_rows') or rows_for_section
            row_meta = [dict(row) for row in section['detail_rows']]
            detail_note = ' | '.join(
                item for item in (section.get('detail_unit_note') or section.get('unit_note'), section.get('yoy_note'))
                if _clean_display_text(item)
            )
            story.extend([
                p(section['display_title'], 'section'),
                p(detail_note, 'note'),
                report_table(
                    [_t(lang, 'metric')] + [period['label'] for period in section['periods']] + [section['yoy_label_q'], section['yoy_label_fy']],
                    rows_for_section,
                    statement_widths(body_width, len(section['periods'])),
                    benchmark_cols=section['benchmark_cols'],
                    group_break_cols=section['group_break_cols'],
                    alignments=['left'] + ['right'] * (len(section['periods']) + 2),
                    delta_cols={len(section['periods']) + 1, len(section['periods']) + 2},
                    statement_mode=True,
                    row_meta=row_meta,
                ),
            ])

    methodology_notes = appendix.get('notes', [])
    covenant_notes = covenant.get('notes', [])
    data_source = _clean_display_text(appendix.get('data_source') or '--')
    disclaimer = _clean_display_text(appendix.get('disclaimer') or '')
    if methodology_notes or covenant_notes or data_source != '--' or disclaimer:
        # Keep the small appendix blocks together.  Flowables may still split
        # naturally if a long statement detail section leaves insufficient room.
        story.append(PageBreak())
        story.extend([
            p(appendix['title'], 'section'),
            section_rule(body_width),
            Spacer(1, 2 * mm),
        ])
        if methodology_notes:
            for note in methodology_notes:
                story.append(p(f'• {note}', 'bullet'))
        if covenant_notes:
            if methodology_notes:
                story.append(Spacer(1, 3 * mm))
            story.extend([
                p(appendix['covenant_note_title'], 'section'),
                section_rule(body_width),
                Spacer(1, 2 * mm),
            ])
            for cn in covenant_notes:
                metric = _clean_display_text(cn.get('metric', '--'))
                desc = _clean_display_text(cn.get('description', '--'))
                story.append(p(f'• {metric}: {desc}', 'bullet'))
        if data_source != '--' or disclaimer:
            story.append(Spacer(1, 3 * mm))
            story.extend([
                p(_t(lang, 'data_source'), 'section'),
                section_rule(body_width),
                Spacer(1, 2 * mm),
            ])
            story.append(p(f'{_t(lang, "data_source")}: {data_source}', 'bullet'))
            if disclaimer:
                story.append(p(f'{_t(lang, "disclaimer")}: {disclaimer}', 'bullet'))

    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=margin,
        rightMargin=margin,
        topMargin=16 * mm,
        bottomMargin=15 * mm,
        title=cover['report_title'],
        author='RiskLens',
    )
    cover_frame = Frame(margin, margin, body_width, body_height, id='cover_frame', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    content_frame = Frame(margin, margin, body_width, body_height, id='content_frame', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([
        PageTemplate(id='cover', frames=[cover_frame], onPage=draw_cover),
        PageTemplate(id='content', frames=[content_frame], onPage=draw_content),
    ])
    doc.build(story)
    return buffer.getvalue()
