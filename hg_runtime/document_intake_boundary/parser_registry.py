"""DIB-2 explicit parser registry (allowlist and disabled parsers)."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import assert_neutral, neutral_flags, record_hash

ALLOWED_PARSERS = {
    "safe_text_plain_v1": {
        "parser_id": "safe_text_plain_v1",
        "allowed_extensions": [".txt"],
        "allowed_classification_classes": ["TEXT_PLAIN_ALLOWED"],
        "parser_status": "PARSER_ALLOWED_TEXT_ONLY",
    },
    "safe_markdown_v1": {
        "parser_id": "safe_markdown_v1",
        "allowed_extensions": [".md"],
        "allowed_classification_classes": ["MARKDOWN_ALLOWED"],
        "parser_status": "PARSER_ALLOWED_TEXT_ONLY",
    },
}

DISABLED_PARSERS = {
    "pdf_text_v1": {
        "parser_id": "pdf_text_v1",
        "parser_status": "PARSER_REJECTED_PDF_DISABLED",
        "reason": "pdf_text_extraction_disabled",
    },
    "ocr_v1": {
        "parser_id": "ocr_v1",
        "parser_status": "PARSER_REJECTED_OCR_DISABLED",
        "reason": "ocr_disabled",
    },
    "html_v1": {
        "parser_id": "html_v1",
        "parser_status": "PARSER_REJECTED_HTML_FUTURE",
        "reason": "html_future_gate",
    },
    "binary_v1": {
        "parser_id": "binary_v1",
        "parser_status": "PARSER_REJECTED_BINARY",
        "reason": "binary_rejected",
    },
}


def build_parser_registry(*, registry_id: str = "dib-parser-registry-v1") -> dict:
    registry = {
        "schema_version": "1",
        "record_type": "parser_registry_v1",
        "registry_id": registry_id,
        "allowed_parsers": list(ALLOWED_PARSERS.keys()),
        "disabled_parsers": list(DISABLED_PARSERS.keys()),
        "parser_allowlist_explicit": True,
        "parser_execution_enabled": False,
        "content_extraction_enabled": False,
        "pdf_ingestion_enabled": False,
        "ocr_ingestion_enabled": False,
        "doctrine_note": "Parser allowlist is not permission to parse arbitrary files.",
        **neutral_flags(),
    }
    registry["record_hash"] = record_hash(registry)
    assert_neutral(registry)
    return registry


def resolve_parser_for_entry(*, entry: dict, classification_class: str) -> str | None:
    from hg_runtime.document_intake_boundary.file_policy import extension_from_path

    ext = extension_from_path(entry.get("manifest_path", ""))
    if entry.get("ocr_requested"):
        return "ocr_v1"
    if ext == ".pdf" or entry.get("declared_media_type") == "application/pdf":
        return "pdf_text_v1"
    if ext in {".html", ".htm"} or entry.get("declared_media_type") in {"text/html", "application/html"}:
        return "html_v1"
    if ext in {".bin", ".exe", ".dll"}:
        return "binary_v1"
    if classification_class == "TEXT_PLAIN_ALLOWED" or ext == ".txt":
        return "safe_text_plain_v1"
    if classification_class == "MARKDOWN_ALLOWED" or ext == ".md":
        return "safe_markdown_v1"
    return None
