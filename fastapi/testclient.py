from __future__ import annotations

import asyncio
import json as json_module
import inspect
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from . import HTTPException as FastAPIHTTPException
from .responses import FileResponse, JSONResponse, StreamingResponse


@dataclass(slots=True)
class _ClientResponse:
    status_code: int
    media_type: str
    content: bytes
    headers: dict[str, str]

    def json(self) -> Any:
        return json_module.loads(self.content.decode("utf-8") or "null")

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")


class TestClient:
    __test__ = False

    def __init__(self, app: Any) -> None:
        self.app = app

    def get(self, path: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> _ClientResponse:
        return self._request("GET", path, params=params, headers=headers)

    def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> _ClientResponse:
        return self._request("POST", path, json=json, headers=headers)

    def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> _ClientResponse:
        route = self.app.routes.get(path)
        if route is None:
            route = self.app.routes.get("/{full_path:path}")
            if route is not None:
                payload = path.lstrip("/")
            else:
                raise AssertionError(f"Route not found: {path}")
        else:
            payload = json if method == "POST" else params or {}

        try:
            result = self._invoke_handler(route.handler, payload)
            if inspect.isawaitable(result):
                result = asyncio.run(result)
        except FastAPIHTTPException as exc:
            return self._make_response(
                status_code=exc.status_code,
                media_type="application/json",
                content=json_module.dumps({"detail": exc.detail}).encode("utf-8"),
                headers=self._apply_cors_headers(headers or {}, {"content-type": "application/json"}),
            )
        except PydanticValidationError as exc:
            errors = []
            for error in exc.errors():
                error_dict = {
                    "type": error.get("type"),
                    "loc": error.get("loc"),
                    "msg": error.get("msg"),
                    "input": str(error.get("input")) if error.get("input") is not None else None,
                }
                if "ctx" in error:
                    error_dict["ctx"] = {k: str(v) for k, v in error["ctx"].items()}
                errors.append(error_dict)

            return self._make_response(
                status_code=422,
                media_type="application/json",
                content=json_module.dumps({"detail": errors}).encode("utf-8"),
                headers=self._apply_cors_headers(headers or {}, {"content-type": "application/json"}),
            )

        content = getattr(result, "content", b"")
        if hasattr(content, "getvalue"):
            content = content.getvalue()
        elif hasattr(content, "read"):
            content = content.read()

        response_headers = dict(getattr(result, "headers", {}) or {})
        media_type = getattr(result, "media_type", "application/octet-stream")
        status_code = getattr(result, "status_code", 200)

        if isinstance(result, JSONResponse) or isinstance(result, dict) or isinstance(result, list):
            if not isinstance(result, JSONResponse):
                content = json_module.dumps(result).encode("utf-8")
            elif not isinstance(content, (bytes, bytearray)):
                content = json_module.dumps(content).encode("utf-8")
            media_type = "application/json"
            response_headers.setdefault("content-type", media_type)
        elif isinstance(result, FileResponse):
            with open(result.path, "rb") as fh:
                content = fh.read()
            media_type = result.media_type
        elif isinstance(result, StreamingResponse):
            if hasattr(result.content, "getvalue"):
                content = result.content.getvalue()
            elif hasattr(result.content, "read"):
                content = result.content.read()
            else:
                content = result.content

        if not isinstance(content, (bytes, bytearray)):
            content = str(content).encode("utf-8")

        response_headers = {str(key).lower(): value for key, value in response_headers.items()}
        response_headers = self._apply_cors_headers(headers or {}, response_headers)
        response_headers.setdefault("content-type", media_type)
        return self._make_response(status_code=status_code, media_type=media_type, content=bytes(content), headers=response_headers)

    def _make_response(self, status_code: int, media_type: str, content: bytes, headers: dict[str, str]) -> _ClientResponse:
        return _ClientResponse(status_code=status_code, media_type=media_type, content=content, headers=headers)

    def _invoke_handler(self, handler: Any, payload: dict[str, Any]) -> Any:
        signature = inspect.signature(handler)
        parameters = list(signature.parameters.values())
        if not parameters:
            return handler()

        if len(parameters) == 1:
            param = parameters[0]
            annotation = param.annotation

            # Handle forward references from __future__ annotations
            if isinstance(annotation, str):
                # Try to resolve from handler's globals
                annotation = handler.__globals__.get(annotation, annotation)

            if inspect.isclass(annotation) and hasattr(annotation, "model_fields") and isinstance(payload, dict):
                try:
                    return handler(annotation(**payload))
                except PydanticValidationError:
                    raise
            return handler(payload)

        if payload:
            return handler(**payload)
        return handler()

    def _apply_cors_headers(self, request_headers: dict[str, str], response_headers: dict[str, str]) -> dict[str, str]:
        origin = request_headers.get("Origin") or request_headers.get("origin")
        if not origin:
            return response_headers

        for middleware_class, kwargs in getattr(self.app, "middleware", []):
            if getattr(middleware_class, "__name__", "") != "CORSMiddleware":
                continue
            allow_origins = kwargs.get("allow_origins", [])
            allow_credentials = bool(kwargs.get("allow_credentials", False))
            expose_headers = kwargs.get("expose_headers", [])
            if "*" in allow_origins or origin in allow_origins:
                response_headers.setdefault("access-control-allow-origin", origin if origin != "*" else "*")
                if allow_credentials:
                    response_headers.setdefault("access-control-allow-credentials", "true")
                if expose_headers:
                    response_headers.setdefault("access-control-expose-headers", ", ".join(expose_headers))
            break
        return response_headers


__all__ = ["TestClient"]
