from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class StaticFiles:
    directory: str | None = None


__all__ = ["StaticFiles"]
