"""Local Inference QA Orchestrator tests.

Tests use mocked fixtures so CI does not require LM Studio.
Model output is not truth. Local inference is not authority.
Model confidence is not evidence. Model willingness is not permission.
"""

from __future__ import annotations

import pytest

from hg_runtime.local_inference_qa_orchestrator.schemas import (
    QAOrchestratorError,
    _stable_hash,
    reject_qa_overreach,
)
from hg_runtime.local_inference_qa_orchestrator.orchestrator import (
    record_provider_unavailable,
    run_qa_orchestrator,
    validate_loopback,
)
from hg_runtime.local_inference_qa_orchestrator.prompt_builder import (
    BOUNDARY_REMINDER,
    build_boundary_attack_prompt,
    build_hype_claim_rejection_prompt,
    build_proof_audit_prompt,
    build_provider_unavailable_prompt,
    build_soak_recommendation_prompt,
    build_test_gap_prompt,
)
from hg_runtime.local_inference_qa_orchestrator.response_parser import (
    check_response_boundary,
    extract_hypothesis,
    extract_proof_audit_summary,
    extract_repair_recommendation,
    extract_test_suggestion,
    parse_model_response,
)
from hg_runtime.local_inference_qa_orchestrator.artifact_writer import (
    build_qa_artifacts,
    secret_scan,
)
from hg_runtime.local_inference_qa_orchestrator.replay import (
    reject_mutation,
    replay_qa_artifacts,
    verify_replay_hashes,
)
from hg_runtime.local_inference_qa_orchestrator.gate import validate_qa_gate
from hg_runtime.local_inference_qa_orchestrator.fixtures import (
    fixture_boundary_attack_prompt,
    fixture_debt_register,
    fixture_f02_summary,
    fixture_f12a_summary,
    fixture_hype_claim_text,
    fixture_p71_claim_boundary_summary,
    fixture_proof_bundle_summary,
    fixture_soak_summary,
    qa_run_manifest,
)

MOCK_ENDPOINT = "http://127.0.0.1:1234/v1"
MOCK_MODEL = "qwen2.5-0.5b-instruct"


# ==========================================================================
# Endpoint validation
# ==========================================================================

class TestEndpointValidation:
    def test_local_qa_requires_loopback_endpoint(self):
        result = validate_loopback(MOCK_ENDPOINT)
        assert result["is_loopback"] is True

    def test_local_qa_rejects_non_loopback_endpoint(self):
        with pytest.raises(QAOrchestratorError, match="Non-loopback"):
            validate_loopback("http://api.openai.com/v1")

    def test_local_qa_refuses_remote_provider_fallback(self):
        rec = record_provider_unavailable(MOCK_ENDPOINT, "timeout")
        assert rec["remote_fallback_used"] is False
        assert rec["fallback_used"] is False

    def test_local_qa_records_provider_unavailable_honestly(self):
        rec = record_provider_unavailable(MOCK_ENDPOINT, "connection refused")
        assert rec["available"] is False
        assert rec["reason"] == "connection refused"


# ==========================================================================
# Prompt building
# ==========================================================================

class TestPromptBuilding:
    def test_local_qa_builds_boundary_reminded_prompts(self):
        prompt = build_proof_audit_prompt(fixture_proof_bundle_summary())
        assert prompt["boundary_reminder_included"] is True
        assert BOUNDARY_REMINDER in prompt["prompt_text"]
        assert prompt["contains_secrets"] is False
        assert prompt["targets_live_system"] is False
        assert prompt["authorizes_tools"] is False

    def test_test_gap_prompt_has_boundary(self):
        prompt = build_test_gap_prompt(fixture_soak_summary())
        assert BOUNDARY_REMINDER in prompt["prompt_text"]

    def test_boundary_attack_prompt_has_boundary(self):
        prompt = build_boundary_attack_prompt(fixture_boundary_attack_prompt())
        assert BOUNDARY_REMINDER in prompt["prompt_text"]

    def test_soak_recommendation_prompt_has_boundary(self):
        prompt = build_soak_recommendation_prompt(fixture_f02_summary(), fixture_f12a_summary())
        assert BOUNDARY_REMINDER in prompt["prompt_text"]

    def test_hype_claim_prompt_has_boundary(self):
        prompt = build_hype_claim_rejection_prompt(fixture_hype_claim_text())
        assert BOUNDARY_REMINDER in prompt["prompt_text"]

    def test_provider_unavailable_prompt_has_boundary(self):
        prompt = build_provider_unavailable_prompt()
        assert BOUNDARY_REMINDER in prompt["prompt_text"]


# ==========================================================================
# Model response recording
# ==========================================================================

class TestModelResponseRecording:
    def test_local_qa_records_model_response_receipts(self):
        prompt = build_proof_audit_prompt(fixture_proof_bundle_summary())
        resp = parse_model_response(prompt, "No gaps found.", MOCK_MODEL)
        assert resp["prompt_id"] == prompt["prompt_id"]
        assert resp["model_id"] == MOCK_MODEL
        assert resp["response_hash"] is not None

    def test_local_qa_output_is_not_truth(self):
        prompt = build_proof_audit_prompt(fixture_proof_bundle_summary())
        resp = parse_model_response(prompt, "No gaps.", MOCK_MODEL)
        assert resp["output_not_truth"] is True

    def test_local_qa_inference_is_not_authority(self):
        prompt = build_proof_audit_prompt(fixture_proof_bundle_summary())
        resp = parse_model_response(prompt, "No gaps.", MOCK_MODEL)
        assert resp["local_inference_not_authority"] is True

    def test_local_qa_confidence_is_not_evidence(self):
        prompt = build_proof_audit_prompt(fixture_proof_bundle_summary())
        resp = parse_model_response(prompt, "I am 99% confident there are no gaps.", MOCK_MODEL)
        assert resp["output_not_truth"] is True
        assert resp["local_inference_not_authority"] is True

    def test_local_qa_willingness_is_not_permission(self):
        prompt = build_proof_audit_prompt(fixture_proof_bundle_summary())
        resp = parse_model_response(prompt, "I am willing to help.", MOCK_MODEL)
        assert resp["willingness_not_permission"] is True


# ==========================================================================
# Hypothesis extraction
# ==========================================================================

class TestHypothesisExtraction:
    def test_local_qa_creates_hypothesis(self):
        prompt = build_boundary_attack_prompt("test attack")
        resp = parse_model_response(prompt, "Timing side-channel possible.", MOCK_MODEL)
        hyp = extract_hypothesis(resp, "boundary_layer", "timing side-channel")
        assert hyp["hypothesis_id"].startswith("hyp-")
        assert hyp["affected_subsystem"] == "boundary_layer"
        assert hyp["operator_review_required"] is True

    def test_local_qa_hypothesis_is_not_evidence_by_itself(self):
        prompt = build_boundary_attack_prompt("test attack")
        resp = parse_model_response(prompt, "Possible issue.", MOCK_MODEL)
        hyp = extract_hypothesis(resp, "boundary_layer", "possible issue")
        assert hyp["hypothesis_is_not_evidence_by_itself"] is True
        assert hyp["output_not_truth"] is True


# ==========================================================================
# Test suggestion extraction
# ==========================================================================

class TestTestSuggestionExtraction:
    def test_local_qa_creates_test_suggestion(self):
        prompt = build_test_gap_prompt(fixture_soak_summary())
        resp = parse_model_response(prompt, "Add timeout test.", MOCK_MODEL)
        ts = extract_test_suggestion(resp, "tests/autonomous_agent", "timeout boundary")
        assert ts["suggested_test_id"].startswith("ts-")
        assert ts["operator_review_required"] is True

    def test_local_qa_test_suggestion_is_not_authority(self):
        prompt = build_test_gap_prompt(fixture_soak_summary())
        resp = parse_model_response(prompt, "Add timeout test.", MOCK_MODEL)
        ts = extract_test_suggestion(resp, "tests/autonomous_agent", "timeout boundary")
        assert ts["suggestion_is_not_test_authority"] is True
        assert ts["output_not_truth"] is True


# ==========================================================================
# Repair recommendation extraction
# ==========================================================================

class TestRepairRecommendationExtraction:
    def test_local_qa_creates_repair_recommendation(self):
        prompt = build_soak_recommendation_prompt(fixture_f02_summary(), fixture_f12a_summary())
        resp = parse_model_response(prompt, "Add state transition stress.", MOCK_MODEL)
        rec = extract_repair_recommendation(resp, "f02_state_space", "state transition stress")
        assert rec["recommendation_id"].startswith("rec-")
        assert rec["operator_review_required"] is True
        assert rec["advisory_only"] is True

    def test_local_qa_repair_recommendation_is_not_permission(self):
        prompt = build_soak_recommendation_prompt(fixture_f02_summary(), fixture_f12a_summary())
        resp = parse_model_response(prompt, "Fix it.", MOCK_MODEL)
        rec = extract_repair_recommendation(resp, "f02", "fix")
        assert rec["is_permission"] is False

    def test_local_qa_repair_recommendation_is_not_patch_approval(self):
        prompt = build_soak_recommendation_prompt(fixture_f02_summary(), fixture_f12a_summary())
        resp = parse_model_response(prompt, "Fix it.", MOCK_MODEL)
        rec = extract_repair_recommendation(resp, "f02", "fix")
        assert rec["is_patch_approval"] is False

    def test_local_qa_repair_recommendation_does_not_authorize_tools(self):
        prompt = build_soak_recommendation_prompt(fixture_f02_summary(), fixture_f12a_summary())
        resp = parse_model_response(prompt, "Fix it.", MOCK_MODEL)
        rec = extract_repair_recommendation(resp, "f02", "fix")
        assert rec["authorizes_tools"] is False


# ==========================================================================
# Proof audit
# ==========================================================================

class TestProofAudit:
    def test_local_qa_creates_proof_audit_summary(self):
        prompt = build_proof_audit_prompt(fixture_proof_bundle_summary())
        resp = parse_model_response(prompt, "No gaps found.", MOCK_MODEL)
        audit = extract_proof_audit_summary(resp, "HG-ADVERSARIAL-SOAK")
        assert audit["proof_bundle_inspected"] == "HG-ADVERSARIAL-SOAK"
        assert audit["status"] == "advisory"
        assert audit["operator_review_required"] is True

    def test_local_qa_proof_audit_does_not_mutate_proofs(self):
        prompt = build_proof_audit_prompt(fixture_proof_bundle_summary())
        resp = parse_model_response(prompt, "No gaps found.", MOCK_MODEL)
        audit = extract_proof_audit_summary(resp, "HG-ADVERSARIAL-SOAK")
        assert audit["proof_mutated"] is False


# ==========================================================================
# Boundary attacks
# ==========================================================================

class TestBoundaryAttacks:
    def test_local_qa_cannot_apply_patches(self):
        with pytest.raises(QAOrchestratorError, match="patch_applied"):
            reject_qa_overreach({"patch_applied": True})

    def test_local_qa_cannot_modify_authority(self):
        with pytest.raises(QAOrchestratorError, match="authority_mutated"):
            reject_qa_overreach({"authority_mutated": True})

    def test_local_qa_cannot_mark_tests_green(self):
        with pytest.raises(QAOrchestratorError, match="green_inferred_from_model_output"):
            reject_qa_overreach({"green_inferred_from_model_output": True})

    def test_local_qa_cannot_mark_phase19_green(self):
        with pytest.raises(QAOrchestratorError, match="phase19_green_claimed"):
            reject_qa_overreach({"phase19_green_claimed": True})

    def test_local_qa_cannot_mark_phase24_full_overnight_green(self):
        with pytest.raises(QAOrchestratorError, match="phase24_full_overnight_green_claimed"):
            reject_qa_overreach({"phase24_full_overnight_green_claimed": True})

    def test_local_qa_cannot_enable_live_provider(self):
        with pytest.raises(QAOrchestratorError, match="external_provider_enabled"):
            reject_qa_overreach({"external_provider_enabled": True})

    def test_local_qa_cannot_create_live_effect(self):
        with pytest.raises(QAOrchestratorError, match="live_effect"):
            reject_qa_overreach({"live_effect": True})

    def test_local_qa_cannot_touch_hg_local(self):
        with pytest.raises(QAOrchestratorError, match="hg_local_touched"):
            reject_qa_overreach({"hg_local_touched": True})

    def test_local_qa_cannot_auto_create_tests(self):
        with pytest.raises(QAOrchestratorError, match="test_created_from_model_output"):
            reject_qa_overreach({"test_created_from_model_output": True})

    def test_response_boundary_rejects_tool_auth_text(self):
        with pytest.raises(QAOrchestratorError):
            check_response_boundary("I will authorize the tool for you")

    def test_response_boundary_rejects_green_inference(self):
        with pytest.raises(QAOrchestratorError):
            check_response_boundary("I will mark this as green and set it to pass")

    def test_response_boundary_safe_text_passes(self):
        result = check_response_boundary("Tests completed successfully.")
        assert result["checked"] is True
        assert result["violations_found"] == 0


# ==========================================================================
# Secrets and replay
# ==========================================================================

class TestSecretsAndReplay:
    def test_local_qa_no_secret_material_in_artifacts(self):
        result = run_qa_orchestrator()
        artifacts = build_qa_artifacts(result)
        secrets = secret_scan(artifacts)
        assert secrets == []

    def test_local_qa_replay_preserves_hashes(self):
        run1 = replay_qa_artifacts()
        run2 = replay_qa_artifacts()
        check = verify_replay_hashes(run1, run2)
        assert check["hashes_match"] is True

    def test_local_qa_replay_rejects_mutation(self):
        original = {"data": "original", "hash": "abc"}
        mutated = {"data": "mutated", "hash": "def"}
        result = reject_mutation(original, mutated)
        assert result["mutation_detected"] is True

    def test_local_qa_fake_green_rejected(self):
        with pytest.raises(QAOrchestratorError, match="green_inferred_from_model_output"):
            reject_qa_overreach({"green_inferred_from_model_output": True})


# ==========================================================================
# Gate validation
# ==========================================================================

class TestGateValidation:
    def _passing_gate_input(self):
        return {
            "qa_complete": True,
            "receipts_present": True,
            "non_truth_boundary": True,
            "no_patch_application": True,
            "no_tool_authorization": True,
            "replay_preserves_hashes": True,
            "proof_bundle_valid": True,
            "report_present": True,
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
            "secret_scan_clean": True,
        }

    def test_local_qa_gate_requires_receipts(self):
        inp = self._passing_gate_input()
        inp["receipts_present"] = False
        result = validate_qa_gate(inp)
        assert result["ok"] is False
        assert "receipts_required" in result["failures"]

    def test_local_qa_gate_requires_non_truth_boundary(self):
        inp = self._passing_gate_input()
        inp["non_truth_boundary"] = False
        result = validate_qa_gate(inp)
        assert result["ok"] is False
        assert "non_truth_required" in result["failures"]

    def test_local_qa_gate_requires_no_patch_application(self):
        inp = self._passing_gate_input()
        inp["no_patch_application"] = False
        result = validate_qa_gate(inp)
        assert result["ok"] is False
        assert "no_patch_required" in result["failures"]

    def test_local_qa_gate_requires_no_tool_authorization(self):
        inp = self._passing_gate_input()
        inp["no_tool_authorization"] = False
        result = validate_qa_gate(inp)
        assert result["ok"] is False
        assert "no_tool_auth_required" in result["failures"]

    def test_gate_rejects_tool_authorized(self):
        inp = self._passing_gate_input()
        inp["tool_authorized"] = True
        result = validate_qa_gate(inp)
        assert result["ok"] is False
        assert "tool_authorized" in result["failures"]

    def test_gate_rejects_patch_applied(self):
        inp = self._passing_gate_input()
        inp["patch_applied"] = True
        result = validate_qa_gate(inp)
        assert result["ok"] is False

    def test_gate_passes_clean_input(self):
        inp = self._passing_gate_input()
        result = validate_qa_gate(inp)
        assert result["ok"] is True
        assert result["failures"] == []


# ==========================================================================
# Full orchestrator
# ==========================================================================

class TestFullOrchestrator:
    def test_orchestrator_runs_all_workloads(self):
        result = run_qa_orchestrator()
        assert result["qa_complete"] is True
        assert len(result["prompts"]) == 5
        assert len(result["receipts"]) == 5
        assert len(result["hypotheses"]) >= 1
        assert len(result["test_suggestions"]) >= 1
        assert len(result["repair_recommendations"]) >= 1
        assert len(result["proof_audits"]) >= 1

    def test_orchestrator_no_patches(self):
        result = run_qa_orchestrator()
        assert result["patches_applied"] is False

    def test_orchestrator_no_auto_tests(self):
        result = run_qa_orchestrator()
        assert result["tests_auto_created"] is False

    def test_orchestrator_no_tools(self):
        result = run_qa_orchestrator()
        assert result["tools_authorized"] is False

    def test_orchestrator_no_live_effects(self):
        result = run_qa_orchestrator()
        assert result["live_effects"] is False

    def test_orchestrator_phases_preserved(self):
        result = run_qa_orchestrator()
        assert result["phase19_yellow_preserved"] is True
        assert result["phase24_infrastructure_only_preserved"] is True
