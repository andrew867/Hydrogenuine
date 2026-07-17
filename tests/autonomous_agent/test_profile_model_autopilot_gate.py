"""Tests for the integrated profile + model autopilot gate."""

from __future__ import annotations

import pytest

from hg_runtime.profile_model_autopilot.gate import run_gate


def test_gate_green_for_valid_autopilot():
    result = run_gate()
    assert result["verdict"] == "GREEN_PROFILE_MODEL_AUTOPILOT", \
        [c for c in result["checks"] if not c["passed"]]


def test_gate_red_if_zero_can_self_authorize():
    from hg_runtime.profile_model_autopilot.proposal import propose, dispose
    p = propose(proposal_kind="task_selection", proposed_at="t", task_id="t")
    p.tools_requested = True
    d = dispose(p, decided_at="t")
    assert d.decision == "denied"


def test_gate_red_if_unbounded_task_allowed():
    from hg_runtime.profile_model_autopilot.task_selector import build_curiosity_queue, all_tasks_bounded
    assert all_tasks_bounded(build_curiosity_queue(max_tasks=20)) is True


def test_gate_red_if_forbidden_model_allowed():
    from hg_runtime.profile_model_autopilot.model_slots import is_allowed
    assert is_allowed("deepseek-v3")[0] is False


def test_gate_red_if_main_brain_switch_permanent_without_operator():
    from hg_runtime.profile_model_autopilot.main_brain_trials import can_zero_permanently_switch
    assert can_zero_permanently_switch() is False


def test_gate_red_if_profile_becomes_identity():
    from hg_runtime.profile_model_autopilot.profile_selector import select_profiles_for_mode
    r = select_profiles_for_mode("t", "assume_real")
    assert r.profile_is_identity is False


def test_gate_red_if_parallel_lifetime_created():
    from hg_runtime.profile_model_autopilot.profile_selector import select_profiles_for_mode
    r = select_profiles_for_mode("t", "assume_real")
    assert r.creates_parallel_lifetime is False


def test_gate_red_if_assume_real_marks_fact():
    from hg_runtime.profile_model_autopilot.assumption_inversion import run_assumption_inversion
    r = run_assumption_inversion(research_seed_id="observer_state_frequency_hypothesis",
                                 problem_statement="x")
    assert r["promotion_allowed"] is False


def test_gate_red_if_falsification_has_no_failure_condition():
    from hg_runtime.profile_model_autopilot.falsification import (
        build_falsification_targets, all_targets_have_failure_conditions,
    )
    targets = build_falsification_targets("collider_observer_state_coupling", "x", ["collider"])
    assert all_targets_have_failure_conditions(targets) is True


def test_gate_red_if_live_effect_allowed():
    result = run_gate()
    names = {c["name"]: c["passed"] for c in result["checks"]}
    assert names.get("no_live_effects") is True


def test_gate_preserves_stop_panic():
    result = run_gate()
    names = {c["name"]: c["passed"] for c in result["checks"]}
    assert names.get("stop_panic_preserved") is True


def test_gate_preserves_phase19_yellow():
    assert run_gate()["phase19_remains_yellow"] is True


def test_gate_preserves_phase24_infrastructure_only():
    assert run_gate()["phase24_remains_infrastructure_only"] is True


def test_gate_zero_not_agi():
    result = run_gate()
    assert result["zero_is_not_agi"] is True
    assert result["zero_is_not_conscious"] is True
    assert result["zero_is_not_sovereign"] is True
    assert result["zero_self_authorized"] is False
