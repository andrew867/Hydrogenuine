"""LEB-0 schema and boundary tests."""

from __future__ import annotations

import pytest

from hg_runtime.local_evidence_bridge.evidence_boundary import validate_source_path
from hg_runtime.local_evidence_bridge.fixtures import build_leb0_fixture_layer
from hg_runtime.local_evidence_bridge.gate import validate_leb0_gate
from hg_runtime.local_evidence_bridge.schemas import EvidenceBridgeError, PHASE19_VERDICT, PHASE24_STATUS, RECORD_TYPES, VERDICT_GREEN, assert_neutral


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "schemas_defined": True,
        "fixture_sources_written": True,
        "source_manifest_written": True,
        "evidence_receipts_written": True,
        "excerpt_receipts_written": True,
        "redaction_record_written": True,
        "boundary_receipt_written": True,
        "operator_source_not_truth": True,
        "local_file_not_trusted_by_default": True,
        "source_excerpt_not_belief": True,
        "evidence_receipt_not_truth": True,
        "evidence_receipt_not_authority": True,
        "ingestion_request_not_permission": True,
        "no_automatic_belief_promotion": True,
        "no_live_web": True,
        "no_external_providers": True,
        "no_arbitrary_path_access": True,
        "path_traversal_rejected": True,
        "no_secrets_in_receipts": True,
        "ais_record_health_hook_documented": True,
        "quarantine_hook_documented": True,
        "fever_hook_documented": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_leb0_defines_required_schemas():
    assert len(RECORD_TYPES) == 8
    assert "local_evidence_receipt_v1" in RECORD_TYPES


def test_leb0_operator_source_is_not_truth():
    layer = build_leb0_fixture_layer()
    assert all(not s["operator_provided_source_is_truth"] for s in layer["sources"])


def test_leb0_local_file_not_trusted_by_default():
    layer = build_leb0_fixture_layer()
    assert all(not s["local_file_trusted_by_default"] for s in layer["sources"])


def test_leb0_source_excerpt_is_not_belief():
    layer = build_leb0_fixture_layer()
    assert all(not r["source_excerpt_is_belief"] for r in layer["excerpt_receipts"])


def test_leb0_evidence_receipt_is_not_truth():
    layer = build_leb0_fixture_layer()
    assert all(not r["evidence_receipt_is_truth"] for r in layer["evidence_receipts"])


def test_leb0_evidence_receipt_is_not_authority():
    layer = build_leb0_fixture_layer()
    assert all(not r["evidence_receipt_is_authority"] for r in layer["evidence_receipts"])


def test_leb0_ingestion_request_is_not_permission():
    layer = build_leb0_fixture_layer()
    assert layer["ingestion_request"]["request_is_permission"] is False


def test_leb0_no_automatic_belief_promotion():
    layer = build_leb0_fixture_layer()
    assert all(not r["belief_promoted"] for r in layer["evidence_receipts"])


def test_leb0_rejects_path_traversal():
    with pytest.raises(EvidenceBridgeError):
        validate_source_path("../outside.txt")


def test_leb0_rejects_unapproved_path():
    with pytest.raises(EvidenceBridgeError):
        validate_source_path("operator_evidence/inbox/source.md")


def test_leb0_accepts_fixture_path():
    validate_source_path("tests/fixtures/local_evidence/source.md")


def test_leb0_neutral_rejects_truth_claim():
    with pytest.raises(EvidenceBridgeError):
        assert_neutral({"truth_claimed": True})


def test_leb0_ais_hooks_documented():
    layer = build_leb0_fixture_layer()
    boundary = layer["boundary_receipt"]
    assert boundary["ais_record_health_can_scan_later"]
    assert boundary["quarantine_can_isolate_suspect_sources_later"]
    assert boundary["fever_can_restrict_ingestion_later"]


def test_leb0_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_leb0_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_leb0_gate_passes_on_full_summary():
    assert validate_leb0_gate(_gate_summary())["ok"] is True


def test_leb0_gate_refuses_truth_claim():
    assert validate_leb0_gate(_gate_summary(truth_claimed=True))["ok"] is False


def test_leb0_gate_refuses_operator_ingestion_enabled():
    assert validate_leb0_gate(_gate_summary(operator_evidence_ingestion_enabled=True))["ok"] is False


def test_leb0_gate_refuses_external_provider():
    assert validate_leb0_gate(_gate_summary(external_provider_calls_made=True))["ok"] is False
