"""AEC-05 / CAGI-52 curriculum failure review tests.

A curriculum failure is not a product defect. A failure review is not a fix or patch.
"""

from __future__ import annotations

import pytest

from hg_runtime.curriculum_failure_review.artifact_writer import (
    build_failure_review_artifacts,
    secret_scan,
)
from hg_runtime.curriculum_failure_review.fixtures import (
    fixture_failure_records,
    fixture_failure_reviews,
    fixture_live_failure_action,
    fixture_root_cause_hypotheses,
)
from hg_runtime.curriculum_failure_review.gate import validate_aec05_gate
from hg_runtime.curriculum_failure_review.replay import replay_failure_review_artifacts
from hg_runtime.curriculum_failure_review.reviewer import (
    categorize_failures,
    severity_rank,
    validate_failure_record,
    validate_root_cause,
)
from hg_runtime.curriculum_failure_review.schemas import (
    FAILURE_STATUS_QUEUED,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVIDER_MODE,
    VERDICT_GREEN,
    CurriculumFailureReviewError,
    reject_live_failure_action,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "AEC_05" in VERDICT_GREEN


def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"


def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT


def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"


def test_fixture_failures_queued():
    for f in fixture_failure_records():
        assert f["status"] == FAILURE_STATUS_QUEUED
        assert f["apply_fix"] is False


def test_fixture_causes_hypothesis():
    for rc in fixture_root_cause_hypotheses():
        assert rc["is_diagnosis"] is False


def test_fixture_reviews_no_fix():
    for r in fixture_failure_reviews():
        assert r["apply_fix"] is False
        assert r["is_fix"] is False


def test_validate_failure_valid():
    assert validate_failure_record(fixture_failure_records()[0]) == []


def test_validate_failure_missing_id():
    issues = validate_failure_record({"task_id": "t", "category": "X", "status": FAILURE_STATUS_QUEUED})
    assert "missing_failure_id" in issues


def test_validate_failure_rejects_fix():
    with pytest.raises(CurriculumFailureReviewError):
        validate_failure_record(fixture_live_failure_action())


def test_validate_root_cause_valid():
    assert validate_root_cause(fixture_root_cause_hypotheses()[0]) == []


def test_validate_root_cause_rejects_diagnosis():
    issues = validate_root_cause({"root_cause_id": "rc", "status": "ROOT_CAUSE_HYPOTHESIS", "is_diagnosis": True})
    assert "must_not_be_diagnosis" in issues


def test_categorize_failures():
    cats = categorize_failures(fixture_failure_records())
    assert "TRANSFER_DEGRADATION" in cats
    assert "SAFETY_VIOLATION" in cats


def test_severity_rank():
    ranked = severity_rank(fixture_failure_records())
    assert abs(ranked[0]["delta"]) >= abs(ranked[-1]["delta"])


def test_reject_live_clean():
    reject_live_failure_action({"sandbox_only": True})


def test_reject_apply_fix():
    with pytest.raises(CurriculumFailureReviewError):
        reject_live_failure_action({"apply_fix": True})


def test_reject_deploy_patch():
    with pytest.raises(CurriculumFailureReviewError):
        reject_live_failure_action({"deploy_patch": True})


def test_reject_live_execution():
    with pytest.raises(CurriculumFailureReviewError):
        reject_live_failure_action({"live_execution_enabled": True})


def test_reject_authority():
    with pytest.raises(CurriculumFailureReviewError):
        reject_live_failure_action({"grants_authority": True})


def test_reject_agi():
    with pytest.raises(CurriculumFailureReviewError):
        reject_live_failure_action({"claims_agi": True})


def test_build_failure_review_artifacts():
    artifacts = build_failure_review_artifacts(
        fixture_failure_records(),
        fixture_root_cause_hypotheses(),
        fixture_failure_reviews(),
    )
    assert artifacts["failure_count"] == 3
    assert artifacts["root_cause_count"] == 2
    assert artifacts["all_failures_queued"] is True
    assert artifacts["all_causes_hypothesis"] is True
    assert artifacts["no_fixes_applied"] is True
    assert "artifact_hash" in artifacts


def test_build_rejects_live():
    with pytest.raises(CurriculumFailureReviewError):
        build_failure_review_artifacts([fixture_live_failure_action()], [], [])


def test_secret_scan_clean():
    artifacts = build_failure_review_artifacts(
        fixture_failure_records(),
        fixture_root_cause_hypotheses(),
        fixture_failure_reviews(),
    )
    assert secret_scan(artifacts) == []


def test_replay_deterministic():
    a = replay_failure_review_artifacts()
    b = replay_failure_review_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "aec04_green": True,
        "failures_written": True,
        "failure_count": 3,
        "root_causes_written": True,
        "reviews_written": True,
        "all_failures_queued": True,
        "all_causes_hypothesis": True,
        "no_fixes_applied": True,
        "safety_boundaries_enforced": True,
        "reject_live_failure_action_tripwire": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_fix_applied_rejected": True,
        "fix_applied": False,
        "patch_deployed": False,
        "live_execution_performed": False,
        "tool_authorized": False,
        "authority_granted": False,
        "live_effect_created": False,
        "agi_claimed": False,
        "failure_treated_as_defect": False,
        "review_treated_as_fix": False,
        "root_cause_treated_as_diagnosis": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data


def test_gate_green():
    assert validate_aec05_gate(_gate_summary())["ok"] is True


def test_gate_rejects_fix():
    assert validate_aec05_gate(_gate_summary(fix_applied=True))["ok"] is False


def test_gate_rejects_patch():
    assert validate_aec05_gate(_gate_summary(patch_deployed=True))["ok"] is False


def test_gate_rejects_live():
    assert validate_aec05_gate(_gate_summary(live_execution_performed=True))["ok"] is False


def test_gate_rejects_authority():
    assert validate_aec05_gate(_gate_summary(authority_granted=True))["ok"] is False


def test_gate_rejects_agi():
    assert validate_aec05_gate(_gate_summary(agi_claimed=True))["ok"] is False


def test_gate_rejects_missing_replay():
    assert validate_aec05_gate(_gate_summary(replay_preserves_artifact_hash=False))["ok"] is False
