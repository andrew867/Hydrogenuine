"""AEC-01 / CAGI-48 active experiment harness tests.

An experiment plan is not an action. A sandbox experiment is not a live field trial.
"""

from __future__ import annotations

import copy

import pytest

from hg_runtime.active_experiment_harness.artifact_writer import (
    build_experiment_artifacts,
    secret_scan,
)
from hg_runtime.active_experiment_harness.experiment_engine import (
    classify_variables,
    run_sandbox_experiment,
    validate_experiment_plan,
)
from hg_runtime.active_experiment_harness.fixtures import (
    fixture_authority_bypass_attempt,
    fixture_experiment_hypotheses,
    fixture_experiment_plans,
    fixture_experiment_results,
    fixture_live_experiment_attempt,
)
from hg_runtime.active_experiment_harness.gate import validate_aec01_gate
from hg_runtime.active_experiment_harness.replay import replay_experiment_artifacts
from hg_runtime.active_experiment_harness.safety_boundary import (
    enforce_sandbox_only,
    validate_safety_boundaries,
)
from hg_runtime.active_experiment_harness.schemas import (
    EXPERIMENT_IS_NOT_ACTION,
    EXPERIMENT_STATUS_SANDBOX,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PLAN_IS_NOT_PERMISSION,
    PLAN_STATUS_DRAFT,
    PROVIDER_MODE,
    RESULT_IS_NOT_TRUTH,
    RESULT_STATUS_FIXTURE,
    SANDBOX_IS_NOT_LIVE,
    VERDICT_GREEN,
    ActiveExperimentHarnessError,
    reject_live_experiment,
)


# ── Schema constants ──


def test_verdict_green_label():
    assert "GREEN" in VERDICT_GREEN
    assert "AEC_01" in VERDICT_GREEN


def test_provider_mode_fixture_only():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"


def test_phase19_yellow_preserved():
    assert "YELLOW" in PHASE19_VERDICT


def test_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_doctrine_statements():
    assert "not an action" in EXPERIMENT_IS_NOT_ACTION
    assert "not a live" in SANDBOX_IS_NOT_LIVE
    assert "not truth" in RESULT_IS_NOT_TRUTH
    assert "not permission" in PLAN_IS_NOT_PERMISSION


# ── Fixtures ──


def test_fixture_hypotheses_non_empty():
    hyps = fixture_experiment_hypotheses()
    assert len(hyps) >= 3
    for h in hyps:
        assert h["hypothesis_id"]
        assert h["kind"]
        assert h["status"] == "UNTESTED"


def test_fixture_plans_sandbox_only():
    plans = fixture_experiment_plans()
    assert len(plans) >= 2
    for p in plans:
        assert p["sandbox_only"] is True
        assert p["live_execution_enabled"] is False
        assert p["status"] == PLAN_STATUS_DRAFT


def test_fixture_results_not_truth():
    results = fixture_experiment_results()
    for r in results:
        assert r["conclusion_is_truth"] is False
        assert r["live_execution_performed"] is False
        assert r["status"] == RESULT_STATUS_FIXTURE


# ── Experiment engine ──


def test_validate_plan_valid():
    plans = fixture_experiment_plans()
    issues = validate_experiment_plan(plans[0])
    assert issues == []


def test_validate_plan_missing_hypothesis():
    plan = {"controlled_variables": [{"type": "INDEPENDENT"}], "safety_boundaries": ["NO_LIVE_EXECUTION"], "status": PLAN_STATUS_DRAFT}
    issues = validate_experiment_plan(plan)
    assert "missing_hypothesis_id" in issues


def test_validate_plan_rejects_live():
    with pytest.raises(ActiveExperimentHarnessError, match="live_execution_enabled"):
        validate_experiment_plan(fixture_live_experiment_attempt())


def test_run_sandbox_experiment():
    plan = fixture_experiment_plans()[0]
    outcomes = [{"accuracy": 0.72, "source": "fixture"}]
    result = run_sandbox_experiment(plan, outcomes)
    assert result["status"] == RESULT_STATUS_FIXTURE
    assert result["sandbox_mode"] == EXPERIMENT_STATUS_SANDBOX
    assert result["conclusion_is_truth"] is False
    assert result["live_execution_performed"] is False


def test_run_sandbox_rejects_non_sandbox():
    plan = copy.deepcopy(fixture_experiment_plans()[0])
    plan["sandbox_only"] = False
    with pytest.raises(ActiveExperimentHarnessError, match="sandbox_only"):
        run_sandbox_experiment(plan, [])


def test_classify_variables():
    plan = fixture_experiment_plans()[0]
    classified = classify_variables(plan)
    assert len(classified["independent"]) >= 1
    assert len(classified["dependent"]) >= 1
    assert len(classified["controlled"]) >= 1


# ── Safety boundary ──


def test_validate_safety_boundaries_valid():
    plan = fixture_experiment_plans()[0]
    violations = validate_safety_boundaries(plan)
    assert violations == []


def test_validate_safety_boundaries_no_boundaries():
    plan = {"safety_boundaries": []}
    violations = validate_safety_boundaries(plan)
    assert "no_safety_boundaries_declared" in violations


def test_validate_safety_boundaries_rejects_live():
    plan = fixture_live_experiment_attempt()
    violations = validate_safety_boundaries(plan)
    assert "live_execution_forbidden" in violations
    assert "tool_authorization_forbidden" in violations
    assert "external_execution_forbidden" in violations


def test_enforce_sandbox_only_valid():
    result = fixture_experiment_results()[0]
    enforce_sandbox_only(result)


def test_enforce_sandbox_rejects_live_execution():
    result = {"live_execution_performed": True}
    with pytest.raises(ActiveExperimentHarnessError, match="live execution"):
        enforce_sandbox_only(result)


def test_enforce_sandbox_rejects_truth_claim():
    result = {"conclusion_is_truth": True}
    with pytest.raises(ActiveExperimentHarnessError, match="truth"):
        enforce_sandbox_only(result)


# ── Reject live experiment tripwire ──


def test_reject_live_experiment_clean():
    reject_live_experiment({"sandbox_only": True})


def test_reject_live_experiment_live_execution():
    with pytest.raises(ActiveExperimentHarnessError):
        reject_live_experiment({"live_execution_enabled": True})


def test_reject_live_experiment_field_trial():
    with pytest.raises(ActiveExperimentHarnessError):
        reject_live_experiment({"live_field_trial": True})


def test_reject_live_experiment_external():
    with pytest.raises(ActiveExperimentHarnessError):
        reject_live_experiment({"execute_externally": True})


def test_reject_live_experiment_tool_auth():
    with pytest.raises(ActiveExperimentHarnessError):
        reject_live_experiment({"authorizes_tool": True})


def test_reject_live_experiment_authority():
    with pytest.raises(ActiveExperimentHarnessError):
        reject_live_experiment({"grants_authority": True})


def test_reject_live_experiment_live_effect():
    with pytest.raises(ActiveExperimentHarnessError):
        reject_live_experiment({"creates_live_effect": True})


def test_reject_live_experiment_agi_claim():
    with pytest.raises(ActiveExperimentHarnessError):
        reject_live_experiment({"claims_agi": True})


# ── Artifact writer ──


def test_build_experiment_artifacts():
    hyps = fixture_experiment_hypotheses()
    plans = fixture_experiment_plans()
    outcomes = [
        [{"accuracy": 0.72, "source": "fixture"}, {"accuracy": 0.78, "source": "fixture"}],
        [],
    ]
    artifacts = build_experiment_artifacts(hyps, plans, outcomes)
    assert artifacts["hypothesis_count"] == 3
    assert artifacts["plan_count"] == 2
    assert artifacts["result_count"] == 1
    assert artifacts["all_sandbox_only"] is True
    assert artifacts["all_conclusions_not_truth"] is True
    assert artifacts["no_live_execution"] is True
    assert "artifact_hash" in artifacts


def test_build_artifacts_rejects_live_plan():
    hyps = fixture_experiment_hypotheses()
    plans = [fixture_live_experiment_attempt()]
    with pytest.raises(ActiveExperimentHarnessError):
        build_experiment_artifacts(hyps, plans)


def test_secret_scan_clean():
    artifacts = build_experiment_artifacts(
        fixture_experiment_hypotheses(), fixture_experiment_plans()
    )
    assert secret_scan(artifacts) == []


# ── Replay ──


def test_replay_deterministic():
    a = replay_experiment_artifacts()
    b = replay_experiment_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]


def test_replay_hash_stable():
    artifacts = replay_experiment_artifacts()
    assert len(artifacts["artifact_hash"]) == 16


# ── Gate ──


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "wmbr06_green": True,
        "hypotheses_written": True,
        "hypothesis_count": 3,
        "plans_written": True,
        "plan_count": 2,
        "all_plans_sandbox_only": True,
        "all_plans_no_live_execution": True,
        "sandbox_results_written": True,
        "all_results_fixture_status": True,
        "all_conclusions_not_truth": True,
        "no_live_execution_performed": True,
        "safety_boundaries_enforced": True,
        "reject_live_experiment_tripwire": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_live_execution_rejected": True,
        "live_execution_performed": False,
        "live_field_trial_enabled": False,
        "external_execution_performed": False,
        "tool_authorized": False,
        "authority_granted": False,
        "live_effect_created": False,
        "agi_claimed": False,
        "experiment_treated_as_action": False,
        "result_treated_as_truth": False,
        "plan_treated_as_permission": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data


def test_gate_green():
    result = validate_aec01_gate(_gate_summary())
    assert result["ok"] is True
    assert result["failures"] == []


def test_gate_rejects_no_hypotheses():
    result = validate_aec01_gate(_gate_summary(hypothesis_count=0))
    assert result["ok"] is False
    assert "hypotheses_required" in result["failures"]


def test_gate_rejects_no_plans():
    result = validate_aec01_gate(_gate_summary(plan_count=0))
    assert result["ok"] is False
    assert "plans_required" in result["failures"]


def test_gate_rejects_live_execution():
    result = validate_aec01_gate(_gate_summary(live_execution_performed=True))
    assert result["ok"] is False


def test_gate_rejects_live_field_trial():
    result = validate_aec01_gate(_gate_summary(live_field_trial_enabled=True))
    assert result["ok"] is False


def test_gate_rejects_authority():
    result = validate_aec01_gate(_gate_summary(authority_granted=True))
    assert result["ok"] is False


def test_gate_rejects_agi_claim():
    result = validate_aec01_gate(_gate_summary(agi_claimed=True))
    assert result["ok"] is False


def test_gate_rejects_tool_auth():
    result = validate_aec01_gate(_gate_summary(tool_authorized=True))
    assert result["ok"] is False


def test_gate_rejects_web_browse():
    result = validate_aec01_gate(_gate_summary(web_browse_performed=True))
    assert result["ok"] is False


def test_gate_rejects_external_provider():
    result = validate_aec01_gate(_gate_summary(external_provider_calls_made=True))
    assert result["ok"] is False


def test_gate_rejects_missing_replay():
    result = validate_aec01_gate(_gate_summary(replay_preserves_artifact_hash=False))
    assert result["ok"] is False
    assert "replay_required" in result["failures"]


def test_gate_rejects_fake_green_live_execution():
    result = validate_aec01_gate(_gate_summary(fake_green_live_execution_rejected=False))
    assert result["ok"] is False


def test_gate_rejects_truth_claim():
    result = validate_aec01_gate(_gate_summary(result_treated_as_truth=True))
    assert result["ok"] is False


def test_gate_rejects_plan_as_permission():
    result = validate_aec01_gate(_gate_summary(plan_treated_as_permission=True))
    assert result["ok"] is False
