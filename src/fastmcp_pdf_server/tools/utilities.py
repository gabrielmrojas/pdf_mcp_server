from __future__ import annotations

import time
import uuid

from fastmcp import FastMCP  # type: ignore

from ..config import settings
from pathlib import Path

from PyPDF2 import PdfReader  # type: ignore

from ..services.file_manager import cleanup_expired, ensure_within_temp, list_resources, to_base64
from ..utils.logger import get_logger


logger = get_logger(__name__)


def register(app: FastMCP) -> None:
    @app.tool()
    async def server_info() -> dict:
        """Return basic server info and configuration snapshot (non-secret)."""
        op_id = uuid.uuid4().hex
        start = time.perf_counter()
        logger.info("server_info called op_id=%s", op_id)
        result = {
            "name": settings.server_name,
            "version": settings.server_version,
            "max_file_size_mb": settings.max_file_size_mb,
            "temp_dir": str(settings.temp_path),
            "log_file": str(settings.log_path),
        }
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info("server_info done op_id=%s ms=%d", op_id, duration_ms)
        return {**result, "meta": {"operation_id": op_id, "execution_ms": duration_ms}}

    @app.tool()
    async def list_temp_resources(content_type: str | None = None, max_items: int | None = 100) -> list[dict]:
        """List available temporary files with optional filtering.
        - content_type: filter by 'application/pdf', 'image/png', 'image/jpeg'
        - max_items: limit the number of returned entries
        """
        op_id = uuid.uuid4().hex
        start = time.perf_counter()
        logger.info("list_temp_resources called op_id=%s", op_id)
        cleanup_expired()
        resources = list_resources()
        if content_type:
            resources = [r for r in resources if r.content_type == content_type]
        results = [
            {
                "path": str(r.path),
                "size": r.size,
                "created": r.created,
                "content_type": r.content_type,
                "filename": r.path.name,
                "extension": r.path.suffix.lower(),
                "directory": str(r.path.parent),
            }
            for r in resources
        ]
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info("list_temp_resources done op_id=%s ms=%d", op_id, duration_ms)
        # x-fastmcp-wrap-result=true => return a list; framework wraps as {"result": [...]}.
        return results[: max_items or 100]

    @app.tool()
    async def get_pdf_info(file_path: str) -> dict:
        """Get comprehensive PDF information without processing content."""
        op_id = uuid.uuid4().hex
        start = time.perf_counter()
        logger.info("get_pdf_info called op_id=%s", op_id)
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            raise ValueError(f"File not found: {file_path}")
        reader = PdfReader(str(p))
        result = {
            "pages": len(reader.pages),
            "size": p.stat().st_size,
            "version": getattr(reader, "pdf_header", None),
            "encrypted": reader.is_encrypted,
        }
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info("get_pdf_info done op_id=%s ms=%d", op_id, duration_ms)
        return {**result, "meta": {"operation_id": op_id, "execution_ms": duration_ms}}

    @app.tool()
    async def get_resource_base64(file_path: str) -> dict:
        """Return base64 for a file within the temp directory only."""
        op_id = uuid.uuid4().hex
        start = time.perf_counter()
        logger.info("get_resource_base64 called op_id=%s", op_id)
        p = ensure_within_temp(Path(file_path))
        result = {"path": str(p), "base64": to_base64(p)}
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info("get_resource_base64 done op_id=%s ms=%d", op_id, duration_ms)
        return {**result, "meta": {"operation_id": op_id, "execution_ms": duration_ms}}
