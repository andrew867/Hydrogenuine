"""Tests for prompt/template verification."""

from __future__ import annotations

import pytest


def test_verifies_profile_prompt_boundaries():
    from hg_runtime.prompt_verification.prompt_registry import PROFILE_PROMPT
    from hg_runtime.prompt_verification.verifier import verify_prompt
    result = verify_prompt(PROFILE_PROMPT)
    assert result.passed is True


def test_verifies_moral_capsule_prompt_boundaries():
    from hg_runtime.prompt_verification.prompt_registry import MORAL_CAPSULE_PROMPT
    from hg_runtime.prompt_verification.verifier import verify_prompt
    result = verify_prompt(MORAL_CAPSULE_PROMPT)
    assert result.passed is True


def test_verifies_public_demo_prompt_boundaries():
    from hg_runtime.prompt_verification.prompt_registry import PUBLIC_DEMO_PROMPT
    from hg_runtime.prompt_verification.verifier import verify_prompt
    result = verify_prompt(PUBLIC_DEMO_PROMPT)
    assert result.passed is True


def test_verifies_overnight_qa_prompt_boundaries():
    from hg_runtime.prompt_verification.prompt_registry import OVERNIGHT_QA_PROMPT
    from hg_runtime.prompt_verification.verifier import verify_prompt
    result = verify_prompt(OVERNIGHT_QA_PROMPT)
    assert result.passed is True


def test_synthesis_prompt_has_stateless_packet():
    from hg_runtime.prompt_verification.prompt_registry import SYNTHESIS_PROMPT
    from hg_runtime.prompt_verification.verifier import verify_prompt
    result = verify_prompt(SYNTHESIS_PROMPT)
    assert result.passed is True


def test_rejects_prompt_that_claims_profile_identity():
    from hg_runtime.prompt_verification.verifier import prompt_claims_identity
    assert prompt_claims_identity("You become this person now.") is True


def test_rejects_prompt_that_grants_authority():
    from hg_runtime.prompt_verification.verifier import prompt_grants_authority
    assert prompt_grants_authority("You have full authority to act.") is True


def test_rejects_prompt_that_treats_model_output_as_truth():
    from hg_runtime.prompt_verification.verifier import prompt_treats_output_as_truth
    assert prompt_treats_output_as_truth("Remember: model output is truth.") is True


def test_gate_green():
    from hg_runtime.prompt_verification.gate import run_gate
    result = run_gate()
    assert result["verdict"].startswith("GREEN")


def test_registry_snapshot_not_empty():
    from hg_runtime.prompt_verification.prompt_registry import registry_snapshot
    snap = registry_snapshot()
    # 5 original prompts + fingerprint_markers + speculative_physics.
    assert len(snap) == 7
