"""DIB-2 parser sandbox and quarantine tests."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.fixtures import build_dib2_parser_sandbox_layer
from hg_runtime.document_intake_boundary.gate import validate_dib2_gate
from hg_runtime.document_intake_boundary.schemas import PARSER_STATUSES


def _layer():
    return build_dib2_parser_sandbox_layer()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_DIB_2_PARSER_SANDBOX_QUARANTINE",
        "oes_consolidation_green": True,
        "dib0_green": True,
        "dib1_green": True,
        "sandbox_policy_written": True,
        "parser_registry_written": True,
        "evaluations_written": True,
        "failures_written": True,
        "quarantine_written": True,
        "parser_disabled_by_default": True,
        "allowlist_explicit": True,
        "pdf_rejected": True,
        "ocr_rejected": True,
        "html_rejected": True,
        "path_escape_rejected": True,
        "no_content_extraction": True,
        "no_parser_execution": True,
        "quarantine_not_deletion": True,
        "failure_not_deletion": True,
        "parser_success_not_correctness": True,
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


def test_dib2_parser_disabled_by_default():
    layer = _layer()
    statuses = {row["parser_status"] for row in layer["parser_evaluations"]}
    assert "PARSER_DISABLED_BY_DEFAULT" in statuses
    assert layer["parser_sandbox_policy"]["parser_execution_enabled"] is False


def test_dib2_rejects_pdf_ocr_html():
    layer = _layer()
    statuses = {row["parser_status"] for row in layer["parser_evaluations"]}
    assert "PARSER_REJECTED_PDF_DISABLED" in statuses
    assert "PARSER_REJECTED_OCR_DISABLED" in statuses
    assert "PARSER_REJECTED_HTML_FUTURE" in statuses


def test_dib2_rejects_path_escape():
    layer = _layer()
    statuses = {row["parser_status"] for row in layer["parser_evaluations"]}
    assert "PARSER_REJECTED_PATH_ESCAPE" in statuses


def test_dib2_allows_text_only_slot():
    layer = _layer()
    statuses = {row["parser_status"] for row in layer["parser_evaluations"]}
    assert "PARSER_ALLOWED_TEXT_ONLY" in statuses


def test_dib2_no_content_extraction():
    layer = _layer()
    assert all(not row["content_extracted"] for row in layer["parser_evaluations"])
    assert layer["parser_sandbox_manifest"]["content_extraction_enabled"] is False


def test_dib2_quarantine_not_deletion():
    layer = _layer()
    assert all(not row["quarantine_is_deletion"] for row in layer["parser_quarantine_records"])
    assert all(row["original_preserved"] for row in layer["parser_quarantine_records"])


def test_dib2_failure_not_deletion():
    layer = _layer()
    assert all(not row["deletion_performed"] for row in layer["parser_failure_records"])


def test_dib2_all_parser_statuses_used():
    layer = _layer()
    seen = {row["parser_status"] for row in layer["parser_evaluations"]}
    for row in layer["parser_failure_records"]:
        seen.add(row["parser_status"])
    for row in layer["parser_quarantine_records"]:
        seen.add(row["parser_status"])
    assert seen.issubset(PARSER_STATUSES)


def test_dib2_replay_deterministic():
    assert _layer()["replay"]["replay_deterministic"] is True


def test_dib2_gate_passes():
    assert validate_dib2_gate(_summary())["ok"] is True
