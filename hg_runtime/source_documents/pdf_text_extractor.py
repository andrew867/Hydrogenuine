"""PDF text extractor using available PDF libraries.

PDF text is not truth. Extracted text is not knowledge. No promotion.
No paywall bypass. No login. Local file read only.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

_PDF_LIB = None
_PDF_LIB_NAME = ""

try:
    import pdfplumber
    _PDF_LIB = "pdfplumber"
    _PDF_LIB_NAME = "pdfplumber"
except ImportError:
    try:
        import pypdf
        _PDF_LIB = "pypdf"
        _PDF_LIB_NAME = "pypdf"
    except ImportError:
        pass


def pdf_library_available() -> tuple[bool, str]:
    if _PDF_LIB:
        return True, _PDF_LIB_NAME
    return False, "no PDF library available (install pdfplumber or pypdf)"


def extract_pdf(file_path: str, *, max_chars: int = 50000,
                max_pages: int = 50) -> dict:
    available, lib_name = pdf_library_available()
    if not available:
        return {
            "status": "yellow_pdf_extraction_unavailable",
            "file_path": file_path,
            "error": lib_name,
            "chars_extracted": 0,
            "text": "",
            "pdf_library": "",
            "extraction_is_not_truth": True,
            "promotion_allowed": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    if not os.path.isfile(file_path):
        return _error_receipt(file_path, "file not found")

    try:
        if _PDF_LIB == "pdfplumber":
            return _extract_pdfplumber(file_path, max_chars, max_pages)
        elif _PDF_LIB == "pypdf":
            return _extract_pypdf(file_path, max_chars, max_pages)
    except Exception as e:
        return _error_receipt(file_path, f"extraction error: {e}")

    return _error_receipt(file_path, "unknown PDF library state")


def _extract_pdfplumber(file_path: str, max_chars: int, max_pages: int) -> dict:
    import pdfplumber

    pages_text = []
    total_pages = 0
    warnings = []

    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages[:max_pages]):
            try:
                text = page.extract_text() or ""
                pages_text.append(text)
            except Exception as e:
                warnings.append(f"page {i}: {e}")
                pages_text.append("")

    full_text = "\n\n".join(pages_text)
    truncated = len(full_text) > max_chars
    text = full_text[:max_chars]

    return {
        "status": "succeeded",
        "file_path": file_path,
        "extension": ".pdf",
        "pdf_library": "pdfplumber",
        "total_pages": total_pages,
        "pages_extracted": min(total_pages, max_pages),
        "chars_extracted": len(text),
        "chars_original": len(full_text),
        "truncated": truncated,
        "text": text,
        "extraction_method": "pdf_text",
        "extraction_warnings": warnings,
        "extraction_is_not_truth": True,
        "ocr_used": False,
        "promotion_allowed": False,
        "operator_review_required": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _extract_pypdf(file_path: str, max_chars: int, max_pages: int) -> dict:
    import pypdf

    pages_text = []
    warnings = []

    reader = pypdf.PdfReader(file_path)
    total_pages = len(reader.pages)

    for i, page in enumerate(reader.pages[:max_pages]):
        try:
            text = page.extract_text() or ""
            pages_text.append(text)
        except Exception as e:
            warnings.append(f"page {i}: {e}")
            pages_text.append("")

    full_text = "\n\n".join(pages_text)
    truncated = len(full_text) > max_chars
    text = full_text[:max_chars]

    return {
        "status": "succeeded",
        "file_path": file_path,
        "extension": ".pdf",
        "pdf_library": "pypdf",
        "total_pages": total_pages,
        "pages_extracted": min(total_pages, max_pages),
        "chars_extracted": len(text),
        "chars_original": len(full_text),
        "truncated": truncated,
        "text": text,
        "extraction_method": "pdf_text",
        "extraction_warnings": warnings,
        "extraction_is_not_truth": True,
        "ocr_used": False,
        "promotion_allowed": False,
        "operator_review_required": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _error_receipt(file_path: str, error: str) -> dict:
    return {
        "status": "error",
        "file_path": file_path,
        "error": error,
        "chars_extracted": 0,
        "text": "",
        "pdf_library": _PDF_LIB_NAME,
        "extraction_is_not_truth": True,
        "promotion_allowed": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
