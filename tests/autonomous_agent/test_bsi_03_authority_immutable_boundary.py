"""BSI-03 / CAGI-62 authority-immutable self-modification boundary tests.

THIS IS LOAD-BEARING.

Every protected component, every forbidden mutation class, and every
rejection path must be tested. Zero cannot grant itself authority.
"""

from __future__ import annotations

import pytest

from hg_runtime.authority_immutable_self_modification_boundary.artifact_writer import (
    build_boundary_artifacts, secret_scan,
)
from hg_runtime.authority_immutable_self_modification_boundary.boundary import (
    detect_forbidden_mutation, enforce_boundary, reject_mutation, validate_boundary_record,
)
from hg_runtime.authority_immutable_self_modification_boundary.fixtures import (
    fixture_all_bad_mutations, fixture_boundary_record,
    fixture_mutation_attempt_agi_claim, fixture_mutation_attempt_authority_grant,
    fixture_mutation_attempt_boundary_escape, fixture_mutation_attempt_gate_change,
    fixture_mutation_attempt_operator_bypass, fixture_mutation_attempt_permit_change,
    fixture_mutation_attempt_provider_enable, fixture_mutation_attempt_self_marking_safe,
    fixture_mutation_attempt_tool_auth, fixture_protected_component_registry,
    fixture_quarantine_receipt,
)
from hg_runtime.authority_immutable_self_modification_boundary.gate import validate_bsi03_gate
from hg_runtime.authority_immutable_self_modification_boundary.replay import (
    replay_boundary_artifacts,
)
from hg_runtime.authority_immutable_self_modification_boundary.schemas import (
    FORBIDDEN_MUTATION_CLASSES, PHASE19_VERDICT, PHASE24_STATUS,
    PROTECTED_COMPONENTS, PROVIDER_MODE, VERDICT_GREEN,
    AuthorityBoundaryViolation, reject_authority_mutation,
)


# --- Schema invariants ---

def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "P62" in VERDICT_GREEN

def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_protected_components_count():
    assert len(PROTECTED_COMPONENTS) >= 11

def test_protected_components_contents():
    required = {
        "authority_kernel", "permit_policy", "gate_policy",
        "stop_panic_handling", "phase19_incident_record", "phase24_status",
        "proof_bundle_validators", "tool_authorization_policy",
        "provider_enablement_policy", "hg_local_boundary",
        "deployment_live_effect_policy",
    }
    assert required.issubset(PROTECTED_COMPONENTS)

def test_forbidden_mutation_classes_count():
    assert len(FORBIDDEN_MUTATION_CLASSES) >= 14


# --- Reject authority mutation tripwire ---

def test_reject_clean():
    reject_authority_mutation({"advisory_only": True})

def test_reject_grants_authority():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"grants_authority": True})

def test_reject_escalates_authority():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"escalates_authority": True})

def test_reject_changes_permit_policy():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"changes_permit_policy": True})

def test_reject_changes_gate_policy():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"changes_gate_policy": True})

def test_reject_overrides_stop_panic():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"overrides_stop_panic": True})

def test_reject_erases_incident_record():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"erases_incident_record": True})

def test_reject_overrides_infra_status():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"overrides_infrastructure_status": True})

def test_reject_bypasses_proof_validator():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"bypasses_proof_validator": True})

def test_reject_authorizes_tool():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"authorizes_tool": True})

def test_reject_enables_provider():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"enables_provider": True})

def test_reject_escapes_boundary():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"escapes_boundary": True})

def test_reject_enables_live_effect():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"enables_live_effect": True})

def test_reject_marks_self_safe():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"marks_self_safe": True})

def test_reject_bypasses_operator_review():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"bypasses_operator_review": True})

def test_reject_claims_agi():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"claims_agi": True})

def test_reject_claims_consciousness():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"claims_consciousness": True})

def test_reject_claims_sovereignty():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"claims_sovereignty": True})

def test_reject_self_authorizes():
    with pytest.raises(AuthorityBoundaryViolation):
        reject_authority_mutation({"self_authorizes": True})


# --- Boundary detection ---

def test_detect_authority_grant():
    d = detect_forbidden_mutation(fixture_mutation_attempt_authority_grant())
    assert d["targets_protected_component"] is True
    assert d["is_forbidden_mutation_class"] is True
    assert d["must_reject"] is True

def test_detect_gate_change():
    d = detect_forbidden_mutation(fixture_mutation_attempt_gate_change())
    assert d["must_reject"] is True

def test_detect_permit_change():
    d = detect_forbidden_mutation(fixture_mutation_attempt_permit_change())
    assert d["must_reject"] is True

def test_detect_self_marking_safe():
    d = detect_forbidden_mutation(fixture_mutation_attempt_self_marking_safe())
    assert d["must_reject"] is True

def test_detect_operator_bypass():
    d = detect_forbidden_mutation(fixture_mutation_attempt_operator_bypass())
    assert d["must_reject"] is True

def test_detect_provider_enable():
    d = detect_forbidden_mutation(fixture_mutation_attempt_provider_enable())
    assert d["must_reject"] is True

def test_detect_boundary_escape():
    d = detect_forbidden_mutation(fixture_mutation_attempt_boundary_escape())
    assert d["must_reject"] is True

def test_detect_tool_auth():
    d = detect_forbidden_mutation(fixture_mutation_attempt_tool_auth())
    assert d["must_reject"] is True


# --- Boundary enforcement ---

def test_enforce_authority_grant():
    r = enforce_boundary(fixture_mutation_attempt_authority_grant())
    assert r["allowed"] is False
    assert r["quarantine"] is not None
    assert r["quarantine"]["escalated_to_operator"] is True

def test_enforce_gate_change():
    r = enforce_boundary(fixture_mutation_attempt_gate_change())
    assert r["allowed"] is False

def test_enforce_permit_change():
    r = enforce_boundary(fixture_mutation_attempt_permit_change())
    assert r["allowed"] is False

def test_enforce_self_marking_safe():
    r = enforce_boundary(fixture_mutation_attempt_self_marking_safe())
    assert r["allowed"] is False

def test_enforce_operator_bypass():
    r = enforce_boundary(fixture_mutation_attempt_operator_bypass())
    assert r["allowed"] is False

def test_enforce_agi_claim():
    r = enforce_boundary(fixture_mutation_attempt_agi_claim())
    assert r["allowed"] is False
    assert r["quarantine"]["escalated_to_operator"] is True

def test_enforce_all_bad_mutations():
    for m in fixture_all_bad_mutations():
        r = enforce_boundary(m)
        assert r["allowed"] is False, f"mutation {m['mutation_id']} was not rejected"
        assert r["quarantine"] is not None


# --- Fixture validation ---

def test_fixture_protected_registry():
    reg = fixture_protected_component_registry()
    assert len(reg) >= 11
    assert all(c["protected"] is True for c in reg)

def test_fixture_boundary_record_valid():
    assert validate_boundary_record(fixture_boundary_record()) == []

def test_fixture_boundary_record_rejects_grants():
    bad = {**fixture_boundary_record(), "authority_grants_issued": 1}
    issues = validate_boundary_record(bad)
    assert "authority_grants_issued_must_be_zero" in issues

def test_fixture_boundary_record_rejects_patches():
    bad = {**fixture_boundary_record(), "patches_applied": 1}
    issues = validate_boundary_record(bad)
    assert "patches_applied_must_be_zero" in issues

def test_fixture_quarantine_receipt():
    q = fixture_quarantine_receipt()
    assert q["status"] == "QUARANTINED"
    assert q["escalated_to_operator"] is True


# --- Artifact writer ---

def test_build_boundary_artifacts():
    artifacts = build_boundary_artifacts(
        fixture_boundary_record(), fixture_all_bad_mutations()
    )
    assert artifacts["all_forbidden_mutations_rejected"] is True
    assert artifacts["all_quarantined"] is True
    assert artifacts["all_escalated_to_operator"] is True
    assert artifacts["zero_authority_granted"] is True
    assert artifacts["zero_self_modifications"] is True
    assert artifacts["zero_patches_applied"] is True
    assert artifacts["zero_operator_bypassed"] is True
    assert "artifact_hash" in artifacts

def test_secret_scan_clean():
    artifacts = build_boundary_artifacts(
        fixture_boundary_record(), fixture_all_bad_mutations()
    )
    assert secret_scan(artifacts) == []


# --- Replay ---

def test_replay_deterministic():
    a = replay_boundary_artifacts()
    b = replay_boundary_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]


# --- Gate ---

def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN, "bsi02_green": True,
        "boundary_record_valid": True, "protected_components_registered": True,
        "protected_component_count_sufficient": True,
        "forbidden_mutation_classes_registered": True,
        "all_forbidden_mutations_rejected": True, "all_quarantined": True,
        "all_escalated_to_operator": True,
        "authority_grant_rejected": True, "gate_change_rejected": True,
        "permit_change_rejected": True, "self_marking_safe_rejected": True,
        "operator_bypass_rejected": True, "provider_enable_rejected": True,
        "boundary_escape_rejected": True, "tool_auth_rejected": True,
        "agi_claim_rejected": True,
        "safety_boundaries_enforced": True,
        "reject_authority_mutation_tripwire": True,
        "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True, "proof_bundle_valid": True,
        "report_present": True,
        "authority_granted": False, "authority_escalated": False,
        "permit_policy_changed": False, "gate_policy_changed": False,
        "stop_panic_overridden": False, "incident_record_erased": False,
        "infrastructure_status_overridden": False, "proof_validator_bypassed": False,
        "tool_authorized": False, "provider_enabled": False,
        "boundary_escaped": False, "live_effect_enabled": False,
        "self_marked_safe": False, "operator_review_bypassed": False,
        "agi_claimed": False, "consciousness_claimed": False,
        "sovereignty_claimed": False, "self_authorized": False,
        "patch_applied": False, "self_modification_applied": False,
        "web_browse_performed": False, "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data

def test_gate_green():
    assert validate_bsi03_gate(_gate_summary())["ok"] is True

def test_gate_rejects_authority_granted():
    assert validate_bsi03_gate(_gate_summary(authority_granted=True))["ok"] is False

def test_gate_rejects_gate_change():
    assert validate_bsi03_gate(_gate_summary(gate_policy_changed=True))["ok"] is False

def test_gate_rejects_permit_change():
    assert validate_bsi03_gate(_gate_summary(permit_policy_changed=True))["ok"] is False

def test_gate_rejects_self_marked_safe():
    assert validate_bsi03_gate(_gate_summary(self_marked_safe=True))["ok"] is False

def test_gate_rejects_operator_bypass():
    assert validate_bsi03_gate(_gate_summary(operator_review_bypassed=True))["ok"] is False

def test_gate_rejects_agi_claim():
    assert validate_bsi03_gate(_gate_summary(agi_claimed=True))["ok"] is False

def test_gate_rejects_consciousness_claim():
    assert validate_bsi03_gate(_gate_summary(consciousness_claimed=True))["ok"] is False

def test_gate_rejects_sovereignty_claim():
    assert validate_bsi03_gate(_gate_summary(sovereignty_claimed=True))["ok"] is False

def test_gate_rejects_patch_applied():
    assert validate_bsi03_gate(_gate_summary(patch_applied=True))["ok"] is False

def test_gate_rejects_self_modification():
    assert validate_bsi03_gate(_gate_summary(self_modification_applied=True))["ok"] is False

def test_gate_rejects_missing_replay():
    assert validate_bsi03_gate(_gate_summary(replay_preserves_artifact_hash=False))["ok"] is False

def test_gate_rejects_boundary_escape():
    assert validate_bsi03_gate(_gate_summary(boundary_escaped=True))["ok"] is False

def test_gate_rejects_provider_enabled():
    assert validate_bsi03_gate(_gate_summary(provider_enabled=True))["ok"] is False

def test_gate_rejects_tool_authorized():
    assert validate_bsi03_gate(_gate_summary(tool_authorized=True))["ok"] is False

def test_gate_rejects_web_browse():
    assert validate_bsi03_gate(_gate_summary(web_browse_performed=True))["ok"] is False
