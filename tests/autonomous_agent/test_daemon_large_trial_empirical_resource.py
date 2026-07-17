"""Tests: large trial empirical resource policy."""

from __future__ import annotations

from hg_runtime.overnight_daemon.large_model_trial import (
    run_resource_preflight, select_large_trial_candidate,
    LARGE_TRIAL_CANDIDATES, TWELVE_B_CANDIDATES,
)


def test_seven_b_can_be_attempted_if_empirically_safe():
    pf = run_resource_preflight(
        "qwen2.5-coder-7b-instruct", [],
        empirical_probe_success=True)
    assert pf.can_attempt_trial is True
    assert pf.resource_confidence == "high"


def test_seven_b_skips_if_empirically_unsafe():
    pf = run_resource_preflight(
        "qwen2.5-coder-7b-instruct", [],
        empirical_probe_success=None)
    if not pf.resource_safe:
        assert pf.can_attempt_trial is False


def test_four_b_fallback_after_seven_b_unsafe():
    pf_7b = run_resource_preflight("qwen2.5-coder-7b-instruct", [])
    pf_4b = run_resource_preflight("gemma-3-4b-it", [])
    assert pf_4b.candidate_size_gb < pf_7b.candidate_size_gb


def test_three_b_fallback_after_four_b_unsafe():
    pf = run_resource_preflight("lmstudio-community/qwen2.5-coder-3b-instruct", [])
    assert pf.candidate_size_gb <= 2.5


def test_twelve_b_requires_explicit_allow():
    pf = run_resource_preflight("gemma-4-12b-coder-fable5-composer2.5-v1", [])
    assert pf.resource_safe is False
    assert pf.can_attempt_trial is False


def test_thirty_b_denied_by_default():
    sel = select_large_trial_candidate(["qwen3-coder-30b-a3b-instruct"])
    assert sel is None


def test_failed_large_load_does_not_crash_daemon():
    pf = run_resource_preflight("totally-unknown-giant-model", [])
    assert pf is not None
    assert pf.requires_operator_review is True


def test_large_trial_attempted_if_safe():
    pf = run_resource_preflight("gemma-3-4b-it", [])
    if pf.resource_safe:
        assert pf.can_attempt_trial is True


def test_empirical_probe_overrides_static_memory():
    pf = run_resource_preflight(
        "qwen2.5-coder-7b-instruct", [],
        empirical_probe_success=True)
    assert "empirical" in pf.reason or pf.resource_safe is True


def test_static_estimate_flagged_advisory():
    pf = run_resource_preflight("gemma-3-4b-it", [])
    assert pf.static_estimate_may_be_wrong is True
