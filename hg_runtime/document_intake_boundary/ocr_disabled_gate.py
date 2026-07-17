"""DIB-5 OCR disabled gate."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.ocr_policy import build_ocr_disabled_policy
from hg_runtime.document_intake_boundary.schemas import assert_neutral, neutral_flags, record_hash


OCR_REJECTION_SCENARIOS = [
    {"file_id": "dib5-ocr-001", "manifest_path": "text/scan.txt", "reason": "ocr_requested_disabled"},
    {"file_id": "dib5-ocr-002", "manifest_path": "image/scan.png", "reason": "image_ocr_disabled"},
    {"file_id": "dib5-ocr-003", "manifest_path": "pdf/scanned.pdf", "reason": "pdf_ocr_disabled"},
]


def build_ocr_rejection_record(*, rejection_id: str, file_id: str, reason: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "ocr_rejection_record_v1",
        "rejection_id": rejection_id,
        "file_id": file_id,
        "reason": reason,
        "ocr_enabled": False,
        "ocr_confidence_treated_as_truth": False,
        "ocr_output_treated_as_truth": False,
        "ocr_text_treated_as_truth": False,
        "rejection_is_deletion": False,
        "deletion_performed": False,
        "original_preserved": True,
        "doctrine_note": "OCR rejection is not deletion.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def evaluate_ocr_disabled_gate(*, policy: dict | None = None) -> dict:
    policy = policy or build_ocr_disabled_policy()
    rejections = [
        build_ocr_rejection_record(rejection_id=f"dib5-reject-{idx:03d}", file_id=scenario["file_id"], reason=scenario["reason"])
        for idx, scenario in enumerate(OCR_REJECTION_SCENARIOS)
    ]
    manifest = {
        "manifest_id": "dib5-ocr-disabled-gate-manifest-v1",
        "scenario_count": len(OCR_REJECTION_SCENARIOS),
        "rejection_count": len(rejections),
        "ocr_enabled": False,
        "ocr_dependency_allowed": False,
        "no_ocr_execution": True,
        "no_image_parsing": True,
        "no_pdf_parsing": True,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return {
        "ocr_disabled_policy": policy,
        "ocr_rejection_records": rejections,
        "ocr_disabled_gate_manifest": manifest,
    }
