"""DIB-5 OCR disabled gate tests."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.gate import validate_dib5_gate
from hg_runtime.document_intake_boundary.ocr_disabled_gate import evaluate_ocr_disabled_gate


def _layer():
    return evaluate_ocr_disabled_gate()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_DIB_5_OCR_DISABLED_GATE",
        "oes_consolidation_green": True,
        "dib0_green": True,
        "dib1_green": True,
        "dib2_green": True,
        "dib3_green": True,
        "dib4_green": True,
        "policy_written": True,
        "rejections_written": True,
        "manifest_written": True,
        "ocr_disabled": True,
        "ocr_confidence_not_truth": True,
        "ocr_output_not_truth": True,
        "ocr_rejection_not_deletion": True,
        "no_ocr_dependency": True,
        "no_ocr_execution": True,
        "no_image_parsing": True,
        "no_pdf_parsing": True,
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


def test_dib5_ocr_disabled():
    layer = _layer()
    assert layer["ocr_disabled_policy"]["ocr_enabled"] is False
    assert layer["ocr_disabled_policy"]["ocr_dependency_allowed"] is False


def test_dib5_rejection_records_written():
    layer = _layer()
    assert len(layer["ocr_rejection_records"]) == 3


def test_dib5_ocr_output_not_truth():
    layer = _layer()
    assert all(not row["ocr_text_treated_as_truth"] for row in layer["ocr_rejection_records"])
    assert all(not row["ocr_output_treated_as_truth"] for row in layer["ocr_rejection_records"])


def test_dib5_rejection_not_deletion():
    layer = _layer()
    assert all(not row["deletion_performed"] for row in layer["ocr_rejection_records"])


def test_dib5_gate_passes():
    assert validate_dib5_gate(_summary())["ok"] is True
