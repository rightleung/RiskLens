from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .responses import FileResponse, JSONResponse, StreamingResponse


@dataclass
class _Route:
    path: str
    handler: Callable[..., Any]


class FastAPI:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs
        self.routes: dict[str, _Route] = {}
        self.middleware: list[tuple[Any, dict[str, Any]]] = []
        self.mounts: list[tuple[str, Any, str | None]] = []
        self.exception_handlers: dict[type[Any], Callable[..., Any]] = {}

    def _route_decorator(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes[path] = _Route(path=path, handler=func)
            return func

        return decorator

    def get(self, path: str, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._route_decorator(path)

    def post(self, path: str, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._route_decorator(path)

    def exception_handler(self, exc_type: type[Any]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.exception_handlers[exc_type] = func
            return func

        return decorator

    def add_middleware(self, middleware_class: Any, **kwargs: Any) -> None:
        self.middleware.append((middleware_class, kwargs))

    def mount(self, path: str, app: Any, name: str | None = None) -> None:
        self.mounts.append((path, app, name))


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: Any = None) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def Query(default: Any = None, **kwargs: Any) -> Any:
    return default


class StaticFiles:
    def __init__(self, directory: str | None = None, **kwargs: Any) -> None:
        self.directory = directory
        self.kwargs = kwargs


__all__ = [
    "FastAPI",
    "FileResponse",
    "HTTPException",
    "JSONResponse",
    "Query",
    "StaticFiles",
    "StreamingResponse",
]
