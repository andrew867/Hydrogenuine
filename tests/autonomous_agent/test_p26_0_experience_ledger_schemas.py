"""P26-0 experience ledger schema tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.experience_ledger.fixtures import build_p26_0_layer, replay_p26_0
from hg_runtime.experience_ledger.gate import validate_p26_0_gate
from hg_runtime.experience_ledger.ledger_policy import build_experience_ledger_policy
from hg_runtime.experience_ledger.memory_record import build_memory_record
from hg_runtime.experience_ledger.promotion_request import build_memory_promotion_request
from hg_runtime.experience_ledger.recall_record import build_recall_result
from hg_runtime.experience_ledger.redaction import secret_scan
from hg_runtime.experience_ledger.schemas import (
    ExperienceLedgerBoundaryError,
    P26_INVARIANTS,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    RECORD_TYPES,
    REQUIRED_POLICY_DEFAULTS,
    assert_neutral,
)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _summary(**overrides):
    data = {
        "verdict": "GREEN_P26_0_EXPERIENCE_LEDGER_SCHEMAS",
        "schemas_declared": True,
        "policy_defaults_declared": True,
        "invariants_declared": True,
        "experience_records_written": True,
        "memory_records_written": True,
        "recall_queries_written": True,
        "recall_results_written": True,
        "promotion_requests_written": True,
        "promotion_decisions_written": True,
        "retraction_records_written": True,
        "memory_is_not_truth": True,
        "recall_is_not_authority": True,
        "experience_is_not_evidence_by_itself": True,
        "ledger_entry_is_not_belief": True,
        "promotion_request_is_not_promotion": True,
        "operator_review_is_not_truth": True,
        "provenance_required_for_recall": True,
        "source_quality_is_not_truth": True,
        "retraction_is_not_erasure": True,
        "quarantine_is_not_deletion": True,
        "no_automatic_belief_promotion": True,
        "no_tool_authorization": True,
        "no_live_effects": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_schema_hashes": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_p26_0_required_schemas_declared():
    assert {
        "experience_ledger_policy_v1",
        "experience_record_v1",
        "memory_record_v1",
        "recall_query_v1",
        "recall_result_v1",
        "memory_promotion_request_v1",
        "memory_promotion_decision_v1",
        "memory_retraction_record_v1",
        "experience_ledger_gate_result_v1",
    } <= RECORD_TYPES


def test_p26_0_policy_defaults_declared():
    policy = build_experience_ledger_policy()
    for key, value in REQUIRED_POLICY_DEFAULTS.items():
        assert policy[key] is value


def test_p26_0_invariants_declared():
    assert P26_INVARIANTS["P26-INV-01"] == "memory_is_not_truth"
    assert P26_INVARIANTS["P26-INV-15"] == "phase24_infrastructure_only_preserved"


def test_p26_0_builds_schema_fixture_records(repo_root):
    layer = build_p26_0_layer(repo_root)
    assert layer["experience_records"][0]["record_type"] == "experience_record_v1"
    assert layer["memory_records"][0]["record_type"] == "memory_record_v1"
    assert layer["recall_results"][0]["record_type"] == "recall_result_v1"


def test_p26_0_memory_is_not_truth(repo_root):
    memory = build_p26_0_layer(repo_root)["memory_records"][0]
    assert memory["memory_is_truth"] is False
    assert memory["memory_treated_as_truth"] is False


def test_p26_0_recall_is_not_authority(repo_root):
    recall = build_p26_0_layer(repo_root)["recall_results"][0]
    assert recall["recall_is_authority"] is False
    assert recall["recall_treated_as_authority"] is False


def test_p26_0_experience_is_not_evidence_by_itself(repo_root):
    experience = build_p26_0_layer(repo_root)["experience_records"][0]
    assert experience["experience_is_evidence_by_itself"] is False


def test_p26_0_ledger_entry_is_not_belief(repo_root):
    memory = build_p26_0_layer(repo_root)["memory_records"][0]
    assert memory["ledger_entry_treated_as_belief"] is False


def test_p26_0_promotion_request_is_not_promotion(repo_root):
    request = build_p26_0_layer(repo_root)["promotion_requests"][0]
    assert request["promotion_request_is_promotion"] is False
    assert request["promotion_request_auto_applied"] is False


def test_p26_0_operator_review_is_not_truth(repo_root):
    decision = build_p26_0_layer(repo_root)["promotion_decisions"][0]
    assert decision["operator_review_is_truth"] is False


def test_p26_0_provenance_required_for_recall(repo_root):
    layer = build_p26_0_layer(repo_root)
    memory = dict(layer["memory_records"][0])
    memory["provenance_refs"] = []
    with pytest.raises(ExperienceLedgerBoundaryError):
        build_recall_result(result_id="bad", query=layer["recall_queries"][0], memory_records=[memory])


def test_p26_0_source_quality_is_not_truth(repo_root):
    memory = build_p26_0_layer(repo_root)["memory_records"][0]
    assert memory["source_quality_treated_as_truth"] is False


def test_p26_0_retraction_is_not_erasure(repo_root):
    retraction = build_p26_0_layer(repo_root)["retraction_records"][0]
    assert retraction["retraction_is_erasure"] is False
    assert retraction["original_memory_preserved"] is True


def test_p26_0_quarantine_is_not_deletion(repo_root):
    policy = build_p26_0_layer(repo_root)["policy"]
    assert policy["quarantine_supported"] is True
    assert policy["deletion_enabled"] is False


def test_p26_0_no_automatic_belief_promotion(repo_root):
    layer = build_p26_0_layer(repo_root)
    assert layer["policy"]["automatic_belief_promotion_enabled"] is False
    assert layer["promotion_decisions"][0]["belief_promoted"] is False


def test_p26_0_no_tool_authorization(repo_root):
    policy = build_p26_0_layer(repo_root)["policy"]
    assert policy["tool_authorization_enabled"] is False


def test_p26_0_no_live_effects(repo_root):
    policy = build_p26_0_layer(repo_root)["policy"]
    assert policy["live_effects_enabled"] is False
    assert policy["external_provider_enabled"] is False
    assert policy["web_enabled"] is False


def test_p26_0_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_p26_0_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_p26_0_replay_preserves_schema_hashes(repo_root):
    assert build_p26_0_layer(repo_root)["replay"]["replay_preserves_record_hashes"] is True


def test_p26_0_replay_changes_when_memory_mutated(repo_root):
    layer = build_p26_0_layer(repo_root)
    baseline = layer["replay"]["receipt_chain_root"]
    records = [dict(r) for r in layer["records"]]
    records[2]["artifact_ref"] = "mutated"
    assert replay_p26_0(records)["receipt_chain_root"] != baseline


def test_p26_0_no_secret_material_in_layer(repo_root):
    assert secret_scan(build_p26_0_layer(repo_root)) is True


def test_p26_0_rejects_memory_truth_laundering(repo_root):
    memory = dict(build_p26_0_layer(repo_root)["memory_records"][0])
    memory["memory_treated_as_truth"] = True
    with pytest.raises(ExperienceLedgerBoundaryError):
        assert_neutral(memory)


def test_p26_0_rejects_recall_authority_laundering(repo_root):
    recall = dict(build_p26_0_layer(repo_root)["recall_results"][0])
    recall["recall_treated_as_authority"] = True
    with pytest.raises(ExperienceLedgerBoundaryError):
        assert_neutral(recall)


def test_p26_0_rejects_promotion_without_provenance(repo_root):
    memory = dict(build_p26_0_layer(repo_root)["memory_records"][0])
    memory["provenance_refs"] = []
    with pytest.raises(ExperienceLedgerBoundaryError):
        build_memory_promotion_request(request_id="bad", memory_record=memory)


def test_p26_0_memory_record_requires_neutrality(repo_root):
    experience = build_p26_0_layer(repo_root)["experience_records"][0]
    memory = build_memory_record(memory_id="neutral", experience_record=experience, provenance_refs=["p"])
    assert memory["authority_granted"] is False


def test_p26_0_gate_passes_full_summary():
    assert validate_p26_0_gate(_summary())["ok"] is True


def test_p26_0_gate_refuses_memory_truth():
    assert validate_p26_0_gate(_summary(memory_treated_as_truth=True))["ok"] is False


def test_p26_0_gate_refuses_recall_authority():
    assert validate_p26_0_gate(_summary(recall_treated_as_authority=True))["ok"] is False


def test_p26_0_gate_refuses_experience_evidence_by_itself():
    assert validate_p26_0_gate(_summary(experience_treated_as_evidence_by_itself=True))["ok"] is False


def test_p26_0_gate_refuses_auto_promotion():
    assert validate_p26_0_gate(_summary(belief_promotion_automatic=True))["ok"] is False


def test_p26_0_gate_refuses_orp_bypass():
    assert validate_p26_0_gate(_summary(orp_bypassed=True))["ok"] is False


def test_p26_0_gate_refuses_tool_authorization():
    assert validate_p26_0_gate(_summary(tools_authorized=True))["ok"] is False


def test_p26_0_gate_refuses_live_effects():
    assert validate_p26_0_gate(_summary(live_external_side_effects_created=True))["ok"] is False


def test_p26_0_gate_refuses_without_proof_bundle():
    assert validate_p26_0_gate(_summary(proof_bundle_valid=False))["ok"] is False

