"""INFER-LIVE governed local inference runtime tests."""

from __future__ import annotations

import pytest

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.iam.types import reset_iam_event_ledger
from hg_core.infer_live.errors import (
    INFER_DRY_RUN_COMPLETE,
    INFER_ESCALATION_REQUEST,
    REFUSED_INSUFFICIENT_HARDWARE,
    REFUSED_LIVE_BACKEND_CALL,
    REFUSED_MISSING_GPP_PERMIT,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_MISSING_UEAK_ADMISSION,
    REFUSED_MODEL_DOWNLOAD,
    REFUSED_STALE_APPROVAL,
)
from hg_runtime.live_inference_runtime import (
    FIXTURE_CLOCK,
    FUTURE_EXPIRY,
    PAST_EXPIRY,
    assign_model_for_organ,
    backend_priority,
    check_backend_readiness,
    cuda_is_optional_only,
    detect_hardware_profile,
    load_infer_fixtures,
    lookup_model_profile,
    process_infer_bundle,
    replay_fixture_stream,
    request_from_fixture,
    run_dry_run_inference,
    run_inference_runtime_fixture,
    validate_inference_request,
)


@pytest.fixture(autouse=True)
def _reset_iam() -> None:
    clear_registry_cache()
    reset_iam_event_ledger()
    load_registry()


def _req(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "request_id": "infer-test",
        "organ_ref": "organ:OEF",
        "model_profile_id": "model:small-default",
        "operator_ref": "op:local",
        "freshness_ref": "tim:approval_window_ok",
        "approval_expires_at": FUTURE_EXPIRY,
        "scope": "approve_change",
        "dry_run": True,
    }
    base.update(overrides)
    return base


def test_hardware_profile_detection_no_live_model() -> None:
    hw = detect_hardware_profile()
    assert hw.profile_id
    assert hw.nvidia_required is False
    readiness = check_backend_readiness(hw)
    assert all(r.readiness_check_only for r in readiness)


def test_openvino_igpu_profile_fixture() -> None:
    bundle = next(b for b in load_infer_fixtures() if b["bundle_id"] == "infer-igpu-profile")
    result = process_infer_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["live_backend_called"] is False


def test_cpu_fallback_profile() -> None:
    bundle = next(b for b in load_infer_fixtures() if b["bundle_id"] == "infer-cpu-fallback")
    result = process_infer_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result.get("backend_used") in ("openvino_cpu", "openvino_igpu", "none")


def test_insufficient_hardware_fail_closed() -> None:
    bundle = next(b for b in load_infer_fixtures() if b["bundle_id"] == "infer-insufficient-hardware")
    result = process_infer_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "fail_closed"
    assert result["reason_code"] == REFUSED_INSUFFICIENT_HARDWARE


def test_cuda_optional_not_required() -> None:
    assert cuda_is_optional_only() is True
    hw = detect_hardware_profile(
        fixture={
            "profile_id": "test",
            "igpu_available": True,
            "ram_gb": 32,
            "meets_minimum_profile": True,
            "nvidia_detected": True,
            "nvidia_required": False,
        }
    )
    assert hw.nvidia_required is False
    priority = backend_priority()
    assert priority[-1] == "cuda_optional"


def test_small_model_for_low_depth_organ() -> None:
    profile = assign_model_for_organ("organ:BRB", depth="low")
    assert profile.tier == "small"


def test_escalation_produces_request_not_authority() -> None:
    bundle = next(b for b in load_infer_fixtures() if b["bundle_id"] == "infer-escalation-request")
    result = process_infer_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["reason_code"] == INFER_ESCALATION_REQUEST
    assert result["permission_granted"] is False


def test_inference_output_tep_wrapped() -> None:
    bundle = next(b for b in load_infer_fixtures() if b["bundle_id"] == "infer-valid-dry-run")
    result = process_infer_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert isinstance(result.get("tep_wrapped"), dict)


def test_inference_output_cannot_approve_action() -> None:
    bundle = next(b for b in load_infer_fixtures() if b["bundle_id"] == "infer-valid-dry-run")
    result = process_infer_bundle(bundle, observed_at=FIXTURE_CLOCK)
    dry = result.get("dry_run_result", {})
    assert dry.get("permission_granted") is False
    output = dry.get("output", {})
    assert output.get("permission_granted") is False
    assert output.get("is_permit") is False


def test_missing_operator_approval_refusal() -> None:
    req = request_from_fixture(_req(operator_ref=None))
    result = validate_inference_request(req, observed_at=FIXTURE_CLOCK)
    assert result["reason_code"] == REFUSED_MISSING_OPERATOR_APPROVAL


def test_stale_approval_refusal() -> None:
    req = request_from_fixture(_req(approval_expires_at=PAST_EXPIRY))
    result = validate_inference_request(req, observed_at=FIXTURE_CLOCK)
    assert result["reason_code"] == REFUSED_STALE_APPROVAL


def test_missing_iam_refusal() -> None:
    req = request_from_fixture(_req(operator_ref="bob"))
    result = validate_inference_request(req, observed_at=FIXTURE_CLOCK)
    assert result["reason_code"] == REFUSED_MISSING_IAM


def test_missing_tim_refusal() -> None:
    req = request_from_fixture(_req(freshness_ref="tim:missing"))
    result = validate_inference_request(req, observed_at=FIXTURE_CLOCK)
    assert result["reason_code"] == REFUSED_MISSING_TIM_FRESHNESS


def test_missing_gpp_refusal() -> None:
    req = request_from_fixture(_req(requires_gpp=True))
    result = validate_inference_request(req, observed_at=FIXTURE_CLOCK)
    assert result["reason_code"] == REFUSED_MISSING_GPP_PERMIT


def test_missing_ueak_refusal() -> None:
    req = request_from_fixture(_req(requires_ueak=True))
    result = validate_inference_request(req, observed_at=FIXTURE_CLOCK)
    assert result["reason_code"] == REFUSED_MISSING_UEAK_ADMISSION


def test_no_model_download_without_approval() -> None:
    bundle = next(b for b in load_infer_fixtures() if b["bundle_id"] == "infer-model-download")
    result = process_infer_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["reason_code"] == REFUSED_MODEL_DOWNLOAD


def test_no_live_backend_call_in_dry_run() -> None:
    req = request_from_fixture(_req(dry_run=True))
    hw = detect_hardware_profile(fixture={"profile_id": "t", "igpu_available": True, "ram_gb": 32, "meets_minimum_profile": True})
    result = run_dry_run_inference(req, hw, observed_at=FIXTURE_CLOCK)
    assert result["reason_code"] == INFER_DRY_RUN_COMPLETE
    assert result["live_backend_called"] is False


def test_live_backend_refused_when_dry_run_off() -> None:
    bundle = next(b for b in load_infer_fixtures() if b["bundle_id"] == "infer-live-backend-call")
    result = process_infer_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["reason_code"] == REFUSED_LIVE_BACKEND_CALL


def test_model_profile_registry() -> None:
    profile = lookup_model_profile("model:small-default")
    assert profile is not None
    assert profile.tier == "small"


def test_deterministic_replay() -> None:
    bundles = list(load_infer_fixtures()[:6])
    _, h1 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    _, h2 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    assert h1 == h2


def test_runtime_fixture() -> None:
    result = run_inference_runtime_fixture(observed_at=FIXTURE_CLOCK)
    assert result["live_backend_called"] is False
