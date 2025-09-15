from __future__ import annotations

from typing import Iterable, List, Set


def parse_page_range(expr: str) -> List[int]:
    pages: Set[int] = set()
    for part in expr.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            a, b = part.split('-', 1)
            start = int(a)
            end = int(b)
            if start <= 0 or end <= 0 or end < start:
                raise ValueError(f"Invalid range segment: {part}")
            pages.update(range(start, end + 1))
        else:
            val = int(part)
            if val <= 0:
                raise ValueError(f"Invalid page number: {part}")
            pages.add(val)
    return sorted(pages)


def clamp_pages(pages: Iterable[int], max_page: int) -> List[int]:
    result: List[int] = []
    for p in pages:
        if p < 1 or p > max_page:
            raise ValueError(f"Page {p} is out of bounds (1..{max_page})")
        result.append(p)
    return result
