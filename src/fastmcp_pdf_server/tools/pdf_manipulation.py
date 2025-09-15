from __future__ import annotations

from typing import Any, Dict, List
import time
import uuid

from fastmcp import FastMCP  # type: ignore

from ..services import pdf_processor
from ..utils.logger import get_logger


logger = get_logger(__name__)


def register(app: FastMCP) -> None:
    @app.tool()
    async def merge_pdfs(input_files: List[str], output_path: str) -> dict:
        """Merge multiple PDF files into one document."""
        op_id = uuid.uuid4().hex
        start = time.perf_counter()
        try:
            result = pdf_processor.merge_pdfs(input_files, output_path)
            duration_ms = int((time.perf_counter() - start) * 1000)
            result["meta"] = {"operation_id": op_id, "execution_ms": duration_ms}
            return result
        except Exception as e:  # noqa: BLE001
            logger.error("merge_pdfs error inputs=%s out=%s: %s", input_files, output_path, e)
            raise ValueError(f"merge_pdfs failed inputs={input_files} out={output_path}: {e}")

    @app.tool()
    async def split_pdf(file_path: str, split_ranges: List[Dict[str, Any]]) -> list[dict]:
        """Split PDF into separate files by page ranges."""
        op_id = uuid.uuid4().hex
        start = time.perf_counter()
        try:
            result = pdf_processor.split_pdf(file_path, split_ranges)
            duration_ms = int((time.perf_counter() - start) * 1000)
            # x-fastmcp-wrap-result=true => return a list
            return result
        except Exception as e:  # noqa: BLE001
            logger.error("split_pdf error file=%s ranges=%s: %s", file_path, split_ranges, e)
            raise ValueError(f"split_pdf failed file={file_path} ranges={split_ranges}: {e}")

    @app.tool()
    async def rotate_pages(file_path: str, rotations: List[Dict[str, int]], output_path: str) -> dict:
        """Rotate specific pages in a PDF."""
        op_id = uuid.uuid4().hex
        start = time.perf_counter()
        try:
            result = pdf_processor.rotate_pages(file_path, rotations, output_path)
            duration_ms = int((time.perf_counter() - start) * 1000)
            result["meta"] = {"operation_id": op_id, "execution_ms": duration_ms}
            return result
        except Exception as e:  # noqa: BLE001
            logger.error("rotate_pages error file=%s rotations=%s out=%s: %s", file_path, rotations, output_path, e)
            raise ValueError(
                f"rotate_pages failed file={file_path} rotations={rotations} out={output_path}: {e}"
            )

