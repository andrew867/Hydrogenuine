"""ORP-0 operator review schema tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.operator_review_promotion.decision import build_operator_review_decision
from hg_runtime.operator_review_promotion.fixtures import build_orp0_layer, replay_orp0
from hg_runtime.operator_review_promotion.gate import validate_orp0_gate
from hg_runtime.operator_review_promotion.promotion_gate import build_promotion_gate_result
from hg_runtime.operator_review_promotion.redaction import secret_scan
from hg_runtime.operator_review_promotion.schemas import (
    DECISION_STATUSES,
    OperatorReviewPromotionError,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    RECORD_TYPES,
)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _layer(repo_root):
    return build_orp0_layer(repo_root)


def _summary(**overrides):
    data = {
        "verdict": "GREEN_ORP_0_OPERATOR_REVIEW_SCHEMAS",
        "schemas_declared": True,
        "decision_statuses_declared": True,
        "operator_review_decisions_written": True,
        "operator_review_manifest_written": True,
        "promotion_policy_receipt_written": True,
        "promotion_request_written": True,
        "promotion_gate_result_written": True,
        "reviewed_evidence_link_written": True,
        "operator_rejection_record_written": True,
        "operator_deferral_record_written": True,
        "operator_review_not_truth": True,
        "operator_approval_not_action_permission": True,
        "operator_approval_does_not_authorize_tools": True,
        "operator_approval_does_not_authorize_web": True,
        "operator_approval_does_not_authorize_providers": True,
        "operator_rejection_not_deletion": True,
        "operator_deferral_not_failure": True,
        "promotion_request_not_promotion": True,
        "promotion_gate_not_truth": True,
        "no_automatic_belief_promotion": True,
        "no_live_effects": True,
        "replay_preserves_review_hashes": True,
        "secret_redaction_passed": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_orp0_required_schemas_declared():
    assert "operator_review_decision_v1" in RECORD_TYPES
    assert "operator_review_manifest_v1" in RECORD_TYPES
    assert "evidence_promotion_request_v1" in RECORD_TYPES
    assert "promotion_gate_result_v1" in RECORD_TYPES
    assert "operator_review_replay_record_v1" in RECORD_TYPES


def test_orp0_decision_statuses_declared():
    assert DECISION_STATUSES == (
        "APPROVE_FOR_PROVISIONAL_USE",
        "REJECT_SOURCE",
        "REQUEST_MORE_EVIDENCE",
        "DEFER_REVIEW",
        "QUARANTINE_RECOMMENDED",
        "RETRACTION_RECOMMENDED",
    )


def test_orp0_builds_decision_fixtures(repo_root):
    layer = _layer(repo_root)
    assert len(layer["decisions"]) == len(DECISION_STATUSES)
    assert layer["manifest"]["decision_count"] == len(DECISION_STATUSES)


def test_orp0_operator_review_is_not_truth(repo_root):
    assert all(not d["operator_review_is_truth"] for d in _layer(repo_root)["decisions"])


def test_orp0_operator_approval_not_action_permission(repo_root):
    assert all(not d["operator_approval_is_action_permission"] for d in _layer(repo_root)["decisions"])


def test_orp0_operator_approval_does_not_authorize_tools(repo_root):
    assert all(not d["operator_approval_authorizes_tools"] for d in _layer(repo_root)["decisions"])


def test_orp0_operator_approval_does_not_authorize_web_or_providers(repo_root):
    assert all(not d["operator_approval_authorizes_web"] for d in _layer(repo_root)["decisions"])
    assert all(not d["operator_approval_authorizes_providers"] for d in _layer(repo_root)["decisions"])


def test_orp0_rejection_is_not_deletion(repo_root):
    rejection = _layer(repo_root)["operator_rejection_records"][0]
    assert rejection["operator_rejection_is_deletion"] is False
    assert rejection["deletion_performed"] is False


def test_orp0_deferral_is_not_failure(repo_root):
    deferral = _layer(repo_root)["operator_deferral_records"][0]
    assert deferral["operator_deferral_is_failure"] is False
    assert deferral["review_remains_open"] is True


def test_orp0_promotion_request_is_not_promotion(repo_root):
    request = _layer(repo_root)["promotion_requests"][0]
    assert request["promotion_request_is_promotion"] is False
    assert request["belief_promoted"] is False


def test_orp0_promotion_gate_is_not_truth(repo_root):
    gate = _layer(repo_root)["promotion_gate_results"][0]
    assert gate["promotion_gate_is_truth"] is False
    assert gate["gate_pass_is_action_permission"] is False


def test_orp0_no_automatic_belief_promotion(repo_root):
    layer = _layer(repo_root)
    assert layer["manifest"]["belief_promotion_automatic"] is False
    assert all(not r["belief_promotion_automatic"] for r in layer["promotion_requests"])


def test_orp0_no_live_effects(repo_root):
    layer = _layer(repo_root)
    everything = layer["decisions"] + layer["promotion_requests"] + layer["promotion_gate_results"]
    assert all(not r["live_external_side_effects_created"] for r in everything)


def test_orp0_rejects_invalid_decision_status(repo_root):
    task = _layer(repo_root)["source_review_queue"]["tasks"][0]
    with pytest.raises(OperatorReviewPromotionError):
        build_operator_review_decision(decision_id="bad", review_task=task, status="MARK_TRUE")


def test_orp0_rejects_gate_truth_laundering(repo_root):
    request = _layer(repo_root)["promotion_requests"][0]
    result = build_promotion_gate_result(gate_result_id="gate", request=request)
    result["promotion_gate_is_truth"] = True
    with pytest.raises(OperatorReviewPromotionError):
        from hg_runtime.operator_review_promotion.schemas import assert_neutral

        assert_neutral(result)


def test_orp0_replay_preserves_review_hashes(repo_root):
    assert _layer(repo_root)["replay"]["replay_preserves_review_hashes"] is True


def test_orp0_replay_changes_when_decision_mutated(repo_root):
    layer = _layer(repo_root)
    decisions = [dict(d) for d in layer["decisions"]]
    baseline = layer["replay"]["receipt_chain_root"]
    decisions[0]["rationale"] = "mutated"
    replay = replay_orp0(
        decisions,
        layer["reviewed_evidence_links"],
        layer["promotion_requests"],
        layer["promotion_gate_results"],
        layer["policy"],
    )
    assert replay["receipt_chain_root"] != baseline


def test_orp0_no_secret_material_in_layer(repo_root):
    assert secret_scan(_layer(repo_root)) is True


def test_orp0_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_orp0_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_orp0_gate_passes_full_summary():
    assert validate_orp0_gate(_summary())["ok"] is True


def test_orp0_gate_refuses_operator_review_truth():
    assert validate_orp0_gate(_summary(operator_review_treated_as_truth=True))["ok"] is False


def test_orp0_gate_refuses_tool_authorization():
    assert validate_orp0_gate(_summary(tools_authorized=True))["ok"] is False


def test_orp0_gate_refuses_web_authorization():
    assert validate_orp0_gate(_summary(web_authorized=True))["ok"] is False


def test_orp0_gate_refuses_provider_authorization():
    assert validate_orp0_gate(_summary(providers_authorized=True))["ok"] is False


def test_orp0_gate_refuses_deletion():
    assert validate_orp0_gate(_summary(deletion_performed=True))["ok"] is False


def test_orp0_gate_refuses_auto_belief_promotion():
    assert validate_orp0_gate(_summary(belief_promotion_automatic=True))["ok"] is False


def test_orp0_gate_refuses_without_replay():
    assert validate_orp0_gate(_summary(replay_preserves_review_hashes=False))["ok"] is False
