"""Pytest configuration - centralized import path setup."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_MODULE_ALIASES = {
    "api": "src.api",
    "data_fetcher": "src.data_fetcher",
    "ratio_analyzer": "src.ratio_analyzer",
    "zscore": "src.zscore",
    "covenant_monitor": "src.covenant_monitor",
    "services": "src.services",
    "risklens_cli": "src.risklens_cli",
}

for alias, target in _MODULE_ALIASES.items():
    sys.modules.setdefault(alias, importlib.import_module(target))


@pytest.fixture(autouse=True)
def _clear_data_fetcher_caches():
    """Clear data_fetcher caches and in-flight state between tests."""
    from data_fetcher import _data_cache, _error_cache, _in_flight, _in_flight_lock
    _data_cache.clear()
    _error_cache.clear()
    with _in_flight_lock:
        _in_flight.clear()
