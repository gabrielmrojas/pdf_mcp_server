from __future__ import annotations

from typing import Any, List, Optional
import time
import uuid

from fastmcp import FastMCP  # type: ignore

from ..services import pdf_processor
from ..services.file_manager import resolve_to_path
from ..utils.logger import get_logger


logger = get_logger(__name__)


def register(app: FastMCP) -> None:
    @app.tool()
    async def extract_text(file: Any, encoding: str | None = "utf-8") -> dict:
        """Extract all text from a PDF.

        Accepts:
        - Full path string
        - Short filename previously written to temp storage
        - Bytes / file-like / dict with base64 (will be saved to temp)
        """
        op_id = uuid.uuid4().hex
        start = time.perf_counter()
        try:
            resolved = resolve_to_path(file, filename_hint="uploaded.pdf")
            res = pdf_processor.extract_text(str(resolved), encoding or "utf-8")
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "text": res.text,
                "page_count": res.page_count,
                "char_count": res.char_count,
                "meta": {"operation_id": op_id, "execution_ms": duration_ms, "resolved_path": str(resolved)},
            }
        except Exception as e:  # noqa: BLE001
            logger.error("extract_text error: %s", e)
            hint = (
                "Provide a full path, upload the file first via 'upload_file', or pass bytes/base64. "
                "Example payload:\n"
                "{\n  \"name\": \"upload_file\",\n  \"arguments\": {\n    \"file\": { \"base64\": \"<...>\", \"filename\": \"my.pdf\" }\n  }\n}"
            )
            raise ValueError(f"extract_text failed: {e}. {hint}")

    @app.tool()
    async def extract_text_by_page(
        file: Any,
        pages: Optional[List[int]] = None,
        page_range: Optional[str] = None,
        encoding: str | None = "utf-8",
    ) -> list[dict]:
        """Extract text from specific pages or page ranges."""
        op_id = uuid.uuid4().hex
        start = time.perf_counter()
        try:
            resolved = resolve_to_path(file, filename_hint="uploaded.pdf")
            result = pdf_processor.extract_text_by_page(
                file_path=str(resolved),
                pages=pages,
                page_range=page_range,
                encoding=encoding or "utf-8",
            )
            duration_ms = int((time.perf_counter() - start) * 1000)
            # x-fastmcp-wrap-result=true => return list; framework wraps.
            return result
        except Exception as e:  # noqa: BLE001
            logger.error(
                "extract_text_by_page error pages=%s range=%s: %s",
                pages,
                page_range,
                e,
            )
            raise ValueError(
                f"extract_text_by_page failed for pages={pages} range={page_range}: {e}"
            )

    @app.tool()
    async def extract_metadata(file: Any) -> dict:
        """Extract comprehensive PDF metadata."""
        op_id = uuid.uuid4().hex
        start = time.perf_counter()
        try:
            resolved = resolve_to_path(file, filename_hint="uploaded.pdf")
            result = pdf_processor.extract_metadata(str(resolved))
            duration_ms = int((time.perf_counter() - start) * 1000)
            result["meta"] = {"operation_id": op_id, "execution_ms": duration_ms}
            return result
        except Exception as e:  # noqa: BLE001
            logger.error("extract_metadata error: %s", e)
            raise ValueError(f"extract_metadata failed: {e}")

