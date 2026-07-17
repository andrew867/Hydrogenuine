"""DIB-3 text extraction receipt builders."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import assert_neutral, neutral_flags, record_hash


def build_text_extraction_receipt(
    *,
    receipt_id: str,
    file_id: str,
    source_id: str,
    content_hash: str,
    excerpt_hash: str,
    redacted_text_hash: str,
    excerpt_boundary_chars: int,
    classification_class: str,
) -> dict:
    receipt = {
        "schema_version": "1",
        "record_type": "extraction_receipt_v1",
        "receipt_id": receipt_id,
        "file_id": file_id,
        "source_id": source_id,
        "classification_class": classification_class,
        "extraction_status": "EXTRACTED_FIXTURE_ONLY",
        "content_hash": content_hash,
        "redacted_text_hash": redacted_text_hash,
        "excerpt_hash": excerpt_hash,
        "excerpt_boundary_chars": excerpt_boundary_chars,
        "parser_success": True,
        "parser_success_treated_as_correctness": False,
        "parsed_text_treated_as_truth": False,
        "extracted_text_treated_as_truth": False,
        "extraction_is_interpretation": False,
        "extraction_receipt_is_truth": False,
        "content_extraction_authorized": False,
        "doctrine_note": "Extracted text is not truth.",
        **neutral_flags(),
    }
    receipt["receipt_hash"] = record_hash(receipt)
    assert_neutral(receipt)
    return receipt
