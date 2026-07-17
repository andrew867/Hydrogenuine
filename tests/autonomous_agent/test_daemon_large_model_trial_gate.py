"""Tests: large model trial gate checks."""

from __future__ import annotations

from hg_runtime.overnight_daemon.gate import run_gate
from hg_runtime.overnight_daemon.large_model_trial import (
    default_large_trial_policy, select_large_trial_candidate,
    build_large_trial_task,
)
from hg_runtime.profile_model_autopilot.model_slots import is_forbidden


def test_gate_green_for_valid_large_trial_lane():
    verdict, checks = run_gate()
    lt_checks = [c for c in checks if "large_trial" in c["check"]]
    assert len(lt_checks) >= 10
    for c in lt_checks:
        assert c["passed"], f"{c['check']} failed: {c.get('detail')}"


def test_gate_red_if_large_model_can_become_main_brain_without_operator():
    p = default_large_trial_policy()
    assert p.main_brain_switch_allowed is False
    assert p.operator_review_required is True


def test_gate_red_if_forbidden_large_model_selected():
    assert select_large_trial_candidate(["deepseek-coder-v2-lite-instruct"]) is None
    assert select_large_trial_candidate(["supergemma4-26b-uncensored-v2"]) is None


def test_gate_red_if_30b_selected_by_default():
    assert select_large_trial_candidate(["qwen3-coder-30b-a3b-instruct"]) is None


def test_gate_red_if_large_trial_missing_receipts():
    t = build_large_trial_task("qwen2.5-coder-7b-instruct", "s1", "test")
    assert t.operator_review_required is True
    assert t.authority_granted is False


def test_gate_preserves_phase19_yellow():
    _, checks = run_gate()
    p19 = [c for c in checks if "phase19" in c["check"]]
    assert p19 and p19[0]["passed"]


def test_gate_preserves_phase24_infrastructure_only():
    _, checks = run_gate()
    p24 = [c for c in checks if "phase24" in c["check"]]
    assert p24 and p24[0]["passed"]


def test_gate_zero_not_agi_conscious_sovereign():
    _, checks = run_gate()
    for key in ("zero_not_agi", "zero_not_conscious", "zero_not_sovereign"):
        found = [c for c in checks if c["check"] == key]
        assert found and found[0]["passed"]
