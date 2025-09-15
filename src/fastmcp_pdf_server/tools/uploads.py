from __future__ import annotations

from typing import Any, Optional
import time
import uuid

from fastmcp import FastMCP  # type: ignore

from ..services.file_manager import resolve_to_path
from ..utils.logger import get_logger


logger = get_logger(__name__)


def register(app: FastMCP) -> None:
    @app.tool()
    async def upload_file(file: Any, filename: Optional[str] = None) -> dict:
        """Persist an uploaded file into the server temp directory.

        Accepts:
        - Full path string
        - Short filename previously written to temp storage
        - Bytes / file-like / dict with base64 (will be saved to temp)
        """
        op_id = uuid.uuid4().hex
        start = time.perf_counter()
        try:
            resolved = resolve_to_path(file, filename_hint=filename or "upload.bin")
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "path": str(resolved),
                "filename": resolved.name,
                "directory": str(resolved.parent),
                "meta": {"operation_id": op_id, "execution_ms": duration_ms},
            }
        except Exception as e:  # noqa: BLE001
            logger.error("upload_file error: %s", e)
            raise ValueError(f"upload_file failed: {e}")

    @app.tool()
    async def upload_file_base64(base64: str, filename: str) -> dict:
        """Upload a file encoded as base64 and persist it in temp storage.

        Pass the base64-encoded content and the desired filename (e.g., "document.pdf").
        """
        op_id = uuid.uuid4().hex
        start = time.perf_counter()
        try:
            from base64 import b64decode
            data = b64decode(base64)
            # Reuse generic resolver by passing a dict
            resolved = resolve_to_path({"base64": base64, "filename": filename}, filename_hint=filename)
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "path": str(resolved),
                "filename": resolved.name,
                "directory": str(resolved.parent),
                "size": len(data),
                "meta": {"operation_id": op_id, "execution_ms": duration_ms},
            }
        except Exception as e:  # noqa: BLE001
            logger.error("upload_file_base64 error: %s", e)
            raise ValueError(f"upload_file_base64 failed: {e}")

    @app.tool()
    async def upload_file_url(url: str, filename: Optional[str] = None) -> dict:
        """Download a file from a URL and persist it in temp storage.

        Provide a direct URL and optional filename override.
        Requires 'requests' to be installed.
        """
        op_id = uuid.uuid4().hex
        start = time.perf_counter()
        try:
            resolved = resolve_to_path({"url": url, "filename": filename} if filename else {"url": url})
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "path": str(resolved),
                "filename": resolved.name,
                "directory": str(resolved.parent),
                "meta": {"operation_id": op_id, "execution_ms": duration_ms},
            }
        except Exception as e:  # noqa: BLE001
            logger.error("upload_file_url error: %s", e)
            raise ValueError(f"upload_file_url failed: {e}")
