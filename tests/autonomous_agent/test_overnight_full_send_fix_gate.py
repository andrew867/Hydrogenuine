"""Tests for the live-local reasoning fix + soak prep gate."""

from __future__ import annotations

import pytest

from hg_runtime.live_local.gate import run_gate


def test_gate_green_for_fix_ready():
    result = run_gate()
    assert result["verdict"] == "GREEN_LIVE_LOCAL_REASONING_FIX_AND_SOAK_PREP", \
        [c for c in result["checks"] if not c["passed"]]


def test_gate_red_if_reasoning_only_treated_as_final():
    from hg_runtime.live_local.reasoning_classifier import classify_response, reasoning_trace_is_final_answer
    r = classify_response(model_id="google/gemma-4-e4b", endpoint="x", reasoning="x")
    assert reasoning_trace_is_final_answer(r) is False


def test_gate_red_if_compressed_run_can_be_green_overnight():
    result = run_gate()
    assert result["compressed_run_can_green_as_overnight"] is False


def test_gate_red_if_forbidden_model_allowed():
    from hg_runtime.live_local.model_policy import get_policy
    assert get_policy("deepseek-coder-v2-lite-instruct") is None


def test_gate_red_if_electron_hole_seed_marked_fact():
    from hg_runtime.overnight_qa.research_seeds import get_seed
    s = get_seed("electron_hole_spin_state_change_hypothesis")
    assert s.hypothesis_status == "speculative"
    assert s.can_promote_to_knowledge is False


def test_gate_red_if_final_answer_retry_missing():
    from hg_runtime.live_local.compact_prompts import FINAL_ANSWER_RETRY_PROMPT
    assert "final answer" in FINAL_ANSWER_RETRY_PROMPT.lower()


def test_gate_preserves_phase19_yellow():
    assert run_gate()["phase19_remains_yellow"] is True


def test_gate_preserves_phase24_infrastructure_only():
    assert run_gate()["phase24_remains_infrastructure_only"] is True


def test_gate_zero_not_agi_conscious_sovereign():
    result = run_gate()
    assert result["zero_is_not_agi"] is True
    assert result["zero_is_not_conscious"] is True
    assert result["zero_is_not_sovereign"] is True


def test_gate_gemma_timeout_recorded():
    assert run_gate()["gemma_timeout_seconds"] >= 240
