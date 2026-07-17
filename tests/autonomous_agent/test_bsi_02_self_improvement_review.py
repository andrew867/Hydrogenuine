"""BSI-02 / CAGI-61 self-improvement review and evaluation tests.

A review pass is not permission. A review pass is not patch approval.
"""

from __future__ import annotations

import pytest

from hg_runtime.self_improvement_review.artifact_writer import build_review_artifacts, secret_scan
from hg_runtime.self_improvement_review.fixtures import (
    fixture_evaluation_criteria, fixture_review_authority_attempt,
    fixture_review_records,
)
from hg_runtime.self_improvement_review.gate import validate_bsi02_gate
from hg_runtime.self_improvement_review.replay import replay_review_artifacts
from hg_runtime.self_improvement_review.reviewer import (
    classify_benefit, classify_risk, requires_operator_escalation, validate_review,
)
from hg_runtime.self_improvement_review.schemas import (
    PHASE19_VERDICT, PHASE24_STATUS, PROVIDER_MODE, VERDICT_GREEN,
    SelfImprovementReviewError, reject_review_authority,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "P61" in VERDICT_GREEN

def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_fixture_reviews_no_patch_approval():
    for r in fixture_review_records():
        assert r["approves_patch"] is False
        assert r["grants_permission"] is False
        assert r["requires_operator_review"] is True

def test_validate_review_valid():
    assert validate_review(fixture_review_records()[0]) == []

def test_validate_review_rejects_authority():
    with pytest.raises(SelfImprovementReviewError):
        validate_review(fixture_review_authority_attempt())

def test_classify_risk():
    assert classify_risk(fixture_review_records()[0]) == "LOW"
    assert classify_risk(fixture_review_records()[1]) == "MEDIUM"

def test_classify_benefit():
    assert classify_benefit(fixture_review_records()[0]) == "MODERATE"

def test_requires_escalation():
    assert requires_operator_escalation(fixture_review_records()[1]) is True
    assert requires_operator_escalation(fixture_review_records()[0]) is False

def test_reject_review_authority_clean():
    reject_review_authority({"advisory_only": True})

def test_reject_review_approves_patch():
    with pytest.raises(SelfImprovementReviewError):
        reject_review_authority({"approves_patch": True})

def test_reject_review_grants_permission():
    with pytest.raises(SelfImprovementReviewError):
        reject_review_authority({"grants_permission": True})

def test_reject_review_self_approves():
    with pytest.raises(SelfImprovementReviewError):
        reject_review_authority({"self_approves": True})

def test_reject_review_mutates_policy():
    with pytest.raises(SelfImprovementReviewError):
        reject_review_authority({"mutates_policy": True})

def test_reject_review_mutates_gate():
    with pytest.raises(SelfImprovementReviewError):
        reject_review_authority({"mutates_gate": True})

def test_reject_review_bypass():
    with pytest.raises(SelfImprovementReviewError):
        reject_review_authority({"bypasses_operator_review": True})

def test_reject_review_agi():
    with pytest.raises(SelfImprovementReviewError):
        reject_review_authority({"claims_agi": True})

def test_build_review_artifacts():
    artifacts = build_review_artifacts(fixture_review_records(), fixture_evaluation_criteria())
    assert artifacts["review_count"] == 3
    assert artifacts["all_reviews_valid"] is True
    assert artifacts["none_approve_patch"] is True
    assert artifacts["all_require_operator_review"] is True
    assert "artifact_hash" in artifacts

def test_build_rejects_authority():
    with pytest.raises(SelfImprovementReviewError):
        build_review_artifacts([fixture_review_authority_attempt()], fixture_evaluation_criteria())

def test_secret_scan_clean():
    artifacts = build_review_artifacts(fixture_review_records(), fixture_evaluation_criteria())
    assert secret_scan(artifacts) == []

def test_replay_deterministic():
    a = replay_review_artifacts()
    b = replay_review_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN, "bsi01_green": True,
        "reviews_written": True, "criteria_written": True,
        "all_reviews_valid": True, "none_approve_patch": True,
        "all_require_operator_review": True, "risk_classified": True,
        "benefit_classified": True, "escalation_routing_present": True,
        "safety_boundaries_enforced": True, "reject_review_authority_tripwire": True,
        "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True, "proof_bundle_valid": True,
        "report_present": True, "fake_green_review_authority_rejected": True,
        "patch_approved": False, "permission_granted": False,
        "tool_authorized": False, "authority_granted": False,
        "policy_mutated": False, "gate_mutated": False,
        "live_effect_created": False, "agi_claimed": False,
        "self_approved": False, "operator_review_bypassed": False,
        "web_browse_performed": False, "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data

def test_gate_green():
    assert validate_bsi02_gate(_gate_summary())["ok"] is True

def test_gate_rejects_patch_approved():
    assert validate_bsi02_gate(_gate_summary(patch_approved=True))["ok"] is False

def test_gate_rejects_self_approved():
    assert validate_bsi02_gate(_gate_summary(self_approved=True))["ok"] is False

def test_gate_rejects_agi():
    assert validate_bsi02_gate(_gate_summary(agi_claimed=True))["ok"] is False

def test_gate_rejects_missing_replay():
    assert validate_bsi02_gate(_gate_summary(replay_preserves_artifact_hash=False))["ok"] is False

def test_gate_rejects_bypass():
    assert validate_bsi02_gate(_gate_summary(operator_review_bypassed=True))["ok"] is False
