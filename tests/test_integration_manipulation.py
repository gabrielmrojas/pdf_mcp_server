from pathlib import Path

from reportlab.pdfgen import canvas

from fastmcp_pdf_server.services import pdf_processor


def make_pdf(tmp_path: Path, label: str, pages: int) -> Path:
    p = tmp_path / f"{label}.pdf"
    c = canvas.Canvas(str(p))
    for i in range(pages):
        c.drawString(100, 750, f"{label} p{i+1}")
        c.showPage()
    c.save()
    return p


def test_merge_split_rotate(tmp_path: Path):
    a = make_pdf(tmp_path, "A", 2)
    b = make_pdf(tmp_path, "B", 3)

    merged = tmp_path / "merged.pdf"
    m = pdf_processor.merge_pdfs([str(a), str(b)], str(merged))
    assert m["total_pages"] == 5
    assert Path(m["output_path"]).exists()

    split_out1 = tmp_path / "part1.pdf"
    split_out2 = tmp_path / "part2.pdf"
    s = pdf_processor.split_pdf(str(merged), [
        {"start_page": 1, "end_page": 2, "output_path": str(split_out1)},
        {"start_page": 3, "end_page": 5, "output_path": str(split_out2)},
    ])
    assert len(s) == 2

    rotated = tmp_path / "rotated.pdf"
    r = pdf_processor.rotate_pages(str(merged), [{"page": 1, "degrees": 90}], str(rotated))
    assert Path(r["output_path"]).exists()