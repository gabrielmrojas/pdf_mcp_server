from __future__ import annotations

from pathlib import Path
import shutil
from typing import List, Optional

from PIL import Image
from pdf2image import convert_from_path

from ..config import settings
from ..services.file_manager import temp_dir
from ..utils.validators import IMAGE_EXTENSIONS, validate_image, validate_pdf


def pdf_to_images(
    file_path: str,
    output_dir: str,
    format: str = "png",
    dpi: int = 150,
    pages: Optional[List[int]] = None,
) -> list[dict]:
    pdf_path = validate_pdf(file_path)
    if shutil.which("pdftoppm") is None:
        raise ValueError(
            "Poppler not found (pdftoppm missing). Install Poppler and put 'bin' on PATH."
        )
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Note: On Windows, pdf2image requires poppler. Documented in README.
    images = convert_from_path(
        str(pdf_path),
        dpi=dpi,
        fmt=format,
        first_page=min(pages) if pages else None,
        last_page=max(pages) if pages else None,
    )

    results: list[dict] = []
    for idx, img in enumerate(images, start=1 if not pages else min(pages)):
        page_no = idx
        out_path = outdir / f"page-{page_no:04d}.{format}"
        img.save(str(out_path))
        results.append({"path": str(out_path.resolve()), "width": img.width, "height": img.height})
    return results


PAGE_SIZES = {
    "A4": (595, 842),
    "LETTER": (612, 792),
    "LEGAL": (612, 1008),
    "A3": (842, 1191),
}


def images_to_pdf(
    image_paths: List[str],
    output_path: str,
    page_size: str = "A4",
    orientation: str = "portrait",
) -> dict:
    if not image_paths:
        raise ValueError("image_paths cannot be empty")

    # Validate images and open
    imgs: list[Image.Image] = []
    for p in image_paths:
        ip = validate_image(p)
        img = Image.open(str(ip))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        imgs.append(img)

    size = PAGE_SIZES.get(page_size.upper())
    if not size:
        raise ValueError("Unsupported page_size; choose A4, Letter, Legal, A3")
    if orientation.lower() == "landscape":
        width, height = size[1], size[0]
    else:
        width, height = size

    def fit(im: Image.Image) -> Image.Image:
        im_ratio = im.width / im.height
        page_ratio = width / height
        if im_ratio > page_ratio:
            new_w = width
            new_h = int(width / im_ratio)
        else:
            new_h = height
            new_w = int(height * im_ratio)
        return im.resize((new_w, new_h))

    # Place images centered on page-sized canvas
    pages: list[Image.Image] = []
    for im in imgs:
        fitted = fit(im)
        canvas = Image.new("RGB", (width, height), color=(255, 255, 255))
        x = (width - fitted.width) // 2
        y = (height - fitted.height) // 2
        canvas.paste(fitted, (x, y))
        pages.append(canvas)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Save multi-page PDF
    pages[0].save(str(out), save_all=True, append_images=pages[1:])
    return {"output_path": str(out.resolve()), "page_count": len(pages), "output_size": out.stat().st_size}
