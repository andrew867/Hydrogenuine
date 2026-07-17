"""Tests: model calibration for daemon launch."""

from __future__ import annotations

from hg_runtime.overnight_daemon.model_calibration import (
    CalibrationManifest, ModelCalibrationEntry,
    discover_models, run_calibration, calibration_snapshot,
    _classify_role, _probe_model,
)
from hg_runtime.overnight_daemon.model_role_routing import (
    FAST_TRIAGE_CANDIDATES, GEMMA_MODEL_ID,
)
from hg_runtime.overnight_daemon.large_model_trial import LARGE_TRIAL_CANDIDATES
from hg_runtime.profile_model_autopilot.model_slots import is_forbidden


def _make_manifest_with_models(models: list[str]) -> CalibrationManifest:
    m = CalibrationManifest()
    m.models_available = models
    m.models_discovered = len(models)
    return m


def test_calibration_discovers_models():
    m = _make_manifest_with_models(["qwen2.5-0.5b-instruct", "google/gemma-4-e4b"])
    assert m.models_discovered == 2
    assert "qwen2.5-0.5b-instruct" in m.models_available


def test_calibration_rejects_forbidden_models():
    for model in ("deepseek-coder-v2-lite-instruct",
                  "supergemma4-26b-uncensored-v2",
                  "cybersecurity-baronllm_offensive_security_llm_q6_k_gguf"):
        assert is_forbidden(model), f"{model} should be forbidden"


def test_calibration_marks_available_not_permission():
    m = CalibrationManifest()
    assert m.available_model_is_permission is False
    assert m.endpoint_reachability_is_authorization is False


def test_calibration_records_telemetry_unknown_without_crash():
    e = ModelCalibrationEntry(model_id="test-model")
    assert e.telemetry_available is False
    assert e.resource_confidence == "unknown"


def test_empirical_success_overrides_low_confidence_static_estimate():
    from hg_runtime.overnight_daemon.large_model_trial import run_resource_preflight
    pf = run_resource_preflight(
        "qwen2.5-coder-7b-instruct", [],
        empirical_probe_success=True)
    assert pf.can_attempt_trial is True


def test_empirical_failure_records_yellow():
    e = ModelCalibrationEntry(
        model_id="test-model",
        empirical_status="failure",
        resource_safe=False)
    assert e.empirical_status == "failure"
    assert e.resource_safe is False


def test_calibration_selects_fast_triage():
    m = CalibrationManifest()
    m.fast_triage_model = "qwen2.5-0.5b-instruct"
    assert m.fast_triage_model in FAST_TRIAGE_CANDIDATES


def test_calibration_selects_large_trial_candidate():
    m = CalibrationManifest()
    m.selected_large_trial = "gemma-3-4b-it"
    assert m.selected_large_trial in LARGE_TRIAL_CANDIDATES


def test_classify_role_fast_triage():
    assert _classify_role("qwen2.5-0.5b-instruct") == "fast_triage"


def test_classify_role_main_synthesis():
    assert _classify_role(GEMMA_MODEL_ID) == "main_synthesis"


def test_classify_role_large_trial():
    assert _classify_role("qwen2.5-coder-7b-instruct") == "large_trial"


def test_classify_role_denied_unknown():
    assert _classify_role("totally-unknown-model-xyz") == "denied"


def test_calibration_snapshot_structure():
    m = CalibrationManifest(
        endpoint="http://test:1234/v1",
        models_discovered=5,
        fast_triage_model="qwen2.5-0.5b-instruct",
        selected_large_trial="gemma-3-4b-it",
    )
    snap = calibration_snapshot(m)
    assert snap["endpoint"] == "http://test:1234/v1"
    assert snap["fast_triage"] == "qwen2.5-0.5b-instruct"
    assert snap["selected_large_trial"] == "gemma-3-4b-it"
    assert snap["available_model_is_permission"] is False
    assert snap["endpoint_reachability_is_authorization"] is False
