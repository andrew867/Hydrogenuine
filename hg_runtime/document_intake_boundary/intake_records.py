"""DIB extraction and provenance schema builders (foundation only)."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import assert_neutral, neutral_flags, record_hash


def build_extraction_receipt(*, receipt_id: str, file_id: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "extraction_receipt_v1",
        "receipt_id": receipt_id,
        "file_id": file_id,
        "extraction_status": "SKIPPED",
        "parser_success": False,
        "parser_success_treated_as_correctness": False,
        "parsed_text_treated_as_truth": False,
        "content_extraction_enabled": False,
        "doctrine_note": "Parsed text is not truth.",
        **neutral_flags(),
    }
    record["receipt_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_extraction_failure_record(*, failure_id: str, file_id: str, failure_class: str = "GATE_DISABLED") -> dict:
    record = {
        "schema_version": "1",
        "record_type": "extraction_failure_record_v1",
        "failure_id": failure_id,
        "file_id": file_id,
        "failure_class": failure_class,
        "deletion_performed": False,
        "original_preserved": True,
        "doctrine_note": "Parser failure is not deletion permission.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_document_source_identity(*, source_id: str, manifest_id: str, file_id: str, content_fingerprint: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "document_source_identity_v1",
        "source_id": source_id,
        "manifest_id": manifest_id,
        "file_id": file_id,
        "content_fingerprint": content_fingerprint,
        "filename_treated_as_source_identity": False,
        "doctrine_note": "Filename is not source identity.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_document_provenance_adapter_record(*, adapter_id: str, source_id: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "document_provenance_adapter_record_v1",
        "adapter_id": adapter_id,
        "source_id": source_id,
        "edge_kind": "INTAKE",
        "metadata_treated_as_provenance": False,
        "provenance_is_authority": False,
        "doctrine_note": "Metadata is not provenance.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
