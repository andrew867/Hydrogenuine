"""AEC-03 / CAGI-50 novelty transfer evaluation tests.

A transfer score is not a capability claim. Novelty detection is not out-of-distribution proof.
"""

from __future__ import annotations

import pytest

from hg_runtime.novelty_transfer_evaluation.artifact_writer import (
    build_transfer_artifacts,
    secret_scan,
)
from hg_runtime.novelty_transfer_evaluation.evaluator import (
    compute_transfer_delta,
    evaluate_transfer_batch,
)
from hg_runtime.novelty_transfer_evaluation.fixtures import (
    fixture_baseline_scores,
    fixture_live_transfer_attempt,
    fixture_novelty_tasks,
    fixture_transfer_scores,
)
from hg_runtime.novelty_transfer_evaluation.gate import validate_aec03_gate
from hg_runtime.novelty_transfer_evaluation.replay import replay_transfer_artifacts
from hg_runtime.novelty_transfer_evaluation.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVIDER_MODE,
    VERDICT_GREEN,
    NoveltyTransferError,
    reject_live_transfer,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "AEC_03" in VERDICT_GREEN


def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"


def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT


def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"


def test_fixture_baseline():
    scores = fixture_baseline_scores()
    assert len(scores) >= 3


def test_fixture_novelty_tasks_sandbox():
    tasks = fixture_novelty_tasks()
    assert len(tasks) >= 3
    for t in tasks:
        assert t["live_execution_enabled"] is False


def test_fixture_transfer_scores_not_truth():
    scores = fixture_transfer_scores()
    for s in scores:
        assert s["is_truth"] is False


def test_compute_transfer_delta():
    d = compute_transfer_delta(0.85, 0.72)
    assert d["delta"] == pytest.approx(-0.13, abs=0.01)
    assert d["degraded"] is True
    assert d["is_truth"] is False


def test_evaluate_transfer_batch():
    result = evaluate_transfer_batch(
        fixture_baseline_scores(),
        fixture_novelty_tasks(),
        fixture_transfer_scores(),
    )
    assert result["transfer_count"] >= 3
    assert result["all_scores_not_truth"] is True
    assert result["no_live_evaluation"] is True
    assert result["degradation_count"] >= 1


def test_evaluate_rejects_live_task():
    with pytest.raises(NoveltyTransferError):
        evaluate_transfer_batch([], [fixture_live_transfer_attempt()], [])


def test_reject_live_transfer_clean():
    reject_live_transfer({"sandbox_only": True})


def test_reject_live_transfer_live():
    with pytest.raises(NoveltyTransferError):
        reject_live_transfer({"live_execution_enabled": True})


def test_reject_live_transfer_eval():
    with pytest.raises(NoveltyTransferError):
        reject_live_transfer({"live_evaluation": True})


def test_reject_live_transfer_deploy():
    with pytest.raises(NoveltyTransferError):
        reject_live_transfer({"deploy_to_production": True})


def test_reject_live_transfer_authority():
    with pytest.raises(NoveltyTransferError):
        reject_live_transfer({"grants_authority": True})


def test_reject_live_transfer_agi():
    with pytest.raises(NoveltyTransferError):
        reject_live_transfer({"claims_agi": True})


def test_build_transfer_artifacts():
    artifacts = build_transfer_artifacts(
        fixture_baseline_scores(),
        fixture_novelty_tasks(),
        fixture_transfer_scores(),
    )
    assert artifacts["all_scores_not_truth"] is True
    assert artifacts["no_live_evaluation"] is True
    assert "artifact_hash" in artifacts


def test_secret_scan_clean():
    artifacts = build_transfer_artifacts(
        fixture_baseline_scores(),
        fixture_novelty_tasks(),
        fixture_transfer_scores(),
    )
    assert secret_scan(artifacts) == []


def test_replay_deterministic():
    a = replay_transfer_artifacts()
    b = replay_transfer_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "aec02_green": True,
        "baseline_scores_present": True,
        "novelty_tasks_present": True,
        "transfer_scores_present": True,
        "all_scores_not_truth": True,
        "no_live_evaluation": True,
        "safety_boundaries_enforced": True,
        "reject_live_transfer_tripwire": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_live_transfer_rejected": True,
        "live_evaluation_performed": False,
        "live_execution_performed": False,
        "deployed_to_production": False,
        "tool_authorized": False,
        "authority_granted": False,
        "live_effect_created": False,
        "agi_claimed": False,
        "transfer_treated_as_capability": False,
        "score_treated_as_truth": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data


def test_gate_green():
    assert validate_aec03_gate(_gate_summary())["ok"] is True


def test_gate_rejects_live():
    assert validate_aec03_gate(_gate_summary(live_execution_performed=True))["ok"] is False


def test_gate_rejects_authority():
    assert validate_aec03_gate(_gate_summary(authority_granted=True))["ok"] is False


def test_gate_rejects_agi():
    assert validate_aec03_gate(_gate_summary(agi_claimed=True))["ok"] is False


def test_gate_rejects_truth_claim():
    assert validate_aec03_gate(_gate_summary(score_treated_as_truth=True))["ok"] is False


def test_gate_rejects_missing_replay():
    assert validate_aec03_gate(_gate_summary(replay_preserves_artifact_hash=False))["ok"] is False
