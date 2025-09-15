from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Coroutine

from .logger import get_logger


logger = get_logger(__name__)


def _shorten(value: Any) -> Any:
    try:
        s = str(value)
    except Exception:
        return "<unrepr>"
    if len(s) > 200:
        return s[:200] + "…"
    return s


def _sanitize_kwargs(kwargs: dict) -> dict:
    redacted = {}
    for k, v in kwargs.items():
        if isinstance(k, str) and ("base64" in k.lower() or "password" in k.lower()):
            redacted[k] = "<redacted>"
        elif isinstance(v, str) and ("base64" in v.lower()):
            redacted[k] = "<redacted>"
        else:
            redacted[k] = _shorten(v)
    return redacted


def _attach_meta(result: Any, op_id: str, duration_ms: int) -> Any:
    meta = {"operation_id": op_id, "execution_ms": duration_ms}
    if isinstance(result, dict):
        if "meta" in result and isinstance(result["meta"], dict):
            result["meta"].update(meta)
        else:
            result["meta"] = meta
        return result
    if isinstance(result, list):
        return {"items": result, "meta": meta}
    return {"result": result, "meta": meta}


def instrument_tool(name: str) -> Callable[[Callable[..., Coroutine[Any, Any, Any]]], Callable[..., Coroutine[Any, Any, Any]]]:
    def decorator(fn: Callable[..., Coroutine[Any, Any, Any]]):
        async def wrapper(*args, **kwargs):
            op_id = uuid.uuid4().hex
            start = time.perf_counter()
            try:
                logger.info("op_start name=%s id=%s kwargs=%s", name, op_id, _sanitize_kwargs(kwargs))
                result = await fn(*args, **kwargs)
                duration_ms = int((time.perf_counter() - start) * 1000)
                logger.info("op_end name=%s id=%s ms=%d", name, op_id, duration_ms)
                return _attach_meta(result, op_id, duration_ms)
            except Exception as e:  # noqa: BLE001
                duration_ms = int((time.perf_counter() - start) * 1000)
                logger.error("op_error name=%s id=%s ms=%d error=%s", name, op_id, duration_ms, e)
                raise

        return wrapper

    return decorator
