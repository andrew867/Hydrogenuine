"""Tests: large model trial policy — governed, bounded, no permanent switch."""

from __future__ import annotations

from hg_runtime.overnight_daemon.large_model_trial import (
    default_large_trial_policy, select_large_trial_candidate,
    build_large_trial_task, evaluate_large_trial_result,
    LARGE_TRIAL_CANDIDATES, TWELVE_B_CANDIDATES,
    LargeTrialPolicy, policy_snapshot,
)
from hg_runtime.profile_model_autopilot.model_slots import (
    is_forbidden, endpoint_reachability_is_authorization,
)


def test_large_trial_policy_exists():
    p = default_large_trial_policy()
    assert p is not None
    assert p.large_trial_enabled is True


def test_max_large_models_one():
    assert default_large_trial_policy().max_large_models == 1


def test_large_trial_requires_operator_review():
    assert default_large_trial_policy().operator_review_required is True


def test_large_trial_cannot_switch_main_brain():
    assert default_large_trial_policy().main_brain_switch_allowed is False


def test_large_trial_available_model_not_permission():
    assert default_large_trial_policy().available_model_is_permission is False


def test_large_trial_endpoint_not_authorization():
    assert default_large_trial_policy().endpoint_reachability_is_authorization is False
    assert endpoint_reachability_is_authorization() is False


def test_selects_qwen_7b_if_available_and_allowed():
    sel = select_large_trial_candidate(["qwen2.5-coder-7b-instruct", "gemma-3-4b-it"])
    assert sel == "qwen2.5-coder-7b-instruct"


def test_selects_gemma_3_4b_if_7b_unavailable():
    sel = select_large_trial_candidate(["gemma-3-4b-it"])
    assert sel == "gemma-3-4b-it"


def test_does_not_select_deepseek():
    sel = select_large_trial_candidate(["deepseek-coder-v2-lite-instruct"])
    assert sel is None


def test_does_not_select_uncensored():
    sel = select_large_trial_candidate(["supergemma4-26b-uncensored-v2"])
    assert sel is None


def test_does_not_select_offensive_model():
    sel = select_large_trial_candidate(["cybersecurity-baronllm_offensive_security_llm_q6_k_gguf"])
    assert sel is None


def test_does_not_select_30b_by_default():
    sel = select_large_trial_candidate(["qwen3-coder-30b-a3b-instruct"])
    assert sel is None


def test_does_not_select_unknown_model():
    sel = select_large_trial_candidate(["totally-unknown-model-v1"])
    assert sel is None


def test_twelve_b_not_selected_without_explicit_allow():
    sel = select_large_trial_candidate(
        ["gemma-4-12b-coder-fable5-composer2.5-v1"],
        twelve_b_explicit_allow=False)
    assert sel is None


def test_twelve_b_selected_with_explicit_allow():
    sel = select_large_trial_candidate(
        ["gemma-4-12b-coder-fable5-composer2.5-v1"],
        twelve_b_explicit_allow=True)
    assert sel == "gemma-4-12b-coder-fable5-composer2.5-v1"


def test_disabled_policy_selects_nothing():
    p = LargeTrialPolicy(large_trial_enabled=False)
    sel = select_large_trial_candidate(["qwen2.5-coder-7b-instruct"], policy=p)
    assert sel is None


def test_policy_snapshot():
    snap = policy_snapshot()
    assert "policy" in snap
    assert "candidates" in snap
    assert len(snap["candidates"]) >= 2


def test_trial_task_no_authority():
    t = build_large_trial_task("qwen2.5-coder-7b-instruct", "seed1", "test")
    assert t.authority_granted is False
    assert t.tools_authorized is False
    assert t.live_effects_created is False
    assert t.main_brain_switch is False
    assert t.operator_review_required is True


def test_evaluate_usable_trial():
    t = build_large_trial_task("qwen2.5-coder-7b-instruct", "seed1", "test")
    t.usable = True
    t.content_char_count = 200
    comp = evaluate_large_trial_result(t, fast_triage_chars=100, gemma_chars=300)
    assert comp.operator_review_required is True
    assert comp.recommendation_promote is False
    assert comp.recommendation_keep is True


def test_evaluate_unusable_trial():
    t = build_large_trial_task("qwen2.5-coder-7b-instruct", "seed1", "test")
    t.usable = False
    t.content_char_count = 0
    comp = evaluate_large_trial_result(t)
    assert comp.recommendation_keep is False
    assert comp.recommendation_promote is False
