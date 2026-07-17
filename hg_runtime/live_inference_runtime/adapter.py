"""INFER-LIVE dry-run adapter — no live backend calls in test mode."""

from __future__ import annotations

from typing import Any

from hg_core.infer_live.config import infer_dry_run_mode, infer_refuse_live_backend_calls
from hg_core.infer_live.errors import INFER_DRY_RUN_COMPLETE, REFUSED_LIVE_BACKEND_CALL
from hg_core.infer_live.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash, compute_record_hash
from hg_runtime.live_inference_runtime.hardware import select_backend
from hg_runtime.live_inference_runtime.model_registry import lookup_model_profile
from hg_runtime.live_inference_runtime.types import (
    FIXTURE_CLOCK,
    BackendKind,
    HardwareProfile,
    InferenceOutput,
    InferenceRuntimeRequest,
)
from hg_runtime.model_provider_fabric.provider_receipts import (
    ProviderKind,
    ProviderMode,
    ProviderRealityVerdict,
    ProviderStatus,
    build_provider_receipt,
    validate_provider_receipt,
)
from hg_runtime.model_provider_fabric.provider_reality import label_non_cognitive_output
from hg_runtime.runtime_mode import resolve_runtime_mode


def _output_id(request_id: str) -> str:
    digest = canonical_hash({"request_id": request_id, "dry_run": True})
    return f"infer-out-{digest.rsplit(':', 1)[-1][:12]}"


def run_dry_run_inference(
    request: InferenceRuntimeRequest,
    hardware: HardwareProfile,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Fixture dry-run inference — no OpenVINO/vLLM/CUDA backend invocation."""
    if not infer_dry_run_mode() or not request.dry_run:
        if infer_refuse_live_backend_calls():
            return {
                **advisory_only_marker(),
                "status": "refused",
                "reason_code": REFUSED_LIVE_BACKEND_CALL,
                "live_backend_called": False,
                "request_id": request.request_id,
            }

    profile = lookup_model_profile(request.model_profile_id)
    preferred: BackendKind = profile.preferred_backend if profile else "openvino_cpu"
    backend = select_backend(hardware, preferred=preferred)

    structured = {
        "proposal": f"dry-run inference for {request.organ_ref}",
        "model_profile_id": request.model_profile_id,
        "backend_selected": backend,
        "is_permit": False,
        "permission_granted": False,
        "authority_created": False,
    }

    output = InferenceOutput(
        output_id=_output_id(request.request_id),
        request_id=request.request_id,
        structured_value=structured,
        backend_used=backend,
        model_profile_id=request.model_profile_id,
        dry_run=True,
    )

    output_payload = output.to_payload()
    structured_text = str(structured.get("proposal", ""))
    if not structured_text.strip():
        receipt = build_provider_receipt(
            provider_id="dry_run_adapter",
            provider_kind=ProviderKind.STUB,
            provider_mode=ProviderMode.DRY_RUN,
            role=request.organ_ref or "INFERENCE",
            request_hash=compute_record_hash({"request_id": request.request_id}),
            config_hash=compute_record_hash({"dry_run": True}),
            runtime_mode=resolve_runtime_mode().runtime_mode.value,
            cognitive_soak_active=False,
            dry_run=True,
            fixture_mode=False,
            status=ProviderStatus.UNAVAILABLE,
            verdict=ProviderRealityVerdict.RED_PROVIDER_EMPTY_OUTPUT,
            error="empty dry-run output",
        )
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "RED_PROVIDER_EMPTY_OUTPUT",
            "provider_receipt": receipt.to_payload(),
            "counts_as_cognition": False,
            "request_id": request.request_id,
        }

    mode_receipt = resolve_runtime_mode()
    receipt = build_provider_receipt(
        provider_id="dry_run_adapter",
        provider_kind=ProviderKind.LOCAL_OPENVINO,
        provider_mode=ProviderMode.DRY_RUN,
        role=request.organ_ref or "INFERENCE",
        request_hash=compute_record_hash({"request_id": request.request_id}),
        config_hash=compute_record_hash({"dry_run": True}),
        runtime_mode=mode_receipt.runtime_mode.value,
        cognitive_soak_active=mode_receipt.cognitive_soak_active,
        dry_run=True,
        fixture_mode=mode_receipt.fixture_allowed,
        status=ProviderStatus.AVAILABLE,
        verdict=ProviderRealityVerdict.YELLOW_PROVIDER_DRY_RUN_LABELLED,
        response_hash=compute_record_hash(output_payload),
        output_bytes=len(structured_text.encode("utf-8")),
    )
    validate_provider_receipt(receipt)

    result = {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": INFER_DRY_RUN_COMPLETE,
        "output": output_payload,
        "backend_used": backend,
        "live_backend_called": False,
        "dry_run": True,
        "permission_granted": False,
        "observed_at": observed_at,
        "provider_receipt": receipt.to_payload(),
        "counts_as_cognition": False,
    }
    return label_non_cognitive_output(receipt, result)


__all__ = ["run_dry_run_inference"]
