from pathlib import Path

import os

from fastmcp_pdf_server.utils.validators import assert_extension, assert_max_size


def test_assert_extension_ok(tmp_path: Path):
    p = tmp_path / "file.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    assert_extension(p, [".pdf"])  # no raise


def test_assert_max_size(tmp_path: Path):
    p = tmp_path / "big.bin"
    p.write_bytes(b"0" * 1024)
    assert_max_size(p, max_mb=1)  # 1MB OK for 1KB file