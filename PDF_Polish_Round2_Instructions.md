# RiskLens PDF 真实数据版第三轮打磨指令

在审查最新生成的 PDF（以 MSFT 为例）时，我们发现了以下几个影响专业感和数据严谨性的细节问题，需要进行最终的修复：

## 1. YoY 同比计算出现“实数”而非百分比
*   **问题表现**：在 Cash Flow 等报表中，当上一期数据为负数（如净亏损）而本期为正数，或者上一期为 0 时，原本应该显示百分比的 YoY 列，突然显示成了带正负号的绝对数值（如 `+12.5B`）。这不符合金融表格规范。
*   **修复方案**：修改 `src/html_pdf_exporter.py` 中的 `_format_yoy_change` 函数。在遇到上一期为 0，或者前后两期符号相反（Sign Flip）时，直接返回 `'N/M'` (Not Meaningful，无意义)，避免输出绝对数值干扰百分比列。

## 2. 财务报表 (P5, P6) 渲染出多余的实线网格
*   **问题表现**：在利润表和资产负债表中，由于底层画线逻辑的问题，几乎每一行数据下方都被画上了一条细实线，导致长长的报表看起来像粗糙的 Excel 网格，而不是专业的投行留白排版。
*   **修复方案**：修改 `src/reportlab_pdf_renderer.py` 中的 `report_table` 函数。移除对每一行都绘制 `LINEBELOW` 的逻辑，仅在“表头 (Header)”和正则匹配到的“汇总行 (Total Rows)”下方绘制分割线。

## 3. 报表上方出现 `N/A vs N/A` 的冗余提示
*   **问题表现**：当只拉取了年报数据，没有季报数据时，利润表等页面上方的 YoY 提示会丑陋地显示为 `(N/A vs N/A | FY25 vs FY24)`。
*   **修复方案**：修改 `src/html_pdf_exporter.py` 中的 `_format_yoy_note` 函数。加入过滤逻辑，如果某个周期的对比字符串含有 N/A（或为空），则直接将其从合并字符串中剔除，只显示有意义的部分，如 `(FY25 vs FY24)`。

## 4. Methodology 脚注被遮挡与 Covenant Pre-Check 无数据
*   **问题表现**：原本要求放在 Page 1 左下角的 Methodology 脚注没有出现，这是因为它的 Y 轴坐标被设置得太高，被首页的白色背景和内容遮挡了。另外，Covenant Pre-Check 表格依然显示 `No valid data`，因为真实数据 API 没有下发契约指标。
*   **修复方案**：
    *   在 `src/reportlab_pdf_renderer.py` 的 `draw_cover` 中，将 `footer_text_y` 下调至 `margin - 12`（打印安全区内），确保它悬浮于内容之上。
    *   在 `src/services/rich_assessment_service.py` 中，在 `_build_assessment` 组装返回结果时，利用已经算好的真实比率（如 Debt/EBITDA）动态生成一组基础的 `covenant_pre_check` 契约预检数据，让表格充实起来。

---

## 具体的代码替换指令 `[Old String]` -> `[New String]`

### 修复 1: 规范 YoY 异常值的显示 (N/M)
**文件**: `src/html_pdf_exporter.py`

**[Old String]**
```python
def _format_yoy_change(current: Any, previous: Any) -> str:
    current_num = _safe_number(current)
    previous_num = _safe_number(previous)
    if current_num is None or previous_num is None:
        return 'N/A'
    if previous_num == 0:
        return _format_number(current_num - previous_num, signed=True)
    if current_num < 0 < previous_num or previous_num < 0 < current_num:
        return _format_number(current_num - previous_num, signed=True)
    if current_num < 0 and previous_num < 0:
        pct = (abs(current_num) - abs(previous_num)) / abs(previous_num) * 100
        return _format_number(pct, signed=True, suffix='%')
    pct = (current_num - previous_num) / abs(previous_num) * 100
    return _format_number(pct, signed=True, suffix='%')
```

**[New String]**
```python
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
```

### 修复 2: 移除财务报表多余的实线网格
**文件**: `src/reportlab_pdf_renderer.py`

**[Old String]**
```python
        else:
            for row_idx in range(0, len(table_data) - 1):
                row_label = _clean_display_text(rows[row_idx - 1][0]) if row_idx > 0 and row_idx - 1 < len(rows) and rows[row_idx - 1] else ''
                if not theme_is_light and re.fullmatch(r'(?i)(total|subtotal|category|gross profit|operating income|net income)', row_label):
                    style_cmds.append(('LINEBELOW', (0, row_idx), (-1, row_idx), 0.8, palette['ink']))
                else:
                    style_cmds.append(('LINEBELOW', (0, row_idx), (-1, row_idx), header_rule_width if row_idx == 0 else row_rule_width, palette['line']))
```

**[New String]**
```python
        else:
            for row_idx in range(0, len(table_data) - 1):
                if row_idx == 0:
                    style_cmds.append(('LINEBELOW', (0, row_idx), (-1, row_idx), header_rule_width, palette['line']))
                    continue
                row_label = str(_clean_display_text(rows[row_idx - 1][0])) if row_idx > 0 and row_idx - 1 < len(rows) and rows[row_idx - 1] else ''
                if total_pattern.match(row_label):
                    style_cmds.append(('LINEBELOW', (0, row_idx), (-1, row_idx), 0.8, palette['ink']))
```

### 修复 3: 清理冗余的 `N/A vs N/A` 提示
**文件**: `src/html_pdf_exporter.py`

**[Old String]**
```python
def _format_yoy_note(lang: str, quarter_current: str | None, quarter_compare: str | None, annual_current: str | None, annual_compare: str | None) -> str:
    quarter_text = _format_yoy_label(lang, quarter_current, quarter_compare) if quarter_current and quarter_compare else f'{quarter_current or "N/A"} vs {quarter_compare or "N/A"}'
    annual_text = _format_yoy_label(lang, annual_current, annual_compare) if annual_current and annual_compare else f'{annual_current or "N/A"} vs {annual_compare or "N/A"}'
    templates = {
        'en': '({quarter} | {annual})',
        'zh-CN': '（{quarter} | {annual}）',
        'zh-TW': '（{quarter} | {annual}）',
        'ja': '（{quarter} | {annual}）',
    }
    return templates.get(lang, templates['en']).format(quarter=quarter_text, annual=annual_text)
```

**[New String]**
```python
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
```

### 修复 4: 抢救被遮挡的 Methodology 脚注
**文件**: `src/reportlab_pdf_renderer.py`

**[Old String]**
```python
        canvas.line(margin, page_height - 13, page_width - margin, page_height - 13)
        # Fixed footer band: rule at 18 mm, text ~5.5 mm above it
        footer_rule_y = 18 * mm
        footer_text_y = footer_rule_y + 5.5 * mm
        canvas.setLineWidth(0.25)
        canvas.setStrokeColor(palette['line'])
        canvas.line(margin, footer_rule_y, page_width - margin, footer_rule_y)
        canvas.setFont(body_font, 6)
        canvas.setFillColor(palette['muted'])
        # Footer: display methodology note on cover page as a compact footnote
        methodology_text = ctx.get('hero_summary', {}).get('note', '')
        canvas.drawString(margin, footer_text_y, methodology_text)
        canvas.restoreState()
```

**[New String]**
```python
        canvas.line(margin, page_height - 13, page_width - margin, page_height - 13)
        # Footer: display methodology note on cover page as a compact footnote
        footer_rule_y = margin - 2
        footer_text_y = margin - 12
        canvas.setLineWidth(0.25)
        canvas.setStrokeColor(palette['line'])
        canvas.line(margin, footer_rule_y, page_width - margin, footer_rule_y)
        
        # In case methodology is in CJK, use localized font
        methodology_text = ctx.get('hero_summary', {}).get('note', '')
        localized_font = body_font
        if any(ord(ch) > 127 for ch in methodology_text) and body_font in {'Helvetica', 'Helvetica-Bold'}:
            lang = ctx.get('lang', 'en')
            if lang == 'ja':
                localized_font = 'HeiseiMin-W3'
            elif lang == 'zh-TW':
                localized_font = 'MSung-Light'
            else:
                localized_font = 'STSong-Light'
        
        canvas.setFont(localized_font, 6)
        canvas.setFillColor(palette['muted'])
        canvas.drawString(margin, footer_text_y, methodology_text)
        canvas.restoreState()
```

### 修复 5: 填充 Covenant Pre-Check 真实指标
**文件**: `src/services/rich_assessment_service.py`

**[Old String]**
```python
        assessment = {
            "risk_score": float(round(z_result.z_score, 2)) if z_result.z_score is not None else 0.0,
            "overall_rating": z_result.zone,
            "implied_rating": z_result.implied_rating,
            "strengths": strengths,
            "weaknesses": weaknesses,
        }
        return self._json_safe(assessment)
```

**[New String]**
```python
        assessment = {
            "risk_score": float(round(z_result.z_score, 2)) if z_result.z_score is not None else 0.0,
            "overall_rating": z_result.zone,
            "implied_rating": z_result.implied_rating,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "covenant_pre_check": [
                {
                    "metric": "Debt/EBITDA",
                    "actual": float(round(ratios.debt_to_ebitda, 2)) if ratios.debt_to_ebitda else None,
                    "threshold": 3.5,
                    "status": "Pass" if ratios.debt_to_ebitda and ratios.debt_to_ebitda <= 3.5 else "Fail",
                    "signal": "Green" if ratios.debt_to_ebitda and ratios.debt_to_ebitda <= 3.5 else "Red",
                    "notes": "Comfortable leverage" if ratios.debt_to_ebitda and ratios.debt_to_ebitda <= 3.5 else "High leverage"
                },
                {
                    "metric": "Interest Coverage",
                    "actual": float(round(ratios.interest_coverage, 2)) if ratios.interest_coverage else None,
                    "threshold": 3.0,
                    "status": "Pass" if ratios.interest_coverage and ratios.interest_coverage >= 3.0 else "Fail",
                    "signal": "Green" if ratios.interest_coverage and ratios.interest_coverage >= 3.0 else "Red",
                    "notes": "Strong coverage" if ratios.interest_coverage and ratios.interest_coverage >= 3.0 else "Weak coverage"
                },
                {
                    "metric": "Current Ratio",
                    "actual": float(round(ratios.current_ratio, 2)) if ratios.current_ratio else None,
                    "threshold": 1.2,
                    "status": "Pass" if ratios.current_ratio and ratios.current_ratio >= 1.2 else "Fail",
                    "signal": "Green" if ratios.current_ratio and ratios.current_ratio >= 1.2 else "Red",
                    "notes": "Adequate liquidity" if ratios.current_ratio and ratios.current_ratio >= 1.2 else "Poor liquidity"
                }
            ]
        }
        return self._json_safe(assessment)
```
