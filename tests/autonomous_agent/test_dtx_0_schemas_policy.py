"""DTX-0 schema and policy tests."""

from __future__ import annotations

from hg_runtime.document_text_exchange.fixtures import build_dtx0_fixture_records
from hg_runtime.document_text_exchange.gate import validate_dtx0_gate
from hg_runtime.document_text_exchange.redaction import secret_scan
from hg_runtime.document_text_exchange.schemas import DOCUMENT_FIXTURE_FAMILIES, EXPECTED_OUTCOME_TYPES, PHASE19_VERDICT, PHASE24_STATUS, RECORD_TYPES


def _records():
    return build_dtx0_fixture_records()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_DTX_0_SCHEMA_POLICY",
        "dib_consolidation_green": True,
        "schemas_declared": True,
        "exchange_written": True,
        "manifest_written": True,
        "fixture_written": True,
        "outcome_written": True,
        "extraction_written": True,
        "bridge_written": True,
        "packet_written": True,
        "policy_written": True,
        "exchange_not_truth": True,
        "extracted_not_truth": True,
        "adapter_not_promotion": True,
        "packet_not_approval": True,
        "replay_not_truth": True,
        "no_pdf_ocr": True,
        "no_arbitrary_ingestion": True,
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


def test_dtx0_declares_required_record_types():
    expected = {
        "safe_text_document_exchange_v1",
        "dtx_manifest_v1",
        "dtx_document_fixture_v1",
        "dtx_extraction_exchange_record_v1",
        "dtx_leb_bridge_record_v1",
        "dtx_packet_exchange_record_v1",
        "dtx_soak_iteration_v1",
        "dtx_gate_result_v1",
    }
    assert expected <= RECORD_TYPES


def test_dtx0_fixture_families_declared():
    assert len(DOCUMENT_FIXTURE_FAMILIES) == 10
    assert len(EXPECTED_OUTCOME_TYPES) == 10


def test_dtx0_exchange_not_truth():
    assert _records()["safe_text_document_exchange"]["document_exchange_treated_as_truth"] is False


def test_dtx0_adapter_not_belief_promotion():
    assert _records()["dtx_leb_bridge_record"]["dib_adapter_treated_as_belief_promotion"] is False


def test_dtx0_secret_scan_passes():
    assert secret_scan(_records()) is True


def test_dtx0_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


def test_dtx0_gate_passes():
    assert validate_dtx0_gate(_summary())["ok"] is True
