from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from ..config import settings


PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def assert_file_exists(path: str | os.PathLike) -> Path:
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise ValueError(f"File not found: {p}")
    return p.resolve()


def assert_extension(path: Path, allowed_exts: Iterable[str]) -> None:
    ext = path.suffix.lower()
    if ext not in allowed_exts:
        raise ValueError(f"Invalid file extension {ext}, allowed: {sorted(set(allowed_exts))}")


def assert_max_size(path: Path, max_mb: int | None = None) -> None:
    limit = (max_mb or settings.max_file_size_mb) * 1024 * 1024
    size = path.stat().st_size
    if size > limit:
        raise ValueError(f"File size {size} exceeds limit {limit} bytes")


def validate_pdf(path: str | os.PathLike) -> Path:
    p = assert_file_exists(path)
    assert_extension(p, PDF_EXTENSIONS)
    assert_max_size(p)
    return p


def validate_image(path: str | os.PathLike) -> Path:
    p = assert_file_exists(path)
    assert_extension(p, IMAGE_EXTENSIONS)
    assert_max_size(p)
    return p
