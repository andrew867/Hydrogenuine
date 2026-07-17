"""OCR policy — off by default, honest YELLOW if unavailable.

OCR text is not truth. OCR is lossy and must be receipted.
No promotion. No hiding OCR errors.
"""

from __future__ import annotations

from datetime import datetime, timezone

_OCR_AVAILABLE = False
_OCR_LIB = ""

try:
    import pytesseract
    _OCR_AVAILABLE = True
    _OCR_LIB = "pytesseract"
except ImportError:
    pass


def ocr_available() -> tuple[bool, str]:
    if _OCR_AVAILABLE:
        return True, _OCR_LIB
    return False, "pytesseract not installed (OCR unavailable)"


def check_ocr_policy(*, enable_ocr: bool = False) -> dict:
    available, detail = ocr_available()

    if not enable_ocr:
        return {
            "ocr_enabled": False,
            "ocr_available": available,
            "status": "disabled_by_policy",
            "detail": "OCR disabled by default (--enable-ocr not set)",
            "ocr_is_lossy": True,
            "ocr_text_is_not_truth": True,
        }

    if not available:
        return {
            "ocr_enabled": True,
            "ocr_available": False,
            "status": "yellow_ocr_unavailable",
            "detail": detail,
            "ocr_is_lossy": True,
            "ocr_text_is_not_truth": True,
        }

    return {
        "ocr_enabled": True,
        "ocr_available": True,
        "status": "available",
        "detail": f"OCR via {_OCR_LIB}",
        "ocr_is_lossy": True,
        "ocr_text_is_not_truth": True,
    }
