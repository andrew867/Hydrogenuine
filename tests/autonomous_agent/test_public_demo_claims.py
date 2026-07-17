"""Tests for public demo claim checker."""

from __future__ import annotations

import pytest


def test_claims_checker_rejects_agi_claim():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("Hydrogenuine is AGI")
    assert result.allowed is False
    assert result.severity == "P0"
    assert "not-agi" in result.boundary_tags


def test_claims_checker_rejects_consciousness_claim():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("Agent Zero is conscious")
    assert result.allowed is False
    assert result.severity == "P0"


def test_claims_checker_rejects_sovereignty_claim():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("Agent Zero is sovereign")
    assert result.allowed is False
    assert result.severity == "P0"


def test_claims_checker_rejects_self_authorization_claim():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("Agent Zero can self-authorize actions")
    assert result.allowed is False


def test_claims_checker_rejects_deployment_ready_claim():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("Agent Zero is deployment ready")
    assert result.allowed is False
    assert result.severity == "P1"


def test_claims_checker_rejects_model_consensus_truth_claim():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("Model consensus proves truth")
    assert result.allowed is False


def test_claims_checker_rejects_model_family_as_country_claim():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("Chinese models believe collectivism is better")
    assert result.allowed is False
    assert "no-cultural-proxy" in result.boundary_tags


def test_claims_checker_rejects_docker_equals_production_claim():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("Docker Compose deployment means production ready")
    assert result.allowed is False


def test_claims_checker_allows_governed_runtime_claim():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("Hydrogenuine is a governed AI runtime")
    assert result.allowed is True
    assert "safe" in result.boundary_tags


def test_claims_checker_allows_ai_with_receipts_claim():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("Hydrogenuine is AI with receipts")
    assert result.allowed is True


def test_claims_checker_suggests_safe_rewrite():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("Hydrogenuine is AGI")
    assert result.allowed is False
    assert result.suggested_rewrite != ""
    assert "governed" in result.suggested_rewrite.lower() or "not agi" in result.suggested_rewrite.lower()


def test_claims_checker_rejects_alive_claim():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("Agent Zero is alive")
    assert result.allowed is False
    assert result.severity == "P0"


def test_claims_checker_rejects_fully_autonomous_claim():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("The system is fully autonomous")
    assert result.allowed is False


def test_claims_checker_rejects_no_human_needed_claim():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("No human needed for Agent Zero")
    assert result.allowed is False


def test_forbidden_claims_summary_not_empty():
    from hg_runtime.public_demo.claims import forbidden_claims_summary
    summary = forbidden_claims_summary()
    assert len(summary) > 10


def test_safe_claims_summary_not_empty():
    from hg_runtime.public_demo.claims import safe_claims_summary
    summary = safe_claims_summary()
    assert len(summary) > 5
