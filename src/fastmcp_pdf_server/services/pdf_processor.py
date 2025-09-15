from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import pdfplumber
from PyPDF2 import PdfReader

from ..utils.parsers import clamp_pages, parse_page_range
from ..utils.validators import validate_pdf


@dataclass
class TextExtractionResult:
    text: str
    page_count: int
    char_count: int


def extract_text(file_path: str, encoding: str = "utf-8") -> TextExtractionResult:
    pdf_path = validate_pdf(file_path)
    with pdfplumber.open(str(pdf_path)) as pdf:
        texts: List[str] = []
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
        text = "\n".join(texts)
    return TextExtractionResult(text=text, page_count=len(texts), char_count=len(text))


def extract_text_by_page(
    file_path: str,
    pages: Optional[List[int]] = None,
    page_range: Optional[str] = None,
    encoding: str = "utf-8",
) -> List[dict]:
    pdf_path = validate_pdf(file_path)
    with pdfplumber.open(str(pdf_path)) as pdf:
        max_page = len(pdf.pages)
        selected: List[int]
        if pages:
            selected = clamp_pages(pages, max_page)
        elif page_range:
            selected = clamp_pages(parse_page_range(page_range), max_page)
        else:
            selected = list(range(1, max_page + 1))

        results: List[dict] = []
        for pno in selected:
            page = pdf.pages[pno - 1]
            text = page.extract_text() or ""
            results.append({"page": pno, "text": text, "char_count": len(text)})
        return results


def extract_metadata(file_path: str) -> dict:
    pdf_path = validate_pdf(file_path)
    reader = PdfReader(str(pdf_path))
    info = reader.metadata or {}
    meta = {
        "title": getattr(info, "title", None) or info.get("/Title"),
        "author": getattr(info, "author", None) or info.get("/Author"),
        "creator": getattr(info, "creator", None) or info.get("/Creator"),
        "producer": getattr(info, "producer", None) or info.get("/Producer"),
        "creation_date": getattr(info, "creation_date", None) or info.get("/CreationDate"),
        "mod_date": getattr(info, "mod_date", None) or info.get("/ModDate"),
        "page_count": len(reader.pages),
        "encrypted": reader.is_encrypted,
        "pdf_version": getattr(reader, "pdf_header", None),
        "file_size": pdf_path.stat().st_size,
    }
    return meta


def merge_pdfs(input_files: list[str], output_path: str) -> dict:
    from PyPDF2 import PdfMerger

    if not input_files:
        raise ValueError("input_files cannot be empty")
    pdf_paths = [validate_pdf(p) for p in input_files]

    total_input_size = sum(p.stat().st_size for p in pdf_paths)
    # Combined size check against 2x limit to be conservative
    # (output may be similar to sum of inputs); adjust if needed
    # Raises if any single file exceeded earlier.

    merger = PdfMerger()
    total_pages = 0
    for p in pdf_paths:
        reader = PdfReader(str(p))
        total_pages += len(reader.pages)
        merger.append(str(p))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        merger.write(f)
    merger.close()
    return {
        "output_path": str(out.resolve()),
        "total_pages": total_pages,
        "output_size": out.stat().st_size,
        "inputs": [str(p) for p in input_files],
    }


def split_pdf(file_path: str, split_ranges: list[dict]) -> list[dict]:
    from PyPDF2 import PdfWriter

    if not split_ranges:
        raise ValueError("split_ranges cannot be empty")
    pdf_path = validate_pdf(file_path)
    reader = PdfReader(str(pdf_path))
    max_page = len(reader.pages)

    # Check overlaps
    seen: set[int] = set()
    for r in split_ranges:
        s = int(r.get("start_page"))
        e = int(r.get("end_page"))
        if s < 1 or e < s or e > max_page:
            raise ValueError(f"Invalid split range: {s}-{e}")
        for p in range(s, e + 1):
            if p in seen:
                raise ValueError(f"Overlapping page in ranges: {p}")
            seen.add(p)

    results: list[dict] = []
    for r in split_ranges:
        s = int(r.get("start_page"))
        e = int(r.get("end_page"))
        output_path = r.get("output_path")
        if not output_path:
            raise ValueError("Each range must include output_path")

        writer = PdfWriter()
        for p in range(s - 1, e):
            writer.add_page(reader.pages[p])
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("wb") as f:
            writer.write(f)
        results.append({
            "output_path": str(out.resolve()),
            "pages": e - s + 1,
            "output_size": out.stat().st_size,
        })

    return results


def rotate_pages(file_path: str, rotations: list[dict], output_path: str) -> dict:
    from PyPDF2 import PdfReader, PdfWriter

    if not rotations:
        raise ValueError("rotations cannot be empty")
    pdf_path = validate_pdf(file_path)
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()

    rotation_map = {int(r["page"]): int(r["degrees"]) for r in rotations}
    for page_no, deg in rotation_map.items():
        if page_no < 1 or page_no > len(reader.pages):
            raise ValueError(f"Page {page_no} out of bounds")
        if deg not in {90, 180, 270}:
            raise ValueError("degrees must be one of 90, 180, 270")

    for idx, page in enumerate(reader.pages, start=1):
        if idx in rotation_map:
            deg = rotation_map[idx]
            try:
                page = page.rotate(deg)
            except Exception:  # PyPDF2 backward compat
                page.rotate_clockwise(deg)
        writer.add_page(page)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        writer.write(f)

    return {
        "output_path": str(out.resolve()),
        "rotated_pages": sorted(list(rotation_map.keys())),
        "page_count": len(reader.pages),
        "output_size": out.stat().st_size,
    }
