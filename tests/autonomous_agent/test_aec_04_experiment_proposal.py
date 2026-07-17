"""AEC-04 / CAGI-51 experiment proposal tests.

A proposal is not approval to execute. A proposal review is not a deployment decision.
"""

from __future__ import annotations

import pytest

from hg_runtime.experiment_proposal.artifact_writer import (
    build_proposal_artifacts,
    secret_scan,
)
from hg_runtime.experiment_proposal.fixtures import (
    fixture_live_proposal_attempt,
    fixture_proposal_reviews,
    fixture_proposals,
)
from hg_runtime.experiment_proposal.gate import validate_aec04_gate
from hg_runtime.experiment_proposal.generator import (
    rank_proposals,
    validate_proposal,
    validate_review,
)
from hg_runtime.experiment_proposal.replay import replay_proposal_artifacts
from hg_runtime.experiment_proposal.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVIDER_MODE,
    VERDICT_GREEN,
    ExperimentProposalError,
    reject_live_proposal,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "AEC_04" in VERDICT_GREEN


def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"


def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT


def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"


def test_fixture_proposals_draft():
    for p in fixture_proposals():
        assert p["approved_for_execution"] is False
        assert p["live_execution_enabled"] is False


def test_fixture_reviews_not_approval():
    for r in fixture_proposal_reviews():
        assert r["is_approval"] is False


def test_validate_proposal_valid():
    assert validate_proposal(fixture_proposals()[0]) == []


def test_validate_proposal_missing_id():
    issues = validate_proposal({"type": "HYPOTHESIS_TEST", "hypothesis_ref": "h1", "status": "DRAFT_NOT_APPROVED"})
    assert "missing_proposal_id" in issues


def test_validate_proposal_rejects_approved():
    with pytest.raises(ExperimentProposalError):
        validate_proposal(fixture_live_proposal_attempt())


def test_validate_review_valid():
    assert validate_review(fixture_proposal_reviews()[0]) == []


def test_validate_review_rejects_approval():
    issues = validate_review({"proposal_id": "p1", "status": "REVIEW_NOT_DECISION", "is_approval": True})
    assert "review_must_not_approve" in issues


def test_rank_proposals():
    ranked = rank_proposals(fixture_proposals())
    assert ranked[0]["priority"] == "CRITICAL_SAFETY"


def test_reject_live_clean():
    reject_live_proposal({"sandbox_only": True})


def test_reject_live_approved():
    with pytest.raises(ExperimentProposalError):
        reject_live_proposal({"approved_for_execution": True})


def test_reject_live_execution():
    with pytest.raises(ExperimentProposalError):
        reject_live_proposal({"live_execution_enabled": True})


def test_reject_live_deploy():
    with pytest.raises(ExperimentProposalError):
        reject_live_proposal({"deploy_to_production": True})


def test_reject_live_authority():
    with pytest.raises(ExperimentProposalError):
        reject_live_proposal({"grants_authority": True})


def test_reject_live_agi():
    with pytest.raises(ExperimentProposalError):
        reject_live_proposal({"claims_agi": True})


def test_build_proposal_artifacts():
    artifacts = build_proposal_artifacts(fixture_proposals(), fixture_proposal_reviews())
    assert artifacts["proposal_count"] == 3
    assert artifacts["review_count"] == 2
    assert artifacts["all_proposals_draft"] is True
    assert artifacts["all_reviews_not_decision"] is True
    assert artifacts["no_approvals_granted"] is True
    assert "artifact_hash" in artifacts


def test_build_rejects_live():
    with pytest.raises(ExperimentProposalError):
        build_proposal_artifacts([fixture_live_proposal_attempt()], [])


def test_secret_scan_clean():
    artifacts = build_proposal_artifacts(fixture_proposals(), fixture_proposal_reviews())
    assert secret_scan(artifacts) == []


def test_replay_deterministic():
    a = replay_proposal_artifacts()
    b = replay_proposal_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "aec03_green": True,
        "proposals_written": True,
        "proposal_count": 3,
        "reviews_written": True,
        "all_proposals_draft": True,
        "all_reviews_not_decision": True,
        "no_approvals_granted": True,
        "safety_boundaries_enforced": True,
        "reject_live_proposal_tripwire": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_approved_proposal_rejected": True,
        "proposal_approved_for_execution": False,
        "live_execution_performed": False,
        "deployed_to_production": False,
        "tool_authorized": False,
        "authority_granted": False,
        "live_effect_created": False,
        "agi_claimed": False,
        "proposal_treated_as_approval": False,
        "review_treated_as_decision": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data


def test_gate_green():
    assert validate_aec04_gate(_gate_summary())["ok"] is True


def test_gate_rejects_approved():
    assert validate_aec04_gate(_gate_summary(proposal_approved_for_execution=True))["ok"] is False


def test_gate_rejects_live():
    assert validate_aec04_gate(_gate_summary(live_execution_performed=True))["ok"] is False


def test_gate_rejects_authority():
    assert validate_aec04_gate(_gate_summary(authority_granted=True))["ok"] is False


def test_gate_rejects_agi():
    assert validate_aec04_gate(_gate_summary(agi_claimed=True))["ok"] is False


def test_gate_rejects_missing_replay():
    assert validate_aec04_gate(_gate_summary(replay_preserves_artifact_hash=False))["ok"] is False
