from __future__ import annotations

import asyncio
from typing import Any, Callable


async def run_in_threadpool(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    return await asyncio.to_thread(func, *args, **kwargs)


__all__ = ["run_in_threadpool"]
