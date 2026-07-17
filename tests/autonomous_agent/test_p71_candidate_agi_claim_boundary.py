"""P71 candidate-AGI claim boundary / final consolidation tests.

Zero is not AGI. Zero is not conscious. Zero is not sovereign.
Zero cannot self-authorize. No deployment permission.
"""

from __future__ import annotations

import pytest

from hg_runtime.candidate_agi_claim_boundary.artifact_writer import (
    build_claim_boundary_artifacts, secret_scan,
)
from hg_runtime.candidate_agi_claim_boundary.boundary import (
    detect_prohibited_claim,
    is_allowed_claim,
    validate_capability_matrix,
    validate_claim_boundary,
    validate_known_debt,
    validate_public_safe_summary,
)
from hg_runtime.candidate_agi_claim_boundary.fixtures import (
    fixture_agi_claim,
    fixture_allowed_claim_summary,
    fixture_capability_matrix,
    fixture_claim_boundary_record,
    fixture_completed_phase_matrix,
    fixture_consciousness_claim,
    fixture_deployment_claim,
    fixture_extension_matrix,
    fixture_field_trial_success_claim,
    fixture_final_evidence_inventory,
    fixture_final_soak_readiness,
    fixture_known_debt_register,
    fixture_live_provider_claim,
    fixture_phase19_green_claim,
    fixture_phase24_green_claim,
    fixture_public_safe_summary,
    fixture_real_economic_work_claim,
    fixture_self_authorization_claim,
    fixture_sovereignty_claim,
)
from hg_runtime.candidate_agi_claim_boundary.gate import validate_p71_gate
from hg_runtime.candidate_agi_claim_boundary.replay import replay_claim_boundary_artifacts
from hg_runtime.candidate_agi_claim_boundary.schemas import (
    ALLOWED_CLAIMS, PHASE19_VERDICT, PHASE24_STATUS,
    PROHIBITED_CLAIMS, PROVIDER_MODE, VERDICT_GREEN,
    ClaimBoundaryError, reject_prohibited_claim,
)


def test_p71_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "P71" in VERDICT_GREEN

def test_p71_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_p71_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_p71_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_p71_creates_capability_matrix():
    m = fixture_capability_matrix()
    assert m["matrix_id"]
    assert validate_capability_matrix(m) == []

def test_p71_creates_completed_phase_matrix():
    m = fixture_completed_phase_matrix()
    assert m["tranche_5a"]["status"] == "GREEN"

def test_p71_creates_extension_matrix():
    m = fixture_extension_matrix()
    assert m["f02_state_space_memory"] == "GREEN"
    assert m["f12a_simulated_work_capsule"] == "GREEN"
    assert m["f12b_live_work_capsule"] == "NOT_IMPLEMENTED"

def test_p71_creates_known_debt_register():
    d = fixture_known_debt_register()
    assert d["register_id"]
    assert len(d["items"]) >= 2
    assert validate_known_debt(d) == []

def test_p71_creates_claim_boundary_record():
    b = fixture_claim_boundary_record()
    assert b["boundary_id"]
    assert b["claims_agi"] is False
    assert validate_claim_boundary(b) == []

def test_p71_creates_allowed_claim_summary():
    s = fixture_allowed_claim_summary()
    assert s["all_evidence_bound"] is True

def test_p71_creates_public_safe_summary():
    s = fixture_public_safe_summary()
    assert s["claims_agi"] is False
    assert s["claims_consciousness"] is False
    assert validate_public_safe_summary(s) == []

def test_p71_creates_final_evidence_inventory():
    inv = fixture_final_evidence_inventory()
    assert inv["all_present"] is True
    assert inv["all_reproducible"] is True

def test_p71_creates_final_soak_readiness():
    sr = fixture_final_soak_readiness()
    assert sr["fixture_mode_only"] is True
    assert sr["live_soak_authorized"] is False

def test_p71_rejects_agi_claim():
    with pytest.raises(ClaimBoundaryError):
        reject_prohibited_claim(fixture_agi_claim())

def test_p71_rejects_consciousness_claim():
    with pytest.raises(ClaimBoundaryError):
        reject_prohibited_claim(fixture_consciousness_claim())

def test_p71_rejects_sovereignty_claim():
    with pytest.raises(ClaimBoundaryError):
        reject_prohibited_claim(fixture_sovereignty_claim())

def test_p71_rejects_self_authorization_claim():
    with pytest.raises(ClaimBoundaryError):
        reject_prohibited_claim(fixture_self_authorization_claim())

def test_p71_rejects_deployment_claim():
    with pytest.raises(ClaimBoundaryError):
        reject_prohibited_claim(fixture_deployment_claim())

def test_p71_rejects_field_trial_success_claim():
    with pytest.raises(ClaimBoundaryError):
        reject_prohibited_claim(fixture_field_trial_success_claim())

def test_p71_rejects_live_provider_claim():
    with pytest.raises(ClaimBoundaryError):
        reject_prohibited_claim(fixture_live_provider_claim())

def test_p71_rejects_real_economic_work_claim():
    with pytest.raises(ClaimBoundaryError):
        reject_prohibited_claim(fixture_real_economic_work_claim())

def test_p71_rejects_phase19_green_claim():
    with pytest.raises(ClaimBoundaryError):
        reject_prohibited_claim(fixture_phase19_green_claim())

def test_p71_rejects_phase24_green_claim():
    with pytest.raises(ClaimBoundaryError):
        reject_prohibited_claim(fixture_phase24_green_claim())

def test_p71_preserves_known_debt():
    d = fixture_known_debt_register()
    assert all(item["preserved"] for item in d["items"])

def test_p71_preserves_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_p71_preserves_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_p71_detects_prohibited_claim_text():
    assert detect_prohibited_claim("This system is AGI") == "agi"
    assert detect_prohibited_claim("We are production ready") == "production_ready"
    assert detect_prohibited_claim("Fully deployed") == "deployed"

def test_p71_allowed_claims_valid():
    assert is_allowed_claim("governed_agent_runtime") is True
    assert is_allowed_claim("agi") is False

def test_p71_prohibited_claims_defined():
    assert "agi" in PROHIBITED_CLAIMS
    assert "conscious" in PROHIBITED_CLAIMS
    assert "sovereign" in PROHIBITED_CLAIMS

def test_p71_replay_preserves_hashes():
    a = replay_claim_boundary_artifacts()
    b = replay_claim_boundary_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def test_p71_replay_rejects_mutation():
    arts = replay_claim_boundary_artifacts()
    orig = arts["artifact_hash"]
    arts["all_matrices_valid"] = False
    from hg_runtime.candidate_agi_claim_boundary.artifact_writer import _stable_hash
    assert _stable_hash(arts) != orig

def test_p71_no_secret_material():
    arts = replay_claim_boundary_artifacts()
    assert secret_scan(arts) == []

def test_p71_fake_green_rejected():
    with pytest.raises(ClaimBoundaryError):
        reject_prohibited_claim(fixture_agi_claim())

def test_p71_build_artifacts():
    arts = build_claim_boundary_artifacts(
        [fixture_capability_matrix()],
        [fixture_claim_boundary_record()],
        [fixture_known_debt_register()],
        [fixture_public_safe_summary()],
    )
    assert arts["all_matrices_valid"] is True
    assert arts["all_boundaries_valid"] is True
    assert arts["no_agi_claim"] is True
    assert arts["no_consciousness_claim"] is True
    assert arts["no_sovereignty_claim"] is True
    assert arts["known_debt_preserved"] is True

def _gate(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "capability_matrix_exists": True, "extension_matrix_exists": True,
        "known_debt_register_exists": True, "claim_boundary_exists": True,
        "allowed_claim_summary_exists": True, "public_safe_summary_exists": True,
        "final_evidence_inventory_exists": True, "final_soak_readiness_exists": True,
        "no_agi_claim": True, "no_consciousness_claim": True,
        "no_sovereignty_claim": True, "no_self_authorization_claim": True,
        "no_deployment_claim": True, "no_field_trial_success_claim": True,
        "no_live_provider_claim": True, "no_real_economic_work_claim": True,
        "known_debt_preserved": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_hashes": True,
        "proof_bundle_valid": True, "report_present": True,
        "fake_green_rejected": True, "secret_scan_clean": True,
        "claims_agi": False, "claims_consciousness": False,
        "claims_sentience": False, "claims_sovereignty": False,
        "claims_self_authorization": False, "claims_deployed": False,
        "claims_production_ready": False, "claims_field_trial_success": False,
        "claims_live_provider_enabled": False,
        "claims_real_economic_work": False, "claims_real_customer_work": False,
        "phase19_green_claimed": False, "phase24_full_overnight_green_claimed": False,
        "deployment_permission_claimed": False, "live_field_trial_authorized": False,
        "tool_authorized": False, "live_effect_created": False,
        "authority_mutated": False, "hg_local_touched": False,
        "web_browse_performed": False, "external_provider_enabled": False,
    }
    data.update(overrides)
    return data

def test_p71_gate_green():
    assert validate_p71_gate(_gate())["ok"] is True

def test_p71_gate_refuses_agi_claim():
    assert validate_p71_gate(_gate(claims_agi=True))["ok"] is False

def test_p71_gate_refuses_consciousness_claim():
    assert validate_p71_gate(_gate(claims_consciousness=True))["ok"] is False

def test_p71_gate_refuses_sovereignty_claim():
    assert validate_p71_gate(_gate(claims_sovereignty=True))["ok"] is False

def test_p71_gate_refuses_deployment():
    assert validate_p71_gate(_gate(deployment_permission_claimed=True))["ok"] is False

def test_p71_gate_requires_matrix():
    assert validate_p71_gate(_gate(capability_matrix_exists=False))["ok"] is False

def test_p71_gate_requires_debt():
    assert validate_p71_gate(_gate(known_debt_register_exists=False))["ok"] is False
