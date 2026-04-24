"""FastAPI exceptions shim for test compatibility."""

from __future__ import annotations

from typing import Any


class RequestValidationError(Exception):
    """Minimal RequestValidationError stub."""
    def __init__(self, errors: list[Any]) -> None:
        super().__init__(errors)
        self.errors = errors


__all__ = ["RequestValidationError"]
