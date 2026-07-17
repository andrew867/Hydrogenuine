"""Local LM Studio shadow soak tests.

Tests use mocked fixtures so CI does not require LM Studio.
Model output is not truth. Local inference is not authority.
Model willingness is not permission.
"""

from __future__ import annotations

import pytest

from hg_runtime.whole_organism_soak.schemas import WholeSoakError, reject_soak_overreach
from hg_runtime.whole_organism_soak.local_lm_studio_shadow import (
    ALLOWED_HOSTS,
    _stable_hash,
    check_boundary_rejection,
    create_provider_handshake,
    create_shadow_repair_recommendation,
    create_shadow_review_packet,
    create_simulated_work_artifact,
    generate_shadow_prompt,
    record_model_response,
    record_provider_unavailable,
    secret_scan_shadow_artifacts,
    validate_loopback_endpoint,
)

MOCK_MODEL = "qwen2.5-0.5b-instruct"
MOCK_ENDPOINT = "http://127.0.0.1:1234/v1"
MOCK_DRAFT = "Simulation completed in fixture mode. All boundaries held."
MOCK_REVIEW = "Draft is acceptable. Minor wording improvement suggested."
MOCK_REPAIR = "Add automatic fixture skip for unused soak phases."


# ==========================================================================
# Endpoint validation
# ==========================================================================

class TestEndpointValidation:
    def test_local_shadow_requires_loopback_endpoint(self):
        result = validate_loopback_endpoint(MOCK_ENDPOINT)
        assert result["is_loopback"] is True

    def test_local_shadow_rejects_non_loopback_endpoint(self):
        with pytest.raises(WholeSoakError, match="Non-loopback"):
            validate_loopback_endpoint("http://api.openai.com/v1")

    def test_rejects_remote_ip(self):
        with pytest.raises(WholeSoakError, match="Non-loopback"):
            validate_loopback_endpoint("http://192.168.1.1:1234/v1")

    def test_accepts_localhost(self):
        result = validate_loopback_endpoint("http://localhost:1234/v1")
        assert result["is_loopback"] is True


# ==========================================================================
# Provider handshake
# ==========================================================================

class TestProviderHandshake:
    def test_handshake_no_api_key(self):
        h = create_provider_handshake(MOCK_ENDPOINT, MOCK_MODEL)
        assert h["api_key_used"] is False

    def test_handshake_no_external_fallback(self):
        h = create_provider_handshake(MOCK_ENDPOINT, MOCK_MODEL)
        assert h["external_provider_fallback"] is False

    def test_handshake_output_not_truth(self):
        h = create_provider_handshake(MOCK_ENDPOINT, MOCK_MODEL)
        assert h["model_output_is_truth"] is False

    def test_handshake_inference_not_authority(self):
        h = create_provider_handshake(MOCK_ENDPOINT, MOCK_MODEL)
        assert h["local_inference_is_authority"] is False

    def test_handshake_willingness_not_permission(self):
        h = create_provider_handshake(MOCK_ENDPOINT, MOCK_MODEL)
        assert h["model_willingness_is_permission"] is False


# ==========================================================================
# Provider unavailability
# ==========================================================================

class TestProviderUnavailability:
    def test_local_shadow_records_provider_unavailable_honestly(self):
        rec = record_provider_unavailable(MOCK_ENDPOINT, "connection refused")
        assert rec["available"] is False
        assert rec["fallback_used"] is False
        assert rec["remote_fallback_used"] is False

    def test_local_shadow_refuses_remote_provider_fallback(self):
        rec = record_provider_unavailable(MOCK_ENDPOINT, "timeout")
        assert rec["remote_fallback_used"] is False


# ==========================================================================
# Model response recording
# ==========================================================================

class TestModelResponseRecording:
    def test_local_shadow_records_model_output_non_truth(self):
        prompt = generate_shadow_prompt("draft", "Write a report")
        resp = record_model_response(prompt, MOCK_DRAFT, MOCK_MODEL)
        assert resp["is_truth"] is False

    def test_local_shadow_records_local_inference_non_authority(self):
        prompt = generate_shadow_prompt("review", "Review this")
        resp = record_model_response(prompt, MOCK_REVIEW, MOCK_MODEL)
        assert resp["is_authority"] is False

    def test_local_shadow_model_willingness_is_not_permission(self):
        prompt = generate_shadow_prompt("repair", "Suggest fix")
        resp = record_model_response(prompt, MOCK_REPAIR, MOCK_MODEL)
        assert resp["is_permission"] is False
        assert resp["is_patch_approval"] is False


# ==========================================================================
# Simulated work artifacts
# ==========================================================================

class TestSimulatedWorkArtifacts:
    def test_local_shadow_generates_simulated_work_artifact(self):
        prompt = generate_shadow_prompt("draft", "Write report")
        resp = record_model_response(prompt, MOCK_DRAFT, MOCK_MODEL)
        art = create_simulated_work_artifact(resp)
        assert art["is_customer_work"] is False
        assert art["is_live_deliverable"] is False

    def test_local_shadow_artifact_is_not_customer_work(self):
        prompt = generate_shadow_prompt("draft", "Write report")
        resp = record_model_response(prompt, MOCK_DRAFT, MOCK_MODEL)
        art = create_simulated_work_artifact(resp)
        assert art["is_customer_work"] is False
        assert art["is_truth"] is False


# ==========================================================================
# Review packets
# ==========================================================================

class TestReviewPackets:
    def test_local_shadow_review_is_not_acceptance(self):
        prompt = generate_shadow_prompt("draft", "Write report")
        resp = record_model_response(prompt, MOCK_DRAFT, MOCK_MODEL)
        art = create_simulated_work_artifact(resp)
        review = create_shadow_review_packet(art, MOCK_REVIEW)
        assert review["is_customer_acceptance"] is False
        assert review["is_authority"] is False
        assert review["is_permission"] is False


# ==========================================================================
# Repair recommendations
# ==========================================================================

class TestRepairRecommendations:
    def test_local_shadow_repair_recommendation_is_not_patch_approval(self):
        prompt = generate_shadow_prompt("repair", "Suggest fix")
        resp = record_model_response(prompt, MOCK_REPAIR, MOCK_MODEL)
        rec = create_shadow_repair_recommendation(resp)
        assert rec["is_permission"] is False
        assert rec["is_patch_approval"] is False
        assert rec["authorizes_tools"] is False
        assert rec["operator_review_required"] is True
        assert rec["advisory_only"] is True


# ==========================================================================
# Boundary attacks
# ==========================================================================

class TestBoundaryAttacks:
    def test_local_shadow_rejects_tool_authorization(self):
        with pytest.raises(WholeSoakError, match="tool_authorized"):
            reject_soak_overreach({"tool_authorized": True})

    def test_local_shadow_rejects_hg_local_access(self):
        with pytest.raises(WholeSoakError, match="hg_local_touched"):
            reject_soak_overreach({"hg_local_touched": True})

    def test_local_shadow_rejects_live_provider_enablement(self):
        with pytest.raises(WholeSoakError, match="external_provider_enabled"):
            reject_soak_overreach({"external_provider_enabled": True})

    def test_local_shadow_rejects_social_posting(self):
        with pytest.raises(WholeSoakError, match="social_post_published"):
            reject_soak_overreach({"social_post_published": True})

    def test_local_shadow_rejects_payment(self):
        with pytest.raises(WholeSoakError, match="money_movement"):
            reject_soak_overreach({"money_movement": True})

    def test_local_shadow_rejects_agi_claim(self):
        with pytest.raises(WholeSoakError, match="claims_agi"):
            reject_soak_overreach({"claims_agi": True})

    def test_boundary_rejection_detects_tool_auth_text(self):
        with pytest.raises(WholeSoakError):
            check_boundary_rejection("I will authorize the tool for you")

    def test_boundary_rejection_safe_text_passes(self):
        result = check_boundary_rejection("Tests completed successfully.")
        assert result["checked"] is True
        assert result["violations_found"] == 0


# ==========================================================================
# Replay and secrets
# ==========================================================================

class TestReplayAndSecrets:
    def test_local_shadow_replay_preserves_hashes(self):
        prompt = generate_shadow_prompt("draft", "Write report")
        h1 = prompt["prompt_hash"]
        prompt2 = generate_shadow_prompt("draft", "Write report")
        h2 = prompt2["prompt_hash"]
        assert h1 == h2

    def test_local_shadow_no_secret_material_in_artifacts(self):
        prompt = generate_shadow_prompt("draft", "Write report")
        resp = record_model_response(prompt, MOCK_DRAFT, MOCK_MODEL)
        art = create_simulated_work_artifact(resp)
        secrets = secret_scan_shadow_artifacts([art])
        assert secrets == []
