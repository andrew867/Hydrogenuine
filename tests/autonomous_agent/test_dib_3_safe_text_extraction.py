"""DIB-3 safe text extraction tests."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.fixtures import build_dib3_extraction_layer
from hg_runtime.document_intake_boundary.gate import validate_dib3_gate


def _layer():
    return build_dib3_extraction_layer()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_DIB_3_SAFE_TEXT_EXTRACTION",
        "oes_consolidation_green": True,
        "dib0_green": True,
        "dib1_green": True,
        "dib2_green": True,
        "manifest_written": True,
        "receipts_written": True,
        "failures_written": True,
        "redaction_written": True,
        "source_identity_written": True,
        "provenance_written": True,
        "leb_adapter_written": True,
        "explicit_manifest_only": True,
        "safe_text_markdown_only": True,
        "json_rejected_for_extraction": True,
        "extracted_not_truth": True,
        "receipt_not_interpretation": True,
        "parser_success_not_correctness": True,
        "leb_adapter_not_belief_promotion": True,
        "filename_not_identity": True,
        "metadata_not_provenance": True,
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


def test_dib3_extracts_txt_and_md():
    layer = _layer()
    classes = {row["classification_class"] for row in layer["extraction_receipts"]}
    assert classes == {"TEXT_PLAIN_ALLOWED", "MARKDOWN_ALLOWED"}
    assert layer["accepted_count"] == 2


def test_dib3_rejects_json_manifest_for_extraction():
    layer = _layer()
    assert layer["rejected_count"] == 1
    assert any("JSON" in row["failure_class"] for row in layer["extraction_failure_records"])


def test_dib3_extracted_text_not_truth():
    layer = _layer()
    assert all(not row["extracted_text_treated_as_truth"] for row in layer["extraction_receipts"])
    assert all(not row["extraction_receipt_is_truth"] for row in layer["extraction_receipts"])


def test_dib3_leb_adapter_not_belief_promotion():
    layer = _layer()
    assert all(not row["automatic_belief_promotion"] for row in layer["dib_to_leb_adapter_records"])
    assert all(not row["leb_adapter_is_belief_promotion"] for row in layer["dib_to_leb_adapter_records"])


def test_dib3_content_hashes_recorded():
    layer = _layer()
    assert all(row["content_hash"] for row in layer["extraction_receipts"])
    assert all(row["excerpt_hash"] for row in layer["extraction_receipts"])


def test_dib3_replay_deterministic():
    assert _layer()["replay"]["replay_deterministic"] is True


def test_dib3_gate_passes():
    assert validate_dib3_gate(_summary())["ok"] is True
