from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class _ClientResponse:
    status_code: int
    media_type: str
    content: bytes
    headers: dict[str, str]


class TestClient:
    __test__ = False

    def __init__(self, app: Any) -> None:
        self.app = app

    def post(self, path: str, json: dict[str, Any] | None = None) -> _ClientResponse:
        route = self.app.routes.get(path)
        if route is None:
            raise AssertionError(f"Route not found: {path}")

        result = route.handler(json or {})
        if inspect.isawaitable(result):
            result = asyncio.run(result)

        content = getattr(result, "content", b"")
        if hasattr(content, "getvalue"):
            content = content.getvalue()
        elif hasattr(content, "read"):
            content = content.read()

        return _ClientResponse(
            status_code=getattr(result, "status_code", 200),
            media_type=getattr(result, "media_type", "application/octet-stream"),
            content=content,
            headers=getattr(result, "headers", {}),
        )


__all__ = ["TestClient"]
