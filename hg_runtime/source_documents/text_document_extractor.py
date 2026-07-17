"""Text/markdown/HTML document extractor.

Reads local files. No network. Extracted text is not knowledge.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone


def extract_text_file(file_path: str, *, max_chars: int = 50000) -> dict:
    if not os.path.isfile(file_path):
        return _error_receipt(file_path, "file not found")

    ext = os.path.splitext(file_path)[1].lower()
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
    except Exception as e:
        return _error_receipt(file_path, f"read error: {e}")

    truncated = len(raw) > max_chars
    text = raw[:max_chars]

    if ext in (".html", ".htm"):
        text = _strip_html(text)

    return {
        "status": "succeeded",
        "file_path": file_path,
        "extension": ext,
        "chars_extracted": len(text),
        "chars_original": len(raw),
        "truncated": truncated,
        "text": text,
        "extraction_method": "text_read",
        "extraction_is_not_truth": True,
        "ocr_used": False,
        "promotion_allowed": False,
        "operator_review_required": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _strip_html(text: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _error_receipt(file_path: str, error: str) -> dict:
    return {
        "status": "error",
        "file_path": file_path,
        "error": error,
        "chars_extracted": 0,
        "text": "",
        "extraction_is_not_truth": True,
        "promotion_allowed": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
