"""Pack 12: PDF text extraction per page. Raises clear error for scanned PDFs (needs OCR)."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

MIN_TEXT_PER_PAGE = 10


def parse_pdf_pages(path: Path) -> List[Tuple[int, str]]:
    """Extract text per page. Returns [(page_no, text), ...]. Page numbers 1-based. Raises if scanned (no text)."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("pypdf is required for PDF parsing; install with pip install pypdf")
    reader = PdfReader(str(path))
    out: List[Tuple[int, str]] = []
    for i, page in enumerate(reader.pages):
        page_no = i + 1
        text = (page.extract_text() or "").strip()
        out.append((page_no, text))
    total_chars = sum(len(t) for _, t in out)
    if total_chars < MIN_TEXT_PER_PAGE:
        raise ValueError("PDF produced no or negligible text (possibly scanned). Needs OCR or a different file.")
    return out
