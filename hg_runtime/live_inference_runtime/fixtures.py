"""INFER-LIVE static fixtures."""

from __future__ import annotations

from typing import Any

from hg_runtime.live_inference_runtime.types import FIXTURE_CLOCK

FUTURE_EXPIRY = "2026-06-15T12:00:00.000000Z"
PAST_EXPIRY = "2026-06-13T12:00:00.000000Z"

INFER_FIXTURE_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "infer-valid-dry-run",
        "hardware_fixture": {
            "profile_id": "infer-hw:igpu-ok",
            "cpu_features": ["x86_64", "AVX2"],
            "igpu_available": True,
            "ram_gb": 32,
            "meets_minimum_profile": True,
        },
        "infer_request": {
            "request_id": "infer-req-valid",
            "organ_ref": "organ:OEF",
            "model_profile_id": "model:small-default",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "dry_run": True,
        },
    },
    {
        "bundle_id": "infer-igpu-profile",
        "hardware_fixture": {
            "profile_id": "infer-hw:igpu",
            "cpu_features": ["x86_64", "AVX2"],
            "igpu_available": True,
            "ram_gb": 32,
            "meets_minimum_profile": True,
        },
        "infer_request": {
            "request_id": "infer-req-igpu",
            "organ_ref": "organ:OEF",
            "model_profile_id": "model:small-default",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "dry_run": True,
        },
    },
    {
        "bundle_id": "infer-cpu-fallback",
        "hardware_fixture": {
            "profile_id": "infer-hw:cpu-only",
            "cpu_features": ["x86_64", "AVX2"],
            "igpu_available": False,
            "ram_gb": 16,
            "meets_minimum_profile": True,
        },
        "infer_request": {
            "request_id": "infer-req-cpu",
            "organ_ref": "organ:DAB",
            "model_profile_id": "model:small-cpu-fallback",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "dry_run": True,
        },
    },
    {
        "bundle_id": "infer-insufficient-hardware",
        "hardware_fixture": {
            "profile_id": "infer-hw:insufficient",
            "cpu_features": ["x86_64"],
            "igpu_available": False,
            "ram_gb": 8,
            "meets_minimum_profile": False,
        },
        "infer_request": {
            "request_id": "infer-req-insufficient",
            "organ_ref": "organ:OEF",
            "model_profile_id": "model:small-default",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "dry_run": True,
        },
    },
    {
        "bundle_id": "infer-cuda-optional",
        "hardware_fixture": {
            "profile_id": "infer-hw:cuda-present",
            "cpu_features": ["x86_64", "AVX2"],
            "igpu_available": True,
            "ram_gb": 32,
            "meets_minimum_profile": True,
            "nvidia_detected": True,
            "nvidia_required": False,
        },
        "infer_request": {
            "request_id": "infer-req-cuda-opt",
            "organ_ref": "organ:OEF",
            "model_profile_id": "model:small-default",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "dry_run": True,
        },
    },
    {
        "bundle_id": "infer-small-model-low-depth",
        "infer_request": {
            "request_id": "infer-req-small",
            "organ_ref": "organ:BRB",
            "model_profile_id": "model:small-default",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "dry_run": True,
        },
    },
    {
        "bundle_id": "infer-escalation-request",
        "infer_request": {
            "request_id": "infer-req-escalation",
            "organ_ref": "organ:DRB",
            "model_profile_id": "model:medium-escalation",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "escalation_requested": True,
            "dry_run": True,
        },
    },
    {
        "bundle_id": "infer-missing-approval",
        "infer_request": {
            "request_id": "infer-req-no-approval",
            "organ_ref": "organ:OEF",
            "model_profile_id": "model:small-default",
            "operator_ref": None,
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "dry_run": True,
        },
    },
    {
        "bundle_id": "infer-stale-approval",
        "infer_request": {
            "request_id": "infer-req-stale",
            "organ_ref": "organ:OEF",
            "model_profile_id": "model:small-default",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": PAST_EXPIRY,
            "scope": "approve_change",
            "dry_run": True,
        },
    },
    {
        "bundle_id": "infer-missing-iam",
        "infer_request": {
            "request_id": "infer-req-no-iam",
            "organ_ref": "organ:OEF",
            "model_profile_id": "model:small-default",
            "operator_ref": "bob",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "dry_run": True,
        },
    },
    {
        "bundle_id": "infer-missing-tim",
        "infer_request": {
            "request_id": "infer-req-no-tim",
            "organ_ref": "organ:OEF",
            "model_profile_id": "model:small-default",
            "operator_ref": "op:local",
            "freshness_ref": "tim:missing",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "dry_run": True,
        },
    },
    {
        "bundle_id": "infer-missing-gpp",
        "infer_request": {
            "request_id": "infer-req-no-gpp",
            "organ_ref": "organ:OEF",
            "model_profile_id": "model:small-default",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "requires_gpp": True,
            "dry_run": True,
        },
    },
    {
        "bundle_id": "infer-missing-ueak",
        "infer_request": {
            "request_id": "infer-req-no-ueak",
            "organ_ref": "organ:OEF",
            "model_profile_id": "model:small-default",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "requires_ueak": True,
            "dry_run": True,
        },
    },
    {
        "bundle_id": "infer-model-download",
        "adversarial_signal": "model_download",
        "notes": "download model without approval",
        "infer_request": {
            "request_id": "infer-req-download",
            "organ_ref": "organ:OEF",
            "model_profile_id": "model:small-default",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "model_download_requested": True,
            "operator_approved_download": False,
            "dry_run": True,
        },
    },
    {
        "bundle_id": "infer-inference-as-permission",
        "adversarial_signal": "inference_as_permission",
        "notes": "inference grants execution",
        "infer_request": {
            "request_id": "infer-req-as-perm",
            "organ_ref": "organ:OEF",
            "model_profile_id": "model:small-default",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "dry_run": True,
        },
    },
    {
        "bundle_id": "infer-live-backend-call",
        "adversarial_signal": "live_backend_call",
        "notes": "invoke openvino now live backend call",
        "infer_request": {
            "request_id": "infer-req-live-backend",
            "organ_ref": "organ:OEF",
            "model_profile_id": "model:small-default",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "dry_run": False,
        },
    },
)


def load_infer_fixtures() -> tuple[dict[str, Any], ...]:
    return INFER_FIXTURE_BUNDLES


__all__ = ["FUTURE_EXPIRY", "INFER_FIXTURE_BUNDLES", "PAST_EXPIRY", "load_infer_fixtures"]
