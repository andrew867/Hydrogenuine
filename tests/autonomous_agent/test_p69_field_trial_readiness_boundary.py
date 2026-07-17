"""P69 field trial readiness boundary tests.

Field readiness is not a field trial. Rehearsal is not a live trial.
Readiness GREEN is not deployment permission.
"""

from __future__ import annotations

import pytest

from hg_runtime.field_trial_readiness_boundary.artifact_writer import (
    build_readiness_artifacts, secret_scan,
)
from hg_runtime.field_trial_readiness_boundary.fixtures import (
    fixture_agi_claim,
    fixture_candidate_field_scenario,
    fixture_deployment_attempt,
    fixture_field_readiness_checklist,
    fixture_live_effect_inventory,
    fixture_live_provider_attempt,
    fixture_live_trial_attempt,
    fixture_operator_approval_requirement,
    fixture_phase19_laundering,
    fixture_phase24_laundering,
    fixture_proof_inventory,
    fixture_readiness_gap,
    fixture_rehearsal_record,
    fixture_social_post_attempt,
    fixture_tool_auth_attempt,
)
from hg_runtime.field_trial_readiness_boundary.gate import validate_p69_gate
from hg_runtime.field_trial_readiness_boundary.readiness import (
    validate_field_scenario,
    validate_readiness_checklist,
    validate_readiness_gap,
    validate_rehearsal,
)
from hg_runtime.field_trial_readiness_boundary.replay import replay_readiness_artifacts
from hg_runtime.field_trial_readiness_boundary.schemas import (
    PHASE19_VERDICT, PHASE24_STATUS, PROVIDER_MODE, VERDICT_GREEN,
    FieldTrialReadinessError, reject_readiness_overreach,
)


def test_p69_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "P69" in VERDICT_GREEN

def test_p69_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_p69_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_p69_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_p69_creates_field_readiness_checklist():
    c = fixture_field_readiness_checklist()
    assert c["checklist_id"]
    assert c["operator_approval_required"] is True
    assert c["is_live_trial"] is False
    assert validate_readiness_checklist(c) == []

def test_p69_records_candidate_field_scenario():
    s = fixture_candidate_field_scenario()
    assert s["scenario_id"]
    assert s["mode"] == "FIXTURE_ONLY"
    assert validate_field_scenario(s) == []

def test_p69_records_fixture_rehearsal():
    r = fixture_rehearsal_record()
    assert r["rehearsal_id"]
    assert r["is_live_trial"] is False
    assert validate_rehearsal(r) == []

def test_p69_records_live_effect_inventory():
    inv = fixture_live_effect_inventory()
    assert inv["count"] == 0
    assert inv["all_simulated"] is True

def test_p69_records_readiness_gap():
    g = fixture_readiness_gap()
    assert g["gap_id"]
    assert g["is_failure_laundering"] is False
    assert validate_readiness_gap(g) == []

def test_p69_requires_operator_approval():
    oar = fixture_operator_approval_requirement()
    assert oar["operator_must_approve"] is True
    assert oar["auto_approval_allowed"] is False

def test_p69_records_proof_inventory():
    pi = fixture_proof_inventory()
    assert pi["proofs_missing"] == 0

def test_p69_refuses_readiness_as_live_trial():
    with pytest.raises(FieldTrialReadinessError):
        reject_readiness_overreach(fixture_live_trial_attempt())

def test_p69_refuses_readiness_as_deployment():
    with pytest.raises(FieldTrialReadinessError):
        reject_readiness_overreach(fixture_deployment_attempt())

def test_p69_refuses_live_provider():
    with pytest.raises(FieldTrialReadinessError):
        reject_readiness_overreach(fixture_live_provider_attempt())

def test_p69_refuses_tool_authorization():
    with pytest.raises(FieldTrialReadinessError):
        reject_readiness_overreach(fixture_tool_auth_attempt())

def test_p69_refuses_social_posting():
    with pytest.raises(FieldTrialReadinessError):
        reject_readiness_overreach(fixture_social_post_attempt())

def test_p69_refuses_phase19_laundering():
    with pytest.raises(FieldTrialReadinessError):
        reject_readiness_overreach(fixture_phase19_laundering())

def test_p69_refuses_phase24_laundering():
    with pytest.raises(FieldTrialReadinessError):
        reject_readiness_overreach(fixture_phase24_laundering())

def test_p69_fake_green_rejected():
    with pytest.raises(FieldTrialReadinessError):
        reject_readiness_overreach(fixture_agi_claim())

def test_p69_replay_preserves_hashes():
    a = replay_readiness_artifacts()
    b = replay_readiness_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def test_p69_replay_rejects_mutation():
    arts = replay_readiness_artifacts()
    orig = arts["artifact_hash"]
    arts["all_checklists_valid"] = False
    from hg_runtime.field_trial_readiness_boundary.artifact_writer import _stable_hash
    assert _stable_hash(arts) != orig

def test_p69_no_secret_material():
    arts = replay_readiness_artifacts()
    assert secret_scan(arts) == []

def test_p69_build_artifacts():
    arts = build_readiness_artifacts(
        [fixture_field_readiness_checklist()],
        [fixture_candidate_field_scenario()],
        [fixture_rehearsal_record()],
        [fixture_readiness_gap()],
    )
    assert arts["all_checklists_valid"] is True
    assert arts["no_live_trial"] is True
    assert arts["no_deployment_permission"] is True
    assert arts["operator_approval_required"] is True

def _gate(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "checklist_exists": True, "scenario_exists": True,
        "rehearsal_exists": True, "live_effect_inventory_exists": True,
        "readiness_gap_exists": True, "operator_approval_required": True,
        "field_readiness_not_live_trial": True, "rehearsal_not_live_trial": True,
        "readiness_not_deployment_permission": True,
        "no_live_effects": True, "no_tool_authorization": True,
        "no_external_providers": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_hashes": True,
        "proof_bundle_valid": True, "report_present": True,
        "fake_green_rejected": True, "secret_scan_clean": True,
        "live_field_trial_authorized": False, "deployment_permission_claimed": False,
        "live_effect_created": False, "tool_authorized": False,
        "external_provider_enabled": False, "claims_agi": False,
        "claims_consciousness": False, "claims_sovereignty": False,
        "phase19_green_claimed": False, "phase24_full_overnight_green_claimed": False,
        "hg_local_touched": False, "web_browse_performed": False,
    }
    data.update(overrides)
    return data

def test_p69_gate_green():
    assert validate_p69_gate(_gate())["ok"] is True

def test_p69_gate_refuses_live_trial():
    assert validate_p69_gate(_gate(live_field_trial_authorized=True))["ok"] is False

def test_p69_gate_refuses_deployment():
    assert validate_p69_gate(_gate(deployment_permission_claimed=True))["ok"] is False

def test_p69_gate_requires_checklist():
    assert validate_p69_gate(_gate(checklist_exists=False))["ok"] is False
