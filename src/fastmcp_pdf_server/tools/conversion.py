from __future__ import annotations

from typing import List, Optional
import time
import uuid

from fastmcp import FastMCP  # type: ignore

from ..services import image_processor
from ..utils.logger import get_logger


logger = get_logger(__name__)


def register(app: FastMCP) -> None:
    @app.tool()
    async def pdf_to_images(
        file_path: str,
        output_dir: str,
        format: str = "png",
        dpi: int = 150,
        pages: Optional[List[int]] = None,
    ) -> list[dict]:
        """Convert PDF pages to image files."""
        op_id = uuid.uuid4().hex
        start = time.perf_counter()
        try:
            result = image_processor.pdf_to_images(file_path, output_dir, format, dpi, pages)
            duration_ms = int((time.perf_counter() - start) * 1000)
            # x-fastmcp-wrap-result=true => return a list
            return result
        except Exception as e:  # noqa: BLE001
            logger.error(
                "pdf_to_images error file=%s dir=%s fmt=%s dpi=%s pages=%s: %s",
                file_path,
                output_dir,
                format,
                dpi,
                pages,
                e,
            )
            raise ValueError(
                f"pdf_to_images failed file={file_path} dir={output_dir} fmt={format} dpi={dpi} pages={pages}: {e}"
            )

    @app.tool()
    async def images_to_pdf(
        image_paths: List[str],
        output_path: str,
        page_size: str = "A4",
        orientation: str = "portrait",
    ) -> dict:
        """Create PDF from multiple image files."""
        op_id = uuid.uuid4().hex
        start = time.perf_counter()
        try:
            result = image_processor.images_to_pdf(image_paths, output_path, page_size, orientation)
            duration_ms = int((time.perf_counter() - start) * 1000)
            result["meta"] = {"operation_id": op_id, "execution_ms": duration_ms}
            return result
        except Exception as e:  # noqa: BLE001
            logger.error(
                "images_to_pdf error images=%s out=%s size=%s orient=%s: %s",
                image_paths,
                output_path,
                page_size,
                orientation,
                e,
            )
            raise ValueError(
                f"images_to_pdf failed images={image_paths} out={output_path} size={page_size} orient={orientation}: {e}"
            )

