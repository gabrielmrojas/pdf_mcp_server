from __future__ import annotations

import base64
import time
from dataclasses import dataclass
import uuid
import base64 as _b64
from pathlib import Path
from typing import Iterable, List

from ..config import settings


RETENTION_SECONDS = 24 * 60 * 60


def temp_dir() -> Path:
    p = settings.temp_path
    p.mkdir(parents=True, exist_ok=True)
    return p


def cleanup_expired(now: float | None = None) -> int:
    now = now or time.time()
    removed = 0
    for f in temp_dir().glob("**/*"):
        if not f.is_file():
            continue
        try:
            if now - f.stat().st_mtime > RETENTION_SECONDS:
                f.unlink(missing_ok=True)
                removed += 1
        except FileNotFoundError:
            pass
    return removed


def write_bytes(name: str, content: bytes) -> Path:
    p = temp_dir() / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    return p.resolve()


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def to_base64(path: Path) -> str:
    return base64.b64encode(read_bytes(path)).decode("ascii")


def _unique_name(name: str) -> str:
    """Return a unique filename if the target already exists in temp_dir()."""
    root = temp_dir()
    candidate = root / name
    if not candidate.exists():
        return name
    stem = candidate.stem
    suffix = candidate.suffix
    return f"{stem}-{uuid.uuid4().hex[:6]}{suffix}"


def write_bytes_unique(name: str, content: bytes) -> Path:
    """Write bytes to temp_dir(), avoiding overwrite by appending a short uuid if needed."""
    safe_name = _unique_name(name)
    return write_bytes(safe_name, content)


@dataclass
class ResourceInfo:
    path: Path
    size: int
    created: float
    content_type: str


def list_resources() -> List[ResourceInfo]:
    resources: List[ResourceInfo] = []
    for f in temp_dir().glob("**/*"):
        if f.is_file():
            resources.append(
                ResourceInfo(
                    path=f.resolve(),
                    size=f.stat().st_size,
                    created=f.stat().st_ctime,
                    content_type=_infer_content_type(f),
                )
            )
    return resources


def _infer_content_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return "application/pdf"
    if ext in {".png"}:
        return "image/png"
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "application/octet-stream"


def ensure_within_temp(path: Path) -> Path:
    root = temp_dir().resolve()
    target = path.resolve()
    try:
        target.relative_to(root)
    except Exception as e:  # noqa: BLE001
        raise ValueError("Access denied: path is outside the temp directory") from e
    return target


def resolve_to_path(value: object, filename_hint: str | None = None) -> Path:
    """
    Resolve various incoming representations into a Path under temp_dir().
    Supported inputs:
    - str path: existing file on disk -> return absolute Path
    - str filename: search temp_dir() for exact filename (newest first)
    - bytes/bytearray: write under temp_dir() using filename_hint (default 'upload.bin')
    - dict with 'base64' (and optional 'filename'): decode+write under temp_dir()
    - dict with 'url' (and optional 'filename'): download + write under temp_dir()
    - file-like with .read(): read+write under temp_dir() using name or filename_hint
    - objects exposing .data/.content/.bytes attribute (bytes or callable)-> write

    Returns: Absolute Path to the resolved file.
    Raises: ValueError when it cannot resolve the input to a file.
    """
    # 1) String path or filename
    if isinstance(value, str):
        p = Path(value)
        if p.exists() and p.is_file():
            return p.resolve()
        # treat as filename in temp_dir
        candidates = [r.path for r in list_resources() if r.path.name == value]
        if candidates:
            candidates.sort(key=lambda q: q.stat().st_mtime, reverse=True)
            return candidates[0].resolve()
        raise ValueError(
            f"File '{value}' not found as path or in temp directory. "
            "Attach the file or provide a full path."
        )

    # 2) Bytes-like
    if isinstance(value, (bytes, bytearray)):
        name = filename_hint or "upload.bin"
        return write_bytes_unique(name, bytes(value))

    # 3) Dict with base64
    if isinstance(value, dict) and "base64" in value:
        try:
            data = _b64.b64decode(value["base64"])  # type: ignore[arg-type]
        except Exception as e:  # noqa: BLE001
            raise ValueError("Invalid base64 content.") from e
        name = value.get("filename") or filename_hint or "upload.bin"  # type: ignore[assignment]
        return write_bytes_unique(str(name), data)

    # 3b) Dict with URL
    if isinstance(value, dict) and "url" in value:
        url = value.get("url")
        name = value.get("filename") or filename_hint or Path(url).name or "download.bin"
        try:
            import requests  # type: ignore

            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return write_bytes_unique(str(name), resp.content)
        except ModuleNotFoundError:
            raise ValueError(
                "URL support requires the 'requests' package. Install it in the environment or provide the file as bytes/base64/full path."
            )
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"Failed to download url={url}: {e}") from e

    # 4) File-like with .read()
    if hasattr(value, "read") and callable(getattr(value, "read")):
        data = value.read()  # type: ignore[assignment]
        if isinstance(data, str):
            data = data.encode("utf-8")
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError("Unsupported file-like object: .read() did not return bytes.")
        name = filename_hint or getattr(value, "name", "upload.bin")  # type: ignore[arg-type]
        return write_bytes_unique(str(name), bytes(data))

    # 5) Objects with bytes on attribute
    for attr in ("data", "content", "bytes", "raw_bytes"):
        if hasattr(value, attr):
            data = getattr(value, attr)
            if callable(data):
                data = data()
            if isinstance(data, (bytes, bytearray)):
                name = filename_hint or getattr(value, "name", "upload.bin")  # type: ignore[arg-type]
                return write_bytes_unique(str(name), bytes(data))

    raise ValueError(
        "Unsupported file input. Provide a full path, a known temp filename, "
        "attach the file (bytes/base64), or upload it first."
    )
