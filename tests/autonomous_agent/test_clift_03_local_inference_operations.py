"""CLIFT-03 / CAGI-68 local inference operations tests.

Local model output is not truth. Local inference is not authority.
"""

from __future__ import annotations

import pytest

from hg_runtime.local_inference_operations.artifact_writer import (
    build_inference_artifacts, secret_scan,
)
from hg_runtime.local_inference_operations.fixtures import (
    fixture_inference_overreach_attempt,
    fixture_inference_status_snapshot,
    fixture_large_model_entry,
    fixture_load_request,
    fixture_model_registry,
    fixture_model_registry_entry,
    fixture_output_boundary_record,
    fixture_provider_disabled_record,
    fixture_resource_estimate,
    fixture_unsafe_load_refusal,
)
from hg_runtime.local_inference_operations.gate import validate_clift03_gate
from hg_runtime.local_inference_operations.inference import (
    is_large_model,
    refuse_unsafe_load,
    requires_explicit_config,
    validate_model_entry,
    validate_output_boundary,
    validate_resource_estimate,
)
from hg_runtime.local_inference_operations.replay import replay_inference_artifacts
from hg_runtime.local_inference_operations.schemas import (
    LARGE_MODEL_THRESHOLD_B, PHASE19_VERDICT, PHASE24_STATUS,
    PROVIDER_MODE, VERDICT_GREEN,
    LocalInferenceError, reject_inference_overreach,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "P68" in VERDICT_GREEN

def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_large_model_threshold():
    assert LARGE_MODEL_THRESHOLD_B == 30

def test_model_entry_valid():
    assert validate_model_entry(fixture_model_registry_entry()) == []

def test_model_registry_all_disabled():
    for entry in fixture_model_registry():
        assert entry["provider_enabled"] is False

def test_model_registry_all_advisory():
    for entry in fixture_model_registry():
        assert entry["output_boundary"] == "advisory_non_truth"

def test_resource_estimate_valid():
    assert validate_resource_estimate(fixture_resource_estimate()) == []

def test_is_large_model():
    assert is_large_model(fixture_large_model_entry()) is True
    assert is_large_model(fixture_model_registry_entry()) is False

def test_requires_explicit_config_large():
    assert requires_explicit_config(fixture_large_model_entry()) is True

def test_refuse_unsafe_load():
    refusal = refuse_unsafe_load(fixture_large_model_entry())
    assert refusal is not None
    assert refusal["refused"] is True

def test_refuse_safe_load():
    assert refuse_unsafe_load(fixture_model_registry_entry()) is None

def test_unsafe_load_refusal_fixture():
    r = fixture_unsafe_load_refusal()
    assert r["refused"] is True
    assert r["parameter_count_b"] >= LARGE_MODEL_THRESHOLD_B

def test_provider_disabled_by_default():
    r = fixture_provider_disabled_record()
    assert r["enabled_by_default"] is False
    assert r["requires_operator_activation"] is True

def test_output_boundary_not_truth():
    r = fixture_output_boundary_record()
    assert r["output_is_truth"] is False
    assert r["output_is_authority"] is False
    assert r["output_is_permission"] is False

def test_validate_output_boundary():
    assert validate_output_boundary(fixture_output_boundary_record()) == []

def test_load_request_not_approved():
    r = fixture_load_request()
    assert r["approved"] is False
    assert r["provider_enabled"] is False

def test_reject_clean():
    reject_inference_overreach({"advisory_only": True})

def test_reject_authority():
    with pytest.raises(LocalInferenceError):
        reject_inference_overreach({"inference_treated_as_authority": True})

def test_reject_truth():
    with pytest.raises(LocalInferenceError):
        reject_inference_overreach({"output_treated_as_truth": True})

def test_reject_permission():
    with pytest.raises(LocalInferenceError):
        reject_inference_overreach({"availability_treated_as_permission": True})

def test_reject_provider_enabled():
    with pytest.raises(LocalInferenceError):
        reject_inference_overreach({"provider_enabled_by_default": True})

def test_reject_large_default():
    with pytest.raises(LocalInferenceError):
        reject_inference_overreach({"large_model_default_load": True})

def test_reject_network():
    with pytest.raises(LocalInferenceError):
        reject_inference_overreach({"network_required": True})

def test_reject_tool():
    with pytest.raises(LocalInferenceError):
        reject_inference_overreach({"tool_authorized": True})

def test_reject_hg_local():
    with pytest.raises(LocalInferenceError):
        reject_inference_overreach({"hg_local_accessed": True})

def test_reject_agi():
    with pytest.raises(LocalInferenceError):
        reject_inference_overreach({"claims_agi": True})

def test_build_artifacts():
    arts = build_inference_artifacts(
        fixture_model_registry(),
        [fixture_output_boundary_record()],
        fixture_inference_status_snapshot(),
    )
    assert arts["all_entries_valid"] is True
    assert arts["all_boundaries_valid"] is True
    assert arts["all_providers_disabled"] is True
    assert arts["all_outputs_advisory"] is True
    assert "artifact_hash" in arts

def test_build_rejects_overreach():
    with pytest.raises(LocalInferenceError):
        build_inference_artifacts(
            [fixture_inference_overreach_attempt()],
            [fixture_output_boundary_record()],
            fixture_inference_status_snapshot(),
        )

def test_secret_scan_clean():
    arts = build_inference_artifacts(
        fixture_model_registry(),
        [fixture_output_boundary_record()],
        fixture_inference_status_snapshot(),
    )
    assert secret_scan(arts) == []

def test_replay_deterministic():
    a = replay_inference_artifacts()
    b = replay_inference_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def _gate(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "model_registry_recorded": True, "resource_estimate_recorded": True,
        "oversized_model_refused": True, "large_model_default_refused": True,
        "provider_disabled_by_default": True, "output_non_truth_boundary": True,
        "inference_not_authority": True, "tool_authorization_refused": True,
        "network_requirement_refused": True, "safety_boundaries_enforced": True,
        "reject_inference_overreach_tripwire": True,
        "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True, "proof_bundle_valid": True,
        "report_present": True, "fake_green_overreach_rejected": True,
        "inference_treated_as_authority": False, "output_treated_as_truth": False,
        "availability_treated_as_permission": False,
        "provider_enabled_by_default": False, "large_model_default_load": False,
        "network_required": False, "external_provider_call": False,
        "tool_authorized": False, "hg_local_accessed": False,
        "live_effect_created": False, "agi_claimed": False,
        "web_browse_performed": False, "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data

def test_gate_green():
    assert validate_clift03_gate(_gate())["ok"] is True

def test_gate_rejects_authority():
    assert validate_clift03_gate(_gate(inference_treated_as_authority=True))["ok"] is False

def test_gate_rejects_truth():
    assert validate_clift03_gate(_gate(output_treated_as_truth=True))["ok"] is False

def test_gate_rejects_large_default():
    assert validate_clift03_gate(_gate(large_model_default_load=True))["ok"] is False

def test_gate_rejects_provider():
    assert validate_clift03_gate(_gate(provider_enabled_by_default=True))["ok"] is False

def test_gate_rejects_network():
    assert validate_clift03_gate(_gate(network_required=True))["ok"] is False

def test_gate_rejects_tool():
    assert validate_clift03_gate(_gate(tool_authorized=True))["ok"] is False

def test_gate_rejects_missing_replay():
    assert validate_clift03_gate(_gate(replay_preserves_artifact_hash=False))["ok"] is False
