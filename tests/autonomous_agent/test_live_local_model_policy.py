"""Tests for per-model live-local policy."""

from __future__ import annotations

import pytest

from hg_runtime.live_local.model_policy import (
    gemma_policy, get_policy, select_fast_triage, fast_triage_candidates,
)


def test_gemma4_reasoning_policy_exists():
    g = gemma_policy()
    assert g.is_reasoning_model is True
    assert g.model_role == "main_brain"


def test_gemma4_timeout_at_least_240_seconds():
    assert gemma_policy().default_timeout_seconds >= 240


def test_gemma4_captures_reasoning_content():
    g = gemma_policy()
    assert g.capture_reasoning_content is True
    assert g.reasoning_content_is_scratchpad is True
    assert g.reasoning_content_is_not_final_answer is True


def test_gemma4_requires_final_answer_for_green_task():
    assert gemma_policy().require_final_answer_for_green_task is True


def test_forbidden_models_still_rejected():
    assert get_policy("deepseek-coder-v2-lite-instruct") is None
    assert get_policy("supergemma4-26b-uncensored-v2") is None
    assert get_policy("qwen3-coder-30b-a3b-instruct") is None


def test_available_model_not_permission():
    # forbidden models present on the endpoint never yield a usable triage selection
    present = ["supergemma4-26b-uncensored-v2", "qwen3-coder-30b-a3b-instruct",
               "deepseek-coder-v2-lite-instruct"]
    assert select_fast_triage(present) is None


def test_endpoint_reachability_not_authorization():
    from hg_runtime.profile_model_autopilot.model_slots import endpoint_reachability_is_authorization
    assert endpoint_reachability_is_authorization() is False


def test_fast_triage_model_requires_allowlist():
    # An allowlisted small instruct present is selectable; forbidden ones are not.
    sel = select_fast_triage(["qwen2.5-coder-3b-instruct", "deepseek-coder-v2-lite-instruct"])
    assert sel == "qwen2.5-coder-3b-instruct"


def test_fast_triage_candidates_nonempty():
    assert len(fast_triage_candidates()) > 0


def test_gemma_no_tools_no_live_effects():
    g = gemma_policy()
    assert g.no_tools is True
    assert g.no_live_effects is True


def test_gemma_final_answer_retry_tokens_sufficient():
    assert gemma_policy().final_answer_retry_max_tokens >= 512
