"""DIB-1 metadata-only file type classifier tests."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.fixtures import build_dib1_classification_layer, build_dib1_fixture_entries
from hg_runtime.document_intake_boundary.gate import validate_dib1_gate
from hg_runtime.document_intake_boundary.schemas import ACCEPTED_CLASSIFICATION_CLASSES, CLASSIFICATION_CLASSES


def _layer():
    return build_dib1_classification_layer()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_DIB_1_FILE_TYPE_CLASSIFIER",
        "oes_consolidation_green": True,
        "dib0_green": True,
        "classifier_written": True,
        "classifications_written": True,
        "accepted_records_written": True,
        "rejected_records_written": True,
        "explicit_manifest_only": True,
        "classification_not_trust": True,
        "extension_not_truth": True,
        "media_type_not_trust": True,
        "filename_not_identity": True,
        "metadata_not_provenance": True,
        "accepted_not_ingestion_approval": True,
        "rejected_not_deletion": True,
        "pdf_rejected_disabled": True,
        "ocr_rejected_disabled": True,
        "no_parser_execution": True,
        "no_content_extraction": True,
        "no_pdf_ocr_enabled": True,
        "no_arbitrary_ingestion": True,
        "no_web_or_provider": True,
        "no_belief_promotion": True,
        "no_tool_authorization": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_dib1_accepts_txt_md_json():
    layer = _layer()
    accepted_classes = {row["classification_class"] for row in layer["document_type_classifications"] if row["accepted"]}
    assert accepted_classes == {"TEXT_PLAIN_ALLOWED", "MARKDOWN_ALLOWED", "JSON_MANIFEST_ALLOWED"}
    assert layer["accepted_count"] == 3


def test_dib1_rejects_pdf_ocr_html_binary_unknown():
    layer = _layer()
    rejected = {row["classification_class"] for row in layer["rejected_document_records"]}
    for cls in (
        "PDF_REJECTED_DISABLED",
        "OCR_REJECTED_DISABLED",
        "HTML_REJECTED_FUTURE",
        "BINARY_REJECTED",
        "UNKNOWN_REJECTED",
    ):
        assert cls in rejected


def test_dib1_rejects_traversal_symlink_crawl():
    layer = _layer()
    rejected = {row["classification_class"] for row in layer["rejected_document_records"]}
    assert "PATH_TRAVERSAL_REJECTED" in rejected
    assert "SYMLINK_REJECTED" in rejected
    assert "DIRECTORY_CRAWL_REJECTED" in rejected


def test_dib1_classification_not_trust():
    layer = _layer()
    assert all(not row["classification_granted_trust"] for row in layer["document_type_classifications"])
    assert all(not row["parser_execution_authorized"] for row in layer["document_type_classifications"])
    assert all(not row["content_extraction_authorized"] for row in layer["document_type_classifications"])


def test_dib1_filename_not_source_identity():
    layer = _layer()
    for row in layer["document_source_identities"]:
        assert row["filename_treated_as_source_identity"] is False
    same_fingerprint = {row["content_fingerprint"] for row in layer["document_source_identities"]}
    assert len(same_fingerprint) == len(layer["document_source_identities"])


def test_dib1_rejected_not_deletion():
    layer = _layer()
    assert all(not row["rejected_type_is_deletion"] for row in layer["rejected_document_records"])


def test_dib1_replay_deterministic():
    assert _layer()["replay"]["replay_deterministic"] is True


def test_dib1_all_classification_classes_used():
    layer = _layer()
    seen = {row["classification_class"] for row in layer["document_type_classifications"]}
    assert seen == CLASSIFICATION_CLASSES


def test_dib1_fixture_entry_count():
    assert len(build_dib1_fixture_entries()) == 11


def test_dib1_gate_passes():
    assert validate_dib1_gate(_summary())["ok"] is True
