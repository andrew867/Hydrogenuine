"""DIB-0 boundary schema tests."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.fixtures import build_dib0_fixture_records
from hg_runtime.document_intake_boundary.gate import validate_dib0_gate
from hg_runtime.document_intake_boundary.redaction import secret_scan
from hg_runtime.document_intake_boundary.schemas import PHASE19_VERDICT, PHASE24_STATUS, POLICY_DEFAULTS, RECORD_TYPES


def _records():
    return build_dib0_fixture_records()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_DIB_0_BOUNDARY_SCHEMAS",
        "oes_consolidation_green": True,
        "schemas_declared": True,
        "policy_written": True,
        "manifest_written": True,
        "parser_policy_written": True,
        "classification_written": True,
        "quarantine_written": True,
        "redaction_written": True,
        "extraction_written": True,
        "source_identity_written": True,
        "provenance_written": True,
        "document_not_truth": True,
        "parsed_text_not_truth": True,
        "ocr_text_not_truth": True,
        "metadata_not_provenance": True,
        "filename_not_identity": True,
        "parser_success_not_correctness": True,
        "quarantine_not_deletion": True,
        "redaction_not_erasure": True,
        "no_pdf_ocr": True,
        "no_arbitrary_ingestion": True,
        "no_web_or_provider": True,
        "no_belief_promotion": True,
        "no_tool_authorization": True,
        "no_parser_execution": True,
        "no_content_extraction": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_dib0_declares_required_record_types():
    expected = {
        "document_intake_manifest_v1",
        "document_file_record_v1",
        "document_type_classification_v1",
        "parser_sandbox_policy_v1",
        "extraction_receipt_v1",
        "extraction_failure_record_v1",
        "parser_quarantine_record_v1",
        "document_redaction_record_v1",
        "document_source_identity_v1",
        "document_provenance_adapter_record_v1",
        "document_intake_gate_result_v1",
    }
    assert expected <= RECORD_TYPES


def test_dib0_builds_all_schema_records():
    records = _records()
    assert records["boundary_policy"]
    assert records["document_intake_manifest"]
    assert records["document_file_record"]
    assert records["document_type_classification"]
    assert records["parser_sandbox_policy"]
    assert records["extraction_receipt"]
    assert records["extraction_failure_record"]
    assert records["parser_quarantine_record"]
    assert records["document_redaction_record"]
    assert records["document_source_identity"]
    assert records["document_provenance_adapter_record"]


def test_dib0_policy_defaults_disabled():
    policy = _records()["boundary_policy"]
    for key, value in POLICY_DEFAULTS.items():
        assert policy[key] is value


def test_dib0_document_is_not_truth():
    assert _records()["document_file_record"]["document_treated_as_truth"] is False


def test_dib0_quarantine_is_not_deletion():
    assert _records()["parser_quarantine_record"]["quarantine_is_deletion"] is False


def test_dib0_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


def test_dib0_secret_scan_passes():
    assert secret_scan(_records()) is True


def test_dib0_gate_passes():
    assert validate_dib0_gate(_summary())["ok"] is True


def test_dib0_gate_refuses_document_as_truth():
    assert validate_dib0_gate(_summary(document_treated_as_truth=True))["ok"] is False
