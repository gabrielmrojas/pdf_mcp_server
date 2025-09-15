from pathlib import Path

from reportlab.pdfgen import canvas

from fastmcp_pdf_server.services import pdf_processor


def make_pdf(tmp_path: Path, text: str = "Hello World", pages: int = 2) -> Path:
    p = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(p))
    for i in range(pages):
        c.drawString(100, 750, f"{text} p{i+1}")
        c.showPage()
    c.save()
    return p


def test_extract_text_and_metadata(tmp_path: Path):
    pdf = make_pdf(tmp_path)
    res = pdf_processor.extract_text(str(pdf))
    assert res.page_count == 2
    assert "Hello World" in res.text

    meta = pdf_processor.extract_metadata(str(pdf))
    assert meta["page_count"] == 2
    assert meta["file_size"] > 0