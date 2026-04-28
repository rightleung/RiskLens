"""Shared utility functions for service layers."""

from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd


# CJK and Japanese text detection patterns
CJK_PATTERN = re.compile(r"[一-鿿]")
JAPANESE_PATTERN = re.compile(r"[぀-ヿ]")


def json_safe(value: Any) -> Any:
    """Recursively replace non-JSON-safe values (NaN, inf) with None.

    Args:
        value: Any Python value (dict, list, float, etc.)

    Returns:
        JSON-safe version of the value
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
    return value


def safe_number(value: Any) -> float | None:
    """Convert numeric-like values to finite floats.

    Handles report strings such as ``"1,234"``, ``"(1,234)"``, ``"12.5%"``,
    and European-style decimal strings like ``"1,25"``.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        num = float(value)
        return None if math.isnan(num) or math.isinf(num) else num
    if isinstance(value, str):
        text = value.strip()
        if not text or text in {"--", "-", "n/a", "N/A"}:
            return None
        negative = text.startswith("(") and text.endswith(")")
        text = text.strip("()").replace("%", "")
        if re.fullmatch(r"[+-]?\d+,\d{1,2}", text):
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")
        try:
            num = float(text)
        except ValueError:
            return None
        if math.isnan(num) or math.isinf(num):
            return None
        return -num if negative else num
    try:
        num = float(value)
        return None if math.isnan(num) or math.isinf(num) else num
    except (TypeError, ValueError):
        return None


def get_dataframe_value(df: pd.DataFrame, key: str, column: str = "Value") -> float | None:
    """Extract a finite float from a standardized financial DataFrame."""
    if df is None or df.empty:
        return None

    try:
        if key in df.index:
            value = df.loc[key]
            if isinstance(value, pd.Series):
                value = value[column] if column in value.index else (value.iloc[0] if len(value) > 0 else None)
        elif key in df.columns:
            value = df[key]
            if isinstance(value, pd.Series):
                value = value.iloc[0] if len(value) > 0 else None
        else:
            return None
        return safe_number(value)
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def infer_fiscal_year(year_label: str | None, fallback: int | None = None) -> int:
    """Infer fiscal year from annual or quarterly labels."""
    from datetime import datetime

    current_year = datetime.now().year
    if not year_label:
        return fallback or current_year

    quarter_match = re.search(
        r"(?:Q([1-4])\s*'?\s*(\d{2,4})|(\d{2,4})\s*Q([1-4]))",
        str(year_label),
        flags=re.I,
    )
    if quarter_match:
        year_text = quarter_match.group(2) or quarter_match.group(3) or ""
        if len(year_text) == 4:
            return int(year_text)
        if len(year_text) == 2:
            value = int(year_text)
            return 2000 + value if value < 80 else 1900 + value

    digits = re.sub(r"\D", "", str(year_label))
    if len(digits) >= 4:
        return int(digits[-4:])
    if len(digits) == 2:
        value = int(digits)
        return 2000 + value if value < 80 else 1900 + value
    return fallback or current_year


def convert_simplified_to_traditional(text: str) -> str:
    """Convert simplified Chinese text to traditional Chinese when OpenCC exists."""
    try:
        import opencc

        return opencc.OpenCC("s2t.json").convert(text)
    except (ImportError, RuntimeError):
        return text


def contains_cjk(text: str) -> bool:
    """Check if text contains CJK characters."""
    return bool(CJK_PATTERN.search(text))


def contains_japanese(text: str) -> bool:
    """Check if text contains Japanese characters."""
    return bool(JAPANESE_PATTERN.search(text))
