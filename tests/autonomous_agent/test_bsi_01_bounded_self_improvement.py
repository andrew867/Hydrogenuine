"""BSI-01 / CAGI-60 bounded self-improvement proposal loop tests.

A proposal is not a patch. A proposal is not permission. A proposal cannot self-apply.
"""

from __future__ import annotations

import pytest

from hg_runtime.bounded_self_improvement.artifact_writer import build_proposal_artifacts, secret_scan
from hg_runtime.bounded_self_improvement.fixtures import (
    fixture_improvement_proposals, fixture_proposal_authority_attempt,
    fixture_proposal_queue,
)
from hg_runtime.bounded_self_improvement.gate import validate_bsi01_gate
from hg_runtime.bounded_self_improvement.proposer import link_evidence, validate_proposal, validate_queue
from hg_runtime.bounded_self_improvement.replay import replay_proposal_artifacts
from hg_runtime.bounded_self_improvement.schemas import (
    PHASE19_VERDICT, PHASE24_STATUS, PROVIDER_MODE, VERDICT_GREEN,
    BoundedSelfImprovementError, reject_proposal_authority,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "P60" in VERDICT_GREEN

def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_fixture_proposals_no_self_apply():
    for p in fixture_improvement_proposals():
        assert p["self_apply"] is False
        assert p["apply_patch"] is False
        assert p["requires_operator_review"] is True

def test_fixture_queue_none_applied():
    q = fixture_proposal_queue()
    assert q["applied"] == 0
    assert q["self_apply"] is False

def test_validate_proposal_valid():
    assert validate_proposal(fixture_improvement_proposals()[0]) == []

def test_validate_proposal_rejects_self_apply():
    with pytest.raises(BoundedSelfImprovementError):
        validate_proposal(fixture_proposal_authority_attempt())

def test_validate_queue_valid():
    assert validate_queue(fixture_proposal_queue()) == []

def test_validate_queue_rejects_applied():
    issues = validate_queue({"queue_id": "q", "applied": 1})
    assert "no_proposals_may_be_applied" in issues

def test_link_evidence():
    result = link_evidence(fixture_improvement_proposals()[0])
    assert result["linked"] is True
    assert len(result["evidence_links"]) >= 1

def test_reject_proposal_authority_clean():
    reject_proposal_authority({"advisory_only": True})

def test_reject_proposal_self_apply():
    with pytest.raises(BoundedSelfImprovementError):
        reject_proposal_authority({"self_apply": True})

def test_reject_proposal_patch():
    with pytest.raises(BoundedSelfImprovementError):
        reject_proposal_authority({"apply_patch": True})

def test_reject_proposal_authority_grant():
    with pytest.raises(BoundedSelfImprovementError):
        reject_proposal_authority({"grants_authority": True})

def test_reject_proposal_mutate_authority():
    with pytest.raises(BoundedSelfImprovementError):
        reject_proposal_authority({"mutates_authority": True})

def test_reject_proposal_mutate_policy():
    with pytest.raises(BoundedSelfImprovementError):
        reject_proposal_authority({"mutates_policy": True})

def test_reject_proposal_mutate_gate():
    with pytest.raises(BoundedSelfImprovementError):
        reject_proposal_authority({"mutates_gate": True})

def test_reject_proposal_bypass_review():
    with pytest.raises(BoundedSelfImprovementError):
        reject_proposal_authority({"bypasses_operator_review": True})

def test_reject_proposal_agi():
    with pytest.raises(BoundedSelfImprovementError):
        reject_proposal_authority({"claims_agi": True})

def test_build_proposal_artifacts():
    artifacts = build_proposal_artifacts(fixture_improvement_proposals(), fixture_proposal_queue())
    assert artifacts["proposal_count"] == 3
    assert artifacts["all_proposals_valid"] is True
    assert artifacts["none_applied"] is True
    assert artifacts["all_require_operator_review"] is True
    assert "artifact_hash" in artifacts

def test_build_rejects_authority():
    with pytest.raises(BoundedSelfImprovementError):
        build_proposal_artifacts([fixture_proposal_authority_attempt()], fixture_proposal_queue())

def test_secret_scan_clean():
    artifacts = build_proposal_artifacts(fixture_improvement_proposals(), fixture_proposal_queue())
    assert secret_scan(artifacts) == []

def test_replay_deterministic():
    a = replay_proposal_artifacts()
    b = replay_proposal_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN, "lhre06_green": True,
        "proposals_written": True, "queue_written": True,
        "all_proposals_valid": True, "none_applied": True,
        "all_require_operator_review": True, "evidence_linked": True,
        "safety_boundaries_enforced": True, "reject_proposal_authority_tripwire": True,
        "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True, "proof_bundle_valid": True,
        "report_present": True, "fake_green_proposal_authority_rejected": True,
        "proposal_self_applied": False, "patch_applied": False,
        "tool_authorized": False, "authority_granted": False,
        "authority_mutated": False, "policy_mutated": False,
        "gate_mutated": False, "permit_mutated": False,
        "live_effect_created": False, "agi_claimed": False,
        "operator_review_bypassed": False,
        "web_browse_performed": False, "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data

def test_gate_green():
    assert validate_bsi01_gate(_gate_summary())["ok"] is True

def test_gate_rejects_self_apply():
    assert validate_bsi01_gate(_gate_summary(proposal_self_applied=True))["ok"] is False

def test_gate_rejects_patch():
    assert validate_bsi01_gate(_gate_summary(patch_applied=True))["ok"] is False

def test_gate_rejects_authority_mutated():
    assert validate_bsi01_gate(_gate_summary(authority_mutated=True))["ok"] is False

def test_gate_rejects_agi():
    assert validate_bsi01_gate(_gate_summary(agi_claimed=True))["ok"] is False

def test_gate_rejects_missing_replay():
    assert validate_bsi01_gate(_gate_summary(replay_preserves_artifact_hash=False))["ok"] is False

def test_gate_rejects_bypass_review():
    assert validate_bsi01_gate(_gate_summary(operator_review_bypassed=True))["ok"] is False
