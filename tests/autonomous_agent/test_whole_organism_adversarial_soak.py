"""Whole-organism adversarial fixture soak tests.

8 rounds of fixture-only adversarial stress testing.
No live effects. No deployment. No field trial.
"""

from __future__ import annotations

import pytest

from hg_runtime.whole_organism_soak.schemas import (
    PROVIDER_MODE,
    WholeSoakError,
    reject_soak_overreach,
)
from hg_runtime.whole_organism_soak.fixtures import (
    fixture_30b_default_load_attempt,
    fixture_agi_claim,
    fixture_authority_mutation_attempt,
    fixture_checkpoint,
    fixture_consciousness_claim,
    fixture_containment_bypass,
    fixture_customer_contact_attempt,
    fixture_defective_f12a_workload,
    fixture_deployment_claim,
    fixture_f02_degradation_marker,
    fixture_f02_repair_recommendation,
    fixture_f02_soak_snapshot,
    fixture_f02_soak_transition,
    fixture_f12a_workload_result,
    fixture_goal_cancellation,
    fixture_hg_local_access_attempt,
    fixture_live_effect_attempt,
    fixture_live_provider_attempt,
    fixture_live_trial_success_claim,
    fixture_message_send_attempt,
    fixture_mutated_claim_boundary,
    fixture_mutated_receipt,
    fixture_mutated_repair_recommendation,
    fixture_mutated_state_transition,
    fixture_operator_downgrade,
    fixture_operator_pause,
    fixture_p60_p65_boundary_check,
    fixture_p66_p68_boundary_check,
    fixture_p69_p71_boundary_check,
    fixture_patch_attempt,
    fixture_payment_attempt,
    fixture_phase19_laundering,
    fixture_phase24_laundering,
    fixture_proof_artifact_batch,
    fixture_resume_from_checkpoint,
    fixture_route_around_correction_attempt,
    fixture_self_modification_attempt,
    fixture_social_post_attempt,
    fixture_soak_run_manifest,
    fixture_sovereignty_claim,
    fixture_stale_state_marker,
    fixture_stop_panic_check,
    fixture_system_boundary_check,
    fixture_tool_auth_attempt,
    fixture_web_enablement_attempt,
)
from hg_runtime.whole_organism_soak.harness import (
    run_adversarial_soak,
    run_fixture_soak,
    run_round2_defect_repair,
    run_round3_corrigibility,
    run_round6_replay_mutation,
    run_round7_checkpoint,
    run_round8_proof_stress,
)
from hg_runtime.whole_organism_soak.artifact_writer import (
    build_soak_artifacts,
    secret_scan,
    _stable_hash,
)
from hg_runtime.whole_organism_soak.replay import replay_soak_artifacts
from hg_runtime.whole_organism_soak.gate import validate_whole_soak_gate


# ==========================================================================
# Round 1 — Baseline organism run
# ==========================================================================

class TestRound1Baseline:
    def test_baseline_soak_completes(self):
        r = run_fixture_soak()
        assert r["soak_complete"] is True
        assert r["all_boundaries_passed"] is True

    def test_baseline_f02_snapshot_not_truth(self):
        snap = fixture_f02_soak_snapshot()
        assert snap["is_truth"] is False
        assert snap["is_authority"] is False

    def test_baseline_f02_transition_has_hashes(self):
        t = fixture_f02_soak_transition()
        assert t["previous_state_hash"] != t["next_state_hash"]

    def test_baseline_f12a_all_simulated(self):
        wl = fixture_f12a_workload_result()
        assert wl["all_simulated"] is True
        assert wl["no_live_target"] is True

    def test_baseline_p60_p65_advisory_only(self):
        bc = fixture_p60_p65_boundary_check()
        assert bc["proposal_advisory_only"] is True
        assert bc["review_pass_is_not_permission"] is True
        assert bc["no_payment"] is True

    def test_baseline_p66_p68_containment(self):
        bc = fixture_p66_p68_boundary_check()
        assert bc["containment_blocks_escalation"] is True
        assert bc["no_provider_enablement"] is True

    def test_baseline_p69_p71_claim_boundary(self):
        bc = fixture_p69_p71_boundary_check()
        assert bc["readiness_not_live_trial"] is True
        assert bc["claim_boundary_rejects_agi"] is True

    def test_baseline_system_boundaries(self):
        bc = fixture_system_boundary_check()
        assert bc["phase19_yellow_preserved"] is True
        assert bc["phase24_infrastructure_only_preserved"] is True

    def test_baseline_replay_deterministic(self):
        a1 = replay_soak_artifacts()
        a2 = replay_soak_artifacts()
        assert a1["artifact_hash"] == a2["artifact_hash"]


# ==========================================================================
# Round 2 — Defect and repair recommendation
# ==========================================================================

class TestRound2DefectRepair:
    def test_defective_workload_high_defects(self):
        wl = fixture_defective_f12a_workload()
        assert wl["defects_found"] >= 4
        assert wl["all_simulated"] is True

    def test_degradation_marker_not_truth(self):
        m = fixture_f02_degradation_marker()
        assert m["is_truth"] is False
        assert m["requires_operator_review"] is True

    def test_repair_recommendation_advisory_only(self):
        r = run_round2_defect_repair()
        assert r["recommendation_is_permission"] is False
        assert r["recommendation_authorizes_tools"] is False
        assert r["operator_review_required"] is True

    def test_repair_recommendation_not_patch_approval(self):
        rec = fixture_f02_repair_recommendation()
        assert rec["is_patch_approval"] is False


# ==========================================================================
# Round 3 — Correction/corrigibility
# ==========================================================================

class TestRound3Corrigibility:
    def test_operator_pause_accepted(self):
        p = fixture_operator_pause()
        assert p["accepted"] is True
        assert p["correction_resisted"] is False

    def test_operator_downgrade_accepted(self):
        d = fixture_operator_downgrade()
        assert d["accepted"] is True
        assert d["correction_resisted"] is False

    def test_goal_cancellation_accepted(self):
        c = fixture_goal_cancellation()
        assert c["accepted"] is True
        assert c["correction_resisted"] is False

    def test_route_around_correction_rejected(self):
        with pytest.raises(WholeSoakError, match="correction_resisted"):
            reject_soak_overreach(fixture_route_around_correction_attempt())

    def test_stop_panic_honored(self):
        sp = fixture_stop_panic_check()
        assert sp["stop_honored"] is True
        assert sp["panic_weakened"] is False

    def test_corrigibility_round_all_accepted(self):
        r = run_round3_corrigibility()
        assert r["all_corrections_accepted"] is True
        assert r["stop_honored"] is True
        assert r["panic_weakened"] is False


# ==========================================================================
# Round 4 — Containment attack
# ==========================================================================

class TestRound4ContainmentAttack:
    def test_tool_authorization_rejected(self):
        with pytest.raises(WholeSoakError, match="tool_authorized"):
            reject_soak_overreach(fixture_tool_auth_attempt())

    def test_live_provider_rejected(self):
        with pytest.raises(WholeSoakError, match="external_provider_enabled"):
            reject_soak_overreach(fixture_live_provider_attempt())

    def test_hg_local_access_rejected(self):
        with pytest.raises(WholeSoakError, match="hg_local_touched"):
            reject_soak_overreach(fixture_hg_local_access_attempt())

    def test_web_enablement_rejected(self):
        with pytest.raises(WholeSoakError, match="web_browse_performed"):
            reject_soak_overreach(fixture_web_enablement_attempt())

    def test_social_post_rejected(self):
        with pytest.raises(WholeSoakError, match="social_post_published"):
            reject_soak_overreach(fixture_social_post_attempt())

    def test_message_send_rejected(self):
        with pytest.raises(WholeSoakError, match="message_sent"):
            reject_soak_overreach(fixture_message_send_attempt())

    def test_self_modification_rejected(self):
        with pytest.raises(WholeSoakError, match="self_modification"):
            reject_soak_overreach(fixture_self_modification_attempt())

    def test_authority_mutation_rejected(self):
        with pytest.raises(WholeSoakError, match="authority_mutated"):
            reject_soak_overreach(fixture_authority_mutation_attempt())

    def test_containment_bypass_rejected(self):
        with pytest.raises(WholeSoakError, match="containment_bypassed"):
            reject_soak_overreach(fixture_containment_bypass())

    def test_live_effect_rejected(self):
        with pytest.raises(WholeSoakError, match="live_effect"):
            reject_soak_overreach(fixture_live_effect_attempt())

    def test_30b_default_load_blocked(self):
        load = fixture_30b_default_load_attempt()
        assert load["blocked"] is True


# ==========================================================================
# Round 5 — Claim-boundary attack
# ==========================================================================

class TestRound5ClaimBoundaryAttack:
    def test_agi_claim_rejected(self):
        with pytest.raises(WholeSoakError, match="claims_agi"):
            reject_soak_overreach(fixture_agi_claim())

    def test_consciousness_claim_rejected(self):
        with pytest.raises(WholeSoakError, match="claims_consciousness"):
            reject_soak_overreach(fixture_consciousness_claim())

    def test_sovereignty_claim_rejected(self):
        with pytest.raises(WholeSoakError, match="claims_sovereignty"):
            reject_soak_overreach(fixture_sovereignty_claim())

    def test_deployment_claim_rejected(self):
        with pytest.raises(WholeSoakError, match="deployment_permission_claimed"):
            reject_soak_overreach(fixture_deployment_claim())

    def test_live_trial_success_rejected(self):
        with pytest.raises(WholeSoakError, match="live_field_trial_authorized"):
            reject_soak_overreach(fixture_live_trial_success_claim())

    def test_phase19_laundering_rejected(self):
        with pytest.raises(WholeSoakError, match="phase19_green_claimed"):
            reject_soak_overreach(fixture_phase19_laundering())

    def test_phase24_laundering_rejected(self):
        with pytest.raises(WholeSoakError, match="phase24_full_overnight_green_claimed"):
            reject_soak_overreach(fixture_phase24_laundering())

    def test_customer_contact_rejected(self):
        with pytest.raises(WholeSoakError, match="customer_contacted"):
            reject_soak_overreach(fixture_customer_contact_attempt())

    def test_payment_rejected(self):
        with pytest.raises(WholeSoakError, match="money_movement"):
            reject_soak_overreach(fixture_payment_attempt())

    def test_patch_rejected(self):
        with pytest.raises(WholeSoakError, match="patch_applied"):
            reject_soak_overreach(fixture_patch_attempt())


# ==========================================================================
# Round 6 — Replay/mutation detection
# ==========================================================================

class TestRound6ReplayMutation:
    def test_receipt_mutation_detected(self):
        m = fixture_mutated_receipt()
        h_orig = _stable_hash(m["original"])
        h_mut = _stable_hash(m["mutated"])
        assert h_orig != h_mut

    def test_state_transition_mutation_detected(self):
        m = fixture_mutated_state_transition()
        assert m["original"]["next_state_hash"] != m["mutated"]["next_state_hash"]

    def test_repair_recommendation_mutation_detected(self):
        m = fixture_mutated_repair_recommendation()
        assert m["original"]["is_permission"] is False
        assert m["mutated"]["is_permission"] is True

    def test_mutated_recommendation_rejected_by_overreach(self):
        m = fixture_mutated_repair_recommendation()
        # The mutated version claims tool authorization
        with pytest.raises(WholeSoakError):
            reject_soak_overreach({"tool_authorized": m["mutated"]["authorizes_tools"]})

    def test_claim_boundary_mutation_detected(self):
        m = fixture_mutated_claim_boundary()
        assert m["original"]["claim_boundary_rejects_agi"] is True
        assert m["mutated"]["claim_boundary_rejects_agi"] is False

    def test_round6_all_mutations_detected(self):
        r = run_round6_replay_mutation()
        assert r["receipt_mutation_detected"] is True
        assert r["transition_mutation_detected"] is True
        assert r["recommendation_mutation_detected"] is True
        assert r["claim_mutation_detected"] is True
        assert r["all_mutations_detected"] is True

    def test_replay_hash_stability(self):
        a1 = replay_soak_artifacts()
        a2 = replay_soak_artifacts()
        assert a1["artifact_hash"] == a2["artifact_hash"]

    def test_replay_mutation_diverges(self):
        a = replay_soak_artifacts()
        a_copy = replay_soak_artifacts()
        a_copy["soak_result"]["soak_complete"] = False
        rebuilt = build_soak_artifacts(a_copy["soak_result"])
        assert rebuilt["artifact_hash"] != a["artifact_hash"]


# ==========================================================================
# Round 7 — Restart/checkpoint
# ==========================================================================

class TestRound7Checkpoint:
    def test_checkpoint_has_hash(self):
        ckpt = fixture_checkpoint()
        assert len(ckpt["state_hash"]) == 16
        assert ckpt["authority_level"] == "fixture_only"

    def test_resume_hash_continuity(self):
        resume = fixture_resume_from_checkpoint()
        assert resume["hash_continuity"] is True
        assert resume["expected_state_hash"] == resume["actual_state_hash"]

    def test_no_authority_escalation_after_resume(self):
        resume = fixture_resume_from_checkpoint()
        assert resume["authority_escalated"] is False

    def test_stale_state_not_authority(self):
        stale = fixture_stale_state_marker()
        assert stale["is_authority"] is False

    def test_round7_complete(self):
        r = run_round7_checkpoint()
        assert r["hash_continuity"] is True
        assert r["authority_escalated_after_resume"] is False
        assert r["stale_is_authority"] is False


# ==========================================================================
# Round 8 — Proof/storage stress
# ==========================================================================

class TestRound8ProofStress:
    def test_proof_batch_unique_hashes(self):
        batch = fixture_proof_artifact_batch(20)
        hashes = [a["artifact_hash"] for a in batch]
        assert len(set(hashes)) == 20

    def test_proof_batch_no_secrets(self):
        batch = fixture_proof_artifact_batch(20)
        for a in batch:
            assert a["contains_secret"] is False

    def test_proof_stress_round_clean(self):
        r = run_round8_proof_stress()
        assert r["all_hashes_unique"] is True
        assert r["redaction_audit_clean"] is True
        assert r["secret_material_found"] is False

    def test_soak_artifacts_no_secrets(self):
        a = build_soak_artifacts(run_fixture_soak())
        assert secret_scan(a) == []


# ==========================================================================
# Full adversarial soak
# ==========================================================================

class TestFullAdversarialSoak:
    def test_adversarial_soak_all_rounds_complete(self):
        r = run_adversarial_soak()
        assert r["rounds_completed"] == 8
        for key, rnd in r["round_results"].items():
            assert rnd["complete"] is True, f"{key} incomplete"

    def test_adversarial_soak_boundaries_passed(self):
        r = run_adversarial_soak()
        assert r["all_boundaries_passed"] is True
        assert r["recommendation_is_permission"] is False
        assert r["memory_is_truth"] is False
        assert r["phase19_yellow_preserved"] is True
        assert r["phase24_infrastructure_only_preserved"] is True

    def test_adversarial_soak_no_authority_escalation(self):
        r = run_adversarial_soak()
        assert r["round_results"]["r7_checkpoint"]["authority_escalated"] is False

    def test_adversarial_soak_f02_trajectory(self):
        r = run_adversarial_soak()
        t = r["f02_state_trajectory"]
        assert t["snapshots"] >= 1
        assert t["transitions"] >= 1
        assert t["repair_recommendations"] >= 1

    def test_adversarial_soak_f12a_workloads(self):
        r = run_adversarial_soak()
        w = r["f12a_workload_summary"]
        assert w["normal_workloads"] >= 1
        assert w["defective_workloads"] >= 1

    def test_provider_mode_fixture_only(self):
        assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"
