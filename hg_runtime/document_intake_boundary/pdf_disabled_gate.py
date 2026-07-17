"""DIB-4 PDF text extraction disabled gate."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.pdf_policy import build_pdf_disabled_policy
from hg_runtime.document_intake_boundary.schemas import assert_neutral, neutral_flags, record_hash


PDF_REJECTION_SCENARIOS = [
    {"file_id": "dib4-pdf-001", "manifest_path": "pdf/sample.pdf", "reason": "pdf_disabled"},
    {"file_id": "dib4-pdf-002", "manifest_path": "pdf/report.pdf", "declared_media_type": "application/pdf", "reason": "pdf_media_type_disabled"},
    {"file_id": "dib4-pdf-003", "manifest_path": "text/disguised.pdf", "reason": "pdf_extension_disabled"},
]


def build_pdf_rejection_record(*, rejection_id: str, file_id: str, reason: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "pdf_rejection_record_v1",
        "rejection_id": rejection_id,
        "file_id": file_id,
        "reason": reason,
        "pdf_ingestion_enabled": False,
        "pdf_text_extraction_enabled": False,
        "pdf_metadata_treated_as_provenance": False,
        "pdf_filename_treated_as_source_identity": False,
        "rejection_is_deletion": False,
        "deletion_performed": False,
        "original_preserved": True,
        "doctrine_note": "PDF rejection is not deletion.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def evaluate_pdf_disabled_gate(*, policy: dict | None = None) -> dict:
    policy = policy or build_pdf_disabled_policy()
    rejections = [
        build_pdf_rejection_record(rejection_id=f"dib4-reject-{idx:03d}", file_id=scenario["file_id"], reason=scenario["reason"])
        for idx, scenario in enumerate(PDF_REJECTION_SCENARIOS)
    ]
    manifest = {
        "manifest_id": "dib4-pdf-disabled-gate-manifest-v1",
        "scenario_count": len(PDF_REJECTION_SCENARIOS),
        "rejection_count": len(rejections),
        "pdf_ingestion_enabled": False,
        "pdf_text_extraction_enabled": False,
        "pdf_parser_dependency_allowed": False,
        "no_pdf_parsing": True,
        "no_content_extraction": True,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return {
        "pdf_disabled_policy": policy,
        "pdf_rejection_records": rejections,
        "pdf_disabled_gate_manifest": manifest,
    }
