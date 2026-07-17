"""SLE-RC-0 schema and manifest tests."""

from __future__ import annotations

from hg_runtime.safe_local_evidence_rc.fixtures import build_sle_rc0_fixture_records
from hg_runtime.safe_local_evidence_rc.gate import required_boundary_assertions_present, required_component_families_present, required_record_types_present, validate_sle_rc0_gate
from hg_runtime.safe_local_evidence_rc.redaction import secret_scan
from hg_runtime.safe_local_evidence_rc.schemas import COMPONENT_FAMILIES, PHASE19_VERDICT, PHASE24_STATUS, RECORD_TYPES


def _records():
    return build_sle_rc0_fixture_records()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_SLE_RC_0_SCHEMA_MANIFEST",
        "schemas_declared": True,
        "rc_written": True,
        "manifest_written": True,
        "status_written": True,
        "assertion_written": True,
        "artifact_index_written": True,
        "risk_written": True,
        "rc_not_deployment": True,
        "rc_green_not_truth": True,
        "rc_green_not_authority": True,
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


def test_sle_rc0_declares_required_record_types():
    assert required_record_types_present()


def test_sle_rc0_component_families_declared():
    assert list(COMPONENT_FAMILIES) == ["WMBR", "AIS", "LEB", "ORP", "SQP", "EWP", "OEC", "OES", "DIB", "DTX"]


def test_sle_rc0_rc_not_deployment():
    assert _records()["safe_local_evidence_rc"]["release_candidate_is_deployment"] is False


def test_sle_rc0_boundary_assertions_complete():
    assert required_boundary_assertions_present(_records()["rc_boundary_assertions"])


def test_sle_rc0_component_statuses_complete():
    assert required_component_families_present(_records()["rc_component_statuses"])


def test_sle_rc0_secret_scan_passes():
    assert secret_scan(_records()) is True


def test_sle_rc0_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


def test_sle_rc0_gate_passes():
    assert validate_sle_rc0_gate(_summary())["ok"] is True
