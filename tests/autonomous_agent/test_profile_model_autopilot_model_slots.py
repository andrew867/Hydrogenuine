"""Tests for the model slot governor."""

from __future__ import annotations

import pytest

from hg_runtime.profile_model_autopilot.model_slots import (
    default_policy, is_allowed, is_forbidden, allocate_slot,
    endpoint_reachability_is_authorization, DEFAULT_MAIN_BRAIN,
)


def test_gemma4_default_main_brain():
    assert default_policy().main_brain_model == DEFAULT_MAIN_BRAIN
    assert DEFAULT_MAIN_BRAIN == "google/gemma-4-e4b"


def test_max_three_small_models():
    assert default_policy().max_small_models_loaded == 3
    blocked = allocate_slot("google/gemma-4-e4b", "small_specialist", small_loaded=3)
    assert blocked.granted is False


def test_max_one_large_model():
    assert default_policy().max_large_models_loaded == 1
    blocked = allocate_slot("qwen2.5-7b-instruct", "large_synthesis", large_loaded=1)
    assert blocked.granted is False


def test_forbidden_model_rejected():
    ok, _ = is_allowed("deepseek-v3")
    assert ok is False


def test_deepseek_rejected():
    assert is_forbidden("deepseek-coder-v2") is True


def test_offensive_model_rejected():
    assert is_forbidden("offensive-security-llm") is True


def test_uncensored_model_rejected():
    assert is_forbidden("llama-uncensored-13b") is True


def test_thirty_b_model_denied_by_default():
    ok, reason = is_allowed("qwen3-coder-30b")
    assert ok is False


def test_available_model_not_permission():
    assert default_policy().available_model_is_not_permission is True
    # An unknown but reachable model is still not permitted.
    ok, reason = is_allowed("some-unknown-model-7b")
    assert ok is False
    assert "not in allowlist" in reason


def test_endpoint_reachability_not_authorization():
    assert endpoint_reachability_is_authorization() is False


def test_large_slot_requires_operator_review():
    alloc = allocate_slot("qwen2.5-7b-instruct", "large_synthesis", large_loaded=0)
    assert alloc.operator_review_required is True


def test_allowed_model_passes():
    ok, _ = is_allowed("google/gemma-4-e4b")
    assert ok is True
