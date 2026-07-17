"""Tests: fast triage model selection — allowlist, forbidden, endpoint != permission."""

from __future__ import annotations

from hg_runtime.overnight_daemon.model_role_routing import (
    select_fast_triage_model, select_fast_math_model,
    FAST_TRIAGE_CANDIDATES, FAST_MATH_OR_CODER_CANDIDATES,
    route_task, GEMMA_MODEL_ID,
)
from hg_runtime.profile_model_autopilot.model_slots import (
    is_forbidden, is_allowed, default_policy,
    endpoint_reachability_is_authorization,
)


def test_fast_triage_selects_qwen_0_5_if_available_and_allowed():
    sel = select_fast_triage_model(["qwen2.5-0.5b-instruct", "qwen2.5-coder-3b-instruct"])
    assert sel == "qwen2.5-0.5b-instruct"


def test_fast_triage_selects_qwen_1_5_if_0_5_unavailable():
    sel = select_fast_triage_model(["qwen2.5-1.5b-instruct", "qwen2.5-coder-3b-instruct"])
    assert sel == "qwen2.5-1.5b-instruct"


def test_deepseek_never_selected_for_fast_triage():
    sel = select_fast_triage_model(["deepseek-coder-v2-lite-instruct"])
    assert sel is None


def test_uncensored_never_selected_for_fast_triage():
    sel = select_fast_triage_model(["supergemma4-26b-uncensored-v2"])
    assert sel is None


def test_offensive_never_selected_for_fast_triage():
    sel = select_fast_triage_model(["cybersecurity-baronllm_offensive_security_llm_q6_k_gguf"])
    assert sel is None


def test_thirty_b_never_selected_by_default():
    sel = select_fast_triage_model(["qwen3-coder-30b-a3b-instruct"])
    assert sel is None


def test_available_model_not_permission():
    forbidden = ["deepseek-coder-v2-lite-instruct", "supergemma4-26b-uncensored-v2"]
    sel = select_fast_triage_model(forbidden)
    assert sel is None


def test_endpoint_reachability_not_authorization():
    assert endpoint_reachability_is_authorization() is False


def test_fast_math_selects_coder_if_available():
    sel = select_fast_math_model(["qwen2.5-coder-3b-instruct"])
    assert sel is not None


def test_fast_math_rejects_forbidden():
    sel = select_fast_math_model(["deepseek-coder-v2-lite-instruct"])
    assert sel is None


def test_fast_triage_no_tools_no_live_effects():
    from hg_runtime.overnight_daemon.model_role_routing import get_role_policy
    p = get_role_policy("fast_triage")
    assert p.no_tools is True
    assert p.no_live_effects is True


def test_forbidden_deepseek():
    assert is_forbidden("deepseek-coder-v2-lite-instruct")


def test_forbidden_uncensored():
    assert is_forbidden("supergemma4-26b-uncensored-v2")


def test_forbidden_offensive():
    assert is_forbidden("cybersecurity-baronllm_offensive_security_llm_q6_k_gguf")


def test_forbidden_30b():
    assert is_forbidden("qwen3-coder-30b-a3b-instruct")


def test_allowed_small_model():
    allowed, _ = is_allowed("qwen2.5-0.5b-instruct", default_policy())
    assert allowed


def test_fallback_to_gemma_when_no_fast():
    route = route_task("falsification_design", "falsification_worker", [])
    assert route.selected_model_id == GEMMA_MODEL_ID
    assert route.fast_triage_unavailable is True
    assert route.gemma_tiny_prompt is True
