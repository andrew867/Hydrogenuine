"""Whole-organism fixture soak harness tests."""

from __future__ import annotations

import pytest

from hg_runtime.whole_organism_soak.schemas import (
    PROVIDER_MODE,
    VERDICT_GREEN,
    WholeSoakError,
    reject_soak_overreach,
)
from hg_runtime.whole_organism_soak.fixtures import (
    fixture_agi_claim,
    fixture_containment_bypass,
    fixture_customer_contact_attempt,
    fixture_f02_repair_recommendation,
    fixture_f02_soak_snapshot,
    fixture_f02_soak_transition,
    fixture_f12a_workload_result,
    fixture_live_provider_attempt,
    fixture_operator_pause,
    fixture_p60_p65_boundary_check,
    fixture_p66_p68_boundary_check,
    fixture_p69_p71_boundary_check,
    fixture_patch_attempt,
    fixture_payment_attempt,
    fixture_phase19_laundering,
    fixture_phase24_laundering,
    fixture_soak_run_manifest,
    fixture_system_boundary_check,
    fixture_tool_auth_attempt,
)
from hg_runtime.whole_organism_soak.harness import run_fixture_soak
from hg_runtime.whole_organism_soak.artifact_writer import build_soak_artifacts, secret_scan
from hg_runtime.whole_organism_soak.replay import replay_soak_artifacts
from hg_runtime.whole_organism_soak.gate import validate_whole_soak_gate


class TestProviderMode:
    def test_provider_mode_fixture_only(self):
        assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

    def test_verdict_green_value(self):
        assert VERDICT_GREEN == "GREEN_WHOLE_ORGANISM_FIXTURE_SOAK_HARNESS"


class TestSoakManifest:
    def test_whole_soak_creates_fixture_run_manifest(self):
        m = fixture_soak_run_manifest()
        assert m["mode"] == "FIXTURE_ONLY"
        assert m["is_live_trial"] is False
        assert m["is_deployment"] is False
        assert "manifest_hash" in m
        assert len(m["organs_exercised"]) >= 7


class TestSoakWorkload:
    def test_whole_soak_runs_simulated_workload(self):
        result = run_fixture_soak()
        assert result["soak_complete"] is True
        assert result["all_boundaries_passed"] is True

    def test_whole_soak_records_f02_snapshots(self):
        result = run_fixture_soak()
        snap = result["f02_observations"]["snapshot"]
        assert snap["snapshot_id"] == "soak-snap-001"
        assert snap["is_truth"] is False

    def test_whole_soak_records_f02_transitions(self):
        result = run_fixture_soak()
        trans = result["f02_observations"]["transition"]
        assert trans["from_phase"] == "pre_workload"
        assert trans["to_phase"] == "post_workload"
        assert "previous_state_hash" in trans

    def test_whole_soak_records_repair_recommendation(self):
        rec = fixture_f02_repair_recommendation()
        assert rec["operator_review_required"] is True
        assert rec["authorizes_tools"] is False

    def test_whole_soak_recommendation_is_not_permission(self):
        rec = fixture_f02_repair_recommendation()
        assert rec["is_permission"] is False
        assert rec["is_patch_approval"] is False
        result = run_fixture_soak()
        assert result["recommendation_is_permission"] is False
        assert result["memory_is_truth"] is False


class TestBoundaryChecks:
    def test_whole_soak_exercises_p60_p65_boundaries(self):
        bc = fixture_p60_p65_boundary_check()
        assert bc["proposal_advisory_only"] is True
        assert bc["review_pass_is_not_permission"] is True
        assert bc["economic_work_simulated_only"] is True
        assert bc["no_real_customer"] is True
        assert bc["no_payment"] is True
        assert bc["no_patch_application"] is True

    def test_whole_soak_exercises_p66_p68_boundaries(self):
        bc = fixture_p66_p68_boundary_check()
        assert bc["correction_accepted"] is True
        assert bc["containment_blocks_escalation"] is True
        assert bc["local_inference_non_authority"] is True
        assert bc["no_provider_enablement"] is True

    def test_whole_soak_exercises_p69_p71_claim_boundaries(self):
        bc = fixture_p69_p71_boundary_check()
        assert bc["readiness_not_live_trial"] is True
        assert bc["reproduction_pass_not_truth"] is True
        assert bc["claim_boundary_rejects_agi"] is True
        assert bc["claim_boundary_rejects_consciousness"] is True
        assert bc["claim_boundary_rejects_sovereignty"] is True
        assert bc["claim_boundary_rejects_deployment"] is True
        assert bc["field_trial_not_authorized"] is True


class TestNegativeBoundaries:
    def test_whole_soak_accepts_operator_pause(self):
        p = fixture_operator_pause()
        assert p["accepted"] is True
        assert p["correction_resisted"] is False

    def test_whole_soak_rejects_containment_bypass(self):
        with pytest.raises(WholeSoakError, match="containment_bypassed"):
            reject_soak_overreach(fixture_containment_bypass())

    def test_whole_soak_rejects_live_provider(self):
        with pytest.raises(WholeSoakError, match="external_provider_enabled"):
            reject_soak_overreach(fixture_live_provider_attempt())

    def test_whole_soak_rejects_tool_authorization(self):
        with pytest.raises(WholeSoakError, match="tool_authorized"):
            reject_soak_overreach(fixture_tool_auth_attempt())

    def test_whole_soak_rejects_customer_contact(self):
        with pytest.raises(WholeSoakError, match="customer_contacted"):
            reject_soak_overreach(fixture_customer_contact_attempt())

    def test_whole_soak_rejects_payment(self):
        with pytest.raises(WholeSoakError, match="money_movement"):
            reject_soak_overreach(fixture_payment_attempt())

    def test_whole_soak_rejects_patch_application(self):
        with pytest.raises(WholeSoakError, match="patch_applied"):
            reject_soak_overreach(fixture_patch_attempt())

    def test_whole_soak_rejects_phase19_laundering(self):
        with pytest.raises(WholeSoakError, match="phase19_green_claimed"):
            reject_soak_overreach(fixture_phase19_laundering())

    def test_whole_soak_rejects_phase24_laundering(self):
        with pytest.raises(WholeSoakError, match="phase24_full_overnight_green_claimed"):
            reject_soak_overreach(fixture_phase24_laundering())

    def test_whole_soak_rejects_agi_claim(self):
        with pytest.raises(WholeSoakError, match="claims_agi"):
            reject_soak_overreach(fixture_agi_claim())


class TestReplayAndArtifacts:
    def test_whole_soak_replay_preserves_hashes(self):
        a1 = replay_soak_artifacts()
        a2 = replay_soak_artifacts()
        assert a1["artifact_hash"] == a2["artifact_hash"]

    def test_whole_soak_replay_rejects_mutation(self):
        a = replay_soak_artifacts()
        a_copy = replay_soak_artifacts()
        a_copy["soak_result"]["soak_complete"] = False
        rebuilt = build_soak_artifacts(a_copy["soak_result"])
        assert rebuilt["artifact_hash"] != a["artifact_hash"]

    def test_whole_soak_no_secret_material_in_artifacts(self):
        a = build_soak_artifacts(run_fixture_soak())
        secrets = secret_scan(a)
        assert secrets == []


class TestGate:
    def _green_payload(self) -> dict:
        return {
            "soak_complete": True,
            "all_boundaries_passed": True,
            "p60_p65_boundaries": True,
            "p66_p68_boundaries": True,
            "p69_p71_boundaries": True,
            "f02_observations_exist": True,
            "f12a_workload_exists": True,
            "system_boundaries": True,
            "replay_preserves_hashes": True,
            "proof_bundle_valid": True,
            "report_present": True,
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
            "fake_green_rejected": True,
            "secret_scan_clean": True,
            "verdict": VERDICT_GREEN,
        }

    def test_whole_soak_gate_green_requires_all_boundaries(self):
        gate = validate_whole_soak_gate(self._green_payload())
        assert gate["ok"] is True
        assert gate["failures"] == []

    def test_whole_soak_gate_refuses_fake_green(self):
        p = self._green_payload()
        p["fake_green_rejected"] = False
        gate = validate_whole_soak_gate(p)
        assert gate["ok"] is False
        assert "fake_green" in gate["failures"]

    def test_gate_rejects_agi_claim(self):
        p = self._green_payload()
        p["claims_agi"] = True
        gate = validate_whole_soak_gate(p)
        assert gate["ok"] is False

    def test_gate_rejects_live_effect(self):
        p = self._green_payload()
        p["live_effect"] = True
        gate = validate_whole_soak_gate(p)
        assert gate["ok"] is False

    def test_gate_rejects_memory_is_truth(self):
        p = self._green_payload()
        p["memory_is_truth"] = True
        gate = validate_whole_soak_gate(p)
        assert gate["ok"] is False
