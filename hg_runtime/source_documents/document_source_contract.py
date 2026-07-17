"""Document source contract — input specification for document extraction.

PDF text is not truth. Extracted text is not knowledge. No promotion.
"""

from __future__ import annotations

from dataclasses import dataclass, field


SUPPORTED_EXTENSIONS = frozenset({".txt", ".md", ".json", ".csv", ".html", ".htm"})
PDF_EXTENSIONS = frozenset({".pdf"})
ALL_EXTENSIONS = SUPPORTED_EXTENSIONS | PDF_EXTENSIONS


@dataclass
class DocumentSourceContract:
    file_path: str = ""
    max_chars: int = 50000
    max_pages: int = 50
    enable_ocr: bool = False
    ocr_language: str = "eng"
    ocr_max_pages: int = 5
    source_candidate_id: str = ""
    origin: str = "operator_provided"

    def validate(self) -> list[str]:
        errors = []
        if not self.file_path:
            errors.append("file_path is required")
        if self.max_chars < 100:
            errors.append("max_chars must be >= 100")
        if self.max_pages < 1:
            errors.append("max_pages must be >= 1")
        return errors

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "max_chars": self.max_chars,
            "max_pages": self.max_pages,
            "enable_ocr": self.enable_ocr,
            "ocr_language": self.ocr_language,
            "ocr_max_pages": self.ocr_max_pages,
            "source_candidate_id": self.source_candidate_id,
            "origin": self.origin,
            "extraction_is_not_truth": True,
            "promotion_allowed": False,
            "operator_review_required": True,
        }
