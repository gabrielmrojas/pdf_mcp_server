import shutil
from pathlib import Path

from reportlab.pdfgen import canvas

from fastmcp_pdf_server.services import image_processor


def make_pdf(tmp_path: Path, pages: int = 2) -> Path:
    p = tmp_path / "conv.pdf"
    c = canvas.Canvas(str(p))
    for i in range(pages):
        c.drawString(100, 750, f"Page {i+1}")
        c.showPage()
    c.save()
    return p


def test_pdf_to_images_and_back(tmp_path: Path):
    if shutil.which("pdftoppm") is None:
        # Skip if Poppler is not present
        return
    pdf = make_pdf(tmp_path, 2)
    outdir = tmp_path / "imgs"
    images = image_processor.pdf_to_images(str(pdf), str(outdir), format="png", dpi=100)
    assert len(images) == 2
    assert Path(images[0]["path"]).exists()

    out_pdf = tmp_path / "roundtrip.pdf"
    r = image_processor.images_to_pdf([i["path"] for i in images], str(out_pdf))
    assert Path(r["output_path"]).exists()