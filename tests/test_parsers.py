from fastmcp_pdf_server.utils.parsers import parse_page_range, clamp_pages


def test_parse_page_range():
    assert parse_page_range("1-3,5,7-9") == [1, 2, 3, 5, 7, 8, 9]


def test_clamp_pages_ok():
    assert clamp_pages([1, 3, 5], 5) == [1, 3, 5]


def test_clamp_pages_oob():
    try:
        clamp_pages([0, 6], 5)
        assert False, "should have raised"
    except ValueError:
        pass