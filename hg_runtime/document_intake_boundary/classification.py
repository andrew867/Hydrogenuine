"""DIB document type classification record builder."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import assert_neutral, neutral_flags, record_hash


def build_document_type_classification(
    *,
    classification_id: str,
    file_id: str,
    classification_class: str,
    manifest_path: str,
    extension_label: str,
    declared_media_type: str = "",
    detection_method: str = "METADATA",
    accepted: bool = False,
    rejection_reason: str = "",
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "document_type_classification_v1",
        "classification_id": classification_id,
        "file_id": file_id,
        "classification_class": classification_class,
        "manifest_path": manifest_path,
        "extension_label": extension_label,
        "declared_media_type": declared_media_type,
        "detection_method": detection_method,
        "accepted": accepted,
        "rejection_reason": rejection_reason,
        "classification_granted_trust": False,
        "extension_treated_as_truth": False,
        "media_type_treated_as_trust": False,
        "accepted_type_is_ingestion_approval": False,
        "rejected_type_is_deletion": False,
        "parser_execution_authorized": False,
        "content_extraction_authorized": False,
        "metadata_treated_as_provenance": False,
        "doctrine_note": "Classification is not trust.",
        **neutral_flags(),
    }
    record["classification_hash"] = record_hash(record)
    assert_neutral(record)
    return record
