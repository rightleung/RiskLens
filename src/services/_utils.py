"""Shared utility functions for service layers."""

from __future__ import annotations

import math
import re
from typing import Any


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
    """Convert value to float, returning None for non-finite values.

    Args:
        value: Any value that might be numeric

    Returns:
        Float value or None if invalid/non-finite
    """
    if value is None:
        return None
    try:
        num = float(value)
        if math.isnan(num) or math.isinf(num):
            return None
        return num
    except (TypeError, ValueError):
        return None


def contains_cjk(text: str) -> bool:
    """Check if text contains CJK characters."""
    return bool(CJK_PATTERN.search(text))


def contains_japanese(text: str) -> bool:
    """Check if text contains Japanese characters."""
    return bool(JAPANESE_PATTERN.search(text))
