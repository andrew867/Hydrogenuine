"""ORP-2 evidence promotion request builder tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_review_promotion.promotion_replay import replay_promotion_requests
from hg_runtime.operator_review_promotion.promotion_request_builder import (
    build_evidence_promotion_requests,
    validate_orp2_gate,
)
from hg_runtime.operator_review_promotion.redaction import secret_scan
from hg_runtime.operator_review_promotion.schemas import PHASE19_VERDICT, PHASE24_STATUS

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    return build_evidence_promotion_requests(ROOT)


def _summary(**overrides):
    data = {
        "verdict": "GREEN_ORP_2_EVIDENCE_PROMOTION_REQUEST_BUILDER",
        "orp1_green": True,
        "approved_decision_created_request": True,
        "rejected_source_blocked": True,
        "deferred_source_blocked": True,
        "quarantine_recommended_blocked": True,
        "retraction_recommended_blocked": True,
        "high_fever_blocked": True,
        "redaction_failure_blocked": True,
        "security_finding_blocked": True,
        "missing_receipt_blocked": True,
        "missing_provenance_blocked": True,
        "promotion_request_not_promotion": True,
        "eligible_is_not_truth": True,
        "blocked_is_not_deletion": True,
        "no_belief_mutation": True,
        "no_old_proof_mutation": True,
        "no_authority": True,
        "no_tools": True,
        "no_live_effects": True,
        "replay_preserves_promotion_hashes": True,
        "secret_redaction_passed": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_orp2_only_approved_decision_creates_request():
    layer = _layer()
    assert len(layer["promotion_requests"]) == 1
    assert layer["promotion_requests"][0]["decision_status"] == "APPROVE_FOR_PROVISIONAL_USE"


def test_orp2_rejected_and_deferred_blocked():
    reasons = {r["block_reason"] for r in _layer()["blocked_promotion_records"]}
    assert "REJECTED_SOURCE_BLOCKS_PROMOTION" in reasons
    assert "DEFERRED_REVIEW_BLOCKS_PROMOTION" in reasons


def test_orp2_quarantine_and_retraction_blocked():
    reasons = {r["block_reason"] for r in _layer()["blocked_promotion_records"]}
    assert "QUARANTINE_RECOMMENDATION_BLOCKS_PROMOTION" in reasons
    assert "RETRACTION_RECOMMENDATION_BLOCKS_PROMOTION" in reasons


def test_orp2_high_fever_redaction_security_missing_blocks():
    reasons = {r["block_reason"] for r in _layer()["blocked_promotion_records"]}
    assert "HIGH_FEVER_BLOCKS_PROMOTION" in reasons
    assert "REDACTION_FAILURE_BLOCKS_PROMOTION" in reasons
    assert "SECURITY_FINDING_BLOCKS_PROMOTION" in reasons
    assert "MISSING_RECEIPT_BLOCKS_PROMOTION" in reasons
    assert "MISSING_PROVENANCE_BLOCKS_PROMOTION" in reasons


def test_orp2_promotion_request_is_not_promotion():
    assert all(not r["promotion_request_is_promotion"] for r in _layer()["promotion_requests"])


def test_orp2_eligible_is_not_truth():
    assert all(not r["eligible_is_truth"] for r in _layer()["eligibility_records"])


def test_orp2_blocked_is_not_deletion():
    assert all(not r["blocked_is_deletion"] and not r["deletion_performed"] for r in _layer()["blocked_promotion_records"])


def test_orp2_no_belief_or_old_proof_mutation():
    assert all(not r["belief_mutated"] and not r["old_proof_mutated"] for r in _layer()["blocked_promotion_records"])
    assert _layer()["manifest"]["belief_mutated"] is False


def test_orp2_no_authority_tools_live_effects():
    layer = _layer()
    everything = layer["eligibility_records"] + layer["promotion_requests"] + layer["blocked_promotion_records"]
    assert all(not r["authority_granted"] for r in everything)
    assert all(not r["tools_authorized"] for r in everything)
    assert all(not r["live_external_side_effects_created"] for r in everything)


def test_orp2_replay_preserves_promotion_hashes():
    assert _layer()["replay"]["replay_preserves_promotion_hashes"] is True


def test_orp2_replay_rejects_mutated_request():
    layer = _layer()
    requests = [dict(r) for r in layer["promotion_requests"]]
    requests[0]["requested_use"] = "MUTATED"
    replay = replay_promotion_requests(
        layer["eligibility_records"],
        requests,
        layer["blocked_promotion_records"],
        layer["manifest"],
    )
    assert replay["replay_preserves_promotion_hashes"] is False


def test_orp2_secret_scan_passes():
    assert secret_scan(_layer()) is True


def test_orp2_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_orp2_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_orp2_gate_passes_full_summary():
    assert validate_orp2_gate(_summary())["ok"] is True


def test_orp2_gate_refuses_request_as_promotion():
    assert validate_orp2_gate(_summary(promotion_request_not_promotion=False))["ok"] is False


def test_orp2_gate_refuses_truth_claim():
    assert validate_orp2_gate(_summary(evidence_treated_as_truth=True))["ok"] is False


def test_orp2_gate_refuses_belief_mutation():
    assert validate_orp2_gate(_summary(no_belief_mutation=False))["ok"] is False


def test_orp2_gate_refuses_authority_or_tools():
    assert validate_orp2_gate(_summary(authority_granted=True))["ok"] is False
    assert validate_orp2_gate(_summary(tools_authorized=True))["ok"] is False


def test_orp2_gate_refuses_old_proof_mutation():
    assert validate_orp2_gate(_summary(old_proof_mutated=True))["ok"] is False


def test_orp2_gate_refuses_without_replay():
    assert validate_orp2_gate(_summary(replay_preserves_promotion_hashes=False))["ok"] is False
