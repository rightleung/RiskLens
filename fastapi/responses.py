from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StreamingResponse:
    content: bytes
    media_type: str = "application/octet-stream"
    headers: dict[str, str] = field(default_factory=dict)
    status_code: int = 200


@dataclass(slots=True)
class JSONResponse:
    content: Any
    status_code: int = 200
    media_type: str = "application/json"
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class FileResponse:
    path: str
    media_type: str = "application/octet-stream"
    headers: dict[str, str] = field(default_factory=dict)
    status_code: int = 200


__all__ = ["StreamingResponse", "JSONResponse", "FileResponse"]
