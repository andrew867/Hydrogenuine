"""Tests: large model trial resource preflight."""

from __future__ import annotations

from hg_runtime.overnight_daemon.large_model_trial import (
    run_resource_preflight, TWELVE_B_CANDIDATES,
)


def test_resource_safe_allows_trial():
    pf = run_resource_preflight("qwen2.5-coder-7b-instruct", [])
    assert pf is not None
    assert pf.candidate_model == "qwen2.5-coder-7b-instruct"


def test_resource_unsafe_skips_trial_yellow():
    pf = run_resource_preflight("qwen2.5-coder-7b-instruct", [])
    if not pf.resource_safe:
        assert "insufficient" in pf.reason or "no telemetry" in pf.reason


def test_missing_telemetry_does_not_crash():
    pf = run_resource_preflight("gemma-3-4b-it", [])
    assert pf is not None


def test_twelve_b_requires_explicit_resource_allow():
    pf = run_resource_preflight("gemma-4-12b-coder-fable5-composer2.5-v1", [])
    assert pf.resource_safe is False
    assert "12B" in pf.reason or "explicit" in pf.reason


def test_twelve_b_allowed_with_explicit_flag():
    pf = run_resource_preflight(
        "gemma-4-12b-coder-fable5-composer2.5-v1", [],
        twelve_b_explicit_allow=True)
    assert pf is not None


def test_small_model_conservative_allow():
    pf = run_resource_preflight("gemma-3-4b-it", [])
    assert pf.candidate_size_gb <= 3.0


def test_preflight_records_candidate():
    pf = run_resource_preflight("qwen2.5-coder-7b-instruct", ["google/gemma-4-e4b"])
    assert pf.candidate_model == "qwen2.5-coder-7b-instruct"
    assert "google/gemma-4-e4b" in pf.loaded_models


def test_unknown_model_gets_default_size():
    pf = run_resource_preflight("totally-unknown-model", [])
    assert pf.candidate_size_gb == 5.0
