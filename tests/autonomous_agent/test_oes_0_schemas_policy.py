"""OES-0 schema and policy tests."""

from __future__ import annotations

from hg_runtime.operator_evidence_soak.fixtures import build_oes0_fixture_records
from hg_runtime.operator_evidence_soak.gate import validate_oes0_gate
from hg_runtime.operator_evidence_soak.redaction import secret_scan
from hg_runtime.operator_evidence_soak.schemas import (
    MUTATION_PROBE_TYPES,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    RECORD_TYPES,
)


def _records():
    return build_oes0_fixture_records()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_OES_0_SCHEMA_POLICY",
        "oec_consolidation_green": True,
        "schemas_declared": True,
        "soak_written": True,
        "policy_written": True,
        "manifest_written": True,
        "iteration_written": True,
        "replay_written": True,
        "boundary_written": True,
        "mutation_probe_written": True,
        "mutation_result_written": True,
        "soak_not_truth": True,
        "replay_not_truth": True,
        "determinism_not_correctness": True,
        "mutation_not_repair": True,
        "no_belief_promotion": True,
        "no_live_effects": True,
        "no_web_or_provider": True,
        "no_arbitrary_ingestion": True,
        "no_pdf_ocr": True,
        "no_deletion": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_oes0_declares_required_record_types():
    expected = {
        "operator_evidence_soak_v1",
        "soak_policy_v1",
        "soak_manifest_v1",
        "soak_iteration_result_v1",
        "soak_replay_result_v1",
        "soak_boundary_assertion_v1",
        "soak_mutation_probe_v1",
        "soak_mutation_result_v1",
        "soak_gate_result_v1",
    }
    assert expected <= RECORD_TYPES


def test_oes0_builds_all_schema_records():
    records = _records()
    assert records["operator_evidence_soak"]
    assert records["soak_policy"]
    assert records["soak_manifest"]
    assert len(records["soak_iterations"]) == 5
    assert records["soak_replay_result"]
    assert records["soak_boundary_assertions"]
    assert len(records["soak_mutation_probes"]) == 8


def test_oes0_mutation_probe_types_declared():
    assert len(MUTATION_PROBE_TYPES) == 8


def test_oes0_soak_is_not_truth():
    assert _records()["operator_evidence_soak"]["soak_treated_as_truth"] is False


def test_oes0_replay_match_is_not_truth():
    assert all(not row["replay_match_treated_as_truth"] for row in _records()["soak_iterations"])


def test_oes0_policy_blocks_arbitrary_ingestion():
    policy = _records()["soak_policy"]
    assert policy["arbitrary_file_ingestion_enabled"] is False
    assert policy["pdf_ingestion_enabled"] is False
    assert policy["directory_crawling_enabled"] is False


def test_oes0_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


def test_oes0_secret_scan_passes():
    assert secret_scan(_records()) is True


def test_oes0_gate_passes():
    assert validate_oes0_gate(_summary())["ok"] is True


def test_oes0_gate_refuses_soak_as_truth():
    assert validate_oes0_gate(_summary(soak_treated_as_truth=True))["ok"] is False
