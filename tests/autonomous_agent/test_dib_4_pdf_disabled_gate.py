"""DIB-4 PDF disabled gate tests."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.gate import validate_dib4_gate
from hg_runtime.document_intake_boundary.pdf_disabled_gate import evaluate_pdf_disabled_gate


def _layer():
    return evaluate_pdf_disabled_gate()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_DIB_4_PDF_DISABLED_GATE",
        "oes_consolidation_green": True,
        "dib0_green": True,
        "dib1_green": True,
        "dib2_green": True,
        "dib3_green": True,
        "policy_written": True,
        "rejections_written": True,
        "manifest_written": True,
        "pdf_ingestion_disabled": True,
        "pdf_extraction_disabled": True,
        "pdf_metadata_not_provenance": True,
        "pdf_filename_not_identity": True,
        "pdf_rejection_not_deletion": True,
        "no_pdf_parser_dependency": True,
        "no_pdf_parsing": True,
        "no_content_extraction": True,
        "no_web_or_provider": True,
        "no_belief_promotion": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_dib4_pdf_ingestion_disabled():
    layer = _layer()
    assert layer["pdf_disabled_policy"]["pdf_ingestion_enabled"] is False
    assert layer["pdf_disabled_policy"]["pdf_text_extraction_enabled"] is False


def test_dib4_rejection_records_written():
    layer = _layer()
    assert len(layer["pdf_rejection_records"]) == 3


def test_dib4_rejection_not_deletion():
    layer = _layer()
    assert all(not row["deletion_performed"] for row in layer["pdf_rejection_records"])
    assert all(row["original_preserved"] for row in layer["pdf_rejection_records"])


def test_dib4_no_pdf_parser_dependency():
    layer = _layer()
    assert layer["pdf_disabled_policy"]["pdf_parser_dependency_allowed"] is False


def test_dib4_gate_passes():
    assert validate_dib4_gate(_summary())["ok"] is True
