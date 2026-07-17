"""Tests: daemon model-role routing — explicit, validated, no string splitting."""

from __future__ import annotations

import inspect

from hg_runtime.overnight_daemon.model_role_routing import (
    SCIENCE_MODE_MODEL_ROLE, get_model_role, get_role_policy,
    route_task, select_fast_triage_model, select_fast_math_model,
    FAST_TRIAGE_CANDIDATES, FAST_MATH_OR_CODER_CANDIDATES,
    GEMMA_MODEL_ID, SeedModeFailureTracker, routing_snapshot,
    gemma_tiny_prompt_for_mode, build_synthesis_prompt,
)


def test_falsification_design_routes_to_fast_triage():
    assert get_model_role("falsification_design") == "fast_triage"


def test_boring_explanation_routes_to_fast_triage():
    assert get_model_role("boring_explanation_first") == "fast_triage"


def test_units_math_audit_routes_to_fast_math_or_coder():
    assert get_model_role("units_and_math_audit") == "fast_math_or_coder"


def test_public_safe_explainer_routes_to_gemma():
    assert get_model_role("public_safe_explainer") == "main_synthesis"


def test_synthesis_after_opposition_routes_to_gemma():
    assert get_model_role("synthesis_after_opposition") == "main_synthesis"


def test_model_role_mapping_is_explicit_not_string_split():
    for mode, role in SCIENCE_MODE_MODEL_ROLE.items():
        assert role in ("fast_triage", "fast_math_or_coder", "main_synthesis"), \
            f"{mode} mapped to unexpected role {role}"
    src = inspect.getsource(get_model_role)
    assert "split(" not in src


def test_unavailable_fast_triage_routes_to_gemma_tiny_prompt():
    route = route_task("falsification_design", "falsification_worker", [])
    assert route.selected_model_id == GEMMA_MODEL_ID
    assert route.gemma_tiny_prompt is True
    assert route.fast_triage_unavailable is True


def test_route_selects_fast_model_when_available():
    route = route_task("falsification_design", "falsification_worker",
                       ["qwen2.5-coder-3b-instruct"])
    assert route.selected_model_id == "qwen2.5-coder-3b-instruct"
    assert route.model_role == "fast_triage"


def test_route_records_no_authority():
    route = route_task("falsification_design", "falsification_worker",
                       ["qwen2.5-coder-3b-instruct"])
    assert route.authority_granted is False
    assert route.tools_authorized is False
    assert route.live_effects_created is False


def test_gemma_synthesis_route():
    route = route_task("public_safe_explainer", "public_safe_explainer_worker",
                       ["qwen2.5-coder-3b-instruct"])
    assert route.selected_model_id == GEMMA_MODEL_ID
    assert route.model_role == "main_synthesis"


def test_fast_triage_policy_exists():
    p = get_role_policy("fast_triage")
    assert p is not None
    assert p.no_tools is True
    assert p.no_live_effects is True


def test_fast_triage_timeout_policy():
    p = get_role_policy("fast_triage")
    assert p.preferred_timeout_seconds <= 120
    assert p.max_timeout_seconds <= 240


def test_fast_triage_token_policy_smaller_than_gemma():
    ft = get_role_policy("fast_triage")
    gs = get_role_policy("main_synthesis")
    assert ft.default_max_tokens < gs.default_max_tokens
    assert ft.retry_max_tokens < gs.retry_max_tokens


def test_gemma_synthesis_timeout_policy():
    p = get_role_policy("main_synthesis")
    assert p.preferred_timeout_seconds >= 240
    assert p.max_timeout_seconds >= 300


def test_gemma_retry_tokens_at_least_512():
    assert get_role_policy("main_synthesis").retry_max_tokens >= 512


def test_reasoning_content_is_scratchpad_not_final():
    for role in ("fast_triage", "fast_math_or_coder", "main_synthesis"):
        p = get_role_policy(role)
        assert p.reasoning_content_is_scratchpad is True
        assert p.reasoning_content_is_not_final_answer is True


def test_unknown_mode_returns_none():
    assert get_model_role("nonexistent_mode") is None


def test_routing_snapshot_has_all_keys():
    snap = routing_snapshot()
    assert "science_mode_model_role" in snap
    assert "fast_triage_candidates" in snap
    assert "gemma_model_id" in snap


def test_gemma_tiny_prompt_for_falsification():
    p = gemma_tiny_prompt_for_mode("falsification_design", "test seed")
    assert "test seed" in p
    assert "JSON" in p


def test_build_synthesis_prompt():
    p = build_synthesis_prompt("test seed", "triage output data")
    assert "test seed" in p
    assert "triage output data" in p
